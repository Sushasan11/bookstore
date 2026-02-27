"""Pydantic schemas for admin review moderation endpoints."""

import math
from datetime import datetime

from pydantic import BaseModel, Field


class AdminReviewAuthor(BaseModel):
    """Reviewer identity in the admin moderation list."""

    user_id: int
    display_name: str  # email.split('@')[0] — same pattern as ReviewAuthorSummary


class AdminReviewBook(BaseModel):
    """Book context in the admin moderation list."""

    book_id: int
    title: str


class AdminReviewEntry(BaseModel):
    """Single review in the admin moderation list.

    Omits verified_purchase (admin concern is content, not purchase status).
    Omits avatar_url and cover_image_url (not needed for moderation).
    """

    id: int
    rating: int
    text: str | None
    created_at: datetime
    updated_at: datetime
    author: AdminReviewAuthor
    book: AdminReviewBook

    model_config = {"from_attributes": True}


class AdminReviewListResponse(BaseModel):
    """Paginated envelope for admin review list — follows admin convention."""

    items: list[AdminReviewEntry]
    total_count: int
    page: int
    per_page: int
    total_pages: int


class BulkDeleteRequest(BaseModel):
    """Request body for bulk review soft-delete.

    Max 50 IDs per request — locked user decision.
    min_length=1 prevents empty list submission.
    """

    review_ids: list[int] = Field(min_length=1, max_length=50)


class BulkDeleteResponse(BaseModel):
    """Response for bulk review soft-delete.

    deleted_count reflects only reviews actually soft-deleted
    (best-effort: missing or already-deleted IDs silently skipped).
    """

    deleted_count: int
