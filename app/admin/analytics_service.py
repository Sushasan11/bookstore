"""Admin analytics service — period bounds, delta calculation, and summary aggregation."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.admin.analytics_repository import AnalyticsRepository


def _period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    """Return (start, end) for the current partial period.

    All bounds are UTC. The end is always `now` (partial period up to this moment).

    Args:
        now: Current UTC datetime (must be timezone-aware).
        period: One of "today", "week", "month".

    Returns:
        (period_start, period_end) tuple.

    Raises:
        ValueError: If period is not a recognised value.
    """
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        monday = now - timedelta(days=now.weekday())
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unknown period: {period!r}. Expected 'today', 'week', or 'month'.")
    return start, now


def _prior_period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    """Return (start, end) for the full previous period.

    All bounds are UTC. The prior period is the complete period immediately
    before the current one (used as baseline for delta_percentage).

    Args:
        now: Current UTC datetime (must be timezone-aware).
        period: One of "today", "week", "month".

    Returns:
        (prior_start, prior_end) tuple.

    Raises:
        ValueError: If period is not a recognised value.
    """
    if period == "today":
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_midnight = today_midnight - timedelta(days=1)
        return yesterday_midnight, today_midnight
    elif period == "week":
        this_monday = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        last_monday = this_monday - timedelta(weeks=1)
        return last_monday, this_monday
    elif period == "month":
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Last day of previous month → replace day=1 to get first of that month
        last_month_last_day = this_month_start - timedelta(days=1)
        last_month_start = last_month_last_day.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return last_month_start, this_month_start
    else:
        raise ValueError(f"Unknown period: {period!r}. Expected 'today', 'week', or 'month'.")


class AdminAnalyticsService:
    """Service layer for admin analytics — computes period summaries with delta comparisons."""

    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    async def sales_summary(self, period: str) -> dict:
        """Return sales summary for the given period with period-over-period delta.

        Args:
            period: One of "today", "week", "month".

        Returns:
            dict with keys: period, revenue, order_count, aov, delta_percentage.
            - revenue: float rounded to 2 decimal places
            - order_count: int
            - aov: float (0.0 when no orders, not null — per product decision)
            - delta_percentage: float | None (null when prior period has zero revenue)
        """
        now = datetime.now(timezone.utc)

        current_start, current_end = _period_bounds(now, period)
        prior_start, prior_end = _prior_period_bounds(now, period)

        current = await self._repo.revenue_summary(
            period_start=current_start, period_end=current_end
        )
        prior = await self._repo.revenue_summary(
            period_start=prior_start, period_end=prior_end
        )

        current_rev: Decimal = current["revenue"] or Decimal("0")
        order_count: int = current["order_count"] or 0
        prior_rev: Decimal = prior["revenue"] or Decimal("0")

        # AOV: 0.00 (not null) when no orders — per locked decision
        aov = float(round(current_rev / order_count, 2)) if order_count > 0 else 0.0

        # Delta: null when prior period has zero revenue — per locked decision
        delta_pct: float | None = (
            float(round((current_rev - prior_rev) / prior_rev * 100, 2))
            if prior_rev > 0
            else None
        )

        return {
            "period": period,
            "revenue": float(round(current_rev, 2)),
            "order_count": order_count,
            "aov": aov,
            "delta_percentage": delta_pct,
        }
