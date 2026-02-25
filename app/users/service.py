"""Auth business logic: register, login, refresh, logout."""

from pwdlib import PasswordHash

from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)
from app.users.repository import RefreshTokenRepository, UserRepository

# Pre-compute at module load for timing-safe login.
# Even when user not found, we run verify_password against DUMMY_HASH
# so response time is constant regardless of whether the email exists.
_ph = PasswordHash.recommended()
DUMMY_HASH = _ph.hash("dummy_password_for_timing_safety_do_not_use")


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        rt_repo: RefreshTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.rt_repo = rt_repo

    async def register(self, email: str, password: str) -> tuple[str, str]:
        """Register a new user. Returns (access_token, refresh_token)."""
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise AppError(
                status_code=409,
                detail="Email already registered",
                code="AUTH_EMAIL_CONFLICT",
                field="email",
            )

        hashed = await hash_password(password)
        user = await self.user_repo.create(email=email, hashed_password=hashed)

        access_token = create_access_token(user.id, user.role.value)
        raw_rt = generate_refresh_token()
        await self.rt_repo.create(raw_rt, user.id)

        return access_token, raw_rt

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """Authenticate user. Returns (access_token, refresh_token).

        Always uses constant-time comparison to prevent email enumeration via timing.
        """
        user = await self.user_repo.get_by_email(email)
        if user is None:
            await verify_password(password, DUMMY_HASH)
            raise AppError(
                status_code=401,
                detail="Invalid email or password",
                code="AUTH_INVALID_CREDENTIALS",
            )

        if not await verify_password(password, user.hashed_password):
            raise AppError(
                status_code=401,
                detail="Invalid email or password",
                code="AUTH_INVALID_CREDENTIALS",
            )

        access_token = create_access_token(user.id, user.role.value)
        raw_rt = generate_refresh_token()
        await self.rt_repo.create(raw_rt, user.id)

        return access_token, raw_rt

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rotate a refresh token. Returns new (access_token, refresh_token).

        Theft detection: if a revoked token is reused, entire family is revoked.
        """
        rt = await self.rt_repo.get_by_token(refresh_token)

        if rt is None or rt.is_expired:
            raise AppError(
                status_code=401,
                detail="Invalid or expired refresh token",
                code="AUTH_REFRESH_INVALID",
            )

        if rt.is_revoked:
            await self.rt_repo.revoke_family(rt.token_family)
            raise AppError(
                status_code=401,
                detail="Refresh token reuse detected — all sessions revoked",
                code="AUTH_TOKEN_REUSE",
            )

        # Revoke current token, issue new pair
        await self.rt_repo.revoke(refresh_token)
        user = await self.user_repo.get_by_id(rt.user_id)
        if user is None or not user.is_active:
            raise AppError(
                status_code=401,
                detail="User not found or inactive",
                code="AUTH_USER_INACTIVE",
            )

        access_token = create_access_token(user.id, user.role.value)
        new_rt = generate_refresh_token()
        await self.rt_repo.create(new_rt, user.id, token_family=rt.token_family)

        return access_token, new_rt

    async def logout(self, refresh_token: str) -> None:
        """Revoke the current session's refresh token only. Idempotent."""
        rt = await self.rt_repo.get_by_token(refresh_token)
        if rt is None or rt.is_revoked:
            return
        await self.rt_repo.revoke(refresh_token)
