"""Auth endpoints: register, login, refresh, logout."""

from fastapi import APIRouter, status

from app.core.deps import DbSession
from app.users.repository import RefreshTokenRepository, UserRepository
from app.users.schemas import LoginRequest, RefreshRequest, TokenResponse, UserCreate
from app.users.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _make_service(db: DbSession) -> AuthService:
    """Instantiate AuthService with repositories bound to the current DB session."""
    return AuthService(
        user_repo=UserRepository(db),
        rt_repo=RefreshTokenRepository(db),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: UserCreate, db: DbSession) -> TokenResponse:
    """Register with email + password. Returns access and refresh tokens."""
    service = _make_service(db)
    access_token, refresh_token = await service.register(body.email, body.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    """Authenticate and receive token pair."""
    service = _make_service(db)
    access_token, refresh_token = await service.login(body.email, body.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    service = _make_service(db)
    access_token, refresh_token = await service.refresh(body.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: DbSession) -> None:
    """Revoke the provided refresh token. Idempotent."""
    service = _make_service(db)
    await service.logout(body.refresh_token)
