"""FastAPI dependency injection functions.

Provides reusable FastAPI dependencies for database session management
and authentication/authorization.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield a per-request AsyncSession with commit/rollback semantics."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for route parameter declarations
DbSession = Annotated[AsyncSession, Depends(get_db)]

# OAuth2 token extraction from Authorization: Bearer header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """Decode the JWT access token. Returns payload dict with sub and role.

    Role comes from JWT claims, NOT from DB lookup.
    """
    return decode_access_token(token)


def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Require admin role. Raises AppError(403) if role is not admin."""
    if current_user.get("role") != "admin":
        raise AppError(
            status_code=403,
            detail="Admin access required",
            code="AUTH_FORBIDDEN",
        )
    return current_user


# Type aliases for clean route parameter declarations
CurrentUser = Annotated[dict, Depends(get_current_user)]
AdminUser = Annotated[dict, Depends(require_admin)]
