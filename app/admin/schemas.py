"""Pydantic schemas for admin user management endpoints."""

from datetime import datetime

from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    """Admin view of a user account."""

    id: int
    email: str
    full_name: str | None = (
        None  # User model has no full_name column yet; always None until migration adds it
    )
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated envelope for admin user list."""

    items: list[AdminUserResponse]
    total_count: int
    page: int
    per_page: int
    total_pages: int
