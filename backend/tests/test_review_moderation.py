"""Integration tests for Phase 18 review moderation dashboard.

Tests cover:
  - MOD-01: GET /admin/reviews — auth, pagination, filtering, sorting, soft-delete exclusion
  - MOD-02: DELETE /admin/reviews/bulk — auth, best-effort semantics, soft-delete, validation
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book, Genre
from app.core.security import hash_password
from app.reviews.models import Review
from app.users.repository import UserRepository

LIST_URL = "/admin/reviews"
BULK_DELETE_URL = "/admin/reviews/bulk"
LOGIN_URL = "/auth/login"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Bearer auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="revmod_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "revmod_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession):
    """Create a regular user and return (user, headers) tuple."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    user = await repo.create(email="revmod_user@example.com", hashed_password=hashed)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "revmod_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return user, headers


@pytest_asyncio.fixture
async def review_data(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict,
    user_headers,
) -> dict:
    """Create test data for review moderation tests.

    Creates:
    - 1 Genre ("Moderation Test Genre")
    - 2 Books (Book Alpha, Book Beta)
    - 2 non-admin users (revmod_user, revmod_reviewer)
    - 5 reviews with varying ratings (4 active, 1 soft-deleted)
    """
    user1, _ = user_headers

    # Create genre
    genre = Genre(name="Moderation Test Genre")
    db_session.add(genre)
    await db_session.flush()

    # Create 2 books
    book_a = Book(
        title="Book Alpha",
        author="Author A",
        price=Decimal("10.00"),
        stock_quantity=100,
        genre_id=genre.id,
    )
    book_b = Book(
        title="Book Beta",
        author="Author B",
        price=Decimal("20.00"),
        stock_quantity=100,
        genre_id=genre.id,
    )
    db_session.add_all([book_a, book_b])
    await db_session.flush()

    # Create second and third reviewer users
    repo = UserRepository(db_session)
    hashed2 = await hash_password("reviewerpass123")
    user2 = await repo.create(email="revmod_reviewer@example.com", hashed_password=hashed2)
    hashed3 = await hash_password("readerpass123")
    user3 = await repo.create(email="revmod_reader@example.com", hashed_password=hashed3)
    await db_session.flush()

    # Create 5 reviews
    # Review 1: user1, book_a, rating=5
    r1 = Review(user_id=user1.id, book_id=book_a.id, rating=5, text="Excellent")
    # Review 2: user1, book_b, rating=2
    r2 = Review(user_id=user1.id, book_id=book_b.id, rating=2, text="Poor")
    # Review 3: user2, book_a, rating=3
    r3 = Review(user_id=user2.id, book_id=book_a.id, rating=3, text="Average")
    # Review 4: user2, book_b, rating=1 (will be soft-deleted)
    r4 = Review(user_id=user2.id, book_id=book_b.id, rating=1, text="Terrible")
    # Review 5: user3, book_a, rating=4, text=None (rating-only)
    # Note: user3 avoids uq_reviews_user_book conflict (user2 already has r3 on book_a)
    r5 = Review(user_id=user3.id, book_id=book_a.id, rating=4, text=None)

    db_session.add_all([r1, r2, r3, r4, r5])
    await db_session.flush()

    # Soft-delete review 4 directly
    r4.deleted_at = datetime.now(UTC)
    await db_session.flush()

    return {
        "books": [book_a, book_b],
        "users": [user1, user2, user3],
        "reviews": [r1, r2, r3, r4, r5],
        "deleted_review": r4,
    }


# ---------------------------------------------------------------------------
# TestAdminReviewListAuth
# ---------------------------------------------------------------------------


class TestAdminReviewListAuth:
    async def test_list_reviews_requires_auth(self, client: AsyncClient) -> None:
        """GET /admin/reviews without token returns 401."""
        resp = await client.get(LIST_URL)
        assert resp.status_code == 401

    async def test_list_reviews_requires_admin(
        self, client: AsyncClient, user_headers
    ) -> None:
        """GET /admin/reviews with regular user token returns 403."""
        _, headers = user_headers
        resp = await client.get(LIST_URL, headers=headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TestAdminReviewListBasic
# ---------------------------------------------------------------------------


class TestAdminReviewListBasic:
    async def test_list_reviews_returns_all_active(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """GET /admin/reviews returns only active (non-deleted) reviews."""
        resp = await client.get(LIST_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 4
        assert len(data["items"]) == 4

    async def test_soft_deleted_review_excluded(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Soft-deleted review (r4) does not appear in the list."""
        deleted_id = review_data["deleted_review"].id
        resp = await client.get(LIST_URL, headers=admin_headers)
        assert resp.status_code == 200
        item_ids = [item["id"] for item in resp.json()["items"]]
        assert deleted_id not in item_ids

    async def test_response_schema_fields(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Response has all expected envelope and item fields."""
        resp = await client.get(LIST_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        # Envelope fields
        for key in ("items", "total_count", "page", "per_page", "total_pages"):
            assert key in data, f"Missing envelope field: {key}"

        # Item fields
        item = data["items"][0]
        for key in ("id", "rating", "text", "created_at", "updated_at", "author", "book"):
            assert key in item, f"Missing item field: {key}"

        # Nested author fields
        for key in ("user_id", "display_name"):
            assert key in item["author"], f"Missing author field: {key}"

        # Nested book fields
        for key in ("book_id", "title"):
            assert key in item["book"], f"Missing book field: {key}"

    async def test_default_pagination(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Default response uses page=1, per_page=20, total_pages=1."""
        resp = await client.get(LIST_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total_pages"] == 1


# ---------------------------------------------------------------------------
# TestAdminReviewListPagination
# ---------------------------------------------------------------------------


class TestAdminReviewListPagination:
    async def test_pagination_limits_items(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """per_page=2 returns 2 items while total_count stays at 4."""
        resp = await client.get(f"{LIST_URL}?per_page=2&page=1", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 4
        assert data["total_pages"] == 2

    async def test_pagination_page_2(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """page=2 with per_page=2 returns items from the second page."""
        resp = await client.get(f"{LIST_URL}?per_page=2&page=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

    async def test_pagination_beyond_last_page(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Requesting a page beyond the last page returns empty items."""
        resp = await client.get(f"{LIST_URL}?per_page=2&page=3", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 0
        assert data["total_count"] == 4


# ---------------------------------------------------------------------------
# TestAdminReviewListFilters
# ---------------------------------------------------------------------------


class TestAdminReviewListFilters:
    async def test_filter_by_book_id(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """book_id filter returns only reviews for that book."""
        book_a = review_data["books"][0]
        resp = await client.get(
            f"{LIST_URL}?book_id={book_a.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # r1, r3, r5 are on book_a (r4 is deleted so excluded)
        assert data["total_count"] == 3
        for item in data["items"]:
            assert item["book"]["book_id"] == book_a.id

    async def test_filter_by_user_id(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """user_id filter returns only reviews by that user."""
        user1 = review_data["users"][0]
        resp = await client.get(
            f"{LIST_URL}?user_id={user1.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # r1, r2 by user1
        assert data["total_count"] == 2
        for item in data["items"]:
            assert item["author"]["user_id"] == user1.id

    async def test_filter_by_rating_min(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """rating_min=4 returns only reviews with rating >= 4."""
        resp = await client.get(f"{LIST_URL}?rating_min=4", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # r1=5, r5=4 (r4=1 is deleted)
        assert data["total_count"] == 2
        for item in data["items"]:
            assert item["rating"] >= 4

    async def test_filter_by_rating_max(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """rating_max=2 returns only reviews with rating <= 2."""
        resp = await client.get(f"{LIST_URL}?rating_max=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # r2=2 (r4=1 is soft-deleted)
        assert data["total_count"] == 1
        for item in data["items"]:
            assert item["rating"] <= 2

    async def test_filter_by_rating_range(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """rating_min=2&rating_max=4 returns only reviews in range [2, 4]."""
        resp = await client.get(
            f"{LIST_URL}?rating_min=2&rating_max=4", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # r2=2, r3=3, r5=4
        assert data["total_count"] == 3
        for item in data["items"]:
            assert 2 <= item["rating"] <= 4

    async def test_combined_filters_are_and(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """book_id AND rating_min filters combine as AND."""
        book_a = review_data["books"][0]
        resp = await client.get(
            f"{LIST_URL}?book_id={book_a.id}&rating_min=4", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # r1=5 on book_a, r5=4 on book_a
        assert data["total_count"] == 2
        for item in data["items"]:
            assert item["book"]["book_id"] == book_a.id
            assert item["rating"] >= 4

    async def test_invalid_rating_min_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """rating_min=0 (below minimum 1) returns 422."""
        resp = await client.get(f"{LIST_URL}?rating_min=0", headers=admin_headers)
        assert resp.status_code == 422

    async def test_invalid_rating_max_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """rating_max=6 (above maximum 5) returns 422."""
        resp = await client.get(f"{LIST_URL}?rating_max=6", headers=admin_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestAdminReviewListSorting
# ---------------------------------------------------------------------------


class TestAdminReviewListSorting:
    async def test_default_sort_is_date_desc(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Default sort is by created_at descending."""
        resp = await client.get(LIST_URL, headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        # Verify consecutive items are in descending created_at order
        for i in range(len(items) - 1):
            assert items[i]["created_at"] >= items[i + 1]["created_at"]

    async def test_sort_by_rating_asc(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """sort_by=rating&sort_dir=asc returns reviews in ascending rating order."""
        resp = await client.get(
            f"{LIST_URL}?sort_by=rating&sort_dir=asc", headers=admin_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        ratings = [item["rating"] for item in items]
        assert ratings == sorted(ratings), f"Ratings not ascending: {ratings}"

    async def test_sort_by_rating_desc(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """sort_by=rating&sort_dir=desc returns reviews in descending rating order."""
        resp = await client.get(
            f"{LIST_URL}?sort_by=rating&sort_dir=desc", headers=admin_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        ratings = [item["rating"] for item in items]
        assert ratings == sorted(ratings, reverse=True), f"Ratings not descending: {ratings}"

    async def test_sort_by_date_asc(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """sort_by=date&sort_dir=asc returns reviews in ascending created_at order."""
        resp = await client.get(
            f"{LIST_URL}?sort_by=date&sort_dir=asc", headers=admin_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        dates = [item["created_at"] for item in items]
        assert dates == sorted(dates), f"Dates not ascending: {dates}"

    async def test_invalid_sort_by_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """sort_by=invalid returns 422."""
        resp = await client.get(f"{LIST_URL}?sort_by=invalid", headers=admin_headers)
        assert resp.status_code == 422

    async def test_invalid_sort_dir_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """sort_dir=invalid returns 422."""
        resp = await client.get(f"{LIST_URL}?sort_dir=invalid", headers=admin_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestBulkDeleteAuth
# ---------------------------------------------------------------------------


class TestBulkDeleteAuth:
    async def test_bulk_delete_requires_auth(self, client: AsyncClient) -> None:
        """DELETE /admin/reviews/bulk without token returns 401."""
        resp = await client.request(
            "DELETE", BULK_DELETE_URL, json={"review_ids": [1]}
        )
        assert resp.status_code == 401

    async def test_bulk_delete_requires_admin(
        self, client: AsyncClient, user_headers
    ) -> None:
        """DELETE /admin/reviews/bulk with regular user token returns 403."""
        _, headers = user_headers
        resp = await client.request(
            "DELETE", BULK_DELETE_URL, json={"review_ids": [1]}, headers=headers
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TestBulkDeleteBehavior
# ---------------------------------------------------------------------------


class TestBulkDeleteBehavior:
    async def test_bulk_delete_soft_deletes_reviews(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Bulk delete soft-deletes specified reviews; they disappear from list."""
        r1 = review_data["reviews"][0]
        r2 = review_data["reviews"][1]

        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": [r1.id, r2.id]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_count"] == 2

        # r1 and r2 should no longer appear; only r3, r5 remain (r4 was pre-deleted)
        list_resp = await client.get(LIST_URL, headers=admin_headers)
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        item_ids = [item["id"] for item in list_data["items"]]
        assert r1.id not in item_ids
        assert r2.id not in item_ids
        assert list_data["total_count"] == 2

    async def test_bulk_delete_skips_already_deleted(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Bulk delete of already-soft-deleted review returns deleted_count=0."""
        r4 = review_data["deleted_review"]

        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": [r4.id]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 0

    async def test_bulk_delete_skips_nonexistent_ids(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Bulk delete of nonexistent IDs returns deleted_count=0."""
        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": [99999]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 0

    async def test_bulk_delete_mixed_valid_invalid(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Bulk delete with mix of valid, already-deleted, and missing IDs."""
        r1 = review_data["reviews"][0]
        r4 = review_data["deleted_review"]

        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": [r1.id, r4.id, 99999]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        # Only r1 actually deleted; r4 already deleted, 99999 missing
        assert resp.json()["deleted_count"] == 1

    async def test_bulk_delete_empty_list_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Empty review_ids list returns 422 (min_length=1)."""
        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": []},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_bulk_delete_exceeds_max_returns_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """51 review IDs returns 422 (max_length=50)."""
        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": list(range(1, 52))},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_deleted_reviews_not_in_subsequent_list(
        self, client: AsyncClient, admin_headers: dict, review_data: dict
    ) -> None:
        """Reviews deleted via bulk delete do not reappear in subsequent GET."""
        r3 = review_data["reviews"][2]

        resp = await client.request(
            "DELETE", BULK_DELETE_URL,
            json={"review_ids": [r3.id]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 1

        list_resp = await client.get(LIST_URL, headers=admin_headers)
        assert list_resp.status_code == 200
        item_ids = [item["id"] for item in list_resp.json()["items"]]
        assert r3.id not in item_ids
