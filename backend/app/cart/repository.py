"""Repository layer for Cart and CartItem database access."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cart.models import Cart, CartItem
from app.core.exceptions import AppError


class CartRepository:
    """Handles Cart persistence — one cart per user via ON CONFLICT DO NOTHING."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: int) -> Cart:
        """Return the user's cart, creating it if it does not yet exist.

        Uses pg INSERT ... ON CONFLICT DO NOTHING to safely handle concurrent
        first-add requests without a race condition.
        """
        stmt = (
            pg_insert(Cart)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

        result = await self.session.execute(select(Cart).where(Cart.user_id == user_id))
        return result.scalar_one()

    async def get_with_items(self, user_id: int) -> Cart | None:
        """Fetch the cart with all items and their books eagerly loaded.

        Uses selectinload to avoid N+1 queries and MissingGreenlet errors
        when accessing relationship attributes after the session context.
        """
        result = await self.session.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.book))
        )
        return result.scalar_one_or_none()


class CartItemRepository:
    """Handles CartItem persistence — add, fetch, update quantity, delete."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, cart_id: int, book_id: int, quantity: int) -> CartItem:
        """Add a book to the cart. Raises AppError(409) on duplicate book."""
        item = CartItem(cart_id=cart_id, book_id=book_id, quantity=quantity)
        self.session.add(item)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            orig = str(e.orig).lower() if e.orig else ""
            if "uq_cart_items" in orig or "cart_items" in orig:
                raise AppError(
                    409,
                    "This book is already in your cart",
                    "CART_ITEM_DUPLICATE",
                    "book_id",
                ) from e
            raise

        # Refresh to load the book relationship for response serialization
        await self.session.refresh(item, ["book"])
        return item

    async def get_by_id(self, item_id: int) -> CartItem | None:
        """Fetch a cart item by ID with cart and book eagerly loaded."""
        result = await self.session.execute(
            select(CartItem)
            .where(CartItem.id == item_id)
            .options(
                selectinload(CartItem.cart),
                selectinload(CartItem.book),
            )
        )
        return result.scalar_one_or_none()

    async def update_quantity(self, item: CartItem, quantity: int) -> CartItem:
        """Update the quantity of an existing cart item."""
        item.quantity = quantity
        await self.session.flush()
        return item

    async def delete(self, item: CartItem) -> None:
        """Remove a cart item from the database."""
        await self.session.delete(item)
        await self.session.flush()
