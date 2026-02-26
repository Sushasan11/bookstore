# Phase 2: Core Auth - Research

**Researched:** 2026-02-25
**Domain:** FastAPI JWT authentication — password hashing (pwdlib/argon2), JWT tokens (PyJWT), refresh token rotation with PostgreSQL storage, RBAC dependency injection
**Confidence:** HIGH (stack decisions pre-validated in STACK.md; PyJWT and pwdlib APIs verified via official docs; patterns verified against FastAPI official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase boundary:**
- Email/password registration and login with JWT access + refresh tokens, token revocation, and RBAC
- OAuth login (Google/GitHub) is Phase 3 — NOT in scope here

**Password & registration policy:**
- No email verification required — register and immediately receive tokens
- Minimum 8 characters password length, no complexity rules (follows NIST guidance)
- Email is the only identifier — no username or display name field at registration
- Duplicate email on registration returns 409 Conflict with clear message (email enumeration accepted for bookstore context)

**Token behavior & session rules:**
- Refresh token rotation on use — each refresh issues a new refresh token and revokes the old one; if a revoked token is reused, revoke the entire family (theft detection)
- Multiple active sessions allowed — each login creates an independent refresh token; devices don't interfere with each other
- Access token TTL: 15 minutes
- Refresh token TTL: 7 days
- Logout revokes only the current session's refresh token (the one sent in the request); other sessions remain active

**Error responses & security posture:**
- Generic error on login failure: always "Invalid email or password" regardless of whether email exists (prevents email enumeration via login)
- No rate limiting in this phase — defer to a future middleware/infrastructure concern
- No account lockout mechanism — failed logins return 401 each time
- Standard REST HTTP status codes: 401 bad credentials / expired token, 403 insufficient role, 409 duplicate email, 422 validation errors

**Role model & admin bootstrapping:**
- Fixed role enum: `user` and `admin` — no roles table, no extensibility needed
- First admin created via CLI seed command (management script), not through the API
- Registration always defaults to `user` role — no request payload can set or elevate the role
- Role embedded in JWT claims (`role` field) — no DB lookup needed for authorization checks; role changes take effect at next token issuance

### Claude's Discretion

- Refresh token storage schema design (DB table structure, indexes)
- Password hashing configuration (argon2 parameters)
- JWT signing algorithm choice
- Exact JSON response shapes for auth endpoints
- Seed command implementation approach (Click CLI, standalone script, etc.)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can sign up with email and password | pwdlib/argon2 hashing in thread pool; Alembic migration for users table; UserRepository.create(); duplicate email → 409 |
| AUTH-02 | User can log in and receive JWT access + refresh tokens | PyJWT encode with sub/role/jti/exp; refresh_tokens DB table; timing-safe password verify with DUMMY_HASH |
| AUTH-03 | User can refresh expired access token using refresh token | refresh_tokens lookup by jti; rotation: revoke old, issue new; family revocation on reuse detection |
| AUTH-04 | User can log out (refresh token revoked) | refresh_tokens.revoke(jti) sets revoked_at; other sessions remain active |
| AUTH-05 | Endpoints enforce role-based access (admin vs user) | get_current_user decodes access token; require_admin checks role claim; 401 for invalid token, 403 for wrong role |

</phase_requirements>

---

## Summary

Phase 2 builds the complete authentication layer on top of the Phase 1 infrastructure. All libraries are pre-installed in pyproject.toml (PyJWT with `[crypto]` extra, pwdlib with `[argon2]` extra, email-validator). The Phase 1 scaffold provides `app/core/security.py` (currently a placeholder), `app/core/deps.py` (has `get_db` only — Phase 2 adds `get_current_user` and `require_admin`), `app/users/__init__.py` (empty package), and `app/db/base.py` (ready for the User model import). No new library installations are needed.

The critical design decision already locked is refresh token rotation with family-level theft detection: each use of a refresh token issues a new one (rotation), and if a previously-revoked token is reused, all tokens for that family are revoked (detection). This requires a `refresh_tokens` DB table with `token_family` UUID column. The access token uses PyJWT with HS256 (HMAC-SHA256); the refresh token is an opaque random UUID stored in the DB, not a JWT — this is the correct pattern for long-lived revocable tokens. Alternatively, if refresh tokens are JWTs, the `jti` must be stored in the DB. Research recommends storing the full refresh token as a random UUID (not a JWT) for simplicity and to avoid the overhead of JWT decoding on every refresh.

Password hashing with `pwdlib[argon2]` is CPU-intensive and MUST run in a thread pool to avoid blocking the async event loop. Use `asyncio.to_thread(password_hash.hash, plain)` and `asyncio.to_thread(password_hash.verify, plain, hashed)` in async routes. The FastAPI official docs use `PasswordHash.recommended()` (no manual argon2 parameter tuning needed — defaults are secure).

**Primary recommendation:** Use PyJWT HS256 for access tokens (stateless, 15-min TTL), store refresh tokens as random UUID tokens in a `refresh_tokens` table (revocable, 7-day TTL, with `token_family` for theft detection), and run all password hashing in `asyncio.to_thread()`.

---

## Standard Stack

### Core (all pre-installed from Phase 1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | 2.11.0 | JWT encode/decode | FastAPI's current official recommendation; replaces abandoned python-jose; lightweight, standards-compliant |
| pwdlib[argon2] | 0.3.0 | Password hashing | FastAPI's current official recommendation; replaces unmaintained passlib; Argon2 is memory-hard, OWASP-recommended |
| SQLAlchemy | 2.0.47 | refresh_tokens ORM model | Already installed; async-native |
| Alembic | 1.18.4 | DB migration for users + refresh_tokens tables | Already installed; configured in Phase 1 |
| pydantic-settings | 2.13.1 | SECRET_KEY, token TTL config | Already installed; reads from .env |
| email-validator | latest | EmailStr validation in UserCreate schema | Already installed |
| FastAPI security | 0.133.0 | OAuth2PasswordBearer for token extraction | Bundled with FastAPI |

### No New Dependencies Required

All required libraries are already in pyproject.toml from Phase 1 planning. The placeholder `app/core/security.py` file references PyJWT and pwdlib and is ready to be implemented.

```bash
# Verify installed (no new installs needed):
poetry show pyjwt pwdlib email-validator
```

If the `[crypto]` extra for PyJWT is not already installed (needed for RSA algorithms, optional for HS256):
```bash
poetry add "pyjwt[crypto]@^2.11.0"
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Opaque UUID refresh tokens (stored in DB) | JWT refresh tokens (jti in DB) | JWT refresh adds decode overhead on every /refresh call; opaque tokens are simpler — just a DB lookup by token string. Either works; research recommends opaque for revocable long-lived tokens |
| HS256 (HMAC) for access tokens | RS256 (RSA) | RS256 needed only for multi-service scenarios where services verify tokens without shared secret. Single-service bookstore: HS256 is correct and simpler |
| asyncio.to_thread() for hashing | run_in_executor(None, ...) | Both work; asyncio.to_thread() is cleaner Python 3.9+ syntax; use it |
| PasswordHash.recommended() | Custom argon2 params | recommended() uses secure Argon2id defaults; no reason to tune unless benchmarking shows unacceptable latency |

---

## Architecture Patterns

### Recommended Phase 2 File Structure

```
app/
├── core/
│   ├── security.py          # JWT encode/decode; password hash/verify (asyncio.to_thread)
│   └── deps.py              # get_current_user, require_admin (NEW in Phase 2)
├── users/
│   ├── models.py            # User SQLAlchemy model + UserRole enum  (NEW)
│   ├── schemas.py           # UserCreate, UserResponse, TokenResponse (NEW)
│   ├── router.py            # /auth/register, /auth/login, /auth/refresh, /auth/logout (NEW)
│   ├── service.py           # UserService, AuthService (NEW)
│   └── repository.py        # UserRepository, RefreshTokenRepository (NEW)
├── db/
│   └── base.py              # Add: from app.users.models import User, RefreshToken
alembic/
└── versions/
    └── XXXX_create_users_and_refresh_tokens.py   # (NEW via autogenerate)
scripts/
└── seed_admin.py            # CLI script to create first admin user (NEW)
tests/
└── test_auth.py             # Integration tests for all 4 auth endpoints (NEW)
```

### Pattern 1: User and RefreshToken SQLAlchemy Models

**What:** SQLAlchemy 2.0 style `Mapped` annotations. `UserRole` is a Python `str` enum stored as a PostgreSQL ENUM type. `RefreshToken` has a `token_family` UUID column for theft detection across rotations.

**When to use:** Both models created together and migrated in one Alembic migration.

```python
# app/users/models.py
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"), default=UserRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    token_family: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        from datetime import timezone
        return self.expires_at < datetime.now(tz=timezone.utc)
```

**Critical:** After creating this file, add imports to `app/db/base.py`:
```python
# app/db/base.py — add these imports
from app.users.models import User, RefreshToken  # noqa: F401
```

Then run: `poetry run alembic revision --autogenerate -m "create_users_and_refresh_tokens"`

### Pattern 2: JWT Security Functions in app/core/security.py

**What:** Implements the token encode/decode functions. Access tokens are short-lived JWTs with `sub` (user ID as string), `role`, `jti` (UUID), `iat`, `exp`. Refresh tokens are random UUID strings (not JWTs) stored in the DB.

**Algorithm choice (Claude's discretion):** HS256 — correct for a single-service API where the server both issues and verifies tokens. RS256 is needed only when external services verify tokens without the shared secret.

```python
# app/core/security.py
import asyncio
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"

# Password hashing — PasswordHash.recommended() uses Argon2id with secure defaults
_password_hash = PasswordHash.recommended()


async def hash_password(plain: str) -> str:
    """Hash a plain password in a thread pool to avoid blocking the event loop.

    Argon2 is CPU-intensive. Running it on the async loop directly blocks all
    concurrent requests during the ~50-200ms hashing window.
    """
    return await asyncio.to_thread(_password_hash.hash, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a hash in a thread pool."""
    return await asyncio.to_thread(_password_hash.verify, plain, hashed)


def create_access_token(user_id: int, role: str) -> str:
    """Create a short-lived JWT access token.

    Claims:
      sub: str(user_id) — standard JWT subject claim
      role: str — user role for RBAC without DB lookup
      jti: UUID — unique token ID (enables future blocklisting)
      iat: datetime — issued at
      exp: datetime — expiration (15 minutes from now)
    """
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

    Raises AppError (401) on:
      - ExpiredSignatureError: token has expired
      - InvalidTokenError: token is malformed, signature invalid, etc.
    """
    from app.core.exceptions import AppError  # local import avoids circular

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
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
    """Generate a cryptographically secure random refresh token.

    Refresh tokens are opaque random strings stored in the DB — NOT JWTs.
    This is simpler and more secure for long-lived revocable tokens:
    no need to decode, just look up by token string.
    """
    return secrets.token_urlsafe(64)  # 512 bits of entropy
```

### Pattern 3: UserRepository and RefreshTokenRepository

**What:** Repository layer performs all DB operations. UserRepository handles user lookup and creation. RefreshTokenRepository handles token creation, lookup, rotation, and family revocation.

```python
# app/users/repository.py
from datetime import UTC, datetime, timedelta
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import RefreshToken, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()  # flush to get the auto-generated id
        return user

    async def set_role_admin(self, user_id: int) -> None:
        """Used by the seed script to promote a user to admin."""
        from app.users.models import UserRole
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
        """Revoke a single refresh token (logout)."""
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_family(self, token_family: uuid.UUID) -> None:
        """Revoke all tokens in a family (theft detection).

        Called when a revoked token is reused — indicates the token was stolen.
        Revoking the entire family forces re-authentication on all sessions
        that derived from the compromised lineage.
        """
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_family == token_family,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
```

### Pattern 4: AuthService — Business Logic

**What:** Service layer contains all business rules. No FastAPI imports. Raises `AppError` for domain errors.

```python
# app/users/service.py (key methods)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)
from app.core.exceptions import AppError
from app.users.repository import RefreshTokenRepository, UserRepository

# DUMMY_HASH: used in timing-safe login to prevent email enumeration via timing
# Run this once at module load — not per-request
import asyncio
from pwdlib import PasswordHash
_ph = PasswordHash.recommended()
DUMMY_HASH = _ph.hash("dummy_password_for_timing_safety")


class AuthService:
    def __init__(self, user_repo: UserRepository, rt_repo: RefreshTokenRepository) -> None:
        self.user_repo = user_repo
        self.rt_repo = rt_repo

    async def register(self, email: str, password: str) -> tuple[str, str]:
        """Register a new user. Returns (access_token, refresh_token)."""
        if len(password) < 8:
            raise AppError(422, "Password must be at least 8 characters", "AUTH_WEAK_PASSWORD", "password")

        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise AppError(409, "Email already registered", "AUTH_EMAIL_CONFLICT", "email")

        hashed = await hash_password(password)
        user = await self.user_repo.create(email=email, hashed_password=hashed)

        access_token = create_access_token(user.id, user.role.value)
        raw_rt = generate_refresh_token()
        await self.rt_repo.create(raw_rt, user.id)

        return access_token, raw_rt

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """Authenticate user. Returns (access_token, refresh_token).

        Always uses a constant-time comparison path to prevent timing attacks
        that would reveal whether an email exists.
        """
        user = await self.user_repo.get_by_email(email)
        if user is None:
            # Run verify against dummy hash to keep timing constant
            await verify_password(password, DUMMY_HASH)
            raise AppError(401, "Invalid email or password", "AUTH_INVALID_CREDENTIALS")

        if not await verify_password(password, user.hashed_password):
            raise AppError(401, "Invalid email or password", "AUTH_INVALID_CREDENTIALS")

        access_token = create_access_token(user.id, user.role.value)
        raw_rt = generate_refresh_token()
        await self.rt_repo.create(raw_rt, user.id)

        return access_token, raw_rt

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rotate a refresh token. Returns new (access_token, refresh_token).

        Theft detection: if a revoked token is reused, revoke the entire family.
        """
        rt = await self.rt_repo.get_by_token(refresh_token)

        if rt is None or rt.is_expired:
            raise AppError(401, "Invalid or expired refresh token", "AUTH_REFRESH_INVALID")

        if rt.is_revoked:
            # Token reuse detected — revoke the entire family
            await self.rt_repo.revoke_family(rt.token_family)
            raise AppError(401, "Refresh token reuse detected — all sessions revoked", "AUTH_TOKEN_REUSE")

        # Revoke the current token and issue new ones
        await self.rt_repo.revoke(refresh_token)
        user = await self.user_repo.get_by_id(rt.user_id)
        if user is None or not user.is_active:
            raise AppError(401, "User not found or inactive", "AUTH_USER_INACTIVE")

        access_token = create_access_token(user.id, user.role.value)
        new_rt = generate_refresh_token()
        # New token inherits the same family for theft detection chain
        await self.rt_repo.create(new_rt, user.id, token_family=rt.token_family)

        return access_token, new_rt

    async def logout(self, refresh_token: str) -> None:
        """Revoke the current session's refresh token only."""
        rt = await self.rt_repo.get_by_token(refresh_token)
        if rt is None or rt.is_revoked:
            return  # Already revoked or doesn't exist — idempotent
        await self.rt_repo.revoke(refresh_token)
```

### Pattern 5: Endpoint Definitions

**What:** Auth router mounts under `/auth` prefix. JSON body for all endpoints (not form data — CONTEXT.md does not specify OAuth2 form, and for REST API JSON is cleaner). The `POST /auth/login` uses JSON body with `email` + `password` fields.

```python
# app/users/router.py
from fastapi import APIRouter, status
from app.core.deps import DbSession
from app.users.schemas import UserCreate, LoginRequest, TokenResponse, RefreshRequest
from app.users.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: DbSession):
    service = AuthService(...)
    access_token, refresh_token = await service.register(body.email, body.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession):
    ...

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbSession):
    ...

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: DbSession):
    ...
```

**Include in app/main.py:**
```python
from app.users.router import router as auth_router
application.include_router(auth_router)
```

### Pattern 6: get_current_user and require_admin Dependencies

**What:** Adds to existing `app/core/deps.py`. `get_current_user` extracts the Bearer token from the Authorization header via `OAuth2PasswordBearer`, decodes it, and returns the user ID and role from claims (no DB lookup needed — role is in the token). `require_admin` builds on top of it.

**Critical design note:** Role comes from the JWT claims, NOT from a DB lookup, per the locked decision. This means role changes don't take effect until the next login (new token issuance). This is the agreed-upon trade-off.

```python
# app/core/deps.py — additions for Phase 2
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_access_token
from app.core.exceptions import AppError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """Decode the JWT access token. Returns payload dict with sub and role.

    Raises AppError(401) on invalid or expired token.
    Does NOT hit the database — role is trusted from JWT claims.
    """
    return decode_access_token(token)


def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Require that the current user has the admin role.

    Raises AppError(403) if the user's role is not 'admin'.
    """
    if current_user.get("role") != "admin":
        raise AppError(
            status_code=403,
            detail="Admin access required",
            code="AUTH_FORBIDDEN",
        )
    return current_user


# Type aliases for clean route declarations
CurrentUser = Annotated[dict, Depends(get_current_user)]
AdminUser = Annotated[dict, Depends(require_admin)]
```

**Usage in other routers (Phase 4+):**
```python
from app.core.deps import CurrentUser, AdminUser

@router.post("/books")
async def create_book(body: BookCreate, _admin: AdminUser, db: DbSession):
    ...

@router.get("/my-orders")
async def list_orders(user: CurrentUser, db: DbSession):
    user_id = int(user["sub"])
    ...
```

### Pattern 7: Pydantic Schemas

```python
# app/users/schemas.py
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

### Pattern 8: Admin Seed Command

**What (Claude's discretion):** A standalone Python script using Click or a direct `asyncio.run()` call. Simpler is better — a single-file script in `scripts/seed_admin.py` that creates a user with `admin` role.

**Recommended approach:** Click CLI for ergonomics:
```python
# scripts/seed_admin.py
import asyncio
import click
from app.db.session import AsyncSessionLocal
from app.users.repository import UserRepository
from app.core.security import hash_password

@click.command()
@click.option("--email", required=True, prompt="Admin email")
@click.option("--password", required=True, prompt="Admin password", hide_input=True)
async def create_admin(email: str, password: str):
    hashed = await hash_password(password)
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.create(email=email, hashed_password=hashed)
        await repo.set_role_admin(user.id)
        await session.commit()
    click.echo(f"Admin created: {email}")

if __name__ == "__main__":
    asyncio.run(create_admin.main(standalone_mode=False))
```

### Anti-Patterns to Avoid

- **Synchronous password hashing in async route:** `_password_hash.hash(plain)` called directly in an `async def` route blocks the event loop for ~50-200ms per call. Always wrap in `asyncio.to_thread()`.

- **Refresh tokens as JWTs without DB storage:** JWT refresh tokens cannot be revoked without a blocklist. The CONTEXT.md requires revocation on logout — this mandates DB storage.

- **Role lookup from DB on every request:** The locked decision explicitly states role comes from JWT claims. Don't add a DB lookup in `get_current_user` — it defeats the purpose of stateless access tokens and adds latency to every protected endpoint.

- **Using `OAuth2PasswordRequestForm` (form data) for login:** The FastAPI tutorial uses form data for compatibility with OAuth2 clients. For a REST JSON API, a JSON body is correct and cleaner. The CONTEXT.md does not require OAuth2 form compatibility.

- **Not importing RefreshToken in app/db/base.py:** If the `RefreshToken` model is not imported in `base.py`, Alembic will not see the `refresh_tokens` table and will generate an empty migration.

- **Forgetting `server_default=func.now()` vs `default=func.now()`:** In SQLAlchemy async, `default=func.now()` is a Python-side default computed at ORM level. `server_default=func.now()` is a SQL-side default. For `created_at`, `server_default` is correct — it is set by the DB and the ORM doesn't need to compute it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt calls | `pwdlib[argon2]` PasswordHash.recommended() | Correct Argon2id parameters, constant-time comparison, upgrade support via verify_and_update() |
| JWT encode/decode | Manual HMAC + base64 | `PyJWT` jwt.encode / jwt.decode | Correct claim validation (exp, iat, nbf), exception hierarchy, algorithm safety |
| Bearer token extraction | Custom Authorization header parsing | `OAuth2PasswordBearer(tokenUrl=...)` | FastAPI handles extraction, 401 on missing header, OpenAPI docs integration |
| Refresh token generation | UUID4 or MD5 | `secrets.token_urlsafe(64)` | Cryptographically secure; 512 bits entropy; URL-safe encoding |
| Timing-safe login | Short-circuit on missing user | Always call verify_password (even with DUMMY_HASH) | Prevents timing attacks that reveal email existence |

**Key insight:** Password hashing and JWT validation have subtle security properties (timing attacks, algorithm confusion, clock skew) that custom implementations almost always get wrong.

---

## Common Pitfalls

### Pitfall 1: Blocking Event Loop with Synchronous Password Hashing

**What goes wrong:** `PasswordHash.recommended().hash(plain)` is called directly in an `async def` endpoint. The Argon2 computation (~100ms) blocks the event loop. All concurrent requests stall during every registration or login.

**Why it happens:** Developers see `pwdlib` advertised as simple and call it synchronously, not realizing async routes still block on CPU-bound operations.

**How to avoid:** Wrap ALL `hash()` and `verify()` calls in `asyncio.to_thread()`:
```python
hashed = await asyncio.to_thread(_password_hash.hash, plain_password)
matches = await asyncio.to_thread(_password_hash.verify, plain_password, hashed)
```

**Warning signs:** Login endpoint takes 100-300ms even under low load; event loop warnings in logs; other endpoints slow down during heavy auth traffic.

### Pitfall 2: Missing DUMMY_HASH for Timing-Safe Login

**What goes wrong:** Login endpoint short-circuits before calling `verify_password` when the user email does not exist. An attacker can measure response time: fast response = email not found, slow response = email exists but wrong password. This leaks user emails despite the generic error message.

**Why it happens:** Developers add the early-return check (`if user is None: raise AppError(401, ...)`) without realizing the hashing step takes measurable time.

**How to avoid:** Pre-compute a `DUMMY_HASH` at module load time. When the user is not found, call `await verify_password(plain_password, DUMMY_HASH)` before raising the error. The locked decision requires "Invalid email or password" generic message — the timing-safe path makes this actually secure.

**Warning signs:** Login response time is measurably different (~100ms) for existing vs. non-existing emails.

### Pitfall 3: Refresh Token Reuse Revokes Wrong Scope

**What goes wrong:** Token theft detection revokes ALL of a user's tokens regardless of family. A user with multiple sessions loses all sessions when any single family is compromised.

**Why it happens:** Simple implementation revokes `WHERE user_id = X` instead of `WHERE token_family = X`.

**How to avoid:** The `token_family` UUID column links only the chain of rotated tokens from a single login session. Family revocation (`WHERE token_family = stolen_family`) only kills the compromised lineage. Other sessions (different families from other logins) remain active.

**Warning signs:** Users report losing all sessions on devices they did not log out from.

### Pitfall 4: Not Adding User/RefreshToken Imports to app/db/base.py

**What goes wrong:** `alembic revision --autogenerate` produces an empty migration. The `users` and `refresh_tokens` tables are never created.

**Why it happens:** The Phase 1 scaffolding explicitly commented "add model imports here in future phases" — it's easy to implement the models but forget to add the imports.

**How to avoid:** Immediately after creating `app/users/models.py`, add to `app/db/base.py`:
```python
from app.users.models import User, RefreshToken  # noqa: F401
```
Then verify the autogenerated migration is non-empty before running it.

**Warning signs:** `alembic revision --autogenerate -m "..."` produces a file with empty `upgrade()` function.

### Pitfall 5: JWT Algorithm Confusion Attack

**What goes wrong:** An attacker changes the `alg` header in the JWT to `none` or `HS256` (when server uses RS256), and the server accepts the tampered token.

**Why it happens:** PyJWT requires passing `algorithms=["HS256"]` (a list) to `jwt.decode()`. If the list is omitted or allows multiple algorithms, the library may accept `alg: none`.

**How to avoid:** Always pass `algorithms=["HS256"]` (explicit list with only one algorithm) to `jwt.decode()`. Never allow `"none"` in the algorithms list.

```python
# CORRECT
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

# WRONG — allows algorithm confusion
payload = jwt.decode(token, settings.SECRET_KEY)
```

**Warning signs:** jwt.decode() call missing the `algorithms` parameter.

### Pitfall 6: Role Elevation via Registration

**What goes wrong:** A malicious user sends `{"email": "x@x.com", "password": "pass1234", "role": "admin"}` to POST /auth/register. If the UserCreate schema accepts a `role` field and passes it to User creation, the attacker becomes an admin.

**Why it happens:** Schema has a `role` field (for response schemas) that bleeds into input schemas.

**How to avoid:** `UserCreate` schema MUST NOT have a `role` field. The User model defaults `role` to `UserRole.USER`. The `UserRepository.create()` method does not accept a role parameter. Registration always creates `user` role.

**Warning signs:** `UserCreate` Pydantic model has a `role` field; `user_repo.create()` accepts a role parameter.

### Pitfall 7: Expired Refresh Tokens Not Cleaned Up (Table Bloat)

**What goes wrong:** The `refresh_tokens` table grows unbounded as 7-day tokens accumulate. With multiple active sessions per user, the table grows proportionally.

**Why it happens:** Phase 2 doesn't implement a cleanup strategy — it's not needed for MVP, but becomes a problem over time.

**How to avoid:** Include an index on `expires_at` column. Document that a periodic cleanup query is needed:
```sql
DELETE FROM refresh_tokens WHERE expires_at < NOW() - INTERVAL '1 day';
```
This can be a future background task (Phase 8+) or a cron job. For v1, the index prevents slow lookups even as the table grows.

**Warning signs:** refresh_tokens table growing without bound; slow token lookups as table grows.

---

## Code Examples

### Verified: PyJWT encode/decode pattern (Source: pyjwt.readthedocs.io/en/latest/usage.html)

```python
import jwt
from datetime import datetime, timezone, timedelta
import uuid

# Encode
payload = {
    "sub": "42",
    "role": "user",
    "jti": str(uuid.uuid4()),
    "iat": datetime.now(tz=timezone.utc),
    "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=15),
}
token = jwt.encode(payload, "secret_key", algorithm="HS256")

# Decode — MUST pass algorithms list to prevent algorithm confusion
decoded = jwt.decode(token, "secret_key", algorithms=["HS256"])

# Exception hierarchy
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
try:
    decoded = jwt.decode(token, "secret_key", algorithms=["HS256"])
except ExpiredSignatureError:
    # Token expired
    ...
except InvalidTokenError:
    # Malformed, bad signature, etc.
    ...
```

### Verified: pwdlib API (Source: frankie567.github.io/pwdlib/reference/pwdlib/)

```python
from pwdlib import PasswordHash

# Initialize once at module level
password_hash = PasswordHash.recommended()  # Uses Argon2id defaults

# Hash
hashed = password_hash.hash("mypassword")

# Verify — returns bool
is_correct = password_hash.verify("mypassword", hashed)

# Verify and upgrade — returns (bool, updated_hash | None)
# Use this to migrate old bcrypt hashes to argon2 transparently
is_correct, new_hash = password_hash.verify_and_update("mypassword", old_hash)
if new_hash:
    # Store new_hash in DB — silently migrated to argon2
    ...

# In async context — MUST use asyncio.to_thread
import asyncio
hashed = await asyncio.to_thread(password_hash.hash, plain_password)
matches = await asyncio.to_thread(password_hash.verify, plain_password, stored_hash)
```

### Verified: OAuth2PasswordBearer pattern (Source: fastapi.tiangolo.com/tutorial/security/simple-oauth2/)

```python
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from fastapi import Depends

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# In dependency:
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    # oauth2_scheme extracts "Bearer <token>" from Authorization header
    # FastAPI returns 401 automatically if header is missing
    return decode_access_token(token)
```

### Verified: Timing-safe login (Source: fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

```python
# Pre-computed at module load — NEVER per-request
DUMMY_HASH = PasswordHash.recommended().hash("dummypassword")

async def authenticate_user(email: str, password: str) -> User:
    user = await user_repo.get_by_email(email)
    if not user:
        # Always verify against dummy hash to keep response time consistent
        await asyncio.to_thread(password_hash.verify, password, DUMMY_HASH)
        raise AppError(401, "Invalid email or password", "AUTH_INVALID_CREDENTIALS")
    if not await asyncio.to_thread(password_hash.verify, password, user.hashed_password):
        raise AppError(401, "Invalid email or password", "AUTH_INVALID_CREDENTIALS")
    return user
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| passlib for password hashing | pwdlib[argon2] | 2024 (FastAPI PR #13917) | passlib is unmaintained + Python 3.13 removed `crypt` module; passlib crashes on 3.13 |
| python-jose for JWT | PyJWT 2.11.0 | 2023-2024 | python-jose abandoned; PyJWT is FastAPI's official recommendation |
| bcrypt work factor as CPU-bound | asyncio.to_thread() for any CPU-bound hash | Python 3.9+ | Thread pool offloading is the correct async pattern; prevents event loop blocking |
| Storing refresh tokens as JWTs with jti | Opaque random token strings in DB | Current best practice | Simpler to revoke; no decode overhead on refresh; jti still on access token for future blocklisting |
| Single algorithm list in jwt.decode | Explicit `algorithms=["HS256"]` list | PyJWT 2.x | Prevents algorithm confusion attack (`alg: none`); mandatory for security |

**Deprecated/outdated (confirmed, do not use):**
- `passlib`: Crashes on Python 3.13 (project uses 3.13). Not an option.
- `python-jose`: Last PyPI release 2022. Not an option.
- `jwt.decode(token, key)` without `algorithms` param: Allows algorithm confusion. Never use.

---

## Open Questions

1. **Refresh token in request body vs. cookie**
   - What we know: CONTEXT.md is silent on transport mechanism; the access token is a Bearer header
   - What's unclear: Should the refresh token be sent in the request body (JSON) or an HttpOnly cookie?
   - Recommendation: Use JSON request body (`{"refresh_token": "..."}`) for POST /auth/refresh and POST /auth/logout. The project is API-first without a browser frontend, so cookie management adds complexity without benefit. This is Claude's discretion.

2. **UserResponse at registration: return full TokenResponse or minimal UserResponse?**
   - What we know: SUCCESS criteria says "receive a 201 with their user record" (AUTH-01)
   - What's unclear: Does "user record" mean just user fields, or the token pair too?
   - Recommendation: Return a `TokenResponse` (access + refresh token) on register so the user is immediately authenticated after registration, consistent with "register and immediately receive tokens" locked decision. Include the user object nested in the response if needed, or make a separate `/users/me` endpoint in a later phase.

3. **Dependency injection style for services**
   - What we know: Phase 1 established `DbSession = Annotated[AsyncSession, Depends(get_db)]` pattern
   - What's unclear: Should AuthService be injected via `Depends()` or instantiated inline in route handlers?
   - Recommendation: Instantiate inline in routes (not via Depends) for simplicity — the service constructor takes repositories which take the session. Service instantiation is cheap. Avoid over-engineering DI for this phase.

4. **Click as dependency for seed script**
   - What we know: Click is not currently in pyproject.toml
   - What's unclear: Add Click as a dependency for the seed script, or use argparse/typer/plain asyncio.run()?
   - Recommendation: Use Python's `sys.argv` + `asyncio.run()` directly, or add `typer` (modern Click alternative with type hints). Avoid adding Click just for this one script unless Click is already planned for other CLI needs.

---

## Sources

### Primary (HIGH confidence)

- [PyJWT 2.11.0 official docs — Usage Examples](https://pyjwt.readthedocs.io/en/latest/usage.html) — encode/decode patterns, exception hierarchy, jti claim
- [PyJWT 2.11.0 official docs — API Reference](https://pyjwt.readthedocs.io/en/latest/api.html) — jwt.encode/decode parameters
- [FastAPI official docs — OAuth2 JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) — pwdlib usage, PasswordHash.recommended(), timing-safe login, get_current_user pattern
- [FastAPI official docs — Simple OAuth2](https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/) — OAuth2PasswordBearer, tokenUrl, Bearer extraction
- [pwdlib official docs — API Reference](https://frankie567.github.io/pwdlib/reference/pwdlib/) — PasswordHash constructor, hash(), verify(), verify_and_update()
- Project STACK.md (D:/Python/claude-test/.planning/research/STACK.md) — library versions pre-validated, PyJWT 2.11.0 and pwdlib 0.3.0 confirmed on PyPI
- Project PITFALLS.md (D:/Python/claude-test/.planning/research/PITFALLS.md) — JWT non-revocation pitfall, async blocking, timing attack patterns
- Project ARCHITECTURE.md (D:/Python/claude-test/.planning/research/ARCHITECTURE.md) — three-layer pattern, User model reference design

### Secondary (MEDIUM confidence)

- [descope.com — Developer's Guide to Refresh Token Rotation](https://www.descope.com/blog/post/refresh-token-rotation) — token family revocation pattern, reuse detection behavior; cross-referenced with CONTEXT.md decisions

### Tertiary (LOW confidence — for pattern confirmation only)

- Multiple WebSearch results on refresh token DB schemas — consistent with token_family UUID column approach; pattern verified against official docs conceptually

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries pre-validated in STACK.md; no new dependencies; API patterns verified via official docs
- Architecture (three-layer pattern): HIGH — locked from Phase 1; confirmed from ARCHITECTURE.md
- JWT encode/decode: HIGH — verified directly from pyjwt.readthedocs.io
- pwdlib API: HIGH — verified directly from frankie567.github.io/pwdlib official docs
- Refresh token rotation/family pattern: MEDIUM-HIGH — conceptually verified; DB schema is Claude's discretion per CONTEXT.md
- asyncio.to_thread for hashing: MEDIUM — standard Python 3.9+ async pattern; no pwdlib-specific doc confirms it but the underlying mechanism is well-established
- Timing-safe login: HIGH — verified directly from FastAPI official JWT tutorial (DUMMY_HASH pattern)

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days; all libraries stable, FastAPI auth docs well-settled)
