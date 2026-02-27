"""Repository layer for WishlistItem database access."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.wishlist.models import WishlistItem


class WishlistRepository:
    """Handles WishlistItem persistence — add, list, lookup, delete."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user_id: int, book_id: int) -> WishlistItem:
        """Add a book to the user's wishlist.

        Raises AppError(409) WISHLIST_ITEM_DUPLICATE if the book is already on the wishlist.
        """
        item = WishlistItem(user_id=user_id, book_id=book_id)
        self.session.add(item)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            orig = str(e.orig).lower() if e.orig else ""
            if "uq_wishlist_items" in orig or "wishlist_items" in orig:
                raise AppError(
                    409,
                    "This book is already on your wishlist",
                    "WISHLIST_ITEM_DUPLICATE",
                    "book_id",
                ) from e
            raise

        # Refresh to load the book relationship for response serialization
        await self.session.refresh(item, ["book"])
        return item

    async def get_all_for_user(self, user_id: int) -> list[WishlistItem]:
        """Return all wishlist items for a user, newest first, with books eager-loaded.

        Secondary sort by id DESC provides a stable tiebreaker when multiple items share
        the same added_at timestamp (e.g., during fast test inserts).
        """
        result = await self.session.execute(
            select(WishlistItem)
            .where(WishlistItem.user_id == user_id)
            .options(selectinload(WishlistItem.book))
            .order_by(WishlistItem.added_at.desc(), WishlistItem.id.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_book(
        self, user_id: int, book_id: int
    ) -> WishlistItem | None:
        """Fetch a wishlist item by user_id and book_id."""
        result = await self.session.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.book_id == book_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, item: WishlistItem) -> None:
        """Remove a wishlist item from the database."""
        await self.session.delete(item)
        await self.session.flush()
