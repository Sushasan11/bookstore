"""Integration tests for Phase 16 sales analytics endpoints.

Tests cover:
  - SALES-01/SALES-02: GET /admin/analytics/sales/summary auth, periods, edge cases
  - SALES-03/SALES-04: GET /admin/analytics/sales/top-books auth, sort orderings, limits
"""

from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book, Genre
from app.core.security import hash_password
from app.orders.models import Order, OrderItem, OrderStatus
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

SUMMARY_URL = "/admin/analytics/sales/summary"
TOP_BOOKS_URL = "/admin/analytics/sales/top-books"
LOGIN_URL = "/auth/login"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Bearer auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="admin_analytics@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "admin_analytics@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return Bearer auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    user = await repo.create(email="user_analytics@example.com", hashed_password=hashed)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "user_analytics@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_user_id(db_session: AsyncSession) -> int:
    """Create and return an admin user ID for order ownership."""
    repo = UserRepository(db_session)
    hashed = await hash_password("ordersadminpass")
    user = await repo.create(email="orders_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    return user.id


@pytest_asyncio.fixture
async def sample_books(db_session: AsyncSession) -> list[Book]:
    """Create a Genre and 3 Books with different prices for test data.

    Book A: price 50.00 — expensive book
    Book B: price 10.00 — cheap book
    Book C: price 30.00 — mid-range book
    """
    genre = Genre(name="Test Analytics Genre")
    db_session.add(genre)
    await db_session.flush()

    book_a = Book(
        title="Book A Expensive",
        author="Author A",
        price=Decimal("50.00"),
        stock_quantity=100,
        genre_id=genre.id,
    )
    book_b = Book(
        title="Book B Cheap",
        author="Author B",
        price=Decimal("10.00"),
        stock_quantity=100,
        genre_id=genre.id,
    )
    book_c = Book(
        title="Book C Midrange",
        author="Author C",
        price=Decimal("30.00"),
        stock_quantity=100,
        genre_id=genre.id,
    )
    db_session.add_all([book_a, book_b, book_c])
    await db_session.flush()
    return [book_a, book_b, book_c]


async def _create_confirmed_order(
    db_session: AsyncSession,
    user_id: int,
    items: list[dict],
) -> Order:
    """Create a CONFIRMED Order with the given OrderItems and flush.

    Each item dict must have: book_id (int), quantity (int), unit_price (Decimal).
    """
    order = Order(user_id=user_id, status=OrderStatus.CONFIRMED)
    db_session.add(order)
    await db_session.flush()

    for item in items:
        order_item = OrderItem(
            order_id=order.id,
            book_id=item["book_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
        )
        db_session.add(order_item)

    await db_session.flush()
    return order


# ---------------------------------------------------------------------------
# TestSalesSummaryAuth
# ---------------------------------------------------------------------------


class TestSalesSummaryAuth:
    async def test_summary_requires_auth(self, client: AsyncClient) -> None:
        """GET /admin/analytics/sales/summary without token returns 401."""
        resp = await client.get(SUMMARY_URL)
        assert resp.status_code == 401

    async def test_summary_requires_admin(
        self, client: AsyncClient, user_headers: dict
    ) -> None:
        """GET /admin/analytics/sales/summary with regular user token returns 403."""
        resp = await client.get(SUMMARY_URL, headers=user_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TestSalesSummary
# ---------------------------------------------------------------------------


class TestSalesSummary:
    async def test_summary_default_period_today(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET without period param returns period='today'."""
        resp = await client.get(SUMMARY_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "today"

    async def test_summary_zero_orders(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET when no orders exist returns zero-value response."""
        resp = await client.get(SUMMARY_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["revenue"] == 0.0
        assert data["order_count"] == 0
        assert data["aov"] == 0.0
        assert data["delta_percentage"] is None

    async def test_summary_with_confirmed_orders(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
        sample_books: list[Book],
    ) -> None:
        """Create a confirmed order and verify revenue, order_count, aov are correct."""
        book_a = sample_books[0]
        await _create_confirmed_order(
            db_session,
            admin_user_id,
            [
                {"book_id": book_a.id, "quantity": 2, "unit_price": Decimal("50.00")},
            ],
        )

        resp = await client.get(f"{SUMMARY_URL}?period=today", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # 2 units * 50.00 = 100.00
        assert data["revenue"] == 100.0
        assert data["order_count"] == 1
        assert data["aov"] == 100.0

    async def test_summary_excludes_payment_failed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
        sample_books: list[Book],
    ) -> None:
        """Revenue counts only CONFIRMED orders, not PAYMENT_FAILED."""
        book_a = sample_books[0]

        # Create one CONFIRMED order: 1 * 50.00 = 50.00
        confirmed_order = Order(user_id=admin_user_id, status=OrderStatus.CONFIRMED)
        db_session.add(confirmed_order)
        await db_session.flush()
        db_session.add(
            OrderItem(
                order_id=confirmed_order.id,
                book_id=book_a.id,
                quantity=1,
                unit_price=Decimal("50.00"),
            )
        )

        # Create one PAYMENT_FAILED order: 3 * 50.00 = 150.00 — should NOT be counted
        failed_order = Order(user_id=admin_user_id, status=OrderStatus.PAYMENT_FAILED)
        db_session.add(failed_order)
        await db_session.flush()
        db_session.add(
            OrderItem(
                order_id=failed_order.id,
                book_id=book_a.id,
                quantity=3,
                unit_price=Decimal("50.00"),
            )
        )
        await db_session.flush()

        resp = await client.get(f"{SUMMARY_URL}?period=today", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only the confirmed order should count
        assert data["revenue"] == 50.0
        assert data["order_count"] == 1

    async def test_summary_invalid_period_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET with ?period=year returns 422 (invalid pattern)."""
        resp = await client.get(f"{SUMMARY_URL}?period=year", headers=admin_headers)
        assert resp.status_code == 422

    async def test_summary_week_period(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET with ?period=week returns period='week' with valid response structure."""
        resp = await client.get(f"{SUMMARY_URL}?period=week", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "week"
        assert "revenue" in data
        assert "order_count" in data
        assert "aov" in data
        assert "delta_percentage" in data

    async def test_summary_month_period(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET with ?period=month returns period='month' with valid response structure."""
        resp = await client.get(f"{SUMMARY_URL}?period=month", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "month"
        assert "revenue" in data
        assert "order_count" in data
        assert "aov" in data
        assert "delta_percentage" in data


# ---------------------------------------------------------------------------
# TestTopBooksAuth
# ---------------------------------------------------------------------------


class TestTopBooksAuth:
    async def test_top_books_requires_auth(self, client: AsyncClient) -> None:
        """GET /admin/analytics/sales/top-books without token returns 401."""
        resp = await client.get(TOP_BOOKS_URL)
        assert resp.status_code == 401

    async def test_top_books_requires_admin(
        self, client: AsyncClient, user_headers: dict
    ) -> None:
        """GET /admin/analytics/sales/top-books with regular user token returns 403."""
        resp = await client.get(TOP_BOOKS_URL, headers=user_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TestTopBooks
# ---------------------------------------------------------------------------


class TestTopBooks:
    async def test_top_books_by_revenue(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
        sample_books: list[Book],
    ) -> None:
        """sort_by=revenue ranks books by total_revenue descending.

        Test data:
          Book A: 2 units * 50.00 = revenue 100.00, volume 2
          Book B: 8 units * 10.00 = revenue  80.00, volume 8
          Book C: 3 units * 30.00 = revenue  90.00, volume 3
        Revenue order: A (100), C (90), B (80).
        """
        book_a, book_b, book_c = sample_books
        await _create_confirmed_order(
            db_session,
            admin_user_id,
            [
                {"book_id": book_a.id, "quantity": 2, "unit_price": Decimal("50.00")},
                {"book_id": book_b.id, "quantity": 8, "unit_price": Decimal("10.00")},
                {"book_id": book_c.id, "quantity": 3, "unit_price": Decimal("30.00")},
            ],
        )

        resp = await client.get(
            f"{TOP_BOOKS_URL}?sort_by=revenue", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sort_by"] == "revenue"
        items = data["items"]
        assert len(items) >= 3

        # Verify schema fields on each item
        for item in items:
            assert "book_id" in item
            assert "title" in item
            assert "author" in item
            assert "total_revenue" in item
            assert "units_sold" in item

        # Verify revenue ordering: A first, then C, then B
        book_ids = [item["book_id"] for item in items[:3]]
        assert book_ids[0] == book_a.id, f"Expected book_a first by revenue, got: {items}"
        assert book_ids[1] == book_c.id, f"Expected book_c second by revenue, got: {items}"
        assert book_ids[2] == book_b.id, f"Expected book_b third by revenue, got: {items}"

    async def test_top_books_by_volume(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
        sample_books: list[Book],
    ) -> None:
        """sort_by=volume ranks books by units_sold descending — distinct from revenue.

        Test data:
          Book A: 2 units * 50.00 = revenue 100.00, volume 2
          Book B: 8 units * 10.00 = revenue  80.00, volume 8
          Book C: 3 units * 30.00 = revenue  90.00, volume 3
        Volume order: B (8), C (3), A (2) — different from revenue order (A, C, B).
        """
        book_a, book_b, book_c = sample_books
        await _create_confirmed_order(
            db_session,
            admin_user_id,
            [
                {"book_id": book_a.id, "quantity": 2, "unit_price": Decimal("50.00")},
                {"book_id": book_b.id, "quantity": 8, "unit_price": Decimal("10.00")},
                {"book_id": book_c.id, "quantity": 3, "unit_price": Decimal("30.00")},
            ],
        )

        resp = await client.get(
            f"{TOP_BOOKS_URL}?sort_by=volume", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sort_by"] == "volume"
        items = data["items"]
        assert len(items) >= 3

        # Verify volume ordering: B first, then C, then A
        book_ids = [item["book_id"] for item in items[:3]]
        assert book_ids[0] == book_b.id, f"Expected book_b first by volume, got: {items}"
        assert book_ids[1] == book_c.id, f"Expected book_c second by volume, got: {items}"
        assert book_ids[2] == book_a.id, f"Expected book_a third by volume, got: {items}"

    async def test_top_books_default_limit(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
    ) -> None:
        """Without limit param, returns at most 10 results."""
        # Create a genre and 12 distinct books, each with one order
        genre = Genre(name="Default Limit Genre")
        db_session.add(genre)
        await db_session.flush()

        books = []
        for i in range(12):
            book = Book(
                title=f"Limit Test Book {i}",
                author=f"Author {i}",
                price=Decimal("10.00"),
                stock_quantity=10,
                genre_id=genre.id,
            )
            db_session.add(book)
            books.append(book)
        await db_session.flush()

        order = Order(user_id=admin_user_id, status=OrderStatus.CONFIRMED)
        db_session.add(order)
        await db_session.flush()
        for book in books:
            db_session.add(
                OrderItem(
                    order_id=order.id,
                    book_id=book.id,
                    quantity=1,
                    unit_price=Decimal("10.00"),
                )
            )
        await db_session.flush()

        resp = await client.get(TOP_BOOKS_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 10

    async def test_top_books_custom_limit(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
        sample_books: list[Book],
    ) -> None:
        """?limit=2 returns exactly 2 results when more are available."""
        book_a, book_b, book_c = sample_books
        await _create_confirmed_order(
            db_session,
            admin_user_id,
            [
                {"book_id": book_a.id, "quantity": 1, "unit_price": Decimal("50.00")},
                {"book_id": book_b.id, "quantity": 2, "unit_price": Decimal("10.00")},
                {"book_id": book_c.id, "quantity": 3, "unit_price": Decimal("30.00")},
            ],
        )

        resp = await client.get(f"{TOP_BOOKS_URL}?limit=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

    async def test_top_books_limit_max_50(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """?limit=100 returns 422 — exceeds max limit of 50."""
        resp = await client.get(f"{TOP_BOOKS_URL}?limit=100", headers=admin_headers)
        assert resp.status_code == 422

    async def test_top_books_excludes_payment_failed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        admin_user_id: int,
        sample_books: list[Book],
    ) -> None:
        """PAYMENT_FAILED orders are not counted in top-books rankings."""
        book_a = sample_books[0]

        # Only a PAYMENT_FAILED order
        failed_order = Order(user_id=admin_user_id, status=OrderStatus.PAYMENT_FAILED)
        db_session.add(failed_order)
        await db_session.flush()
        db_session.add(
            OrderItem(
                order_id=failed_order.id,
                book_id=book_a.id,
                quantity=5,
                unit_price=Decimal("50.00"),
            )
        )
        await db_session.flush()

        resp = await client.get(
            f"{TOP_BOOKS_URL}?sort_by=revenue", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # book_a should not appear since it only has payment_failed orders
        book_ids_in_result = [item["book_id"] for item in data["items"]]
        assert book_a.id not in book_ids_in_result

    async def test_top_books_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """No orders at all returns empty items list."""
        resp = await client.get(
            f"{TOP_BOOKS_URL}?sort_by=revenue", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sort_by"] == "revenue"
        assert data["items"] == []

    async def test_top_books_invalid_sort_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET with ?sort_by=rating returns 422 (invalid pattern)."""
        resp = await client.get(
            f"{TOP_BOOKS_URL}?sort_by=rating", headers=admin_headers
        )
        assert resp.status_code == 422
