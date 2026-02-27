"""Integration tests for book price range filtering and sort direction (Phase 21).

Tests cover:
  - CATL-04: min_price / max_price query params on GET /books
  - sort_dir: asc/desc sorting for all sort fields
  - avg_rating sort via left-join subquery against reviews
"""

from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book
from app.core.security import hash_password
from app.reviews.models import Review
from app.users.repository import UserRepository


@pytest_asyncio.fixture
async def admin_headers_books(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Authorization headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="books_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "books_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# TestBookPriceFilterAndSortDir
# ---------------------------------------------------------------------------


class TestBookPriceFilterAndSortDir:
    """Tests for min_price, max_price, sort_dir params and avg_rating sort."""

    async def test_min_price_filter(
        self, client: AsyncClient, admin_headers_books: dict
    ) -> None:
        """GET /books?min_price=10 returns only books priced >= 10."""
        r1 = await client.post(
            "/books",
            json={"title": "Cheap Book", "author": "Author A", "price": "5.00"},
            headers=admin_headers_books,
        )
        r2 = await client.post(
            "/books",
            json={"title": "Expensive Book", "author": "Author B", "price": "15.00"},
            headers=admin_headers_books,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

        resp = await client.get("/books?min_price=10")
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.json()["items"]]
        assert "Expensive Book" in titles
        assert "Cheap Book" not in titles

    async def test_max_price_filter(
        self, client: AsyncClient, admin_headers_books: dict
    ) -> None:
        """GET /books?max_price=10 returns only books priced <= 10."""
        r1 = await client.post(
            "/books",
            json={"title": "Budget Book", "author": "Author C", "price": "5.00"},
            headers=admin_headers_books,
        )
        r2 = await client.post(
            "/books",
            json={"title": "Pricey Book", "author": "Author D", "price": "15.00"},
            headers=admin_headers_books,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

        resp = await client.get("/books?max_price=10")
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.json()["items"]]
        assert "Budget Book" in titles
        assert "Pricey Book" not in titles

    async def test_price_range_filter(
        self, client: AsyncClient, admin_headers_books: dict
    ) -> None:
        """GET /books?min_price=8&max_price=12 returns only books in [$8, $12]."""
        r1 = await client.post(
            "/books",
            json={"title": "Low Price Book", "author": "Author E", "price": "5.00"},
            headers=admin_headers_books,
        )
        r2 = await client.post(
            "/books",
            json={"title": "Mid Price Book", "author": "Author F", "price": "10.00"},
            headers=admin_headers_books,
        )
        r3 = await client.post(
            "/books",
            json={"title": "High Price Book", "author": "Author G", "price": "15.00"},
            headers=admin_headers_books,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r3.status_code == 201

        resp = await client.get("/books?min_price=8&max_price=12")
        assert resp.status_code == 200
        titles = [b["title"] for b in resp.json()["items"]]
        assert "Mid Price Book" in titles
        assert "Low Price Book" not in titles
        assert "High Price Book" not in titles

    async def test_sort_dir_desc(
        self, client: AsyncClient, admin_headers_books: dict
    ) -> None:
        """GET /books?sort=price&sort_dir=desc returns books in descending price order."""
        r1 = await client.post(
            "/books",
            json={"title": "Alpha Book", "author": "Author H", "price": "5.00"},
            headers=admin_headers_books,
        )
        r2 = await client.post(
            "/books",
            json={"title": "Zeta Book", "author": "Author I", "price": "20.00"},
            headers=admin_headers_books,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

        resp = await client.get("/books?sort=price&sort_dir=desc")
        assert resp.status_code == 200
        items = resp.json()["items"]
        titles = [b["title"] for b in items]
        assert "Zeta Book" in titles
        assert "Alpha Book" in titles
        # Zeta (price $20) must appear before Alpha (price $5) in desc order
        zeta_idx = titles.index("Zeta Book")
        alpha_idx = titles.index("Alpha Book")
        assert zeta_idx < alpha_idx, f"Expected Zeta before Alpha, got {titles}"

    async def test_sort_avg_rating(
        self, client: AsyncClient, admin_headers_books: dict, db_session: AsyncSession
    ) -> None:
        """GET /books?sort=avg_rating&sort_dir=desc returns book with higher avg rating first."""
        # Create two books
        r1 = await client.post(
            "/books",
            json={"title": "Highly Rated Book", "author": "Author J", "price": "12.00"},
            headers=admin_headers_books,
        )
        r2 = await client.post(
            "/books",
            json={"title": "Lowly Rated Book", "author": "Author K", "price": "8.00"},
            headers=admin_headers_books,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        book_a_id = r1.json()["id"]
        book_b_id = r2.json()["id"]

        # Get the admin user id (created by admin_headers_books fixture)
        from app.users.repository import UserRepository
        user_repo = UserRepository(db_session)
        admin_user = await user_repo.get_by_email("books_admin@example.com")
        assert admin_user is not None

        # Insert reviews directly via DB — book A avg 4.5, book B avg 2.0
        # We need a second user for the second review on each book
        from app.core.security import hash_password as hp
        hashed2 = await hp("pass123")
        user2 = await user_repo.create(email="reviewer2@example.com", hashed_password=hashed2)
        await db_session.flush()

        review_a1 = Review(user_id=admin_user.id, book_id=book_a_id, rating=5)
        review_a2 = Review(user_id=user2.id, book_id=book_a_id, rating=4)
        review_b1 = Review(user_id=admin_user.id, book_id=book_b_id, rating=2)
        review_b2 = Review(user_id=user2.id, book_id=book_b_id, rating=2)
        db_session.add_all([review_a1, review_a2, review_b1, review_b2])
        await db_session.flush()

        resp = await client.get(
            f"/books?sort=avg_rating&sort_dir=desc&min_price=7&max_price=13"
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        titles = [b["title"] for b in items]
        assert "Highly Rated Book" in titles
        assert "Lowly Rated Book" in titles
        # Highly Rated (avg 4.5) must appear before Lowly Rated (avg 2.0)
        high_idx = titles.index("Highly Rated Book")
        low_idx = titles.index("Lowly Rated Book")
        assert high_idx < low_idx, f"Expected Highly Rated before Lowly Rated, got {titles}"
