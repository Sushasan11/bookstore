"""Pydantic schemas for the shopping cart feature."""

from decimal import Decimal

from pydantic import BaseModel, Field, computed_field


class CartItemAdd(BaseModel):
    """Request body for POST /cart/items."""

    book_id: int
    quantity: int = Field(ge=1, default=1)


class CartItemUpdate(BaseModel):
    """Request body for PUT /cart/items/{item_id}."""

    quantity: int = Field(ge=1)


class BookSummary(BaseModel):
    """Minimal book info embedded in cart item responses."""

    id: int
    title: str
    author: str
    price: Decimal
    cover_image_url: str | None

    model_config = {"from_attributes": True}


class CartItemResponse(BaseModel):
    """Response schema for a single cart item."""

    id: int
    book_id: int
    quantity: int
    book: BookSummary

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    """Response schema for GET /cart — full cart with computed totals."""

    items: list[CartItemResponse]

    @computed_field  # type: ignore[misc]
    @property
    def total_items(self) -> int:
        """Sum of all item quantities."""
        return sum(item.quantity for item in self.items)

    @computed_field  # type: ignore[misc]
    @property
    def total_price(self) -> Decimal:
        """Sum of (book.price * quantity) for all items."""
        return sum(item.book.price * item.quantity for item in self.items) or Decimal(
            "0"
        )
