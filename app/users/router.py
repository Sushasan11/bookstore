"""Auth endpoints: register, login, refresh, logout, OAuth (Google, GitHub)."""

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, status
from starlette.requests import Request

from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.core.oauth import oauth
from app.users.repository import OAuthAccountRepository, RefreshTokenRepository, UserRepository
from app.users.schemas import LoginRequest, RefreshRequest, TokenResponse, UserCreate
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
        )

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


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------


@router.get("/github")
async def github_login(request: Request):
    """Redirect to GitHub's authorization screen for OAuth login."""
    redirect_uri = request.url_for("github_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback", response_model=TokenResponse)
async def github_callback(request: Request, db: DbSession) -> TokenResponse:
    """Handle GitHub's OAuth callback. Returns JWT token pair.

    GitHub does not support OIDC, so we must fetch user info via API calls.
    Email may be null if user has private email -- fetch from /user/emails.
    """
    try:
        token = await oauth.github.authorize_access_token(request)
    except OAuthError as e:
        raise AppError(
            status_code=401,
            detail=f"GitHub authentication failed: {e.description}",
            code="AUTH_OAUTH_FAILED",
        )

    # Fetch user profile
    resp = await oauth.github.get("user", token=token)
    resp.raise_for_status()
    profile = resp.json()
    provider_user_id = str(profile["id"])

    # Email may be null if user has private email settings
    email = profile.get("email")
    if not email:
        email_resp = await oauth.github.get("user/emails", token=token)
        email_resp.raise_for_status()
        emails = email_resp.json()
        primary = next(
            (e for e in emails if e["primary"] and e["verified"]),
            None,
        )
        if primary:
            email = primary["email"]

    if not email:
        raise AppError(
            status_code=401,
            detail="Could not retrieve a verified email from GitHub",
            code="AUTH_OAUTH_NO_EMAIL",
        )

    service = _make_service(db)
    access_token, refresh_token = await service.oauth_login(
        provider="github",
        provider_user_id=provider_user_id,
        email=email,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
