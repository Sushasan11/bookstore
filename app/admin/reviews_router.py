"""Admin review moderation endpoints — GET /admin/reviews, DELETE /admin/reviews/bulk."""

import math

from fastapi import APIRouter, Depends, Query

from app.admin.reviews_schemas import (
    AdminReviewEntry,
    AdminReviewListResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from app.core.deps import AdminUser, DbSession, require_admin
from app.reviews.repository import ReviewRepository

router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin-reviews"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AdminReviewListResponse)
async def list_reviews(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    book_id: int | None = Query(None),
    user_id: int | None = Query(None),
    rating_min: int | None = Query(None, ge=1, le=5),
    rating_max: int | None = Query(None, ge=1, le=5),
    sort_by: str = Query("date", pattern="^(date|rating)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> AdminReviewListResponse:
    """Return paginated, filtered list of all non-deleted reviews for admin moderation.

    Query parameters:
    - page: Page number (default 1, minimum 1).
    - per_page: Items per page (default 20, 1-100).
    - book_id: Filter by book ID (optional).
    - user_id: Filter by user ID (optional).
    - rating_min: Minimum rating 1-5 inclusive (optional).
    - rating_max: Maximum rating 1-5 inclusive (optional).
    - sort_by: "date" (default) or "rating".
    - sort_dir: "desc" (default) or "asc".

    Filters combine as AND. Admin only. Invalid values return 422.
    """
    repo = ReviewRepository(db)
    reviews, total = await repo.list_all_admin(
        page=page, per_page=per_page,
        book_id=book_id, user_id=user_id,
        rating_min=rating_min, rating_max=rating_max,
        sort_by=sort_by, sort_dir=sort_dir,
    )
    items = [
        AdminReviewEntry.model_validate({
            "id": r.id,
            "rating": r.rating,
            "text": r.text,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "author": {"user_id": r.user.id, "display_name": r.user.email.split("@")[0]},
            "book": {"book_id": r.book.id, "title": r.book.title},
        })
        for r in reviews
    ]
    return AdminReviewListResponse(
        items=items,
        total_count=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )
