"""Repository layer for Review database access."""

from datetime import UTC, datetime

from sqlalchemy import func, select
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
