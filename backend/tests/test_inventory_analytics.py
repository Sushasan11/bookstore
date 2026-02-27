"""Integration tests for Phase 17 inventory analytics endpoint.

Tests cover:
  - INV-01: GET /admin/analytics/inventory/low-stock auth, threshold filtering,
    ordering, boundary conditions, and response schema.
"""

from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book, Genre
from app.core.security import hash_password
from app.users.repository import UserRepository

LOW_STOCK_URL = "/admin/analytics/inventory/low-stock"
LOGIN_URL = "/auth/login"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Bearer auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="admin_inventory@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "admin_inventory@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return Bearer auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    user = await repo.create(email="user_inventory@example.com", hashed_password=hashed)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "user_inventory@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def stock_books(db_session: AsyncSession) -> list[Book]:
    """Create books with specific stock_quantity values for boundary testing.

    Stock levels:
    - 0:  zero-stock, must sort first, included at any positive threshold
    - 5:  low-stock, below default threshold (10)
    - 10: exactly at default threshold (10), MUST be included (at-or-below)
    - 11: just above default threshold, MUST be excluded
    - 50: well stocked, always excluded at reasonable thresholds
    """
    genre = Genre(name="Inventory Test Genre")
    db_session.add(genre)
    await db_session.flush()

    books = [
        Book(title="Zero Stock Book",   author="Author Z", price=Decimal("10.00"), stock_quantity=0,  genre_id=genre.id),
        Book(title="Low Stock Book",    author="Author L", price=Decimal("10.00"), stock_quantity=5,  genre_id=genre.id),
        Book(title="Threshold Book",    author="Author T", price=Decimal("10.00"), stock_quantity=10, genre_id=genre.id),
        Book(title="Above Threshold",   author="Author A", price=Decimal("10.00"), stock_quantity=11, genre_id=genre.id),
        Book(title="Well Stocked Book", author="Author W", price=Decimal("10.00"), stock_quantity=50, genre_id=genre.id),
    ]
    db_session.add_all(books)
    await db_session.flush()
    return books


# ---------------------------------------------------------------------------
# TestLowStockAuth
# ---------------------------------------------------------------------------


class TestLowStockAuth:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        """GET /inventory/low-stock without token returns 401."""
        resp = await client.get(LOW_STOCK_URL)
        assert resp.status_code == 401

    async def test_requires_admin(self, client: AsyncClient, user_headers: dict) -> None:
        """GET /inventory/low-stock with regular user token returns 403."""
        resp = await client.get(LOW_STOCK_URL, headers=user_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TestLowStockBehavior
# ---------------------------------------------------------------------------


class TestLowStockBehavior:
    async def test_default_threshold_is_10(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Call without ?threshold= — default is 10, returns 3 books (stock 0, 5, 10)."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["threshold"] == 10
        assert data["total_low_stock"] == 3

    async def test_custom_threshold_filters_correctly(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """?threshold=5 returns 2 books (stock 0 and 5; 10, 11, 50 excluded)."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_low_stock"] == 2
        stocks = [item["current_stock"] for item in data["items"]]
        assert all(s <= 5 for s in stocks)

    async def test_book_at_exact_threshold_is_included(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Book with stock_quantity==threshold must be included (tests <= not <)."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 10})
        assert resp.status_code == 200
        data = resp.json()
        titles = [item["title"] for item in data["items"]]
        assert "Threshold Book" in titles, f"Threshold Book (stock=10) should be in results: {titles}"

    async def test_book_above_threshold_excluded(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Book with stock_quantity above threshold must be excluded."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 10})
        assert resp.status_code == 200
        data = resp.json()
        titles = [item["title"] for item in data["items"]]
        assert "Above Threshold" not in titles, f"Above Threshold (stock=11) should NOT be in results: {titles}"
        stocks = [item["current_stock"] for item in data["items"]]
        assert all(s <= 10 for s in stocks)

    async def test_ordered_by_stock_ascending(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Items are ordered by current_stock ascending (smallest first)."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 10})
        assert resp.status_code == 200
        data = resp.json()
        stocks = [item["current_stock"] for item in data["items"]]
        assert stocks == sorted(stocks), f"Items not in ascending order: {stocks}"

    async def test_zero_stock_books_appear_first(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Zero-stock book is first in the list."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["current_stock"] == 0
        assert data["items"][0]["title"] == "Zero Stock Book"

    async def test_threshold_echoed_in_each_item(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Every item in the response echoes the threshold value."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 7})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["threshold"] == 7, f"Expected threshold=7 in item, got: {item}"

    async def test_total_low_stock_count_correct(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """?threshold=20 returns 4 books (stock 0, 5, 10, 11; 50 excluded)."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 20})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_low_stock"] == 4
        assert len(data["items"]) == 4

    async def test_empty_result_when_no_books_below_threshold(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ) -> None:
        """Empty catalog returns 200 with total_low_stock=0 and empty items list."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_low_stock"] == 0
        assert data["items"] == []

    async def test_threshold_zero_returns_only_zero_stock(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """?threshold=0 returns only books with stock_quantity==0."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_low_stock"] == 1
        assert data["items"][0]["current_stock"] == 0

    async def test_negative_threshold_returns_422(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ) -> None:
        """?threshold=-1 returns 422 (ge=0 constraint)."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": -1})
        assert resp.status_code == 422

    async def test_response_schema_fields(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """Response has exactly the expected top-level and item-level fields."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 10})
        assert resp.status_code == 200
        data = resp.json()

        # Top-level keys
        assert set(data.keys()) == {"threshold", "total_low_stock", "items"}

        # Per-item keys
        assert len(data["items"]) > 0
        item = data["items"][0]
        assert set(item.keys()) == {"book_id", "title", "author", "current_stock", "threshold"}

    async def test_large_threshold_returns_all_books(
        self,
        client: AsyncClient,
        admin_headers: dict,
        stock_books: list[Book],
    ) -> None:
        """?threshold=100 returns all 5 books since max stock is 50."""
        resp = await client.get(LOW_STOCK_URL, headers=admin_headers, params={"threshold": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_low_stock"] == 5
        assert len(data["items"]) == 5
