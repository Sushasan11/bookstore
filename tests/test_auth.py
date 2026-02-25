"""Integration tests for auth endpoints (AUTH-01 through AUTH-05)."""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
REFRESH_URL = "/auth/refresh"
LOGOUT_URL = "/auth/logout"
HEALTH_URL = "/health"

VALID_EMAIL = "test@example.com"
VALID_PASSWORD = "securepass123"


async def register_user(
    client: AsyncClient,
    email: str = VALID_EMAIL,
    password: str = VALID_PASSWORD,
) -> dict:
    """Helper to register a user and return the JSON response."""
    resp = await client.post(REGISTER_URL, json={"email": email, "password": password})
    return resp.json()


@pytest_asyncio.fixture
async def registered_tokens(client: AsyncClient) -> dict:
    """Register a user and return the token response."""
    return await register_user(client)


@pytest_asyncio.fixture
async def admin_tokens(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user directly and return login tokens."""
    repo = UserRepository(db_session)
    hashed = await hash_password(VALID_PASSWORD)
    user = await repo.create(email="admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        LOGIN_URL,
        json={"email": "admin@example.com", "password": VALID_PASSWORD},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# AUTH-01: Registration
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        resp = await client.post(
            REGISTER_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        await register_user(client)
        resp = await client.post(
            REGISTER_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "AUTH_EMAIL_CONFLICT"

    async def test_register_short_password(self, client: AsyncClient) -> None:
        resp = await client.post(
            REGISTER_URL,
            json={"email": "short@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        resp = await client.post(
            REGISTER_URL,
            json={"email": "not-an-email", "password": VALID_PASSWORD},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AUTH-02: Login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_success(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        resp = await client.post(
            LOGIN_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        resp = await client.post(
            LOGIN_URL,
            json={"email": VALID_EMAIL, "password": "wrongpassword123"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    async def test_login_nonexistent_email(self, client: AsyncClient) -> None:
        resp = await client.post(
            LOGIN_URL,
            json={"email": "nobody@example.com", "password": VALID_PASSWORD},
        )
        assert resp.status_code == 401
        # Same generic message — no email enumeration
        assert resp.json()["detail"] == "Invalid email or password"

    async def test_login_returns_valid_jwt_claims(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        resp = await client.post(
            LOGIN_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        data = resp.json()
        # Decode the access token to verify claims
        from app.core.security import decode_access_token

        payload = decode_access_token(data["access_token"])
        assert payload["role"] == "user"
        assert "sub" in payload
        assert "jti" in payload
        assert "exp" in payload


# ---------------------------------------------------------------------------
# AUTH-03: Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    async def test_refresh_success(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        resp = await client.post(
            REFRESH_URL,
            json={"refresh_token": registered_tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token is different from the old one
        assert data["refresh_token"] != registered_tokens["refresh_token"]

    async def test_refresh_revoked_token_rejected(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        old_rt = registered_tokens["refresh_token"]
        # First refresh succeeds (rotates the token)
        resp1 = await client.post(REFRESH_URL, json={"refresh_token": old_rt})
        assert resp1.status_code == 200

        # Second refresh with the OLD token fails (already revoked)
        resp2 = await client.post(REFRESH_URL, json={"refresh_token": old_rt})
        assert resp2.status_code == 401

    async def test_refresh_nonexistent_token(self, client: AsyncClient) -> None:
        resp = await client.post(
            REFRESH_URL, json={"refresh_token": "nonexistent-token"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# AUTH-04: Logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_logout_success(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        resp = await client.post(
            LOGOUT_URL,
            json={"refresh_token": registered_tokens["refresh_token"]},
        )
        assert resp.status_code == 204

    async def test_refresh_after_logout_fails(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        rt = registered_tokens["refresh_token"]
        # Logout
        logout_resp = await client.post(LOGOUT_URL, json={"refresh_token": rt})
        assert logout_resp.status_code == 204

        # Refresh with the revoked token fails
        refresh_resp = await client.post(REFRESH_URL, json={"refresh_token": rt})
        assert refresh_resp.status_code == 401

    async def test_logout_idempotent(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        rt = registered_tokens["refresh_token"]
        # Logout twice — both should return 204
        resp1 = await client.post(LOGOUT_URL, json={"refresh_token": rt})
        assert resp1.status_code == 204
        resp2 = await client.post(LOGOUT_URL, json={"refresh_token": rt})
        assert resp2.status_code == 204


# ---------------------------------------------------------------------------
# AUTH-05: RBAC
# ---------------------------------------------------------------------------


class TestRBAC:
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        """Request without Authorization header to a protected route."""
        # Use the /health endpoint with a fake protected check
        # Since we don't have a protected-only endpoint yet, we test the
        # dependency directly by calling an endpoint that requires auth.
        # We'll import and test the dependency mechanism.
        from fastapi import APIRouter

        from app.core.deps import CurrentUser
        from app.main import app

        # Add a temporary test route
        test_router = APIRouter()

        @test_router.get("/test-protected")
        async def protected_route(current_user: CurrentUser) -> dict:
            return {"user": current_user["sub"]}

        app.include_router(test_router)

        resp = await client.get("/test-protected")
        assert resp.status_code == 401

    async def test_user_token_on_admin_route_returns_403(
        self, client: AsyncClient, registered_tokens: dict
    ) -> None:
        """User-role token on admin-guarded endpoint returns 403."""
        from fastapi import APIRouter

        from app.core.deps import AdminUser
        from app.main import app

        test_router = APIRouter()

        @test_router.get("/test-admin-only")
        async def admin_route(admin_user: AdminUser) -> dict:
            return {"admin": admin_user["sub"]}

        app.include_router(test_router)

        resp = await client.get(
            "/test-admin-only",
            headers={"Authorization": f"Bearer {registered_tokens['access_token']}"},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "AUTH_FORBIDDEN"

    async def test_admin_token_on_admin_route_returns_200(
        self, client: AsyncClient, admin_tokens: dict
    ) -> None:
        """Admin-role token on admin-guarded endpoint returns 200."""
        from fastapi import APIRouter

        from app.core.deps import AdminUser
        from app.main import app

        test_router = APIRouter()

        @test_router.get("/test-admin-access")
        async def admin_access_route(admin_user: AdminUser) -> dict:
            return {"admin": admin_user["sub"]}

        app.include_router(test_router)

        resp = await client.get(
            "/test-admin-access",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert resp.status_code == 200
