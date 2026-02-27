"""Auth endpoints: register, login, refresh, logout, OAuth (Google)."""

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from starlette.requests import Request

from app.core.config import get_settings
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.core.oauth import oauth
from app.users.repository import (
    OAuthAccountRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.users.schemas import (
    GoogleTokenRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
)
from app.users.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _make_service(db: DbSession) -> AuthService:
    """Instantiate AuthService with repositories bound to the current DB session."""
    return AuthService(
        user_repo=UserRepository(db),
        rt_repo=RefreshTokenRepository(db),
        oauth_repo=OAuthAccountRepository(db),
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


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google's consent screen for OAuth login."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(request: Request, db: DbSession) -> TokenResponse:
    """Handle Google's OAuth callback. Returns JWT token pair."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        raise AppError(
            status_code=401,
            detail=f"Google authentication failed: {e.description}",
            code="AUTH_OAUTH_FAILED",
        ) from e

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        raise AppError(
            status_code=401,
            detail="Could not retrieve email from Google",
            code="AUTH_OAUTH_NO_EMAIL",
        )

    if not userinfo.get("email_verified"):
        raise AppError(
            status_code=401,
            detail="Google email is not verified",
            code="AUTH_OAUTH_EMAIL_UNVERIFIED",
        )

    service = _make_service(db)
    access_token, refresh_token = await service.oauth_login(
        provider="google",
        provider_user_id=userinfo["sub"],
        email=userinfo["email"],
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/google/token", response_model=TokenResponse)
async def google_token_exchange(body: GoogleTokenRequest, db: DbSession) -> TokenResponse:
    """Exchange a Google id_token (from NextAuth) for a FastAPI token pair.

    This endpoint validates the Google id_token using Google's public keys,
    extracts the user's email and Google user ID, then delegates to the
    existing oauth_login() service method.

    Used by NextAuth.js v5 jwt callback after Google OAuth consent completes
    on the frontend — avoids conflicting with Authlib's server-side OAuth state.
    """
    settings = get_settings()
    try:
        idinfo = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise AppError(
            status_code=401,
            detail="Invalid Google token",
            code="AUTH_GOOGLE_INVALID_TOKEN",
        ) from e

    if not idinfo.get("email_verified"):
        raise AppError(
            status_code=401,
            detail="Google email is not verified",
            code="AUTH_OAUTH_EMAIL_UNVERIFIED",
        )

    service = _make_service(db)
    access_token, refresh_token = await service.oauth_login(
        provider="google",
        provider_user_id=idinfo["sub"],
        email=idinfo["email"],
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
