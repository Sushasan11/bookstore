"""Repository layer for Order and OrderItem database access."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.books.models import Book
from app.cart.models import CartItem
from app.orders.models import Order, OrderItem, OrderStatus


class OrderRepository:
    """Handles Order persistence with SELECT FOR UPDATE stock locking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_books(self, book_ids: list[int]) -> list[Book]:
        """Lock book rows in ascending ID order to prevent deadlocks.

        Caller MUST pass book_ids already sorted ascending.
        Uses SELECT FOR UPDATE to prevent concurrent stock decrements.
        """
        result = await self.session.execute(
            select(Book)
            .where(Book.id.in_(book_ids))
            .order_by(Book.id)
            .with_for_update()
        )
        return list(result.scalars().all())

    async def create_order(
        self,
        user_id: int,
        cart_items: list[CartItem],
        book_map: dict[int, Book],
    ) -> Order:
        """Create an order from the cart, decrement stock, and flush.

        Eagerly loads items and their books so the returned Order is ready
        for response serialization without additional async queries.
        """
        order = Order(user_id=user_id, status=OrderStatus.CONFIRMED)
        self.session.add(order)
        await self.session.flush()  # obtain order.id

        for item in cart_items:
            oi = OrderItem(
                order_id=order.id,
                book_id=item.book_id,
                quantity=item.quantity,
                unit_price=book_map[item.book_id].price,
            )
            self.session.add(oi)
            book_map[item.book_id].stock_quantity -= item.quantity

        await self.session.flush()

        # Eagerly load relationships for response serialization
        await self.session.refresh(order, ["items"])
        for oi in order.items:
            await self.session.refresh(oi, ["book"])

        return order

    async def get_by_id_for_user(self, order_id: int, user_id: int) -> Order | None:
        """Fetch a single order owned by the given user, with items and books."""
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(selectinload(Order.items).selectinload(OrderItem.book))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[Order]:
        """Return all orders for a user, newest first, with items and books."""
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items).selectinload(OrderItem.book))
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Order]:
        """Return all orders (admin view), newest first, with items and books."""
        result = await self.session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items).selectinload(OrderItem.book))
        )
        return list(result.scalars().all())
