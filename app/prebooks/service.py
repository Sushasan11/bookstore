"""PreBookService: business rules for pre-booking operations."""

from app.books.repository import BookRepository
from app.core.exceptions import AppError
from app.prebooks.models import PreBooking, PreBookStatus
from app.prebooks.repository import PreBookRepository


class PreBookService:
    """Enforces business rules for creating, listing, and cancelling pre-bookings."""

    def __init__(self, prebook_repo: PreBookRepository, book_repo: BookRepository) -> None:
        self.prebook_repo = prebook_repo
        self.book_repo = book_repo

    async def create(self, user_id: int, book_id: int) -> PreBooking:
        """Create a pre-booking for an out-of-stock book.

        Raises:
            AppError(404) BOOK_NOT_FOUND if book does not exist.
            AppError(409) PREBOOK_BOOK_IN_STOCK if book has stock > 0.
            AppError(409) PREBOOK_DUPLICATE if user already has an active pre-booking.
        """
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise AppError(
                status_code=404,
                detail="Book not found",
                code="BOOK_NOT_FOUND",
                field="book_id",
            )
        if book.stock_quantity > 0:
            raise AppError(
                status_code=409,
                detail="Book is in stock — add to cart instead",
                code="PREBOOK_BOOK_IN_STOCK",
                field="book_id",
            )
        return await self.prebook_repo.add(user_id, book_id)

    async def list(self, user_id: int) -> list[PreBooking]:
        """Return all pre-bookings for a user (all statuses)."""
        return await self.prebook_repo.get_all_for_user(user_id)

    async def cancel(self, user_id: int, prebook_id: int) -> None:
        """Cancel a pre-booking (soft-delete to CANCELLED status).

        Raises:
            AppError(404) PREBOOK_NOT_FOUND if not found or belongs to another user.
            AppError(409) PREBOOK_ALREADY_CANCELLED if already cancelled.
        """
        prebook = await self.prebook_repo.get_by_id(prebook_id)
        if prebook is None or prebook.user_id != user_id:
            # Never reveal existence to other users — treat as 404
            raise AppError(
                status_code=404,
                detail="Pre-booking not found",
                code="PREBOOK_NOT_FOUND",
            )
        if prebook.status == PreBookStatus.CANCELLED:
            raise AppError(
                status_code=409,
                detail="Pre-booking is already cancelled",
                code="PREBOOK_ALREADY_CANCELLED",
            )
        await self.prebook_repo.cancel(prebook)
