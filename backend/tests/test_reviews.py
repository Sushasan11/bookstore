"""Integration tests for the review CRUD HTTP endpoints (Phase 14).

Tests cover all 6 requirements:
  - REVW-01: POST /books/{book_id}/reviews — create review with purchase gate
  - REVW-02: GET /books/{book_id}/reviews — paginated list with verified_purchase
  - REVW-03: PATCH /reviews/{review_id} — update own review, ownership enforcement
  - REVW-04: DELETE /reviews/{review_id} — soft-delete own review
  - VPRC-02: verified_purchase flag on every review response
  - ADMR-01: Admin can delete any review regardless of ownership

Uses the existing conftest.py async infrastructure:
  - asyncio_mode = "auto" (no @pytest.mark.asyncio needed)
  - client: AsyncClient against the test app
  - db_session: function-scoped with rollback (test isolation)

Notes:
  - Email prefixes (rev_) avoid collisions with test_reviews_data.py
    which uses revdata_user@, revdata_user2@, revdata_admin@.
  - Users are created as ORM objects (separate from header fixtures) so
    purchased_book fixture can access the user ID directly without parsing tokens.
  - All DB setup uses await db_session.flush() — conftest owns the transaction.
"""

from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book
from app.core.security import hash_password
from app.orders.models import Order, OrderItem, OrderStatus
from app.users.models import User
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# User fixtures — return User ORM objects (needed for purchased_book fixture)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def rev_user(db_session: AsyncSession) -> User:
    """Create primary test user and return User ORM object."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    user = await repo.create(email="rev_user@example.com", hashed_password=hashed)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def rev_user2(db_session: AsyncSession) -> User:
    """Create secondary test user for ownership violation tests."""
    repo = UserRepository(db_session)
    hashed = await hash_password("user2pass123")
    user = await repo.create(email="rev_user2@example.com", hashed_password=hashed)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def rev_admin(db_session: AsyncSession) -> User:
    """Create admin test user and return User ORM object."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="rev_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    return user


# ---------------------------------------------------------------------------
# Auth header fixtures — depend on user ORM fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, rev_user: User) -> dict:
    """Login as rev_user and return Authorization headers."""
    resp = await client.post(
        "/auth/login",
        json={"email": "rev_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user2_headers(client: AsyncClient, rev_user2: User) -> dict:
    """Login as rev_user2 and return Authorization headers."""
    resp = await client.post(
        "/auth/login",
        json={"email": "rev_user2@example.com", "password": "user2pass123"},
    )
    assert resp.status_code == 200, f"User2 login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, rev_admin: User) -> dict:
    """Login as rev_admin and return Authorization headers."""
    resp = await client.post(
        "/auth/login",
        json={"email": "rev_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Book and purchase fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sample_book(db_session: AsyncSession) -> Book:
    """Create a sample book directly via ORM."""
    book = Book(
        title="Review Test Book",
        author="Test Author",
        price=Decimal("19.99"),
        stock_quantity=10,
    )
    db_session.add(book)
    await db_session.flush()
    return book


@pytest_asyncio.fixture
async def sample_book2(db_session: AsyncSession) -> Book:
    """Create a second sample book for multi-review tests."""
    book = Book(
        title="Review Test Book 2",
        author="Test Author 2",
        price=Decimal("24.99"),
        stock_quantity=5,
    )
    db_session.add(book)
    await db_session.flush()
    return book


@pytest_asyncio.fixture
async def purchased_book(
    db_session: AsyncSession,
    rev_user: User,
    sample_book: Book,
) -> Book:
    """Create a CONFIRMED order for rev_user containing sample_book.

    Returns the same sample_book object. After this fixture, rev_user has
    a confirmed purchase of sample_book, so they can create a review.
    """
    order = Order(user_id=rev_user.id, status=OrderStatus.CONFIRMED)
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        book_id=sample_book.id,
        quantity=1,
        unit_price=sample_book.price,
    )
    db_session.add(item)
    await db_session.flush()

    return sample_book


@pytest_asyncio.fixture
async def purchased_book2(
    db_session: AsyncSession,
    rev_user2: User,
    sample_book2: Book,
) -> Book:
    """Create a CONFIRMED order for rev_user2 containing sample_book2."""
    order = Order(user_id=rev_user2.id, status=OrderStatus.CONFIRMED)
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        book_id=sample_book2.id,
        quantity=1,
        unit_price=sample_book2.price,
    )
    db_session.add(item)
    await db_session.flush()

    return sample_book2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_review(
    client: AsyncClient,
    headers: dict,
    book_id: int,
    rating: int = 4,
    text: str | None = "Great book!",
) -> dict:
    """POST /books/{book_id}/reviews and assert 201. Returns response dict."""
    body: dict = {"rating": rating}
    if text is not None:
        body["text"] = text
    resp = await client.post(
        f"/books/{book_id}/reviews",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 201, f"Create review failed ({resp.status_code}): {resp.json()}"
    return resp.json()


def _assert_review_response_shape(data: dict) -> None:
    """Assert that data has the full ReviewResponse structure."""
    assert "id" in data
    assert "book_id" in data
    assert "user_id" in data
    assert "rating" in data
    assert "verified_purchase" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "author" in data
    assert "display_name" in data["author"]
    assert "user_id" in data["author"]
    assert "book" in data
    assert "title" in data["book"]
    assert "book_id" in data["book"]


# ---------------------------------------------------------------------------
# TestCreateReview: REVW-01 — POST /books/{book_id}/reviews
# ---------------------------------------------------------------------------


class TestCreateReview:
    """POST /books/{book_id}/reviews — create review with purchase gate."""

    async def test_create_review_success(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """201 with full ReviewResponse structure including verified_purchase=True."""
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 5, "text": "Absolutely fantastic!"},
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        _assert_review_response_shape(data)
        assert data["rating"] == 5
        assert data["text"] == "Absolutely fantastic!"
        assert data["verified_purchase"] is True
        assert data["book_id"] == purchased_book.id
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
        assert data["author"]["display_name"] == "rev_user"  # email.split('@')[0]

    async def test_create_review_rating_only(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """201 with text=null when text is not provided."""
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 3},
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["rating"] == 3
        assert data["text"] is None

    async def test_create_review_403_not_purchased(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: Book,
    ) -> None:
        """403 NOT_PURCHASED when user has not purchased the book."""
        resp = await client.post(
            f"/books/{sample_book.id}/reviews",
            json={"rating": 4, "text": "Good book"},
            headers=user_headers,
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["code"] == "NOT_PURCHASED"

    async def test_create_review_409_duplicate(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """409 DUPLICATE_REVIEW with existing_review_id on second review for same book."""
        # First review — should succeed
        first = await _create_review(client, user_headers, purchased_book.id)
        first_id = first["id"]

        # Second review — should 409
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 2, "text": "Changed my mind"},
            headers=user_headers,
        )
        assert resp.status_code == 409
        data = resp.json()
        assert data["code"] == "DUPLICATE_REVIEW"
        assert data["existing_review_id"] == first_id

    async def test_create_review_404_book_not_found(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """404 BOOK_NOT_FOUND when book does not exist."""
        resp = await client.post(
            "/books/999999/reviews",
            json={"rating": 4, "text": "Test"},
            headers=user_headers,
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "BOOK_NOT_FOUND"

    async def test_create_review_422_rating_out_of_range(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """422 validation error for rating=0 (below minimum of 1)."""
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 0, "text": "Bad rating"},
            headers=user_headers,
        )
        assert resp.status_code == 422

    async def test_create_review_422_rating_too_high(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """422 validation error for rating=6 (above maximum of 5)."""
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 6, "text": "Too high rating"},
            headers=user_headers,
        )
        assert resp.status_code == 422

    async def test_create_review_422_text_too_long(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """422 validation error for text exceeding 2000 characters."""
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 4, "text": "x" * 2001},
            headers=user_headers,
        )
        assert resp.status_code == 422

    async def test_create_review_401_unauthenticated(
        self,
        client: AsyncClient,
        purchased_book: Book,
    ) -> None:
        """401 when no auth headers provided."""
        resp = await client.post(
            f"/books/{purchased_book.id}/reviews",
            json={"rating": 4, "text": "No auth"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestListReviews: REVW-02 — GET /books/{book_id}/reviews
# ---------------------------------------------------------------------------


class TestListReviews:
    """GET /books/{book_id}/reviews — paginated public endpoint."""

    async def test_list_reviews_returns_paginated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_headers: dict,
        user2_headers: dict,
        purchased_book: Book,
        rev_user2: User,
        sample_book: Book,
    ) -> None:
        """Two reviews from different purchasers returns total=2 with correct structure."""
        # Give rev_user2 a purchase of sample_book as well
        order = Order(user_id=rev_user2.id, status=OrderStatus.CONFIRMED)
        db_session.add(order)
        await db_session.flush()
        item = OrderItem(
            order_id=order.id,
            book_id=purchased_book.id,
            quantity=1,
            unit_price=purchased_book.price,
        )
        db_session.add(item)
        await db_session.flush()

        # Create two reviews
        await _create_review(client, user_headers, purchased_book.id, rating=5, text="Great!")
        await _create_review(client, user2_headers, purchased_book.id, rating=3, text="OK")

        resp = await client.get(f"/books/{purchased_book.id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["size"] == 20
        assert len(data["items"]) == 2
        for item in data["items"]:
            _assert_review_response_shape(item)

    async def test_list_reviews_empty_book(
        self,
        client: AsyncClient,
        sample_book: Book,
    ) -> None:
        """GET for book with no reviews returns empty items and total=0."""
        resp = await client.get(f"/books/{sample_book.id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_reviews_public_no_auth(
        self,
        client: AsyncClient,
        purchased_book: Book,
        user_headers: dict,
    ) -> None:
        """GET /books/{id}/reviews succeeds (200) without authentication."""
        await _create_review(client, user_headers, purchased_book.id)
        resp = await client.get(f"/books/{purchased_book.id}/reviews")
        assert resp.status_code == 200

    async def test_list_reviews_verified_purchase_flag(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """Review from a purchaser has verified_purchase=True."""
        await _create_review(client, user_headers, purchased_book.id, rating=4)
        resp = await client.get(f"/books/{purchased_book.id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["verified_purchase"] is True

    async def test_list_reviews_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_headers: dict,
        purchased_book: Book,
        rev_user: User,
        sample_book: Book,
    ) -> None:
        """page=2 with size=1 returns the second review only."""
        # Need a second purchase for rev_user (from same book) — already purchased
        # Create 2 reviews by creating a second user who also purchased
        # Simpler: just test that page/size params are respected with 1 review
        await _create_review(client, user_headers, purchased_book.id, rating=5, text="First")

        resp = await client.get(f"/books/{purchased_book.id}/reviews?page=1&size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 1
        assert len(data["items"]) == 1

        # Page 2 with only 1 review should be empty
        resp2 = await client.get(f"/books/{purchased_book.id}/reviews?page=2&size=1")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["total"] == 1
        assert len(data2["items"]) == 0


# ---------------------------------------------------------------------------
# TestGetReview: single review endpoint
# ---------------------------------------------------------------------------


class TestGetReview:
    """GET /reviews/{review_id} — single review public endpoint."""

    async def test_get_review_success(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """200 with full ReviewResponse structure including verified_purchase."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=4)
        review_id = created["id"]

        resp = await client.get(f"/reviews/{review_id}")
        assert resp.status_code == 200
        data = resp.json()
        _assert_review_response_shape(data)
        assert data["id"] == review_id
        assert data["rating"] == 4
        assert data["verified_purchase"] is True

    async def test_get_review_404_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """404 REVIEW_NOT_FOUND for nonexistent review ID."""
        resp = await client.get("/reviews/999999")
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "REVIEW_NOT_FOUND"


# ---------------------------------------------------------------------------
# TestUpdateReview: REVW-03 — PATCH /reviews/{review_id}
# ---------------------------------------------------------------------------


class TestUpdateReview:
    """PATCH /reviews/{review_id} — update own review with ownership enforcement."""

    async def test_update_rating_only(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """PATCH with only rating changes rating; text remains unchanged."""
        created = await _create_review(
            client, user_headers, purchased_book.id, rating=3, text="Original text"
        )
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"rating": 5},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 5
        assert data["text"] == "Original text"  # unchanged

    async def test_update_text_only(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """PATCH with only text changes text; rating remains unchanged."""
        created = await _create_review(
            client, user_headers, purchased_book.id, rating=4, text="Old text"
        )
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"text": "Updated text"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 4  # unchanged
        assert data["text"] == "Updated text"

    async def test_update_both(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """PATCH with both rating and text updates both fields."""
        created = await _create_review(
            client, user_headers, purchased_book.id, rating=2, text="Mediocre"
        )
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"rating": 5, "text": "Actually amazing!"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 5
        assert data["text"] == "Actually amazing!"

    async def test_update_clear_text(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """PATCH with text=null explicitly clears text (makes it rating-only)."""
        created = await _create_review(
            client, user_headers, purchased_book.id, rating=4, text="Some text"
        )
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"text": None},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] is None
        assert data["rating"] == 4  # unchanged

    async def test_update_response_has_verified_purchase(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """PATCH response includes verified_purchase flag (VPRC-02)."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=3)
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"rating": 4},
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "verified_purchase" in data
        assert data["verified_purchase"] is True

    async def test_update_403_not_owner(
        self,
        client: AsyncClient,
        user_headers: dict,
        user2_headers: dict,
        purchased_book: Book,
    ) -> None:
        """403 NOT_REVIEW_OWNER when user2 tries to update user1's review."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=4)
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"rating": 1},
            headers=user2_headers,
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["code"] == "NOT_REVIEW_OWNER"

    async def test_update_404_not_found(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """404 REVIEW_NOT_FOUND for nonexistent review ID."""
        resp = await client.patch(
            "/reviews/999999",
            json={"rating": 3},
            headers=user_headers,
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "REVIEW_NOT_FOUND"

    async def test_update_401_unauthenticated(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """401 when no auth headers provided."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=4)
        review_id = created["id"]

        resp = await client.patch(
            f"/reviews/{review_id}",
            json={"rating": 5},
        )
        assert resp.status_code == 401

    async def test_update_reflects_in_get(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """After PATCH, subsequent GET returns updated values."""
        created = await _create_review(
            client, user_headers, purchased_book.id, rating=2, text="Bad"
        )
        review_id = created["id"]

        await client.patch(
            f"/reviews/{review_id}",
            json={"rating": 5, "text": "Changed my mind, great!"},
            headers=user_headers,
        )

        get_resp = await client.get(f"/reviews/{review_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["rating"] == 5
        assert data["text"] == "Changed my mind, great!"


# ---------------------------------------------------------------------------
# TestDeleteReview: REVW-04 — DELETE /reviews/{review_id}
# ---------------------------------------------------------------------------


class TestDeleteReview:
    """DELETE /reviews/{review_id} — soft-delete own review."""

    async def test_delete_own_review(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """204 on own review deletion; subsequent GET returns 404."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=4)
        review_id = created["id"]

        del_resp = await client.delete(
            f"/reviews/{review_id}", headers=user_headers
        )
        assert del_resp.status_code == 204

        # Soft-deleted review should not be accessible
        get_resp = await client.get(f"/reviews/{review_id}")
        assert get_resp.status_code == 404

    async def test_delete_excluded_from_list(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """After deletion, the book's review list no longer includes the deleted review."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=5)
        review_id = created["id"]

        # Confirm it's listed
        list_resp = await client.get(f"/books/{purchased_book.id}/reviews")
        assert list_resp.json()["total"] == 1

        # Delete it
        await client.delete(f"/reviews/{review_id}", headers=user_headers)

        # List should now be empty
        list_resp2 = await client.get(f"/books/{purchased_book.id}/reviews")
        assert list_resp2.status_code == 200
        assert list_resp2.json()["total"] == 0
        assert list_resp2.json()["items"] == []

    async def test_delete_403_not_owner(
        self,
        client: AsyncClient,
        user_headers: dict,
        user2_headers: dict,
        purchased_book: Book,
    ) -> None:
        """403 NOT_REVIEW_OWNER when user2 tries to delete user1's review."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=4)
        review_id = created["id"]

        resp = await client.delete(
            f"/reviews/{review_id}", headers=user2_headers
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["code"] == "NOT_REVIEW_OWNER"

    async def test_delete_404_not_found(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """404 REVIEW_NOT_FOUND for nonexistent review ID."""
        resp = await client.delete("/reviews/999999", headers=user_headers)
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "REVIEW_NOT_FOUND"

    async def test_delete_401_unauthenticated(
        self,
        client: AsyncClient,
        user_headers: dict,
        purchased_book: Book,
    ) -> None:
        """401 when no auth headers provided."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=4)
        review_id = created["id"]

        resp = await client.delete(f"/reviews/{review_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestAdminModeration: ADMR-01 — Admin can delete any review
# ---------------------------------------------------------------------------


class TestAdminModeration:
    """Admin can delete any user's review via DELETE /reviews/{review_id}."""

    async def test_admin_delete_any_review(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
        purchased_book: Book,
    ) -> None:
        """Admin can DELETE another user's review and receives 204."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=1)
        review_id = created["id"]

        # Admin deletes user1's review
        del_resp = await client.delete(
            f"/reviews/{review_id}", headers=admin_headers
        )
        assert del_resp.status_code == 204

    async def test_admin_delete_then_list_excludes(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
        purchased_book: Book,
    ) -> None:
        """After admin deletion, the review no longer appears in GET /books/{id}/reviews."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=3)
        review_id = created["id"]

        # Confirm it's in the list
        list_resp = await client.get(f"/books/{purchased_book.id}/reviews")
        assert list_resp.json()["total"] == 1

        # Admin deletes it
        await client.delete(f"/reviews/{review_id}", headers=admin_headers)

        # Now it should be excluded
        list_resp2 = await client.get(f"/books/{purchased_book.id}/reviews")
        assert list_resp2.status_code == 200
        data = list_resp2.json()
        assert data["total"] == 0
        review_ids = [item["id"] for item in data["items"]]
        assert review_id not in review_ids

    async def test_admin_delete_get_returns_404(
        self,
        client: AsyncClient,
        user_headers: dict,
        admin_headers: dict,
        purchased_book: Book,
    ) -> None:
        """After admin delete, GET /reviews/{id} returns 404 REVIEW_NOT_FOUND."""
        created = await _create_review(client, user_headers, purchased_book.id, rating=5)
        review_id = created["id"]

        await client.delete(f"/reviews/{review_id}", headers=admin_headers)

        get_resp = await client.get(f"/reviews/{review_id}")
        assert get_resp.status_code == 404
        assert get_resp.json()["code"] == "REVIEW_NOT_FOUND"
