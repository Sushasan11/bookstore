"""Integration tests for ReviewRepository and OrderRepository.has_user_purchased_book.

Tests cover:
  - VPRC-01: ReviewRepository CRUD operations with real PostgreSQL database
  - Duplicate detection via UniqueConstraint (raises AppError 409 REVIEW_DUPLICATE)
  - Soft-delete filtering in get, list, and aggregate queries
  - Pagination in list_for_book (page/size, ordering)
  - Live aggregate computation (avg_rating, review_count excluding soft-deleted)
  - has_user_purchased_book: True only for CONFIRMED orders, False otherwise

Uses the existing conftest.py async infrastructure:
  - asyncio_mode = "auto" (no @pytest.mark.asyncio needed)
  - db_session: function-scoped with rollback (test isolation)

Notes:
  - Module-specific email prefixes (revdata_user@, revdata_user2@) avoid collisions
    with other test modules sharing the same test DB schema.
  - Book and Order objects are created directly via ORM (no HTTP) — this is a
    data-layer test that does not require the HTTP client.
  - ISBN values use unique module-specific prefixes to avoid unique constraint errors
    across parallel or sequential test runs within the same session.
"""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.orders.models import Order, OrderItem, OrderStatus
from app.orders.repository import OrderRepository
from app.reviews.repository import ReviewRepository
from app.users.models import User
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def review_user(db_session: AsyncSession) -> User:
    """Create the primary test user for review data tests."""
    repo = UserRepository(db_session)
    hashed = await hash_password("testpass123")
    user = await repo.create(email="revdata_user@example.com", hashed_password=hashed)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def review_user2(db_session: AsyncSession) -> User:
    """Create a secondary test user (for multi-user tests)."""
    repo = UserRepository(db_session)
    hashed = await hash_password("testpass123")
    user = await repo.create(email="revdata_user2@example.com", hashed_password=hashed)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sample_book(db_session: AsyncSession) -> Book:
    """Create a sample Book directly via ORM."""
    book = Book(
        title="Data Layer Test Book",
        author="Test Author",
        isbn="978-9990000001",
        price=Decimal("19.99"),
        stock_quantity=10,
        description="Test book for review data layer tests",
    )
    db_session.add(book)
    await db_session.flush()
    return book


@pytest_asyncio.fixture
async def sample_book2(db_session: AsyncSession) -> Book:
    """Create a second sample Book for multi-book tests."""
    book = Book(
        title="Data Layer Test Book 2",
        author="Test Author 2",
        isbn="978-9990000002",
        price=Decimal("24.99"),
        stock_quantity=5,
        description="Second test book for review data layer tests",
    )
    db_session.add(book)
    await db_session.flush()
    return book


# ---------------------------------------------------------------------------
# TestReviewCreate
# ---------------------------------------------------------------------------


class TestReviewCreate:
    async def test_create_review_success(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Create a review with rating and text; verify returned Review has correct fields."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id,
            book_id=sample_book.id,
            rating=4,
            text="A great read!",
        )
        assert review.id is not None
        assert review.user_id == review_user.id
        assert review.book_id == sample_book.id
        assert review.rating == 4
        assert review.text == "A great read!"
        assert review.deleted_at is None
        # Relationships should be eagerly loaded
        assert review.user is not None
        assert review.book is not None
        assert review.user.id == review_user.id
        assert review.book.id == sample_book.id

    async def test_create_review_rating_only(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Create a rating-only review (text=None); verify text is None."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id,
            book_id=sample_book.id,
            rating=3,
            text=None,
        )
        assert review.rating == 3
        assert review.text is None

    async def test_create_duplicate_raises_409(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Creating a second review for same user+book raises AppError(409, REVIEW_DUPLICATE)."""
        repo = ReviewRepository(db_session)
        await repo.create(
            user_id=review_user.id,
            book_id=sample_book.id,
            rating=4,
            text="First review",
        )
        with pytest.raises(AppError) as exc_info:
            await repo.create(
                user_id=review_user.id,
                book_id=sample_book.id,
                rating=5,
                text="Duplicate review",
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "REVIEW_DUPLICATE"


# ---------------------------------------------------------------------------
# TestReviewGet
# ---------------------------------------------------------------------------


class TestReviewGet:
    async def test_get_by_id_returns_review(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Create a review; get_by_id returns it."""
        repo = ReviewRepository(db_session)
        created = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=4
        )
        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.rating == 4

    async def test_get_by_id_returns_none_for_deleted(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Soft-deleted review is not returned by get_by_id."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=3
        )
        await repo.soft_delete(review)
        result = await repo.get_by_id(review.id)
        assert result is None

    async def test_get_by_id_returns_none_for_nonexistent(
        self,
        db_session: AsyncSession,
    ) -> None:
        """get_by_id with a non-existent ID returns None."""
        repo = ReviewRepository(db_session)
        result = await repo.get_by_id(999_999)
        assert result is None

    async def test_get_by_user_and_book(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """get_by_user_and_book returns the review for the given user+book pair."""
        repo = ReviewRepository(db_session)
        created = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=5
        )
        found = await repo.get_by_user_and_book(review_user.id, sample_book.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_user_and_book_excludes_deleted(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Soft-deleted review is not returned by get_by_user_and_book."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=4
        )
        await repo.soft_delete(review)
        result = await repo.get_by_user_and_book(review_user.id, sample_book.id)
        assert result is None


# ---------------------------------------------------------------------------
# TestReviewUpdate
# ---------------------------------------------------------------------------


class TestReviewUpdate:
    async def test_update_rating(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Update rating from 3 to 5; verify the change persists."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=3
        )
        updated = await repo.update(review, rating=5)
        assert updated.rating == 5

    async def test_update_text(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Update text from 'original' to 'updated'; verify the change."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id,
            book_id=sample_book.id,
            rating=4,
            text="original",
        )
        updated = await repo.update(review, text="updated")
        assert updated.text == "updated"

    async def test_update_clears_text_with_none(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Passing text=None to update() clears the review text."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id,
            book_id=sample_book.id,
            rating=4,
            text="Some text",
        )
        updated = await repo.update(review, text=None)
        assert updated.text is None


# ---------------------------------------------------------------------------
# TestReviewSoftDelete
# ---------------------------------------------------------------------------


class TestReviewSoftDelete:
    async def test_soft_delete_sets_deleted_at(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """Soft-deleting a review sets deleted_at to a non-None datetime."""
        repo = ReviewRepository(db_session)
        review = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=4
        )
        assert review.deleted_at is None
        await repo.soft_delete(review)
        assert review.deleted_at is not None


# ---------------------------------------------------------------------------
# TestReviewListForBook
# ---------------------------------------------------------------------------


class TestReviewListForBook:
    async def test_list_for_book_basic(
        self,
        db_session: AsyncSession,
        review_user: User,
        review_user2: User,
        sample_book: Book,
    ) -> None:
        """Create 2 reviews for same book (different users); list returns both, total=2."""
        repo = ReviewRepository(db_session)
        await repo.create(user_id=review_user.id, book_id=sample_book.id, rating=4)
        await repo.create(user_id=review_user2.id, book_id=sample_book.id, rating=5)
        reviews, total = await repo.list_for_book(sample_book.id)
        assert total == 2
        assert len(reviews) == 2

    async def test_list_for_book_excludes_deleted(
        self,
        db_session: AsyncSession,
        review_user: User,
        review_user2: User,
        sample_book: Book,
    ) -> None:
        """Create 2 reviews, soft_delete one; list returns 1, total=1."""
        repo = ReviewRepository(db_session)
        r1 = await repo.create(user_id=review_user.id, book_id=sample_book.id, rating=4)
        await repo.create(user_id=review_user2.id, book_id=sample_book.id, rating=5)
        await repo.soft_delete(r1)
        reviews, total = await repo.list_for_book(sample_book.id)
        assert total == 1
        assert len(reviews) == 1

    async def test_list_for_book_pagination(
        self,
        db_session: AsyncSession,
        review_user: User,
        review_user2: User,
        sample_book: Book,
        sample_book2: Book,
    ) -> None:
        """Create 3 reviews for book; page=1 size=2 returns 2 items total=3; page=2 returns 1."""
        # Need a third user — create inline
        repo_u = UserRepository(db_session)
        hashed = await hash_password("testpass123")
        user3 = await repo_u.create(
            email="revdata_user3@example.com", hashed_password=hashed
        )
        await db_session.flush()

        repo = ReviewRepository(db_session)
        await repo.create(user_id=review_user.id, book_id=sample_book.id, rating=3)
        await repo.create(user_id=review_user2.id, book_id=sample_book.id, rating=4)
        await repo.create(user_id=user3.id, book_id=sample_book.id, rating=5)

        page1, total1 = await repo.list_for_book(sample_book.id, page=1, size=2)
        assert total1 == 3
        assert len(page1) == 2

        page2, total2 = await repo.list_for_book(sample_book.id, page=2, size=2)
        assert total2 == 3
        assert len(page2) == 1

    async def test_list_for_book_ordered_newest_first(
        self,
        db_session: AsyncSession,
        review_user: User,
        review_user2: User,
        sample_book: Book,
    ) -> None:
        """list_for_book returns reviews newest-first (created_at DESC)."""
        repo = ReviewRepository(db_session)
        r1 = await repo.create(user_id=review_user.id, book_id=sample_book.id, rating=3)
        r2 = await repo.create(user_id=review_user2.id, book_id=sample_book.id, rating=5)
        reviews, _ = await repo.list_for_book(sample_book.id)
        # r2 was created after r1 so it should appear first
        assert reviews[0].id == r2.id or reviews[0].created_at >= reviews[1].created_at


# ---------------------------------------------------------------------------
# TestReviewAggregates
# ---------------------------------------------------------------------------


class TestReviewAggregates:
    async def test_aggregates_with_reviews(
        self,
        db_session: AsyncSession,
        review_user: User,
        review_user2: User,
        sample_book: Book,
        sample_book2: Book,
    ) -> None:
        """Create reviews with ratings [3, 4, 5]; verify avg_rating=4.0, review_count=3."""
        # Need a third user — create inline
        repo_u = UserRepository(db_session)
        hashed = await hash_password("testpass123")
        user3 = await repo_u.create(
            email="revdata_agg_user3@example.com", hashed_password=hashed
        )
        await db_session.flush()

        repo = ReviewRepository(db_session)
        await repo.create(user_id=review_user.id, book_id=sample_book.id, rating=3)
        await repo.create(user_id=review_user2.id, book_id=sample_book.id, rating=4)
        await repo.create(user_id=user3.id, book_id=sample_book.id, rating=5)

        agg = await repo.get_aggregates(sample_book.id)
        assert agg["review_count"] == 3
        assert agg["avg_rating"] == pytest.approx(4.0, abs=0.05)

    async def test_aggregates_no_reviews(
        self,
        db_session: AsyncSession,
        sample_book: Book,
    ) -> None:
        """Book with no reviews returns avg_rating=None, review_count=0."""
        repo = ReviewRepository(db_session)
        agg = await repo.get_aggregates(sample_book.id)
        assert agg["avg_rating"] is None
        assert agg["review_count"] == 0

    async def test_aggregates_excludes_deleted(
        self,
        db_session: AsyncSession,
        review_user: User,
        review_user2: User,
        sample_book: Book,
    ) -> None:
        """Soft-deleted review is excluded from aggregates."""
        repo = ReviewRepository(db_session)
        r1 = await repo.create(
            user_id=review_user.id, book_id=sample_book.id, rating=3
        )
        r2 = await repo.create(
            user_id=review_user2.id, book_id=sample_book.id, rating=5
        )
        await repo.soft_delete(r2)

        agg = await repo.get_aggregates(sample_book.id)
        assert agg["review_count"] == 1
        assert agg["avg_rating"] == pytest.approx(3.0, abs=0.05)


# ---------------------------------------------------------------------------
# TestHasUserPurchasedBook
# ---------------------------------------------------------------------------


class TestHasUserPurchasedBook:
    async def test_confirmed_order_returns_true(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """User with a CONFIRMED order containing the book returns True."""
        order = Order(user_id=review_user.id, status=OrderStatus.CONFIRMED)
        db_session.add(order)
        await db_session.flush()
        order_item = OrderItem(
            order_id=order.id,
            book_id=sample_book.id,
            quantity=1,
            unit_price=Decimal("19.99"),
        )
        db_session.add(order_item)
        await db_session.flush()

        repo = OrderRepository(db_session)
        result = await repo.has_user_purchased_book(review_user.id, sample_book.id)
        assert result is True

    async def test_payment_failed_returns_false(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """PAYMENT_FAILED order does not count as a purchase — returns False."""
        order = Order(user_id=review_user.id, status=OrderStatus.PAYMENT_FAILED)
        db_session.add(order)
        await db_session.flush()
        order_item = OrderItem(
            order_id=order.id,
            book_id=sample_book.id,
            quantity=1,
            unit_price=Decimal("19.99"),
        )
        db_session.add(order_item)
        await db_session.flush()

        repo = OrderRepository(db_session)
        result = await repo.has_user_purchased_book(review_user.id, sample_book.id)
        assert result is False

    async def test_no_orders_returns_false(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
    ) -> None:
        """User with no orders returns False."""
        repo = OrderRepository(db_session)
        result = await repo.has_user_purchased_book(review_user.id, sample_book.id)
        assert result is False

    async def test_different_book_returns_false(
        self,
        db_session: AsyncSession,
        review_user: User,
        sample_book: Book,
        sample_book2: Book,
    ) -> None:
        """Confirmed order for book A does not count as purchase of book B."""
        order = Order(user_id=review_user.id, status=OrderStatus.CONFIRMED)
        db_session.add(order)
        await db_session.flush()
        order_item = OrderItem(
            order_id=order.id,
            book_id=sample_book.id,
            quantity=1,
            unit_price=Decimal("19.99"),
        )
        db_session.add(order_item)
        await db_session.flush()

        repo = OrderRepository(db_session)
        # Checking book2, but order only contains book1
        result = await repo.has_user_purchased_book(review_user.id, sample_book2.id)
        assert result is False
