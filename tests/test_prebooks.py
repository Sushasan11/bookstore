"""Integration tests for the pre-booking feature (Phase 11).

Tests cover all six PRBK requirements:
  - PRBK-01: POST /prebooks (create pre-booking for out-of-stock book, duplicate rejection)
  - PRBK-02: GET /prebooks (view pre-bookings with book details, user isolation)
  - PRBK-03: DELETE /prebooks/{id} (cancel via soft-delete, re-reservation after cancel)
  - PRBK-04: POST /prebooks rejected with 409 when book is in stock
  - PRBK-05: Status and timestamp tracking (waiting/notified/cancelled + timestamps)
  - PRBK-06: Restock broadcast transitions all waiting pre-bookings to notified atomically

Edge cases covered:
  - Duplicate pre-booking for same book (409 PREBOOK_DUPLICATE)
  - Nonexistent book (404 BOOK_NOT_FOUND)
  - Unauthenticated access (401)
  - In-stock book pre-booking (409 PREBOOK_BOOK_IN_STOCK)
  - Already cancelled pre-booking (409 PREBOOK_ALREADY_CANCELLED)
  - Ownership isolation (cancel other user's booking returns 404)
  - Re-reservation after cancel (partial unique index allows it)
  - Restock of already-in-stock book (no re-notification)
  - Cancelled pre-booking not notified on restock
  - 0->0 stock update (no notification triggered)

Uses the existing conftest.py async infrastructure:
  - asyncio_mode = "auto" (no @pytest.mark.asyncio needed)
  - client: AsyncClient against the test app
  - db_session: function-scoped with rollback (test isolation)

Notes:
  - Module-specific email prefixes (prebook_admin@, prebook_user@, prebook_user2@)
    avoid collisions with other test modules sharing the same test DB schema.
  - GET /prebooks items are ordered by created_at descending (most recent first).
"""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PREBOOKS_URL = "/prebooks"
BOOKS_URL = "/books"
STOCK_URL_TPL = "/books/{book_id}/stock"
LOGIN_URL = "/auth/login"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Authorization headers with a valid bearer token."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="prebook_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        LOGIN_URL,
        json={"email": "prebook_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return Authorization headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="prebook_user@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        LOGIN_URL,
        json={"email": "prebook_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user2_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a second regular user for user isolation tests."""
    repo = UserRepository(db_session)
    hashed = await hash_password("user2pass123")
    await repo.create(email="prebook_user2@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        LOGIN_URL,
        json={"email": "prebook_user2@example.com", "password": "user2pass123"},
    )
    assert resp.status_code == 200, f"User2 login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def out_of_stock_book(client: AsyncClient, admin_headers: dict) -> dict:
    """Create an out-of-stock book via POST /books. Returns the book response dict.

    Books default to stock_quantity=0 so no stock update is needed.
    """
    resp = await client.post(
        BOOKS_URL,
        json={"title": "Out of Stock Book", "author": "Test Author", "price": 19.99},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Book creation failed: {resp.json()}"
    return resp.json()


@pytest_asyncio.fixture
async def in_stock_book(client: AsyncClient, admin_headers: dict) -> dict:
    """Create an in-stock book via POST /books, then set stock to 10. Returns book dict.

    BookCreate does not accept stock_quantity, so we use PATCH /books/{id}/stock
    after creation to set stock > 0.
    """
    resp = await client.post(
        BOOKS_URL,
        json={"title": "In Stock Book", "author": "Test Author", "price": 29.99},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Book creation failed: {resp.json()}"
    book = resp.json()

    # Set stock to 10 so book is "in stock"
    stock_resp = await client.patch(
        STOCK_URL_TPL.format(book_id=book["id"]),
        json={"quantity": 10},
        headers=admin_headers,
    )
    assert stock_resp.status_code == 200, f"Stock update failed: {stock_resp.json()}"
    return stock_resp.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_out_of_stock_book(
    client: AsyncClient, admin_headers: dict, title: str = "OOS Book", price: float = 19.99
) -> dict:
    """Create an out-of-stock book. Returns book response dict.

    Books default to stock_quantity=0 so no stock update needed.
    """
    resp = await client.post(
        BOOKS_URL,
        json={"title": title, "author": "Test Author", "price": price},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# TestCreatePreBooking: PRBK-01, PRBK-04
# ---------------------------------------------------------------------------


class TestCreatePreBooking:
    """POST /prebooks — create a pre-booking for an out-of-stock book."""

    async def test_create_prebook_success(
        self,
        client: AsyncClient,
        user_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """POST /prebooks for an out-of-stock book returns 201 with status=waiting. (PRBK-01)"""
        resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["book_id"] == out_of_stock_book["id"]
        assert data["book_title"] == "Out of Stock Book"
        assert data["book_author"] == "Test Author"
        assert data["status"] == "waiting"
        assert "created_at" in data
        assert data["notified_at"] is None
        assert data["cancelled_at"] is None

    async def test_create_prebook_in_stock_rejected(
        self,
        client: AsyncClient,
        user_headers: dict,
        in_stock_book: dict,
    ) -> None:
        """POST /prebooks for an in-stock book returns 409 PREBOOK_BOOK_IN_STOCK. (PRBK-04)"""
        resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": in_stock_book["id"]},
            headers=user_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "PREBOOK_BOOK_IN_STOCK"

    async def test_create_prebook_duplicate_rejected(
        self,
        client: AsyncClient,
        user_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """POST /prebooks twice for same book: first 201, second 409 PREBOOK_DUPLICATE. (PRBK-01 duplicate guard)"""
        # First pre-booking succeeds
        first_resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert first_resp.status_code == 201

        # Second pre-booking is a duplicate
        second_resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert second_resp.status_code == 409
        assert second_resp.json()["code"] == "PREBOOK_DUPLICATE"

    async def test_create_prebook_nonexistent_book(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """POST /prebooks with a nonexistent book_id returns 404 BOOK_NOT_FOUND."""
        resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": 99999},
            headers=user_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "BOOK_NOT_FOUND"

    async def test_create_prebook_unauthenticated(
        self,
        client: AsyncClient,
        out_of_stock_book: dict,
    ) -> None:
        """POST /prebooks without auth headers returns 401."""
        resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestListPreBookings: PRBK-02, PRBK-05
# ---------------------------------------------------------------------------


class TestListPreBookings:
    """GET /prebooks — list authenticated user's pre-bookings."""

    async def test_list_prebooks_empty(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """GET /prebooks with no pre-bookings returns 200 with empty items list. (PRBK-02)"""
        resp = await client.get(PREBOOKS_URL, headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["items"] == []

    async def test_list_prebooks_with_items(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
    ) -> None:
        """GET /prebooks returns 200 with items containing book details, status=waiting. (PRBK-02, PRBK-05)"""
        # Create two distinct out-of-stock books
        book1 = await _create_out_of_stock_book(client, admin_headers, title="OOS Book Alpha")
        book2 = await _create_out_of_stock_book(client, admin_headers, title="OOS Book Beta")

        # Create pre-bookings for both
        await client.post(PREBOOKS_URL, json={"book_id": book1["id"]}, headers=user_headers)
        await client.post(PREBOOKS_URL, json={"book_id": book2["id"]}, headers=user_headers)

        resp = await client.get(PREBOOKS_URL, headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

        # Validate structure of first item
        item = data["items"][0]
        assert "id" in item
        assert "book_id" in item
        assert "book_title" in item
        assert "book_author" in item
        assert "status" in item
        assert item["status"] == "waiting"
        assert "created_at" in item
        assert item["notified_at"] is None
        assert item["cancelled_at"] is None

        # Both books appear in the result (order may vary at millisecond precision)
        book_ids = {i["book_id"] for i in data["items"]}
        assert book1["id"] in book_ids
        assert book2["id"] in book_ids

    async def test_list_prebooks_user_isolation(
        self,
        client: AsyncClient,
        user_headers: dict,
        user2_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """User 2 sees empty list even after User 1 creates a pre-booking. (PRBK-02 isolation)"""
        # User 1 creates a pre-booking
        resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert resp.status_code == 201

        # User 2 should see nothing
        resp2 = await client.get(PREBOOKS_URL, headers=user2_headers)
        assert resp2.status_code == 200
        assert resp2.json()["items"] == []

    async def test_list_prebooks_shows_all_statuses(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
    ) -> None:
        """GET /prebooks shows both cancelled and waiting items. (PRBK-05 — all statuses visible)"""
        book1 = await _create_out_of_stock_book(client, admin_headers, title="OOS Book For Cancel")
        book2 = await _create_out_of_stock_book(client, admin_headers, title="OOS Book Staying")

        # Create and cancel first pre-booking
        create_resp = await client.post(
            PREBOOKS_URL, json={"book_id": book1["id"]}, headers=user_headers
        )
        assert create_resp.status_code == 201
        prebook_id = create_resp.json()["id"]

        cancel_resp = await client.delete(
            f"{PREBOOKS_URL}/{prebook_id}", headers=user_headers
        )
        assert cancel_resp.status_code == 204

        # Create second pre-booking (waiting)
        await client.post(
            PREBOOKS_URL, json={"book_id": book2["id"]}, headers=user_headers
        )

        resp = await client.get(PREBOOKS_URL, headers=user_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2

        statuses = {item["status"] for item in items}
        assert "cancelled" in statuses
        assert "waiting" in statuses


# ---------------------------------------------------------------------------
# TestCancelPreBooking: PRBK-03
# ---------------------------------------------------------------------------


class TestCancelPreBooking:
    """DELETE /prebooks/{id} — cancel (soft-delete) a pre-booking."""

    async def test_cancel_prebook_success(
        self,
        client: AsyncClient,
        user_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """DELETE /prebooks/{id} returns 204, and GET /prebooks shows status=cancelled. (PRBK-03)"""
        # Create pre-booking
        create_resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert create_resp.status_code == 201
        prebook_id = create_resp.json()["id"]

        # Cancel it
        del_resp = await client.delete(
            f"{PREBOOKS_URL}/{prebook_id}", headers=user_headers
        )
        assert del_resp.status_code == 204

        # Verify status in list
        list_resp = await client.get(PREBOOKS_URL, headers=user_headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "cancelled"
        assert items[0]["cancelled_at"] is not None

    async def test_cancel_prebook_already_cancelled(
        self,
        client: AsyncClient,
        user_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """Cancelling an already-cancelled pre-booking returns 409 PREBOOK_ALREADY_CANCELLED. (PRBK-03 idempotency guard)"""
        # Create and cancel
        create_resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert create_resp.status_code == 201
        prebook_id = create_resp.json()["id"]

        await client.delete(f"{PREBOOKS_URL}/{prebook_id}", headers=user_headers)

        # Cancel again
        second_cancel = await client.delete(
            f"{PREBOOKS_URL}/{prebook_id}", headers=user_headers
        )
        assert second_cancel.status_code == 409
        assert second_cancel.json()["code"] == "PREBOOK_ALREADY_CANCELLED"

    async def test_cancel_prebook_not_found(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """DELETE /prebooks/99999 returns 404. (PRBK-03 edge case)"""
        resp = await client.delete(f"{PREBOOKS_URL}/99999", headers=user_headers)
        assert resp.status_code == 404

    async def test_cancel_prebook_other_user(
        self,
        client: AsyncClient,
        user_headers: dict,
        user2_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """User 2 cannot cancel User 1's pre-booking — returns 404 (ownership, not 403). (PRBK-03 ownership)"""
        # User 1 creates pre-booking
        create_resp = await client.post(
            PREBOOKS_URL,
            json={"book_id": out_of_stock_book["id"]},
            headers=user_headers,
        )
        assert create_resp.status_code == 201
        prebook_id = create_resp.json()["id"]

        # User 2 tries to cancel it — must get 404 (prevents enumeration)
        resp = await client.delete(
            f"{PREBOOKS_URL}/{prebook_id}", headers=user2_headers
        )
        assert resp.status_code == 404

    async def test_rebook_after_cancel(
        self,
        client: AsyncClient,
        user_headers: dict,
        out_of_stock_book: dict,
    ) -> None:
        """Re-reservation after cancel returns 201 — partial unique index allows it. (PRBK-03 + partial unique index)"""
        book_id = out_of_stock_book["id"]

        # Create and cancel
        create_resp = await client.post(
            PREBOOKS_URL, json={"book_id": book_id}, headers=user_headers
        )
        assert create_resp.status_code == 201
        prebook_id = create_resp.json()["id"]

        await client.delete(f"{PREBOOKS_URL}/{prebook_id}", headers=user_headers)

        # Re-book the same book
        rebook_resp = await client.post(
            PREBOOKS_URL, json={"book_id": book_id}, headers=user_headers
        )
        assert rebook_resp.status_code == 201

        # GET /prebooks shows both: cancelled + waiting
        list_resp = await client.get(PREBOOKS_URL, headers=user_headers)
        items = list_resp.json()["items"]
        assert len(items) == 2
        statuses = {item["status"] for item in items}
        assert "cancelled" in statuses
        assert "waiting" in statuses


# ---------------------------------------------------------------------------
# TestRestockNotification: PRBK-06
# ---------------------------------------------------------------------------


class TestRestockNotification:
    """PATCH /books/{id}/stock — restock triggers notification of waiting pre-bookings."""

    async def test_restock_notifies_waiting_prebooks(
        self,
        client: AsyncClient,
        user_headers: dict,
        user2_headers: dict,
        admin_headers: dict,
    ) -> None:
        """Restocking from 0 to >0 sets all waiting pre-bookings to notified with notified_at. (PRBK-06 broadcast)"""
        book = await _create_out_of_stock_book(client, admin_headers, title="Broadcast Restock Book")

        # Both users pre-book the same book
        resp1 = await client.post(
            PREBOOKS_URL, json={"book_id": book["id"]}, headers=user_headers
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            PREBOOKS_URL, json={"book_id": book["id"]}, headers=user2_headers
        )
        assert resp2.status_code == 201

        # Admin restocks
        stock_url = STOCK_URL_TPL.format(book_id=book["id"])
        restock_resp = await client.patch(
            stock_url, json={"quantity": 5}, headers=admin_headers
        )
        assert restock_resp.status_code == 200

        # User 1 sees notified status
        list1 = await client.get(PREBOOKS_URL, headers=user_headers)
        assert list1.status_code == 200
        items1 = list1.json()["items"]
        assert len(items1) == 1
        assert items1[0]["status"] == "notified"
        assert items1[0]["notified_at"] is not None

        # User 2 also sees notified status
        list2 = await client.get(PREBOOKS_URL, headers=user2_headers)
        assert list2.status_code == 200
        items2 = list2.json()["items"]
        assert len(items2) == 1
        assert items2[0]["status"] == "notified"
        assert items2[0]["notified_at"] is not None

    async def test_restock_already_in_stock_no_notification(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
    ) -> None:
        """Restocking from >0 to >0 does not re-notify already-notified pre-bookings. (PRBK-06 — only 0->positive triggers)"""
        book = await _create_out_of_stock_book(client, admin_headers, title="Already In Stock Book")

        # Pre-book and trigger first notification
        create_resp = await client.post(
            PREBOOKS_URL, json={"book_id": book["id"]}, headers=user_headers
        )
        assert create_resp.status_code == 201

        stock_url = STOCK_URL_TPL.format(book_id=book["id"])
        # First restock: 0 -> 5 (should notify)
        await client.patch(stock_url, json={"quantity": 5}, headers=admin_headers)

        # Verify notified
        list_resp = await client.get(PREBOOKS_URL, headers=user_headers)
        assert list_resp.json()["items"][0]["status"] == "notified"
        first_notified_at = list_resp.json()["items"][0]["notified_at"]

        # Second restock: 5 -> 10 (was already >0 — should NOT re-notify)
        await client.patch(stock_url, json={"quantity": 10}, headers=admin_headers)

        # Status should remain "notified" with same notified_at timestamp
        list_resp2 = await client.get(PREBOOKS_URL, headers=user_headers)
        items = list_resp2.json()["items"]
        assert items[0]["status"] == "notified"
        assert items[0]["notified_at"] == first_notified_at

    async def test_restock_does_not_notify_cancelled(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
    ) -> None:
        """Restocking does not change cancelled pre-bookings to notified. (PRBK-06 — only waiting transitions)"""
        book = await _create_out_of_stock_book(client, admin_headers, title="Cancel Before Restock Book")

        # Create and cancel pre-booking
        create_resp = await client.post(
            PREBOOKS_URL, json={"book_id": book["id"]}, headers=user_headers
        )
        assert create_resp.status_code == 201
        prebook_id = create_resp.json()["id"]

        await client.delete(f"{PREBOOKS_URL}/{prebook_id}", headers=user_headers)

        # Admin restocks
        stock_url = STOCK_URL_TPL.format(book_id=book["id"])
        await client.patch(stock_url, json={"quantity": 5}, headers=admin_headers)

        # Status should remain "cancelled"
        list_resp = await client.get(PREBOOKS_URL, headers=user_headers)
        items = list_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "cancelled"
        assert items[0]["notified_at"] is None

    async def test_restock_zero_to_zero_no_notification(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
    ) -> None:
        """Setting stock from 0 to 0 does not trigger notification. (PRBK-06 — 0->0 is not a positive transition)"""
        book = await _create_out_of_stock_book(client, admin_headers, title="Zero To Zero Book")

        # Pre-book the book
        create_resp = await client.post(
            PREBOOKS_URL, json={"book_id": book["id"]}, headers=user_headers
        )
        assert create_resp.status_code == 201

        # Admin sets stock to 0 (still out of stock)
        stock_url = STOCK_URL_TPL.format(book_id=book["id"])
        await client.patch(stock_url, json={"quantity": 0}, headers=admin_headers)

        # Status should remain "waiting"
        list_resp = await client.get(PREBOOKS_URL, headers=user_headers)
        items = list_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "waiting"
        assert items[0]["notified_at"] is None
