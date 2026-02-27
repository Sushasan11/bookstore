"""Admin analytics endpoints — GET /admin/analytics/sales/summary."""

from fastapi import APIRouter, Depends, Query

from app.admin.analytics_repository import AnalyticsRepository
from app.admin.analytics_schemas import SalesSummaryResponse
from app.admin.analytics_service import AdminAnalyticsService
from app.core.deps import AdminUser, DbSession, require_admin

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin-analytics"],
    dependencies=[Depends(require_admin)],
)


@router.get("/sales/summary", response_model=SalesSummaryResponse)
async def get_sales_summary(
    db: DbSession,
    _admin: AdminUser,
    period: str = Query("today", pattern="^(today|week|month)$"),
) -> SalesSummaryResponse:
    """Return revenue summary for the given period with period-over-period delta.

    Period options:
    - today: Current day from UTC midnight to now.
    - week: Current ISO week (Monday 00:00 UTC to now).
    - month: Current month (1st 00:00 UTC to now).

    Response fields:
    - revenue: Total revenue from CONFIRMED orders (float, 2dp).
    - order_count: Number of distinct CONFIRMED orders.
    - aov: Average order value (0.0 when no orders).
    - delta_percentage: % change vs previous full period (null when prior revenue is 0).

    Admin only. Invalid period values return 422.
    """
    repo = AnalyticsRepository(db)
    svc = AdminAnalyticsService(repo)
    data = await svc.sales_summary(period)
    return SalesSummaryResponse(**data)
