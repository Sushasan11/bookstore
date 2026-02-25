"""Repository layer for User and RefreshToken database operations."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import RefreshToken, User, UserRole


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

    async def set_role_admin(self, user_id: int) -> None:
        """Promote a user to admin. Used only by the seed script."""
        await self.session.execute(
            update(User).where(User.id == user_id).values(role=UserRole.ADMIN)
        )


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
