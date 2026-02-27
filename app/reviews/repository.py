"""Repository layer for Review database access."""

from datetime import UTC, datetime

from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.reviews.models import Review

# Sentinel value to distinguish "not provided" from explicit None for text field
_UNSET = object()


class ReviewRepository:
    """Handles Review persistence — CRUD, pagination, and aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        book_id: int,
        rating: int,
        text: str | None = None,
    ) -> Review:
        """Create a new review.

        Raises AppError(409) REVIEW_DUPLICATE if user has already reviewed this book.
        FK violations (invalid user_id or book_id) are re-raised as-is.
        """
        review = Review(user_id=user_id, book_id=book_id, rating=rating, text=text)
        self.session.add(review)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            orig = str(e.orig).lower() if e.orig else ""
            if "uq_reviews_user_book" in orig:
                raise AppError(
                    409,
                    "You have already reviewed this book",
                    "REVIEW_DUPLICATE",
                    "book_id",
                ) from e
            raise

        # Eager-load relationships for response serialization
        await self.session.refresh(review, ["book", "user"])
        return review

    async def get_by_id(self, review_id: int) -> Review | None:
        """Fetch a review by ID, excluding soft-deleted records.

        Eager-loads book and user relationships.
        """
        result = await self.session.execute(
            select(Review)
            .where(Review.id == review_id, Review.deleted_at.is_(None))
            .options(selectinload(Review.user), selectinload(Review.book))
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_book(
        self, user_id: int, book_id: int
    ) -> Review | None:
        """Fetch a review by user_id and book_id, excluding soft-deleted records."""
        result = await self.session.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.book_id == book_id,
                Review.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        review: Review,
        rating: int | None = None,
        text: object = _UNSET,
    ) -> Review:
        """Update a review's rating and/or text.

        Only updates fields that are explicitly provided.
        Pass text=None to clear the review text (rating-only review).
        The _UNSET sentinel distinguishes "not provided" from explicit None.
        """
        if rating is not None:
            review.rating = rating
        if text is not _UNSET:
            review.text = text  # type: ignore[assignment]
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def soft_delete(self, review: Review) -> None:
        """Soft-delete a review by setting deleted_at timestamp."""
        review.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def list_for_book(
        self,
        book_id: int,
        *,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Review], int]:
        """Return paginated reviews for a book, newest first.

        Secondary sort by id DESC provides a stable tiebreaker.
        Eager-loads user relationship for reviewer info.
        Returns (reviews, total_count).
        """
        base_stmt = (
            select(Review)
            .where(Review.book_id == book_id, Review.deleted_at.is_(None))
        )

        # Count query
        count_result = await self.session.execute(
            select(func.count()).select_from(base_stmt.subquery())
        )
        total = count_result.scalar_one()

        # Paginated data query
        result = await self.session.execute(
            base_stmt
            .options(selectinload(Review.user), selectinload(Review.book))
            .order_by(Review.created_at.desc(), Review.id.desc())
            .limit(size)
            .offset((page - 1) * size)
        )
        reviews = list(result.scalars().all())

        return reviews, total

    async def list_all_admin(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        book_id: int | None = None,
        user_id: int | None = None,
        rating_min: int | None = None,
        rating_max: int | None = None,
        sort_by: str = "date",
        sort_dir: str = "desc",
    ) -> tuple[list[Review], int]:
        """Return paginated, filtered, sorted reviews for admin moderation.

        Filters combine as AND (e.g., book_id=5 AND rating_min=3).
        Soft-deleted reviews are always excluded.
        Eager-loads user and book relationships for response serialization.

        Args:
            page: 1-indexed page number.
            per_page: Items per page.
            book_id: Filter to reviews for this book only.
            user_id: Filter to reviews by this user only.
            rating_min: Minimum rating (inclusive, 1-5).
            rating_max: Maximum rating (inclusive, 1-5).
            sort_by: "date" (created_at) or "rating".
            sort_dir: "asc" or "desc".

        Returns:
            Tuple of (reviews list, total count).
        """
        stmt = (
            select(Review)
            .where(Review.deleted_at.is_(None))
            .options(selectinload(Review.user), selectinload(Review.book))
        )

        # Conditional filters — all combine as AND
        if book_id is not None:
            stmt = stmt.where(Review.book_id == book_id)
        if user_id is not None:
            stmt = stmt.where(Review.user_id == user_id)
        if rating_min is not None:
            stmt = stmt.where(Review.rating >= rating_min)
        if rating_max is not None:
            stmt = stmt.where(Review.rating <= rating_max)

        # Sort column and direction
        sort_col = Review.created_at if sort_by == "date" else Review.rating
        order_expr = desc(sort_col) if sort_dir == "desc" else asc(sort_col)
        stmt = stmt.order_by(order_expr, Review.id.desc())  # id as stable tiebreaker

        # Count (reuses same filters via subquery)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Paginate
        result = await self.session.execute(
            stmt.limit(per_page).offset((page - 1) * per_page)
        )
        return list(result.scalars().all()), total

    async def bulk_soft_delete(self, review_ids: list[int]) -> int:
        """Soft-delete multiple reviews by ID list in a single UPDATE.

        Best-effort: silently skips IDs that are missing or already soft-deleted.
        Returns the count of reviews actually soft-deleted.

        Uses synchronize_session="fetch" per project convention (STATE.md).
        """
        if not review_ids:
            return 0

        result = await self.session.execute(
            update(Review)
            .where(Review.id.in_(review_ids), Review.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount

    async def get_aggregates(self, book_id: int) -> dict:
        """Return avg_rating and review_count for a book.

        avg_rating is rounded to 1 decimal place, or None if no reviews.
        review_count is 0 if no reviews.
        """
        result = await self.session.execute(
            select(
                func.avg(Review.rating),
                func.count(Review.id),
            ).where(
                Review.book_id == book_id,
                Review.deleted_at.is_(None),
            )
        )
        row = result.one()
        avg_rating = row[0]
        review_count = row[1]

        return {
            "avg_rating": float(round(avg_rating, 1)) if avg_rating is not None else None,
            "review_count": review_count,
        }
