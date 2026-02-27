"""Integration tests for OAuth endpoints (AUTH-06).

Covers: Google redirect flow, callback token issuance,
account linking by email, OAuth-only user behavior, duplicate/idempotent
login, and error cases (unverified email, no email).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.core.security import decode_access_token
from app.users.models import OAuthAccount, User

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

GOOGLE_LOGIN_URL = "/auth/google"
GOOGLE_CALLBACK_URL = "/auth/google/callback"
REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_google_userinfo(
    *,
    sub: str = "google-123",
    email: str = "googleuser@test.com",
    email_verified: bool = True,
) -> dict:
    """Build a fake Google OIDC userinfo dict."""
    info: dict = {"sub": sub}
    if email is not None:
        info["email"] = email
    info["email_verified"] = email_verified
    return info


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_google_oauth():
    """Patch oauth.google methods to simulate Google OIDC without real credentials.

    By default:
    - authorize_redirect returns a 307 redirect to a fake Google URL.
    - authorize_access_token returns a token dict with userinfo for a verified user.

    Tests can override the mock return values as needed.
    """
    redirect_response = RedirectResponse(
        url="https://accounts.google.com/o/oauth2/auth?fake=1", status_code=307
    )

    mock_authorize_redirect = AsyncMock(return_value=redirect_response)
    mock_authorize_access_token = AsyncMock(
        return_value={
            "access_token": "fake-google-access-token",
            "userinfo": _make_google_userinfo(),
        }
    )

    with (
        patch("app.users.router.oauth") as mock_oauth,
    ):
        # Set up the google client mock
        mock_google = MagicMock()
        mock_google.authorize_redirect = mock_authorize_redirect
        mock_google.authorize_access_token = mock_authorize_access_token
        mock_oauth.google = mock_google

        yield {
            "oauth": mock_oauth,
            "authorize_redirect": mock_authorize_redirect,
            "authorize_access_token": mock_authorize_access_token,
        }


# ---------------------------------------------------------------------------
# TestGoogleOAuth
# ---------------------------------------------------------------------------


class TestGoogleOAuth:
    """Tests for GET /auth/google and GET /auth/google/callback."""

    async def test_google_login_redirects(
        self, client: AsyncClient, mock_google_oauth: dict
    ) -> None:
        """GET /auth/google returns a redirect response to Google's OAuth URL."""
        resp = await client.get(GOOGLE_LOGIN_URL, follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "accounts.google.com" in resp.headers["location"]

    async def test_google_callback_returns_tokens(
        self, client: AsyncClient, db_session: AsyncSession, mock_google_oauth: dict
    ) -> None:
        """GET /auth/google/callback with valid OAuth returns JWT access + refresh tokens."""
        resp = await client.get(GOOGLE_CALLBACK_URL)
        assert resp.status_code == 200

        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Decode the access token and verify it contains a valid user sub
        payload = decode_access_token(data["access_token"])
        assert "sub" in payload
        assert int(payload["sub"]) > 0

    async def test_google_callback_unverified_email_rejected(
        self, client: AsyncClient, mock_google_oauth: dict
    ) -> None:
        """Google OAuth with unverified email returns 401 with AUTH_OAUTH_EMAIL_UNVERIFIED."""
        # Override the mock to return unverified email
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-token",
            "userinfo": _make_google_userinfo(email_verified=False),
        }

        resp = await client.get(GOOGLE_CALLBACK_URL)
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_OAUTH_EMAIL_UNVERIFIED"

    async def test_google_callback_no_email_rejected(
        self, client: AsyncClient, mock_google_oauth: dict
    ) -> None:
        """Google OAuth with no email in userinfo returns 401 with AUTH_OAUTH_NO_EMAIL."""
        # Override the mock: userinfo without email
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-token",
            "userinfo": {"sub": "google-noemail"},
        }

        resp = await client.get(GOOGLE_CALLBACK_URL)
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_OAUTH_NO_EMAIL"

    async def test_google_callback_no_userinfo_rejected(
        self, client: AsyncClient, mock_google_oauth: dict
    ) -> None:
        """Google OAuth with missing userinfo dict returns 401 with AUTH_OAUTH_NO_EMAIL."""
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-token",
            # No "userinfo" key at all
        }

        resp = await client.get(GOOGLE_CALLBACK_URL)
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_OAUTH_NO_EMAIL"


# ---------------------------------------------------------------------------
# TestAccountLinking
# ---------------------------------------------------------------------------


class TestAccountLinking:
    """Tests for OAuth account linking, OAuth-only user behavior, and idempotency."""

    async def test_oauth_links_existing_email(
        self, client: AsyncClient, db_session: AsyncSession, mock_google_oauth: dict
    ) -> None:
        """OAuth login with email matching existing user links to that account (no duplicate)."""
        # 1. Register a user via email/password
        existing_email = "existing@test.com"
        reg_resp = await client.post(
            REGISTER_URL,
            json={"email": existing_email, "password": "securepass123"},
        )
        assert reg_resp.status_code == 201
        reg_payload = decode_access_token(reg_resp.json()["access_token"])
        original_user_id = reg_payload["sub"]

        # 2. Simulate Google OAuth callback returning the same email
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-google-token",
            "userinfo": _make_google_userinfo(
                sub="google-existing", email=existing_email
            ),
        }

        oauth_resp = await client.get(GOOGLE_CALLBACK_URL)
        assert oauth_resp.status_code == 200

        # 3. Verify the JWT sub is the same user
        oauth_payload = decode_access_token(oauth_resp.json()["access_token"])
        assert oauth_payload["sub"] == original_user_id

        # 4. Verify no duplicate user was created
        result = await db_session.execute(
            select(User).where(User.email == existing_email)
        )
        users = result.scalars().all()
        assert len(users) == 1

    async def test_oauth_user_no_password(
        self, client: AsyncClient, db_session: AsyncSession, mock_google_oauth: dict
    ) -> None:
        """OAuth-only user has hashed_password=None."""
        new_email = "newuser-nopass@test.com"
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-google-token",
            "userinfo": _make_google_userinfo(
                sub="google-newuser", email=new_email
            ),
        }

        resp = await client.get(GOOGLE_CALLBACK_URL)
        assert resp.status_code == 200

        # Query the user from DB
        payload = decode_access_token(resp.json()["access_token"])
        user_id = int(payload["sub"])
        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        assert user.hashed_password is None
        assert user.email == new_email

    async def test_duplicate_oauth_login_idempotent(
        self, client: AsyncClient, db_session: AsyncSession, mock_google_oauth: dict
    ) -> None:
        """Logging in via the same OAuth identity twice is idempotent."""
        repeat_email = "repeat@test.com"
        repeat_sub = "google-repeat"
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-google-token",
            "userinfo": _make_google_userinfo(
                sub=repeat_sub, email=repeat_email
            ),
        }

        # First OAuth login
        resp1 = await client.get(GOOGLE_CALLBACK_URL)
        assert resp1.status_code == 200

        # Second OAuth login with same identity
        resp2 = await client.get(GOOGLE_CALLBACK_URL)
        assert resp2.status_code == 200

        # Both return tokens for the same user
        payload1 = decode_access_token(resp1.json()["access_token"])
        payload2 = decode_access_token(resp2.json()["access_token"])
        assert payload1["sub"] == payload2["sub"]

        # Only one User exists with that email
        result = await db_session.execute(
            select(User).where(User.email == repeat_email)
        )
        users = result.scalars().all()
        assert len(users) == 1

        # Only one OAuthAccount row for this provider + id
        result = await db_session.execute(
            select(OAuthAccount).where(
                OAuthAccount.oauth_provider == "google",
                OAuthAccount.oauth_account_id == repeat_sub,
            )
        )
        oauth_accounts = result.scalars().all()
        assert len(oauth_accounts) == 1

    async def test_oauth_user_password_login_rejected(
        self, client: AsyncClient, db_session: AsyncSession, mock_google_oauth: dict
    ) -> None:
        """OAuth-only user trying to log in with password gets 400 with AUTH_OAUTH_ONLY_ACCOUNT."""
        oauth_email = "oauthonly@test.com"
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-google-token",
            "userinfo": _make_google_userinfo(
                sub="google-oauthonly", email=oauth_email
            ),
        }

        # Create user via Google OAuth (no password)
        oauth_resp = await client.get(GOOGLE_CALLBACK_URL)
        assert oauth_resp.status_code == 200

        # Try password login with that email
        login_resp = await client.post(
            LOGIN_URL,
            json={"email": oauth_email, "password": "anypassword123"},
        )
        assert login_resp.status_code == 400
        assert login_resp.json()["code"] == "AUTH_OAUTH_ONLY_ACCOUNT"

    async def test_linked_user_retains_password(
        self, client: AsyncClient, db_session: AsyncSession, mock_google_oauth: dict
    ) -> None:
        """User registered with password who links via OAuth retains their password."""
        linked_email = "linked-user@test.com"
        password = "securepass123"

        # Register with email/password first
        reg_resp = await client.post(
            REGISTER_URL,
            json={"email": linked_email, "password": password},
        )
        assert reg_resp.status_code == 201

        # Now do Google OAuth callback with same email
        mock_google_oauth["authorize_access_token"].return_value = {
            "access_token": "fake-google-token",
            "userinfo": _make_google_userinfo(
                sub="google-linked", email=linked_email
            ),
        }
        oauth_resp = await client.get(GOOGLE_CALLBACK_URL)
        assert oauth_resp.status_code == 200

        # Verify user still has password (can still log in with password)
        login_resp = await client.post(
            LOGIN_URL,
            json={"email": linked_email, "password": password},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()
