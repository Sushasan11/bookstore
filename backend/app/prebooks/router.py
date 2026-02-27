"""Pre-booking HTTP endpoints: POST /prebooks, GET /prebooks, DELETE /prebooks/{id}."""

from fastapi import APIRouter, status

from app.books.repository import BookRepository
from app.core.deps import ActiveUser, DbSession
from app.prebooks.repository import PreBookRepository
from app.prebooks.schemas import PreBookCreate, PreBookListResponse, PreBookResponse
from app.prebooks.service import PreBookService

router = APIRouter(prefix="/prebooks", tags=["prebooks"])


def _make_service(db: DbSession) -> PreBookService:
    """Instantiate PreBookService with repositories bound to the current DB session."""
    return PreBookService(
        prebook_repo=PreBookRepository(db),
        book_repo=BookRepository(db),
    )


@router.post("", response_model=PreBookResponse, status_code=status.HTTP_201_CREATED)
async def create_pre_booking(
    body: PreBookCreate, db: DbSession, current_user: ActiveUser
) -> PreBookResponse:
    """Reserve an out-of-stock book for the authenticated user.

    409 PREBOOK_BOOK_IN_STOCK if book has stock > 0 (add to cart instead).
    409 PREBOOK_DUPLICATE if user already has an active pre-booking for this book.
    404 BOOK_NOT_FOUND if book does not exist.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    prebook = await service.create(user_id, body.book_id)
    return PreBookResponse.from_orm_with_book(prebook)


@router.get("", response_model=PreBookListResponse)
async def list_pre_bookings(db: DbSession, current_user: ActiveUser) -> PreBookListResponse:
    """Return all pre-bookings for the authenticated user (all statuses, newest first)."""
    user_id = int(current_user["sub"])
    service = _make_service(db)
    prebooks = await service.list(user_id)
    return PreBookListResponse(
        items=[PreBookResponse.from_orm_with_book(pb) for pb in prebooks]
    )


@router.delete("/{prebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_pre_booking(
    prebook_id: int, db: DbSession, current_user: ActiveUser
) -> None:
    """Cancel (soft-delete) a pre-booking. Sets status to CANCELLED.

    404 PREBOOK_NOT_FOUND if not found or belongs to another user.
    409 PREBOOK_ALREADY_CANCELLED if already cancelled.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    await service.cancel(user_id, prebook_id)
