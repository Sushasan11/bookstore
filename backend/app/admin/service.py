"""Admin business logic for user management: list, deactivate, reactivate."""

from app.core.exceptions import AppError
from app.users.models import User, UserRole
from app.users.repository import RefreshTokenRepository, UserRepository


class AdminUserService:
    def __init__(
        self, user_repo: UserRepository, rt_repo: RefreshTokenRepository
    ) -> None:
        self.user_repo = user_repo
        self.rt_repo = rt_repo

    async def list_users(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        return await self.user_repo.list_paginated(
            page=page,
            per_page=per_page,
            role=role,
            is_active=is_active,
        )

    async def deactivate_user(self, target_user_id: int) -> User:
        user = await self._get_user_or_404(target_user_id)
        if user.role == UserRole.ADMIN:
            raise AppError(
                status_code=403,
                detail="Cannot deactivate admin accounts",
                code="ADMN_CANNOT_DEACTIVATE_ADMIN",
            )
        # Idempotent: skip if already deactivated
        if user.is_active:
            user.is_active = False
            await self.user_repo.session.flush()
            await self.rt_repo.revoke_all_for_user(user.id)
        return user

    async def reactivate_user(self, target_user_id: int) -> User:
        user = await self._get_user_or_404(target_user_id)
        # Idempotent: skip if already active
        if not user.is_active:
            user.is_active = True
            await self.user_repo.session.flush()
        return user

    async def _get_user_or_404(self, user_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AppError(
                status_code=404,
                detail="User not found",
                code="USER_NOT_FOUND",
            )
        return user
