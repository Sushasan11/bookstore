"""Pydantic schemas for the reviews feature."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewAuthorSummary(BaseModel):
    """Nested author summary embedded in every ReviewResponse.

    display_name is derived from email (email.split('@')[0]) since
    the User model has no display_name column.
    avatar_url is always None until a profile feature is added.
    """

    user_id: int
    display_name: str
    avatar_url: str | None

    model_config = {"from_attributes": True}


class ReviewBookSummary(BaseModel):
    """Nested book summary embedded in every ReviewResponse.

    book_id maps to Book.id — constructed explicitly by the service
    because the field name differs from the ORM attribute.
    """

    book_id: int
    title: str
    cover_image_url: str | None

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    """Request body for POST /books/{book_id}/reviews."""

    rating: int = Field(ge=1, le=5)
    text: str | None = Field(None, max_length=2000)


class ReviewUpdate(BaseModel):
    """Request body for PATCH /reviews/{review_id}.

    All fields are optional — only provided fields are updated.
    Defined here for use in Plan 14-02.
    """

    rating: int | None = Field(None, ge=1, le=5)
    text: str | None = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    """Full review response including nested author and book summaries.

    verified_purchase is NOT on the ORM model — it is injected by the service
    via _build_review_data() and validated from a plain dict.
    """

    id: int
    book_id: int
    user_id: int
    rating: int
    text: str | None
    verified_purchase: bool
    created_at: datetime
    updated_at: datetime
    author: ReviewAuthorSummary
    book: ReviewBookSummary

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    """Paginated review list response envelope for GET /books/{book_id}/reviews."""

    items: list[ReviewResponse]
    total: int
    page: int
    size: int
