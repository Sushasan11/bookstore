"""Pydantic response schemas for the admin analytics endpoints."""

from pydantic import BaseModel


class SalesSummaryResponse(BaseModel):
    """Response schema for GET /admin/analytics/sales/summary.

    All money fields are float (not Decimal) — Pydantic v2 serializes Decimal as
    string by default, which would break JSON clients expecting numeric values.
    """

    period: str
    revenue: float
    order_count: int
    aov: float
    delta_percentage: float | None
