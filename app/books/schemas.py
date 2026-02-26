"""Pydantic schemas for book catalog CRUD."""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, computed_field, Field, field_validator


def _validate_isbn(isbn: str) -> str:
    """Validate ISBN-10 or ISBN-13 with checksum. Raise ValueError on failure.

    Strips hyphens and spaces before checking. Returns the cleaned (stripped)
    ISBN string on success.
    """
    cleaned = re.sub(r"[-\s]", "", isbn).upper()

    if len(cleaned) == 10:
        # ISBN-10: 9 digits + check digit (0-9 or X)
        if not re.match(r"^\d{9}[\dX]$", cleaned):
            raise ValueError("ISBN-10 must be 9 digits followed by a digit or X")
        total = sum(
            (10 - i) * (int(c) if c != "X" else 10) for i, c in enumerate(cleaned)
        )
        if total % 11 != 0:
            raise ValueError("ISBN-10 checksum invalid")
    elif len(cleaned) == 13:
        # ISBN-13: 13 digits with alternating 1/3 weights
        if not re.match(r"^\d{13}$", cleaned):
            raise ValueError("ISBN-13 must be exactly 13 digits")
        total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(cleaned))
        if total % 10 != 0:
            raise ValueError("ISBN-13 checksum invalid")
    else:
        raise ValueError("ISBN must be 10 or 13 digits (hyphens ignored)")

    return cleaned


class BookCreate(BaseModel):
    """Request body for POST /books. title, author, price are required."""

    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0, decimal_places=2)
    isbn: str | None = None
    genre_id: int | None = None
    description: str | None = None
    cover_image_url: Annotated[str | None, Field(None, max_length=2048)] = None
    publish_date: date | None = None

    @field_validator("isbn", mode="before")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return _validate_isbn(str(v))

    model_config = {"from_attributes": True}


class BookUpdate(BaseModel):
    """Request body for PUT /books/{id}. All fields optional."""

    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = Field(None, min_length=1, max_length=255)
    price: Decimal | None = Field(None, gt=0, decimal_places=2)
    isbn: str | None = None
    genre_id: int | None = None
    description: str | None = None
    cover_image_url: Annotated[str | None, Field(None, max_length=2048)] = None
    publish_date: date | None = None

    @field_validator("isbn", mode="before")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return _validate_isbn(str(v))


class StockUpdate(BaseModel):
    """Request body for PATCH /books/{id}/stock."""

    quantity: int = Field(ge=0, description="Absolute stock quantity to set")


class BookResponse(BaseModel):
    """Response schema for book records."""

    id: int
    title: str
    author: str
    price: Decimal
    isbn: str | None
    genre_id: int | None
    description: str | None
    cover_image_url: str | None
    publish_date: date | None
    stock_quantity: int

    model_config = {"from_attributes": True}


class BookDetailResponse(BaseModel):
    """Response for GET /books/{id} -- extends BookResponse with computed in_stock field.

    in_stock is a derived boolean (stock_quantity > 0) -- not stored in DB.
    stock_quantity is still included for admin-facing clients that need the exact count.
    avg_rating and review_count are computed live from reviews (AGGR-01, AGGR-02).
    """

    id: int
    title: str
    author: str
    price: Decimal
    isbn: str | None
    genre_id: int | None
    description: str | None
    cover_image_url: str | None
    publish_date: date | None
    stock_quantity: int
    avg_rating: float | None = None   # None when no reviews exist
    review_count: int = 0             # 0 when no reviews exist

    @computed_field  # type: ignore[misc]
    @property
    def in_stock(self) -> bool:
        """True when at least one copy is available."""
        return self.stock_quantity > 0

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    """Paginated book list response envelope for GET /books."""

    items: list[BookResponse]
    total: int
    page: int
    size: int


class GenreCreate(BaseModel):
    """Request body for POST /genres."""

    name: str = Field(min_length=1, max_length=100)


class GenreResponse(BaseModel):
    """Response schema for genre records."""

    id: int
    name: str

    model_config = {"from_attributes": True}
