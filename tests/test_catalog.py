"""Integration tests for catalog endpoints (Phase 4).

Tests cover:
  - CATL-01: POST /books (create with all metadata)
  - CATL-02: PUT /books/{id} (edit book details)
  - CATL-03: DELETE /books/{id} (delete book)
  - CATL-04: PATCH /books/{id}/stock (update stock quantity)
  - CATL-05: POST /genres, GET /genres (genre taxonomy)
"""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.repository import UserRepository


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Authorization headers with valid bearer token."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="catalog_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "catalog_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return Authorization headers (non-admin)."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="catalog_user@example.com", hashed_password=hashed)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "catalog_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# CATL-05: Genre taxonomy
# ---------------------------------------------------------------------------


async def test_create_genre(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can create a genre; it returns 201 with id and name."""
    resp = await client.post("/genres", json={"name": "Fantasy"}, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Fantasy"
    assert "id" in data


async def test_list_genres_public(client: AsyncClient, admin_headers: dict) -> None:
    """GET /genres is public; returns list including created genre."""
    await client.post(
        "/genres", json={"name": "Science Fiction"}, headers=admin_headers
    )
    resp = await client.get("/genres")
    assert resp.status_code == 200
    names = [g["name"] for g in resp.json()]
    assert "Science Fiction" in names


async def test_create_genre_duplicate_returns_409(
    client: AsyncClient, admin_headers: dict
) -> None:
    """Duplicate genre name returns 409 with GENRE_CONFLICT code."""
    await client.post("/genres", json={"name": "Mystery"}, headers=admin_headers)
    resp = await client.post("/genres", json={"name": "Mystery"}, headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "GENRE_CONFLICT"


async def test_create_genre_requires_admin(
    client: AsyncClient, user_headers: dict
) -> None:
    """Non-admin users cannot create genres (403)."""
    resp = await client.post("/genres", json={"name": "Thriller"}, headers=user_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# CATL-01: Create book
# ---------------------------------------------------------------------------


async def test_create_book_minimal(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can create a book with only required fields; stock defaults to 0."""
    resp = await client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "price": "15.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert float(data["price"]) == 15.99
    assert data["stock_quantity"] == 0
    assert data["isbn"] is None
    assert data["genre_id"] is None
    assert "id" in data


async def test_create_book_all_fields(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can create a book with all optional fields including valid ISBN-13."""
    # First create a genre
    genre_resp = await client.post(
        "/genres", json={"name": "Classic"}, headers=admin_headers
    )
    genre_id = genre_resp.json()["id"]

    resp = await client.post(
        "/books",
        json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "price": "12.50",
            "isbn": "9780743273565",
            "genre_id": genre_id,
            "description": "A novel set in the Jazz Age.",
            "cover_image_url": "https://example.com/gatsby.jpg",
            "publish_date": "1925-04-10",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["isbn"] == "9780743273565"
    assert data["genre_id"] == genre_id
    assert data["description"] == "A novel set in the Jazz Age."
    assert data["cover_image_url"] == "https://example.com/gatsby.jpg"
    assert data["publish_date"] == "1925-04-10"


async def test_create_book_invalid_isbn_checksum_returns_422(
    client: AsyncClient, admin_headers: dict
) -> None:
    """Invalid ISBN checksum returns 422 (validation error)."""
    resp = await client.post(
        "/books",
        json={
            "title": "Bad ISBN Book",
            "author": "Author",
            "price": "9.99",
            "isbn": "9780306406158",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


async def test_create_book_duplicate_isbn_returns_409(
    client: AsyncClient, admin_headers: dict
) -> None:
    """Duplicate ISBN returns 409 with BOOK_ISBN_CONFLICT code."""
    payload = {
        "title": "Book A",
        "author": "Author",
        "price": "10.00",
        "isbn": "9780743273565",
    }
    await client.post("/books", json=payload, headers=admin_headers)
    resp = await client.post(
        "/books",
        json={
            "title": "Book B",
            "author": "Author",
            "price": "12.00",
            "isbn": "9780743273565",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "BOOK_ISBN_CONFLICT"


async def test_create_book_requires_admin(
    client: AsyncClient, user_headers: dict
) -> None:
    """Non-admin users cannot create books (403)."""
    resp = await client.post(
        "/books",
        json={"title": "No Permission", "author": "Author", "price": "9.99"},
        headers=user_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /books/{id} (public read)
# ---------------------------------------------------------------------------


async def test_get_book(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books/{id} is public and returns the created book."""
    create_resp = await client.post(
        "/books",
        json={
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "price": "11.99",
        },
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]
    resp = await client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "To Kill a Mockingbird"


async def test_get_book_not_found(client: AsyncClient) -> None:
    """GET /books/{id} for non-existent book returns 404 with BOOK_NOT_FOUND code."""
    resp = await client.get("/books/999999")
    assert resp.status_code == 404
    assert resp.json()["code"] == "BOOK_NOT_FOUND"


# ---------------------------------------------------------------------------
# CATL-02: Edit book
# ---------------------------------------------------------------------------


async def test_update_book(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can update book title and price; GET confirms the changes."""
    create_resp = await client.post(
        "/books",
        json={"title": "Original Title", "author": "Author", "price": "10.00"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]

    resp = await client.put(
        f"/books/{book_id}",
        json={"title": "Updated Title", "price": "14.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert float(data["price"]) == 14.99
    # Author unchanged
    assert data["author"] == "Author"


async def test_update_book_not_found(client: AsyncClient, admin_headers: dict) -> None:
    """PUT /books/{id} for non-existent book returns 404."""
    resp = await client.put(
        "/books/999999",
        json={"title": "Ghost Book"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "BOOK_NOT_FOUND"


async def test_update_book_requires_admin(
    client: AsyncClient, admin_headers: dict, user_headers: dict
) -> None:
    """Non-admin users cannot update books (403)."""
    create_resp = await client.post(
        "/books",
        json={"title": "Protected Book", "author": "Author", "price": "10.00"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]
    resp = await client.put(
        f"/books/{book_id}", json={"title": "Hacked"}, headers=user_headers
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# CATL-03: Delete book
# ---------------------------------------------------------------------------


async def test_delete_book(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can delete a book; subsequent GET returns 404."""
    create_resp = await client.post(
        "/books",
        json={"title": "Doomed Book", "author": "Author", "price": "9.99"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/books/{book_id}", headers=admin_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/books/{book_id}")
    assert get_resp.status_code == 404


async def test_delete_book_not_found(client: AsyncClient, admin_headers: dict) -> None:
    """DELETE /books/{id} for non-existent book returns 404."""
    resp = await client.delete("/books/999999", headers=admin_headers)
    assert resp.status_code == 404


async def test_delete_book_requires_admin(
    client: AsyncClient, admin_headers: dict, user_headers: dict
) -> None:
    """Non-admin users cannot delete books (403)."""
    create_resp = await client.post(
        "/books",
        json={"title": "Undeleteable Book", "author": "Author", "price": "9.99"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]
    resp = await client.delete(f"/books/{book_id}", headers=user_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# CATL-04: Stock management
# ---------------------------------------------------------------------------


async def test_update_stock(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can set stock quantity; GET reflects the updated value."""
    create_resp = await client.post(
        "/books",
        json={"title": "Stocked Book", "author": "Author", "price": "20.00"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]
    assert create_resp.json()["stock_quantity"] == 0

    stock_resp = await client.patch(
        f"/books/{book_id}/stock", json={"quantity": 50}, headers=admin_headers
    )
    assert stock_resp.status_code == 200
    assert stock_resp.json()["stock_quantity"] == 50

    # Verify GET reflects the change
    get_resp = await client.get(f"/books/{book_id}")
    assert get_resp.json()["stock_quantity"] == 50


async def test_update_stock_to_zero(client: AsyncClient, admin_headers: dict) -> None:
    """Admin can set stock to 0 (boundary value)."""
    create_resp = await client.post(
        "/books",
        json={"title": "Zero Stock Book", "author": "Author", "price": "8.99"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]
    await client.patch(
        f"/books/{book_id}/stock", json={"quantity": 10}, headers=admin_headers
    )

    resp = await client.patch(
        f"/books/{book_id}/stock", json={"quantity": 0}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["stock_quantity"] == 0


async def test_update_stock_requires_admin(
    client: AsyncClient, admin_headers: dict, user_headers: dict
) -> None:
    """Non-admin users cannot update stock (403)."""
    create_resp = await client.post(
        "/books",
        json={"title": "Stock Protected", "author": "Author", "price": "9.99"},
        headers=admin_headers,
    )
    book_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/books/{book_id}/stock", json={"quantity": 100}, headers=user_headers
    )
    assert resp.status_code == 403


async def test_update_stock_not_found(client: AsyncClient, admin_headers: dict) -> None:
    """PATCH /books/{id}/stock for non-existent book returns 404."""
    resp = await client.patch(
        "/books/999999/stock", json={"quantity": 5}, headers=admin_headers
    )
    assert resp.status_code == 404
