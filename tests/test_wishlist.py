"""Integration tests for the wishlist feature (Phase 8).

Tests cover:
  - ENGM-01: POST /wishlist (add book), DELETE /wishlist/{book_id} (remove)
  - ENGM-02: GET /wishlist (view wishlist with book details including stock_quantity)

Edge cases:
  - Duplicate book on wishlist (409 WISHLIST_ITEM_DUPLICATE)
  - Nonexistent book (404 BOOK_NOT_FOUND)
  - Item not on wishlist for delete (404 WISHLIST_ITEM_NOT_FOUND)
  - Unauthenticated access to all endpoints (401)
  - User isolation — User A's wishlist invisible to User B

Uses the existing conftest.py async infrastructure:
  - asyncio_mode = "auto" (no @pytest.mark.asyncio needed)
  - client: AsyncClient against the test app
  - db_session: function-scoped with rollback (test isolation)

Notes:
  - Module-specific email prefixes (wishlist_admin@, wishlist_user@, wishlist_user2@)
    avoid collisions with other test modules sharing the same test DB schema.
  - GET /wishlist items are ordered by added_at descending (most recent first).
  - BookSummary includes stock_quantity to show current stock visibility.
"""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Authorization headers with a valid bearer token."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="wishlist_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "wishlist_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return Authorization headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="wishlist_user@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "wishlist_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user2_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a second regular user for user isolation tests."""
    repo = UserRepository(db_session)
    hashed = await hash_password("user2pass123")
    await repo.create(email="wishlist_user2@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "wishlist_user2@example.com", "password": "user2pass123"},
    )
    assert resp.status_code == 200, f"User2 login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def sample_book(client: AsyncClient, admin_headers: dict) -> dict:
    """Create a test book via POST /books and return the book dict."""
    resp = await client.post(
        "/books",
        json={"title": "The Lord of the Rings", "author": "J.R.R. Tolkien", "price": "24.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Book creation failed: {resp.json()}"
    return resp.json()


@pytest_asyncio.fixture
async def sample_book2(client: AsyncClient, admin_headers: dict) -> dict:
    """Create a second test book for multi-item list and ordering tests."""
    resp = await client.post(
        "/books",
        json={"title": "Neuromancer", "author": "William Gibson", "price": "14.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Book2 creation failed: {resp.json()}"
    return resp.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _add_to_wishlist(
    client: AsyncClient, headers: dict, book_id: int
) -> dict:
    """POST /wishlist and return the response dict. Asserts 201."""
    resp = await client.post(
        "/wishlist",
        json={"book_id": book_id},
        headers=headers,
    )
    assert resp.status_code == 201, (
        f"Add to wishlist failed ({resp.status_code}): {resp.json()}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# TestAddToWishlist: ENGM-01 — add a book to the wishlist
# ---------------------------------------------------------------------------


class TestAddToWishlist:
    """POST /wishlist — add a book to the authenticated user's wishlist."""

    async def test_add_book_returns_201_with_structure(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
    ) -> None:
        """POST /wishlist returns 201 with id, book_id, added_at, and embedded book details."""
        resp = await client.post(
            "/wishlist",
            json={"book_id": sample_book["id"]},
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()

        # Top-level fields
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["book_id"] == sample_book["id"]
        assert "added_at" in data

        # Embedded book summary
        assert "book" in data
        book = data["book"]
        assert book["id"] == sample_book["id"]
        assert book["title"] == "The Lord of the Rings"
        assert book["author"] == "J.R.R. Tolkien"
        assert abs(float(book["price"]) - 24.99) < 0.01
        # stock_quantity must be present in book summary (ENGM-02 success criteria)
        assert "stock_quantity" in book
        assert isinstance(book["stock_quantity"], int)
        # cover_image_url may be None but must be present
        assert "cover_image_url" in book

    async def test_add_duplicate_book_returns_409(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
    ) -> None:
        """POST /wishlist twice with the same book returns 409 WISHLIST_ITEM_DUPLICATE."""
        # First add succeeds
        await _add_to_wishlist(client, user_headers, sample_book["id"])

        # Second add is a duplicate
        resp = await client.post(
            "/wishlist",
            json={"book_id": sample_book["id"]},
            headers=user_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "WISHLIST_ITEM_DUPLICATE"

    async def test_add_nonexistent_book_returns_404(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """POST /wishlist with a nonexistent book_id returns 404 BOOK_NOT_FOUND."""
        resp = await client.post(
            "/wishlist",
            json={"book_id": 999999},
            headers=user_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "BOOK_NOT_FOUND"

    async def test_add_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        sample_book: dict,
    ) -> None:
        """POST /wishlist without Authorization header returns 401."""
        resp = await client.post(
            "/wishlist",
            json={"book_id": sample_book["id"]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestViewWishlist: ENGM-02 — view the wishlist
# ---------------------------------------------------------------------------


class TestViewWishlist:
    """GET /wishlist — retrieve the authenticated user's wishlist."""

    async def test_get_wishlist_with_items(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
    ) -> None:
        """GET /wishlist returns 200 with items list and book details including stock_quantity."""
        await _add_to_wishlist(client, user_headers, sample_book["id"])

        resp = await client.get("/wishlist", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["book_id"] == sample_book["id"]
        assert "added_at" in item
        assert "book" in item
        book = item["book"]
        assert book["title"] == "The Lord of the Rings"
        assert book["author"] == "J.R.R. Tolkien"
        # stock_quantity must be in book summary (success criteria)
        assert "stock_quantity" in book
        assert isinstance(book["stock_quantity"], int)

    async def test_get_wishlist_empty(
        self,
        client: AsyncClient,
        user_headers: dict,
    ) -> None:
        """GET /wishlist for a user who has never added anything returns 200 with items=[]."""
        resp = await client.get("/wishlist", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_get_wishlist_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """GET /wishlist without Authorization header returns 401."""
        resp = await client.get("/wishlist")
        assert resp.status_code == 401

    async def test_get_wishlist_user_isolation(
        self,
        client: AsyncClient,
        user_headers: dict,
        user2_headers: dict,
        sample_book: dict,
    ) -> None:
        """User B's wishlist is empty even after User A adds a book (user isolation)."""
        # User A adds a book
        await _add_to_wishlist(client, user_headers, sample_book["id"])

        # User B's wishlist must remain empty
        resp = await client.get("/wishlist", headers=user2_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_get_wishlist_ordering_most_recent_first(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
        sample_book2: dict,
    ) -> None:
        """GET /wishlist returns items ordered by added_at descending (most recent first)."""
        # Add book1 first, then book2
        await _add_to_wishlist(client, user_headers, sample_book["id"])
        await _add_to_wishlist(client, user_headers, sample_book2["id"])

        resp = await client.get("/wishlist", headers=user_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2

        # Most recent (sample_book2) should come first
        assert items[0]["book_id"] == sample_book2["id"]
        assert items[1]["book_id"] == sample_book["id"]

    async def test_get_wishlist_multiple_items(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
        sample_book2: dict,
    ) -> None:
        """GET /wishlist with two books returns all items with correct book details."""
        await _add_to_wishlist(client, user_headers, sample_book["id"])
        await _add_to_wishlist(client, user_headers, sample_book2["id"])

        resp = await client.get("/wishlist", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

        # Both books must appear in the response
        book_ids = {item["book_id"] for item in data["items"]}
        assert sample_book["id"] in book_ids
        assert sample_book2["id"] in book_ids


# ---------------------------------------------------------------------------
# TestRemoveFromWishlist: ENGM-01 — remove a book from the wishlist
# ---------------------------------------------------------------------------


class TestRemoveFromWishlist:
    """DELETE /wishlist/{book_id} — remove a book from the authenticated user's wishlist."""

    async def test_remove_book_returns_204(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
    ) -> None:
        """DELETE /wishlist/{book_id} returns 204 and GET /wishlist shows empty list."""
        await _add_to_wishlist(client, user_headers, sample_book["id"])

        del_resp = await client.delete(
            f"/wishlist/{sample_book['id']}", headers=user_headers
        )
        assert del_resp.status_code == 204

        # Wishlist should now be empty
        get_resp = await client.get("/wishlist", headers=user_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["items"] == []

    async def test_remove_not_on_wishlist_returns_404(
        self,
        client: AsyncClient,
        user_headers: dict,
        sample_book: dict,
    ) -> None:
        """DELETE /wishlist/{book_id} for a book not on the wishlist returns 404 WISHLIST_ITEM_NOT_FOUND."""
        resp = await client.delete(
            f"/wishlist/{sample_book['id']}", headers=user_headers
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "WISHLIST_ITEM_NOT_FOUND"

    async def test_remove_unauthenticated_returns_401(
        self,
        client: AsyncClient,
        sample_book: dict,
    ) -> None:
        """DELETE /wishlist/{book_id} without Authorization header returns 401."""
        resp = await client.delete(f"/wishlist/{sample_book['id']}")
        assert resp.status_code == 401
