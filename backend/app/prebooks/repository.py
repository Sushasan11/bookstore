"""Repository layer for PreBooking database access."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.prebooks.models import PreBooking, PreBookStatus


class PreBookRepository:
    """Handles PreBooking persistence — add, list, lookup, cancel, notify."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user_id: int, book_id: int) -> PreBooking:
        """Create a pre-booking with status=WAITING.

        Raises AppError(409) PREBOOK_DUPLICATE if user already has an active
        (WAITING) pre-booking for this book, enforced by partial unique index.
        After flush, eagerly loads the book relationship for response serialization.
        """
        prebook = PreBooking(
            user_id=user_id,
            book_id=book_id,
            status=PreBookStatus.WAITING,
        )
        self.session.add(prebook)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            orig = str(e.orig).lower() if e.orig else ""
            if "uq_pre_bookings_user_book_waiting" in orig or "pre_bookings" in orig:
                raise AppError(
                    409,
                    "You already have an active pre-booking for this book",
                    "PREBOOK_DUPLICATE",
                    "book_id",
                ) from e
            raise

        await self.session.refresh(prebook, ["book"])
        return prebook

    async def get_all_for_user(self, user_id: int) -> list[PreBooking]:
        """Return all pre-bookings for a user (all statuses), newest first, with books eager-loaded."""
        result = await self.session.execute(
            select(PreBooking)
            .where(PreBooking.user_id == user_id)
            .options(selectinload(PreBooking.book))
            .order_by(PreBooking.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, prebook_id: int) -> PreBooking | None:
        """Fetch a pre-booking by its primary key."""
        result = await self.session.execute(
            select(PreBooking).where(PreBooking.id == prebook_id)
        )
        return result.scalar_one_or_none()

    async def cancel(self, prebook: PreBooking) -> PreBooking:
        """Soft-delete: set status to CANCELLED and record cancelled_at timestamp."""
        prebook.status = PreBookStatus.CANCELLED
        prebook.cancelled_at = datetime.now(UTC)
        await self.session.flush()
        return prebook

    async def notify_waiting_by_book(self, book_id: int) -> list[int]:
        """Bulk-update all WAITING pre-bookings for a book to NOTIFIED.

        Returns list of user_ids whose pre-bookings were notified.
        Returns empty list if no waiting pre-bookings exist.
        Called atomically within the stock update transaction.
        """
        result = await self.session.execute(
            update(PreBooking)
            .where(
                PreBooking.book_id == book_id,
                PreBooking.status == PreBookStatus.WAITING,
            )
            .values(status=PreBookStatus.NOTIFIED, notified_at=datetime.now(UTC))
            .returning(PreBooking.user_id)
        )
        return list(result.scalars().all())
