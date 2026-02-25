"""Business logic for the wishlist feature: book existence validation."""

from app.books.repository import BookRepository
from app.core.exceptions import AppError
from app.wishlist.models import WishlistItem
from app.wishlist.repository import WishlistRepository


class WishlistService:
    """Orchestrates wishlist operations with book existence validation."""

    def __init__(
        self,
        wishlist_repo: WishlistRepository,
        book_repo: BookRepository,
    ) -> None:
        self.wishlist_repo = wishlist_repo
        self.book_repo = book_repo

    async def add(self, user_id: int, book_id: int) -> WishlistItem:
        """Add a book to the user's wishlist.

        Raises:
            AppError(404) BOOK_NOT_FOUND if the book does not exist.
            AppError(409) WISHLIST_ITEM_DUPLICATE if book is already on wishlist.
        """
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise AppError(404, "Book not found", "BOOK_NOT_FOUND", "book_id")
        return await self.wishlist_repo.add(user_id, book_id)

    async def list(self, user_id: int) -> list[WishlistItem]:
        """Return all wishlist items for the user, newest first."""
        return await self.wishlist_repo.get_all_for_user(user_id)

    async def remove(self, user_id: int, book_id: int) -> None:
        """Remove a book from the user's wishlist.

        Raises:
            AppError(404) WISHLIST_ITEM_NOT_FOUND if the book is not on the wishlist.
        """
        item = await self.wishlist_repo.get_by_user_and_book(user_id, book_id)
        if item is None:
            raise AppError(
                404,
                "Wishlist item not found",
                "WISHLIST_ITEM_NOT_FOUND",
                "book_id",
            )
        await self.wishlist_repo.delete(item)
