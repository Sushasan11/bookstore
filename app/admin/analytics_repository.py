"""Analytics repository — read-only aggregate queries against existing order tables."""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
