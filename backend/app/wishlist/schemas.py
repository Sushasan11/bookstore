"""Pydantic schemas for the wishlist feature."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class WishlistAdd(BaseModel):
    """Request body for POST /wishlist."""

    book_id: int


class BookSummary(BaseModel):
    """Minimal book info embedded in wishlist item responses."""

    id: int
    title: str
    author: str
    price: Decimal
    stock_quantity: int
    cover_image_url: str | None

    model_config = {"from_attributes": True}


class WishlistItemResponse(BaseModel):
    """Response schema for a single wishlist item."""

    id: int
    book_id: int
    added_at: datetime
    book: BookSummary

    model_config = {"from_attributes": True}


class WishlistResponse(BaseModel):
    """Response schema for GET /wishlist — full wishlist with all saved books."""

    items: list[WishlistItemResponse]
