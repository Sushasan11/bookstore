"""Pydantic schemas for the orders feature."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, computed_field


class CheckoutRequest(BaseModel):
    """Request body for POST /orders/checkout."""

    force_payment_failure: bool = False


class OrderItemBookSummary(BaseModel):
    """Minimal book info embedded in order item responses."""

    id: int
    title: str
    author: str
    cover_image_url: str | None = None
    price: Decimal | None = None

    model_config = {"from_attributes": True}


class OrderItemResponse(BaseModel):
    """Response schema for a single order item."""

    id: int
    book_id: int | None
    quantity: int
    unit_price: Decimal
    book: OrderItemBookSummary | None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """Response schema for an order with all line items."""

    id: int
    status: str
    created_at: datetime
    items: list[OrderItemResponse]

    @computed_field  # type: ignore[misc]
    @property
    def total_price(self) -> Decimal:
        """Sum of (unit_price * quantity) for all items."""
        return sum(i.unit_price * i.quantity for i in self.items) or Decimal("0")

    model_config = {"from_attributes": True}


class InsufficientStockItem(BaseModel):
    """Details of a single item with insufficient stock — used in error responses."""

    book_id: int
    title: str
    requested: int
    available: int
