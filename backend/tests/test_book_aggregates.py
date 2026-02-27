"""Integration tests for book detail aggregate fields (Phase 15).

Tests cover AGGR-01 (avg_rating) and AGGR-02 (review_count) on GET /books/{id}.
Three success criteria:
  1. avg_rating rounded to 1 decimal, review_count as integer (with reviews)
  2. avg_rating=null, review_count=0 (no reviews)
  3. Post-review-submit reflects updated aggregate immediately
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
# User fixtures — use agg_ prefix to avoid collisions with other test files
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def agg_user(db_session: AsyncSession) -> User:
    """Create primary test user and return User ORM object."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    user = await repo.create(email="agg_user@example.com", hashed_password=hashed)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def agg_user2(db_session: AsyncSession) -> User:
    """Create secondary test user for multi-review avg tests."""
    repo = UserRepository(db_session)
    hashed = await hash_password("user2pass123")
    user = await repo.create(email="agg_user2@example.com", hashed_password=hashed)
    await db_session.flush()
    return user


# ---------------------------------------------------------------------------
# Auth header fixtures — depend on user ORM fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def agg_user_headers(client: AsyncClient, agg_user: User) -> dict:
    """Login as agg_user and return Authorization headers."""
    resp = await client.post(
        "/auth/login",
        json={"email": "agg_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def agg_user2_headers(client: AsyncClient, agg_user2: User) -> dict:
    """Login as agg_user2 and return Authorization headers."""
    resp = await client.post(
        "/auth/login",
        json={"email": "agg_user2@example.com", "password": "user2pass123"},
    )
    assert resp.status_code == 200, f"User2 login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Book and purchase fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def agg_book(db_session: AsyncSession) -> Book:
    """Create a test book for aggregate tests."""
    book = Book(
        title="Aggregate Test Book",
        author="Agg Author",
        price=Decimal("14.99"),
        stock_quantity=5,
    )
    db_session.add(book)
    await db_session.flush()
    return book


@pytest_asyncio.fixture
async def agg_purchased_book(
    db_session: AsyncSession,
    agg_user: User,
    agg_book: Book,
) -> Book:
    """Create a CONFIRMED order for agg_user containing agg_book.

    Returns agg_book. After this fixture, agg_user has a confirmed purchase,
    so they can submit a review.
    """
    order = Order(user_id=agg_user.id, status=OrderStatus.CONFIRMED)
    db_session.add(order)
    await db_session.flush()
    item = OrderItem(
        order_id=order.id,
        book_id=agg_book.id,
        quantity=1,
        unit_price=agg_book.price,
    )
    db_session.add(item)
    await db_session.flush()
    return agg_book


@pytest_asyncio.fixture
async def agg_purchased_book_user2(
    db_session: AsyncSession,
    agg_user2: User,
    agg_book: Book,
) -> Book:
    """Create a CONFIRMED order for agg_user2 containing agg_book.

    Returns agg_book. After this fixture, agg_user2 has a confirmed purchase,
    so they can submit a review.
    """
    order = Order(user_id=agg_user2.id, status=OrderStatus.CONFIRMED)
    db_session.add(order)
    await db_session.flush()
    item = OrderItem(
        order_id=order.id,
        book_id=agg_book.id,
        quantity=1,
        unit_price=agg_book.price,
    )
    db_session.add(item)
    await db_session.flush()
    return agg_book


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBookDetailAggregates:
    """Integration tests for AGGR-01 (avg_rating) and AGGR-02 (review_count)."""

    async def test_no_reviews_returns_null_avg_and_zero_count(
        self, client: AsyncClient, agg_book: Book
    ) -> None:
        """AGGR-02: When no reviews exist, avg_rating is null and review_count is 0."""
        resp = await client.get(f"/books/{agg_book.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] is None
        assert data["review_count"] == 0
        assert data["in_stock"] is True  # existing field still works

    async def test_single_review_returns_exact_rating(
        self,
        client: AsyncClient,
        agg_user_headers: dict,
        agg_purchased_book: Book,
    ) -> None:
        """AGGR-01: Single review returns exact rating as avg_rating."""
        book_id = agg_purchased_book.id

        # Submit review
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 4, "text": "Good book"},
            headers=agg_user_headers,
        )
        assert resp.status_code == 201

        # Check aggregates
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] == 4.0
        assert data["review_count"] == 1

    async def test_multiple_reviews_returns_rounded_avg(
        self,
        client: AsyncClient,
        agg_user_headers: dict,
        agg_user2_headers: dict,
        agg_purchased_book: Book,
        agg_purchased_book_user2: Book,
    ) -> None:
        """AGGR-01: Multiple reviews return correctly computed average."""
        book_id = agg_purchased_book.id

        # Submit review from user1: rating=4
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 4, "text": "Great read"},
            headers=agg_user_headers,
        )
        assert resp.status_code == 201

        # Submit review from user2: rating=5
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 5, "text": "Excellent"},
            headers=agg_user2_headers,
        )
        assert resp.status_code == 201

        # Average of 4 and 5 is 4.5
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] == 4.5
        assert data["review_count"] == 2

    async def test_after_review_submitted_aggregate_reflects_change(
        self,
        client: AsyncClient,
        agg_user_headers: dict,
        agg_purchased_book: Book,
    ) -> None:
        """AGGR-01/AGGR-02: Aggregate reflects new review immediately after submit."""
        book_id = agg_purchased_book.id

        # Before any review: null avg_rating and 0 count
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] is None
        assert data["review_count"] == 0

        # Submit review with rating=3
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 3, "text": "Average book"},
            headers=agg_user_headers,
        )
        assert resp.status_code == 201

        # After review: avg_rating=3.0 and review_count=1
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] == 3.0
        assert data["review_count"] == 1

    async def test_avg_rating_rounds_to_one_decimal(
        self,
        client: AsyncClient,
        agg_user_headers: dict,
        agg_user2_headers: dict,
        agg_purchased_book: Book,
        agg_purchased_book_user2: Book,
    ) -> None:
        """AGGR-01: avg_rating is rounded to 1 decimal place."""
        book_id = agg_purchased_book.id

        # Submit rating=3 from user1
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 3},
            headers=agg_user_headers,
        )
        assert resp.status_code == 201

        # Submit rating=5 from user2
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 5},
            headers=agg_user2_headers,
        )
        assert resp.status_code == 201

        # Average of 3 and 5 is 4.0 (exact, rounded to 1 decimal = 4.0)
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] == 4.0

    async def test_deleted_review_excluded_from_aggregate(
        self,
        client: AsyncClient,
        agg_user_headers: dict,
        agg_user2_headers: dict,
        agg_purchased_book: Book,
        agg_purchased_book_user2: Book,
    ) -> None:
        """AGGR-01/AGGR-02: Soft-deleted reviews are excluded from aggregates."""
        book_id = agg_purchased_book.id

        # Submit rating=2 from user1, save review_id
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 2, "text": "Not great"},
            headers=agg_user_headers,
        )
        assert resp.status_code == 201
        review_id = resp.json()["id"]

        # Submit rating=4 from user2
        resp = await client.post(
            f"/books/{book_id}/reviews",
            json={"rating": 4, "text": "Pretty good"},
            headers=agg_user2_headers,
        )
        assert resp.status_code == 201

        # Before delete: avg_rating=3.0 (average of 2 and 4), review_count=2
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] == 3.0
        assert data["review_count"] == 2

        # Soft-delete user1's review
        resp = await client.delete(
            f"/reviews/{review_id}",
            headers=agg_user_headers,
        )
        assert resp.status_code == 204

        # After delete: only user2's rating=4 remains
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_rating"] == 4.0
        assert data["review_count"] == 1
