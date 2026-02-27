"""Admin user management endpoints: GET /admin/users, PATCH /admin/users/{id}/deactivate, PATCH /admin/users/{id}/reactivate."""

import math

from fastapi import APIRouter, Query

from app.admin.schemas import AdminUserResponse, UserListResponse
from app.admin.service import AdminUserService
from app.core.deps import AdminUser, DbSession
from app.users.models import UserRole
from app.users.repository import RefreshTokenRepository, UserRepository

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _make_service(db: DbSession) -> AdminUserService:
    return AdminUserService(
        user_repo=UserRepository(db),
        rt_repo=RefreshTokenRepository(db),
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: UserRole | None = Query(None),  # noqa: B008
    is_active: bool | None = Query(None),  # noqa: B008
) -> UserListResponse:
    """Return a paginated list of all users. Admin only.

    Supports optional filtering by role and/or is_active status.
    Results are sorted by created_at DESC (newest first).
    """
    svc = _make_service(db)
    users, total = await svc.list_users(
        page=page,
        per_page=per_page,
        role=role,
        is_active=is_active,
    )
    return UserListResponse(
        items=[AdminUserResponse.model_validate(u) for u in users],
        total_count=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.patch("/{user_id}/deactivate", response_model=AdminUserResponse)
async def deactivate_user(
    user_id: int,
    db: DbSession,
    _admin: AdminUser,
) -> AdminUserResponse:
    """Deactivate a user account and revoke all their refresh tokens. Admin only.

    403 ADMN_CANNOT_DEACTIVATE_ADMIN if target user is an admin.
    404 USER_NOT_FOUND if user does not exist.
    Idempotent: returns 200 if user is already deactivated.
    """
    svc = _make_service(db)
    user = await svc.deactivate_user(user_id)
    return AdminUserResponse.model_validate(user)


@router.patch("/{user_id}/reactivate", response_model=AdminUserResponse)
async def reactivate_user(
    user_id: int,
    db: DbSession,
    _admin: AdminUser,
) -> AdminUserResponse:
    """Reactivate a previously deactivated user account. Admin only.

    404 USER_NOT_FOUND if user does not exist.
    Idempotent: returns 200 if user is already active.
    """
    svc = _make_service(db)
    user = await svc.reactivate_user(user_id)
    return AdminUserResponse.model_validate(user)
