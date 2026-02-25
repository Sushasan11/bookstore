"""Security utilities: JWT access tokens and password hashing.

- Password hashing via pwdlib (Argon2id) — always in asyncio.to_thread
- JWT access tokens via PyJWT (HS256) — synchronous (fast, no I/O)
- Opaque refresh tokens via secrets.token_urlsafe (not JWTs)
"""

import asyncio
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

ALGORITHM = "HS256"

# Initialize once at module level — not per-request
_password_hash = PasswordHash.recommended()


async def hash_password(plain: str) -> str:
    """Hash a plain password in a thread pool.

    Argon2 is CPU-intensive (~50-200ms). Running in asyncio.to_thread()
    prevents blocking the event loop during registration/login.
    """
    return await asyncio.to_thread(_password_hash.hash, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a hash in a thread pool."""
    return await asyncio.to_thread(_password_hash.verify, plain, hashed)


def create_access_token(user_id: int, role: str) -> str:
    """Create a short-lived JWT access token (HS256).

    Claims: sub (str user_id), role, jti (UUID), iat, exp (15-min TTL).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token.

    Returns the full payload dict on success.
    Raises AppError(401) on expired or invalid token.
    MUST pass algorithms=["HS256"] to prevent algorithm confusion attack.
    """
    from app.core.exceptions import AppError

    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise AppError(
            status_code=401,
            detail="Access token has expired",
            code="AUTH_TOKEN_EXPIRED",
        )
    except InvalidTokenError:
        raise AppError(
            status_code=401,
            detail="Invalid access token",
            code="AUTH_TOKEN_INVALID",
        )


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token.

    Returns a random URL-safe string (512 bits of entropy).
    Refresh tokens are NOT JWTs — they are opaque strings stored in the DB.
    """
    return secrets.token_urlsafe(64)
