"""Wishlist HTTP endpoints: POST /wishlist, GET /wishlist, DELETE /wishlist/{book_id}."""

from fastapi import APIRouter, status

from app.books.repository import BookRepository
from app.core.deps import ActiveUser, DbSession
from app.wishlist.repository import WishlistRepository
from app.wishlist.schemas import WishlistAdd, WishlistItemResponse, WishlistResponse
from app.wishlist.service import WishlistService

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def _make_service(db: DbSession) -> WishlistService:
    """Instantiate WishlistService with all repositories bound to the current DB session."""
    return WishlistService(
        wishlist_repo=WishlistRepository(db),
        book_repo=BookRepository(db),
    )


@router.post(
    "", response_model=WishlistItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_to_wishlist(
    body: WishlistAdd, db: DbSession, current_user: ActiveUser
) -> WishlistItemResponse:
    """Add a book to the authenticated user's wishlist.

    409 WISHLIST_ITEM_DUPLICATE if the book is already on the wishlist.
    404 BOOK_NOT_FOUND if the book does not exist.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    item = await service.add(user_id, body.book_id)
    return WishlistItemResponse.model_validate(item)


@router.get("", response_model=WishlistResponse)
async def get_wishlist(db: DbSession, current_user: ActiveUser) -> WishlistResponse:
    """Return the authenticated user's wishlist with current book price and stock."""
    user_id = int(current_user["sub"])
    service = _make_service(db)
    items = await service.list(user_id)
    return WishlistResponse(
        items=[WishlistItemResponse.model_validate(i) for i in items]
    )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    book_id: int, db: DbSession, current_user: ActiveUser
) -> None:
    """Remove a book from the authenticated user's wishlist.

    404 WISHLIST_ITEM_NOT_FOUND if the book is not on the wishlist.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    await service.remove(user_id, book_id)
