"""Repository layer for User and RefreshToken database operations."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import OAuthAccount, RefreshToken, User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> User:
        """Create a new user with default role=USER.

        Does NOT accept a role parameter — role elevation is impossible via this method.
        """
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_oauth_user(self, email: str) -> User:
        """Create a new user without a password (OAuth-only).
        Default role=USER, hashed_password=None."""
        user = User(email=email, hashed_password=None)
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_role_admin(self, user_id: int) -> None:
        """Promote a user to admin. Used only by the seed script."""
        await self.session.execute(
            update(User).where(User.id == user_id).values(role=UserRole.ADMIN)
        )

    async def list_paginated(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """Return paginated list of users sorted by created_at DESC with optional filters."""
        stmt = select(User).order_by(User.created_at.desc())
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)
        result = await self.session.execute(stmt)
        users = list(result.scalars().all())
        return users, total or 0


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        token: str,
        user_id: int,
        expires_in_days: int = 7,
        token_family: uuid.UUID | None = None,
    ) -> RefreshToken:
        """Create a new refresh token.

        token_family: If provided, part of an existing rotation chain.
        If None, a new family UUID is generated (new login session).
        """
        rt = RefreshToken(
            token=token,
            user_id=user_id,
            token_family=token_family or uuid.uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        )
        self.session.add(rt)
        await self.session.flush()
        return rt

    async def get_by_token(self, token: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> None:
        """Revoke a single refresh token."""
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_family(self, token_family: uuid.UUID) -> None:
        """Revoke all non-revoked tokens in a family (theft detection)."""
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_family == token_family,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke all non-revoked refresh tokens for a user. Returns count of revoked tokens."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        return result.rowcount


class OAuthAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_provider_and_id(
        self, provider: str, provider_account_id: str
    ) -> OAuthAccount | None:
        result = await self.session.execute(
            select(OAuthAccount).where(
                OAuthAccount.oauth_provider == provider,
                OAuthAccount.oauth_account_id == provider_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, user_id: int, oauth_provider: str, oauth_account_id: str
    ) -> OAuthAccount:
        account = OAuthAccount(
            user_id=user_id,
            oauth_provider=oauth_provider,
            oauth_account_id=oauth_account_id,
        )
        self.session.add(account)
        await self.session.flush()
        return account
