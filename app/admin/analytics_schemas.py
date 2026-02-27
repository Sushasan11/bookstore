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


class TopBookEntry(BaseModel):
    """Single book entry in the top-books ranking.

    total_revenue is float (same pattern as SalesSummaryResponse) to avoid
    Pydantic v2 Decimal-as-string serialization.
    """

    book_id: int
    title: str
    author: str
    total_revenue: float
    units_sold: int


class TopBooksResponse(BaseModel):
    """Response schema for GET /admin/analytics/sales/top-books."""

    sort_by: str
    items: list[TopBookEntry]
