"""Integration tests for OAuth endpoints (AUTH-06).

Covers: Google and GitHub redirect flows, callback token issuance,
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
GITHUB_LOGIN_URL = "/auth/github"
GITHUB_CALLBACK_URL = "/auth/github/callback"
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


def _make_github_mock_response(json_data: dict) -> MagicMock:
    """Create a mock response object with .json() and .raise_for_status()."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


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

        # Also keep github as a MagicMock so it doesn't break if accessed
        mock_oauth.github = MagicMock()

        yield {
            "oauth": mock_oauth,
            "authorize_redirect": mock_authorize_redirect,
            "authorize_access_token": mock_authorize_access_token,
        }


@pytest.fixture
def mock_github_oauth():
    """Patch oauth.github methods to simulate GitHub OAuth2 without real credentials.

    By default:
    - authorize_redirect returns a 307 redirect to a fake GitHub URL.
    - authorize_access_token returns a token dict.
    - get("user") returns a profile with id and email.
    - get("user/emails") returns a list with one primary verified email.

    Tests can override mock return values as needed.
    """
    redirect_response = RedirectResponse(
        url="https://github.com/login/oauth/authorize?fake=1", status_code=307
    )

    mock_authorize_redirect = AsyncMock(return_value=redirect_response)
    mock_authorize_access_token = AsyncMock(
        return_value={"access_token": "fake-github-access-token"}
    )

    # Default responses for GET calls
    user_profile = {"id": 456, "email": "ghuser@test.com", "login": "ghuser"}
    user_emails = [
        {"email": "ghuser@test.com", "primary": True, "verified": True},
    ]

    async def mock_get_side_effect(url, **kwargs):
        if url == "user":
            return _make_github_mock_response(user_profile)
        elif url == "user/emails":
            return _make_github_mock_response(user_emails)
        raise ValueError(f"Unexpected GitHub API URL: {url}")

    mock_get = AsyncMock(side_effect=mock_get_side_effect)

    with (
        patch("app.users.router.oauth") as mock_oauth,
    ):
        mock_github = MagicMock()
        mock_github.authorize_redirect = mock_authorize_redirect
        mock_github.authorize_access_token = mock_authorize_access_token
        mock_github.get = mock_get
        mock_oauth.github = mock_github

        # Also keep google as a MagicMock
        mock_oauth.google = MagicMock()

        yield {
            "oauth": mock_oauth,
            "authorize_redirect": mock_authorize_redirect,
            "authorize_access_token": mock_authorize_access_token,
            "get": mock_get,
            "user_profile": user_profile,
            "user_emails": user_emails,
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
# TestGitHubOAuth
# ---------------------------------------------------------------------------


class TestGitHubOAuth:
    """Tests for GET /auth/github and GET /auth/github/callback."""

    async def test_github_login_redirects(
        self, client: AsyncClient, mock_github_oauth: dict
    ) -> None:
        """GET /auth/github returns a redirect response to GitHub's authorization URL."""
        resp = await client.get(GITHUB_LOGIN_URL, follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "github.com" in resp.headers["location"]

    async def test_github_callback_returns_tokens(
        self, client: AsyncClient, db_session: AsyncSession, mock_github_oauth: dict
    ) -> None:
        """GET /auth/github/callback with valid OAuth returns JWT access + refresh tokens."""
        resp = await client.get(GITHUB_CALLBACK_URL)
        assert resp.status_code == 200

        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Decode the access token
        payload = decode_access_token(data["access_token"])
        assert "sub" in payload
        assert int(payload["sub"]) > 0

    async def test_github_callback_private_email(
        self, client: AsyncClient, db_session: AsyncSession, mock_github_oauth: dict
    ) -> None:
        """GitHub callback fetches email from /user/emails when profile email is null."""
        private_email = "private@test.com"

        # Override: profile has no email, but /user/emails has a primary verified one
        profile_no_email = {"id": 789, "email": None, "login": "private-user"}
        emails_with_primary = [
            {"email": private_email, "primary": True, "verified": True},
        ]

        async def mock_get_private(url, **kwargs):
            if url == "user":
                return _make_github_mock_response(profile_no_email)
            elif url == "user/emails":
                return _make_github_mock_response(emails_with_primary)
            raise ValueError(f"Unexpected URL: {url}")

        mock_github_oauth["get"].side_effect = mock_get_private

        resp = await client.get(GITHUB_CALLBACK_URL)
        assert resp.status_code == 200

        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify the user was created with the private email
        payload = decode_access_token(data["access_token"])
        user_id = int(payload["sub"])
        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        assert user.email == private_email

    async def test_github_callback_no_verified_email(
        self, client: AsyncClient, mock_github_oauth: dict
    ) -> None:
        """GitHub callback with no verified email returns 401 with AUTH_OAUTH_NO_EMAIL."""
        profile_no_email = {"id": 999, "email": None, "login": "noemail-user"}
        unverified_emails = [
            {"email": "unverified@test.com", "primary": True, "verified": False},
        ]

        async def mock_get_no_email(url, **kwargs):
            if url == "user":
                return _make_github_mock_response(profile_no_email)
            elif url == "user/emails":
                return _make_github_mock_response(unverified_emails)
            raise ValueError(f"Unexpected URL: {url}")

        mock_github_oauth["get"].side_effect = mock_get_no_email

        resp = await client.get(GITHUB_CALLBACK_URL)
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

    async def test_github_oauth_creates_oauth_account_row(
        self, client: AsyncClient, db_session: AsyncSession, mock_github_oauth: dict
    ) -> None:
        """GitHub OAuth creates an OAuthAccount row linked to the user."""
        resp = await client.get(GITHUB_CALLBACK_URL)
        assert resp.status_code == 200

        payload = decode_access_token(resp.json()["access_token"])
        user_id = int(payload["sub"])

        # Verify OAuthAccount was created
        result = await db_session.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.oauth_provider == "github",
            )
        )
        oauth_account = result.scalar_one()
        assert oauth_account.oauth_account_id == str(
            mock_github_oauth["user_profile"]["id"]
        )
