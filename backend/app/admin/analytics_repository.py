"""Analytics repository — read-only aggregate queries against existing order tables."""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book
from app.orders.models import Order, OrderItem, OrderStatus


class AnalyticsRepository:
    """Read-only repository for analytics aggregate queries.

    Reads directly from Order and OrderItem tables — no writes, no migrations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def revenue_summary(
        self, *, period_start: datetime, period_end: datetime
    ) -> dict:
        """Return total revenue and order count for CONFIRMED orders in the given period.

        Uses func.coalesce so empty periods return Decimal("0") instead of None.

        Args:
            period_start: Inclusive start of the period (UTC).
            period_end: Exclusive end of the period (UTC).

        Returns:
            dict with keys "revenue" (Decimal) and "order_count" (int).
        """
        stmt = (
            select(
                func.coalesce(
                    func.sum(OrderItem.quantity * OrderItem.unit_price),
                    Decimal("0"),
                ).label("revenue"),
                func.count(Order.id.distinct()).label("order_count"),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.status == OrderStatus.CONFIRMED,
                Order.created_at >= period_start,
                Order.created_at < period_end,
            )
        )
        row = (await self._db.execute(stmt)).one()
        return {"revenue": row.revenue, "order_count": row.order_count}

    async def top_books(self, *, sort_by: str, limit: int = 10) -> list[dict]:
        """Return top-selling books ranked by revenue or volume.

        Only CONFIRMED orders are included. Books that have been deleted
        (book_id IS NULL in order_items) are excluded.

        Args:
            sort_by: "revenue" to rank by total_revenue, "volume" to rank by units_sold.
            limit: Maximum number of books to return (default 10, max 50).

        Returns:
            List of dicts with keys: book_id, title, author, total_revenue, units_sold.
        """
        revenue_col = func.sum(OrderItem.unit_price * OrderItem.quantity).label(
            "total_revenue"
        )
        volume_col = func.sum(OrderItem.quantity).label("units_sold")
        order_col = revenue_col if sort_by == "revenue" else volume_col

        stmt = (
            select(
                OrderItem.book_id,
                Book.title,
                Book.author,
                revenue_col,
                volume_col,
            )
            .join(Order, OrderItem.order_id == Order.id)
            .join(Book, OrderItem.book_id == Book.id)
            .where(
                Order.status == OrderStatus.CONFIRMED,
                OrderItem.book_id.is_not(None),
            )
            .group_by(OrderItem.book_id, Book.title, Book.author)
            .order_by(desc(order_col))
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return [row._asdict() for row in result.all()]

    async def low_stock_books(self, *, threshold: int) -> list[dict]:
        """Return all books with stock_quantity at or below threshold, ordered ascending.

        Args:
            threshold: Inclusive upper bound for stock_quantity filter.

        Returns:
            List of dicts: {book_id, title, author, current_stock}.
            Ordered by current_stock ascending (zero-stock books first).
        """
        stmt = (
            select(
                Book.id.label("book_id"),
                Book.title,
                Book.author,
                Book.stock_quantity.label("current_stock"),
            )
            .where(Book.stock_quantity <= threshold)
            .order_by(asc(Book.stock_quantity))
        )
        result = await self._db.execute(stmt)
        return [row._asdict() for row in result.all()]
