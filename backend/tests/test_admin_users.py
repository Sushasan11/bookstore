"""Integration tests for admin user management endpoints (Phase 10).

Tests cover:
  - ADMN-01: GET /admin/users with pagination metadata
  - ADMN-02: GET /admin/users with role and is_active filters
  - ADMN-03: PATCH /admin/users/{id}/deactivate with atomic token revocation
  - ADMN-04: PATCH /admin/users/{id}/reactivate
  - ADMN-05: Admin self-protection (cannot deactivate admin accounts)
"""

import math

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.repository import UserRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ADMIN_URL = "/admin/users"
LOGIN_URL = "/auth/login"
REFRESH_URL = "/auth/refresh"
CART_URL = "/cart"


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="admin_mgmt@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "admin_mgmt@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create a regular user and return auth headers."""
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="regular_user@example.com", hashed_password=hashed)
    await db_session.flush()
    resp = await client.post(
        LOGIN_URL,
        json={"email": "regular_user@example.com", "password": "userpass123"},
    )
    assert resp.status_code == 200, f"User login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_user(
    db_session: AsyncSession, email: str, *, is_admin: bool = False
) -> int:
    """Helper to create a user directly via repository. Returns user ID."""
    repo = UserRepository(db_session)
    hashed = await hash_password("testpass123")
    user = await repo.create(email=email, hashed_password=hashed)
    if is_admin:
        await repo.set_role_admin(user.id)
    await db_session.flush()
    return user.id


# ---------------------------------------------------------------------------
# ADMN-01, ADMN-02: List users with pagination and filters
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_list_users_paginated(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """GET /admin/users returns items list with full pagination metadata."""
        await _create_user(db_session, "list_user1@example.com")
        await _create_user(db_session, "list_user2@example.com")
        await _create_user(db_session, "list_user3@example.com")

        resp = await client.get(ADMIN_URL, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        # Envelope fields present
        assert "items" in data
        assert "total_count" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        # At least the 3 created users + the admin fixture user
        assert data["total_count"] >= 4
        assert isinstance(data["items"], list)
        assert data["page"] == 1
        assert data["per_page"] == 20

        # Verify AdminUserResponse schema on each item
        for item in data["items"]:
            assert "id" in item
            assert "email" in item
            assert "role" in item
            assert "is_active" in item
            assert "created_at" in item
            # full_name is always None (no full_name column yet)
            assert item["full_name"] is None

    async def test_list_users_filter_by_role_user(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """GET /admin/users?role=user returns only users with role=user."""
        await _create_user(db_session, "role_user1@example.com")
        await _create_user(db_session, "role_admin1@example.com", is_admin=True)

        resp = await client.get(f"{ADMIN_URL}?role=user", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["role"] == "user" for item in data["items"])

    async def test_list_users_filter_by_role_admin(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """GET /admin/users?role=admin returns only users with role=admin."""
        await _create_user(db_session, "role_user2@example.com")
        await _create_user(db_session, "role_admin2@example.com", is_admin=True)

        resp = await client.get(f"{ADMIN_URL}?role=admin", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["role"] == "admin" for item in data["items"])
        assert data["total_count"] >= 2  # fixture admin + created admin

    async def test_list_users_filter_by_active_status(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """GET /admin/users?is_active=false returns only deactivated users."""
        user_id = await _create_user(db_session, "to_deactivate@example.com")

        # Deactivate the user via API
        deact_resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert deact_resp.status_code == 200

        resp = await client.get(f"{ADMIN_URL}?is_active=false", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["is_active"] is False for item in data["items"])
        assert data["total_count"] >= 1

    async def test_list_users_combined_filters(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """GET /admin/users?role=user&is_active=true returns users matching both."""
        await _create_user(db_session, "active_user@example.com")
        deact_id = await _create_user(db_session, "inactive_user2@example.com")

        # Deactivate one user
        await client.patch(f"{ADMIN_URL}/{deact_id}/deactivate", headers=admin_headers)

        resp = await client.get(
            f"{ADMIN_URL}?role=user&is_active=true", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["role"] == "user"
            assert item["is_active"] is True

    async def test_list_users_pagination_params(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """GET /admin/users?page=1&per_page=2 returns exactly 2 items."""
        # Create enough users to exceed per_page
        for i in range(3):
            await _create_user(db_session, f"paginate_user{i}@example.com")

        resp = await client.get(f"{ADMIN_URL}?page=1&per_page=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["per_page"] == 2
        assert data["page"] == 1
        total = data["total_count"]
        expected_pages = math.ceil(total / 2)
        assert data["total_pages"] == expected_pages

    async def test_list_users_non_admin_forbidden(
        self, client: AsyncClient, user_headers: dict
    ) -> None:
        """GET /admin/users with regular user token returns 403."""
        resp = await client.get(ADMIN_URL, headers=user_headers)
        assert resp.status_code == 403

    async def test_list_users_unauthenticated(self, client: AsyncClient) -> None:
        """GET /admin/users without auth returns 401."""
        resp = await client.get(ADMIN_URL)
        assert resp.status_code == 401

    async def test_list_users_invalid_role_422(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """GET /admin/users?role=invalid returns 422 (invalid enum value)."""
        resp = await client.get(f"{ADMIN_URL}?role=invalid", headers=admin_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# ADMN-03, ADMN-05: Deactivate user
# ---------------------------------------------------------------------------


class TestDeactivateUser:
    async def test_deactivate_user_success(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """PATCH /admin/users/{id}/deactivate returns 200 with is_active=false."""
        user_id = await _create_user(db_session, "deactivate_success@example.com")

        resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user_id
        assert data["is_active"] is False
        assert data["email"] == "deactivate_success@example.com"

    async def test_deactivate_revokes_refresh_tokens(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """After deactivation, the user's refresh token fails on /auth/refresh."""
        # Create user and get a refresh token via login
        user_id = await _create_user(db_session, "revoke_tokens@example.com")
        login_resp = await client.post(
            LOGIN_URL,
            json={"email": "revoke_tokens@example.com", "password": "testpass123"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Deactivate the user
        deact_resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert deact_resp.status_code == 200

        # Refresh token should now fail (revoked by deactivation)
        refresh_resp = await client.post(
            REFRESH_URL, json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 401

    async def test_deactivate_blocks_login(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """After deactivation, login attempt returns 403 with deactivation message."""
        user_id = await _create_user(db_session, "deactivate_login@example.com")

        deact_resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert deact_resp.status_code == 200

        login_resp = await client.post(
            LOGIN_URL,
            json={"email": "deactivate_login@example.com", "password": "testpass123"},
        )
        assert login_resp.status_code == 403
        assert login_resp.json()["detail"] == "Account deactivated. Contact support."

    async def test_deactivate_blocks_access_token(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """After deactivation, using existing access token on GET /cart returns 403.

        Cart routes use ActiveUser dep (from Plan 01 Task 3) so they enforce is_active.
        """
        user_id = await _create_user(db_session, "deactivate_token@example.com")

        # Get user's access token
        login_resp = await client.post(
            LOGIN_URL,
            json={"email": "deactivate_token@example.com", "password": "testpass123"},
        )
        assert login_resp.status_code == 200
        access_token = login_resp.json()["access_token"]
        user_auth = {"Authorization": f"Bearer {access_token}"}

        # Verify access works before deactivation
        pre_resp = await client.get(CART_URL, headers=user_auth)
        assert pre_resp.status_code == 200

        # Deactivate the user
        deact_resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert deact_resp.status_code == 200

        # Access token should now be rejected on protected endpoints
        post_resp = await client.get(CART_URL, headers=user_auth)
        assert post_resp.status_code == 403
        assert post_resp.json()["detail"] == "Account deactivated. Contact support."

    async def test_deactivate_admin_forbidden(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """Deactivating another admin account returns 403 ADMN_CANNOT_DEACTIVATE_ADMIN."""
        other_admin_id = await _create_user(
            db_session, "other_admin@example.com", is_admin=True
        )

        resp = await client.patch(
            f"{ADMIN_URL}/{other_admin_id}/deactivate", headers=admin_headers
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "ADMN_CANNOT_DEACTIVATE_ADMIN"
        assert resp.json()["detail"] == "Cannot deactivate admin accounts"

    async def test_deactivate_self_admin_forbidden(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Admin deactivating their own account returns 403."""
        # Create a fresh admin specifically for self-deactivation test
        repo = UserRepository(db_session)
        hashed = await hash_password("selfadminpass")
        user = await repo.create(email="self_admin@example.com", hashed_password=hashed)
        await repo.set_role_admin(user.id)
        await db_session.flush()
        self_admin_id = user.id

        login_resp = await client.post(
            LOGIN_URL,
            json={"email": "self_admin@example.com", "password": "selfadminpass"},
        )
        assert login_resp.status_code == 200
        self_admin_headers = {
            "Authorization": f"Bearer {login_resp.json()['access_token']}"
        }

        resp = await client.patch(
            f"{ADMIN_URL}/{self_admin_id}/deactivate", headers=self_admin_headers
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "ADMN_CANNOT_DEACTIVATE_ADMIN"

    async def test_deactivate_idempotent(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """Deactivating an already-deactivated user returns 200 with is_active=false."""
        user_id = await _create_user(db_session, "idempotent_deact@example.com")

        # First deactivation
        resp1 = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert resp1.status_code == 200
        assert resp1.json()["is_active"] is False

        # Second deactivation — should still return 200 (idempotent)
        resp2 = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is False

    async def test_deactivate_nonexistent_user_404(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """PATCH /admin/users/99999/deactivate returns 404 USER_NOT_FOUND."""
        resp = await client.patch(
            f"{ADMIN_URL}/99999/deactivate", headers=admin_headers
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "USER_NOT_FOUND"


# ---------------------------------------------------------------------------
# ADMN-04: Reactivate user
# ---------------------------------------------------------------------------


class TestReactivateUser:
    async def test_reactivate_user_success(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """Deactivate then reactivate: returns 200 with is_active=true."""
        user_id = await _create_user(db_session, "reactivate_success@example.com")

        # Deactivate first
        deact_resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers
        )
        assert deact_resp.status_code == 200
        assert deact_resp.json()["is_active"] is False

        # Now reactivate
        react_resp = await client.patch(
            f"{ADMIN_URL}/{user_id}/reactivate", headers=admin_headers
        )
        assert react_resp.status_code == 200
        data = react_resp.json()
        assert data["id"] == user_id
        assert data["is_active"] is True

    async def test_reactivate_requires_fresh_login(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """After reactivation, the user can log in again (fresh login required)."""
        user_id = await _create_user(db_session, "fresh_login@example.com")

        # Deactivate
        await client.patch(f"{ADMIN_URL}/{user_id}/deactivate", headers=admin_headers)

        # Confirm login is blocked
        blocked_resp = await client.post(
            LOGIN_URL,
            json={"email": "fresh_login@example.com", "password": "testpass123"},
        )
        assert blocked_resp.status_code == 403

        # Reactivate
        await client.patch(f"{ADMIN_URL}/{user_id}/reactivate", headers=admin_headers)

        # Login should work again
        login_resp = await client.post(
            LOGIN_URL,
            json={"email": "fresh_login@example.com", "password": "testpass123"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    async def test_reactivate_idempotent(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ) -> None:
        """Reactivating an already-active user returns 200 with is_active=true."""
        user_id = await _create_user(db_session, "idempotent_react@example.com")

        # User starts active; reactivate without deactivating first
        resp1 = await client.patch(
            f"{ADMIN_URL}/{user_id}/reactivate", headers=admin_headers
        )
        assert resp1.status_code == 200
        assert resp1.json()["is_active"] is True

        # Reactivate again — still 200 (idempotent)
        resp2 = await client.patch(
            f"{ADMIN_URL}/{user_id}/reactivate", headers=admin_headers
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is True

    async def test_reactivate_nonexistent_user_404(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """PATCH /admin/users/99999/reactivate returns 404 USER_NOT_FOUND."""
        resp = await client.patch(
            f"{ADMIN_URL}/99999/reactivate", headers=admin_headers
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "USER_NOT_FOUND"
