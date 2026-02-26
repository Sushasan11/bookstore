"""Pydantic schemas for the pre-booking feature."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.prebooks.models import PreBooking


class PreBookCreate(BaseModel):
    """Request body for POST /prebooks."""

    book_id: int = Field(description="ID of the book to pre-book")


class PreBookResponse(BaseModel):
    """Response schema for a single pre-booking."""

    id: int
    book_id: int
    book_title: str
    book_author: str
    status: str
    created_at: datetime
    notified_at: datetime | None
    cancelled_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_book(cls, prebook: PreBooking) -> PreBookResponse:
        """Construct response from ORM object with eagerly loaded book relationship."""
        return cls(
            id=prebook.id,
            book_id=prebook.book_id,
            book_title=prebook.book.title,
            book_author=prebook.book.author,
            status=prebook.status.value,
            created_at=prebook.created_at,
            notified_at=prebook.notified_at,
            cancelled_at=prebook.cancelled_at,
        )


class PreBookListResponse(BaseModel):
    """Response envelope for GET /prebooks."""

    items: list[PreBookResponse]
