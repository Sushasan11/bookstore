"""Integration tests for cart endpoints (Phase 6).

Tests cover:
  - COMM-01: POST /cart/items (add to cart) and GET /cart
  - COMM-02: PUT /cart/items/{id} (update quantity) and DELETE /cart/items/{id} (remove)

Edge cases:
  - Out-of-stock book (409 CART_BOOK_OUT_OF_STOCK)
  - Nonexistent book (404 BOOK_NOT_FOUND)
  - Duplicate item in cart (409 CART_ITEM_DUPLICATE)
  - Invalid quantity (422)
  - Ownership enforcement — User B cannot modify User A's cart items (403)
  - Cross-session persistence — cart survives logout and re-login

Uses the existing conftest.py async infrastructure:
  - asyncio_mode = "auto" (no @pytest.mark.asyncio needed)
  - client: AsyncClient against the test app
  - db_session: function-scoped with rollback (test isolation)
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
    user = await repo.create(email="cart_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "cart_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return Authorization headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="cart_user@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "cart_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def other_user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a second regular user for ownership enforcement tests."""
    repo = UserRepository(db_session)
    hashed = await hash_password("otherpass123")
    await repo.create(email="cart_other@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "cart_other@example.com", "password": "otherpass123"},
    )
    assert resp.status_code == 200, f"Other user login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def sample_book(client: AsyncClient, admin_headers: dict) -> dict:
    """Create a book with stock > 0 via POST /books and return the book dict."""
    resp = await client.post(
        "/books",
        json={"title": "The Hobbit", "author": "J.R.R. Tolkien", "price": "12.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Book creation failed: {resp.json()}"
    book = resp.json()

    # Set stock to 10 so it can be added to cart
    stock_resp = await client.patch(
        f"/books/{book['id']}/stock",
        json={"quantity": 10},
        headers=admin_headers,
    )
    assert stock_resp.status_code == 200, f"Stock update failed: {stock_resp.json()}"
    return stock_resp.json()


@pytest_asyncio.fixture
async def out_of_stock_book(client: AsyncClient, admin_headers: dict) -> dict:
    """Create a book with stock_quantity=0 via POST /books and return the book dict."""
    resp = await client.post(
        "/books",
        json={"title": "Out of Print Book", "author": "Some Author", "price": "8.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Book creation failed: {resp.json()}"
    # Default stock_quantity is 0, no stock update needed
    return resp.json()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _add_item(
    client: AsyncClient, headers: dict, book_id: int, quantity: int = 1
) -> dict:
    """POST /cart/items and return the response dict. Asserts 201."""
    resp = await client.post(
        "/cart/items",
        json={"book_id": book_id, "quantity": quantity},
        headers=headers,
    )
    assert resp.status_code == 201, (
        f"Add cart item failed ({resp.status_code}): {resp.json()}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# COMM-01: Add books to cart
# ---------------------------------------------------------------------------


async def test_add_item_to_cart(
    client: AsyncClient, user_headers: dict, sample_book: dict
) -> None:
    """POST /cart/items returns 201 with id, book_id, quantity, and embedded book summary."""
    resp = await client.post(
        "/cart/items",
        json={"book_id": sample_book["id"], "quantity": 2},
        headers=user_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["book_id"] == sample_book["id"]
    assert data["quantity"] == 2
    # Embedded book summary
    assert "book" in data
    assert data["book"]["title"] == "The Hobbit"
    assert data["book"]["author"] == "J.R.R. Tolkien"
    assert float(data["book"]["price"]) == 12.99


async def test_get_cart_with_items(
    client: AsyncClient, user_headers: dict, sample_book: dict
) -> None:
    """GET /cart after adding a book returns 200 with correct items, total_items, total_price."""
    await _add_item(client, user_headers, sample_book["id"], quantity=3)

    resp = await client.get("/cart", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == sample_book["id"]
    assert data["items"][0]["quantity"] == 3
    assert data["total_items"] == 3
    # total_price = 12.99 * 3 = 38.97
    assert abs(float(data["total_price"]) - 38.97) < 0.01


async def test_get_cart_empty(client: AsyncClient, user_headers: dict) -> None:
    """GET /cart for a user who has never added anything returns 200 with empty items list."""
    resp = await client.get("/cart", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_items"] == 0
    assert float(data["total_price"]) == 0.0


async def test_get_cart_unauthenticated(client: AsyncClient) -> None:
    """GET /cart without Authorization header returns 401."""
    resp = await client.get("/cart")
    assert resp.status_code == 401


async def test_add_item_out_of_stock(
    client: AsyncClient, user_headers: dict, out_of_stock_book: dict
) -> None:
    """POST /cart/items with an out-of-stock book returns 409 CART_BOOK_OUT_OF_STOCK."""
    resp = await client.post(
        "/cart/items",
        json={"book_id": out_of_stock_book["id"], "quantity": 1},
        headers=user_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CART_BOOK_OUT_OF_STOCK"


async def test_add_item_nonexistent_book(
    client: AsyncClient, user_headers: dict
) -> None:
    """POST /cart/items with nonexistent book_id returns 404 BOOK_NOT_FOUND."""
    resp = await client.post(
        "/cart/items",
        json={"book_id": 999999, "quantity": 1},
        headers=user_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "BOOK_NOT_FOUND"


async def test_add_item_duplicate(
    client: AsyncClient, user_headers: dict, sample_book: dict
) -> None:
    """POST /cart/items twice with the same book returns 409 CART_ITEM_DUPLICATE on second."""
    await _add_item(client, user_headers, sample_book["id"])

    resp = await client.post(
        "/cart/items",
        json={"book_id": sample_book["id"], "quantity": 1},
        headers=user_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CART_ITEM_DUPLICATE"


async def test_add_item_invalid_quantity(
    client: AsyncClient, user_headers: dict, sample_book: dict
) -> None:
    """POST /cart/items with quantity=0 returns 422 validation error (ge=1 constraint)."""
    resp = await client.post(
        "/cart/items",
        json={"book_id": sample_book["id"], "quantity": 0},
        headers=user_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# COMM-02: Update and remove cart items
# ---------------------------------------------------------------------------


async def test_update_item_quantity(
    client: AsyncClient, user_headers: dict, sample_book: dict
) -> None:
    """PUT /cart/items/{id} with a new quantity returns 200 with updated quantity."""
    item = await _add_item(client, user_headers, sample_book["id"], quantity=1)
    item_id = item["id"]

    resp = await client.put(
        f"/cart/items/{item_id}",
        json={"quantity": 5},
        headers=user_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == item_id
    assert data["quantity"] == 5
    assert data["book_id"] == sample_book["id"]


async def test_update_item_not_found(client: AsyncClient, user_headers: dict) -> None:
    """PUT /cart/items/99999 for nonexistent item returns 404 CART_ITEM_NOT_FOUND."""
    resp = await client.put(
        "/cart/items/99999",
        json={"quantity": 5},
        headers=user_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "CART_ITEM_NOT_FOUND"


async def test_update_item_forbidden(
    client: AsyncClient,
    user_headers: dict,
    other_user_headers: dict,
    sample_book: dict,
) -> None:
    """User B cannot update a cart item that belongs to User A — returns 403 CART_ITEM_FORBIDDEN."""
    # User A adds item
    item = await _add_item(client, user_headers, sample_book["id"])
    item_id = item["id"]

    # User B tries to update User A's item
    resp = await client.put(
        f"/cart/items/{item_id}",
        json={"quantity": 99},
        headers=other_user_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "CART_ITEM_FORBIDDEN"


async def test_delete_item(
    client: AsyncClient, user_headers: dict, sample_book: dict
) -> None:
    """DELETE /cart/items/{id} returns 204 and GET /cart shows empty items list."""
    item = await _add_item(client, user_headers, sample_book["id"])
    item_id = item["id"]

    del_resp = await client.delete(f"/cart/items/{item_id}", headers=user_headers)
    assert del_resp.status_code == 204

    # Cart should now be empty
    cart_resp = await client.get("/cart", headers=user_headers)
    assert cart_resp.status_code == 200
    assert cart_resp.json()["items"] == []


async def test_delete_item_not_found(client: AsyncClient, user_headers: dict) -> None:
    """DELETE /cart/items/99999 for nonexistent item returns 404 CART_ITEM_NOT_FOUND."""
    resp = await client.delete("/cart/items/99999", headers=user_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "CART_ITEM_NOT_FOUND"


# ---------------------------------------------------------------------------
# Cross-session persistence
# ---------------------------------------------------------------------------


async def test_cart_persists_across_sessions(
    client: AsyncClient, db_session: AsyncSession, sample_book: dict
) -> None:
    """Cart survives logout and re-login — new token still shows same items."""
    # Register and login as a fresh user
    repo = UserRepository(db_session)
    hashed = await hash_password("persistpass123")
    await repo.create(email="cart_persist@example.com", hashed_password=hashed)
    await db_session.flush()

    login_resp = await client.post(
        "/auth/login",
        json={"email": "cart_persist@example.com", "password": "persistpass123"},
    )
    assert login_resp.status_code == 200
    first_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Add item with first token
    await _add_item(client, first_headers, sample_book["id"], quantity=2)

    # Login again (simulates new session / token refresh)
    login_resp2 = await client.post(
        "/auth/login",
        json={"email": "cart_persist@example.com", "password": "persistpass123"},
    )
    assert login_resp2.status_code == 200
    second_headers = {"Authorization": f"Bearer {login_resp2.json()['access_token']}"}

    # Cart should still have the item with the new token
    cart_resp = await client.get("/cart", headers=second_headers)
    assert cart_resp.status_code == 200
    data = cart_resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["book_id"] == sample_book["id"]
    assert data["items"][0]["quantity"] == 2


# ---------------------------------------------------------------------------
# Computed totals
# ---------------------------------------------------------------------------


async def test_cart_totals_multiple_items(
    client: AsyncClient,
    user_headers: dict,
    admin_headers: dict,
    sample_book: dict,
) -> None:
    """GET /cart with 2 different books correctly sums total_items and total_price."""
    # Create a second book with stock
    resp2 = await client.post(
        "/books",
        json={"title": "Foundation", "author": "Isaac Asimov", "price": "9.99"},
        headers=admin_headers,
    )
    assert resp2.status_code == 201
    book2 = resp2.json()
    await client.patch(
        f"/books/{book2['id']}/stock",
        json={"quantity": 5},
        headers=admin_headers,
    )

    # Add both books: book1 qty=2, book2 qty=3
    await _add_item(client, user_headers, sample_book["id"], quantity=2)
    await _add_item(client, user_headers, book2["id"], quantity=3)

    cart_resp = await client.get("/cart", headers=user_headers)
    assert cart_resp.status_code == 200
    data = cart_resp.json()

    assert len(data["items"]) == 2
    # total_items = 2 + 3 = 5
    assert data["total_items"] == 5
    # total_price = (12.99 * 2) + (9.99 * 3) = 25.98 + 29.97 = 55.95
    expected_total = (12.99 * 2) + (9.99 * 3)
    assert abs(float(data["total_price"]) - expected_total) < 0.02
