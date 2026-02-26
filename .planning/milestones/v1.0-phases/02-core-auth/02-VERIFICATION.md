---
phase: 02-core-auth
verified: 2026-02-26T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 2: Core Auth Verification Report

**Phase Goal:** Users can register and log in with email/password, stay authenticated across sessions with refresh tokens, log out with token revocation, and all endpoints enforce admin vs user roles
**Verified:** 2026-02-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Key Finding: Plan Frontmatter Deviation (Informational, Non-Blocking)

Plan 02-01 specified that `app/db/base.py` should import User and RefreshToken for Alembic discovery. The SUMMARY noted a deviation: imports were placed in `alembic/env.py` instead (line 14: `from app.users.models import OAuthAccount, RefreshToken, User  # noqa: F401`). The comment in `app/db/base.py` itself confirms this intentional change: "Model imports for Alembic discovery live in alembic/env.py to avoid circular imports."

This is a valid architectural decision — `alembic/env.py` imports `Base` from `app/db/base.py`, and models import `Base` from the same file. Placing model imports in `app/db/base.py` would create a circular dependency. The Alembic discovery chain (`env.py` → `Base.metadata` + model imports) works correctly. This deviation does NOT block the phase goal.

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                        | Status     | Evidence                                                                                                 |
|----|----------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------|
| 1  | Users table exists with correct schema                                                        | VERIFIED   | `451f9697aceb` migration creates users table; model has all required columns                             |
| 2  | Refresh tokens table exists with token_family UUID for session/theft management               | VERIFIED   | Migration creates refresh_tokens with token_family UUID index; model has is_revoked/is_expired properties |
| 3  | UserRole enum has exactly two values: user and admin                                          | VERIFIED   | `class UserRole(enum.StrEnum)` with USER="user", ADMIN="admin" — no other values                         |
| 4  | Password hashing runs async (asyncio.to_thread) to avoid blocking the event loop             | VERIFIED   | `security.py:31,36` — both hash_password and verify_password use `asyncio.to_thread`                     |
| 5  | JWT access tokens contain sub, role, jti, iat, exp claims; decode raises AppError(401)       | VERIFIED   | `create_access_token` sets all 5 claims; `decode_access_token` catches Expired/Invalid and raises AppError |
| 6  | JWT decode passes `algorithms=["HS256"]` (prevents algorithm confusion attack)               | VERIFIED   | `security.py:67` — `jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])`                      |
| 7  | Refresh token is opaque (secrets.token_urlsafe), not a JWT                                   | VERIFIED   | `generate_refresh_token()` uses `secrets.token_urlsafe(64)` — 512 bits entropy                           |
| 8  | AuthService.login() always runs verify_password even when user not found (timing-safe)        | VERIFIED   | `service.py:63` — DUMMY_HASH computed at module load; verify_password awaited on user-not-found path      |
| 9  | Refresh token rotation revokes old token; reuse of revoked token revokes entire family        | VERIFIED   | `service.py:104-110` — is_revoked check triggers revoke_family; new token inherits same token_family      |
| 10 | POST /auth/{register,login,refresh,logout} endpoints all wired and return correct status codes | VERIFIED  | `router.py` defines all 4; `main.py:66` includes auth_router; router uses response_model=TokenResponse   |
| 11 | get_current_user returns 401 without token; require_admin returns 403 for non-admin role      | VERIFIED   | `deps.py:39-55` — oauth2_scheme auto-401s missing header; require_admin checks role != "admin"           |

**Score:** 11/11 truths verified

---

## Required Artifacts

| Artifact                        | Expected                                          | Status      | Details                                                                                              |
|---------------------------------|---------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------|
| `app/users/models.py`           | User, RefreshToken, UserRole models               | VERIFIED    | All three defined; User has all required columns; hashed_password now nullable (Phase 3 OAuth change) |
| `alembic/versions/451f9697aceb_create_users_and_refresh_tokens.py` | Migration creating both tables | VERIFIED | Non-empty upgrade() with op.create_table for users and refresh_tokens; both indexes created |
| `alembic/env.py`                | Model aggregator for Alembic autogenerate          | VERIFIED    | Imports User, RefreshToken, OAuthAccount from users.models with noqa:F401; target_metadata = Base.metadata |
| `app/core/security.py`          | 5 security functions                               | VERIFIED    | hash_password, verify_password, create_access_token, decode_access_token, generate_refresh_token all present and substantive |
| `app/core/config.py`            | SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES (15), REFRESH_TOKEN_EXPIRE_DAYS (7) | VERIFIED | All three present with correct defaults |
| `app/users/schemas.py`          | 5 Pydantic schemas                                | VERIFIED    | UserCreate (no role field, min_length=8), LoginRequest, RefreshRequest, TokenResponse, UserResponse all present |
| `app/users/repository.py`       | UserRepository, RefreshTokenRepository            | VERIFIED    | Both classes present; create() takes no role parameter; revoke_family targets token_family UUID       |
| `app/users/service.py`          | AuthService with 4 methods + DUMMY_HASH           | VERIFIED    | register, login, refresh, logout all present; DUMMY_HASH at module level (line 22); timing-safe path confirmed |
| `app/core/deps.py`              | oauth2_scheme, get_current_user, require_admin, CurrentUser, AdminUser | VERIFIED | All 5 present; get_current_user makes no DB call; require_admin checks role == "admin" (lowercase) |
| `app/users/router.py`           | 4 auth endpoints                                  | VERIFIED    | POST /auth/register (201), /auth/login (200), /auth/refresh (200), /auth/logout (204) all defined    |
| `app/main.py`                   | Auth router registered                            | VERIFIED    | Line 66: `application.include_router(auth_router)` inside create_app()                               |
| `scripts/seed_admin.py`         | Admin creation script                             | VERIFIED    | asyncio.run, getpass, duplicate check, set_role_admin, commit — all present                          |
| `tests/test_auth.py`            | 12+ integration tests                             | VERIFIED    | 17 tests across 5 classes; covers all 4 endpoints + RBAC; tests check status codes AND response body |

---

## Key Link Verification

| From                   | To                        | Via                                             | Status   | Details                                                                         |
|------------------------|---------------------------|-------------------------------------------------|----------|---------------------------------------------------------------------------------|
| `app/users/models.py`  | `alembic/env.py`          | `from app.users.models import ... # noqa:F401` | WIRED    | env.py:14 imports User, RefreshToken, OAuthAccount; target_metadata = Base.metadata |
| `app/core/security.py` | `app/core/config.py`      | `get_settings()` call for SECRET_KEY and TTL   | WIRED    | security.py:17 imports get_settings; called in create_access_token and decode_access_token |
| `app/core/security.py` | `app/core/exceptions.py`  | AppError raised on JWT decode failure           | WIRED    | security.py:63 local import of AppError; raised on ExpiredSignatureError and InvalidTokenError |
| `app/users/service.py` | `app/core/security.py`    | hash_password, verify_password, create_access_token, generate_refresh_token | WIRED | service.py:6-11 imports all 4 functions; all used in register/login/refresh |
| `app/users/service.py` | `app/users/repository.py` | UserRepository and RefreshTokenRepository injected | WIRED | service.py:12-16 imports repos; __init__ assigns self.user_repo and self.rt_repo |
| `app/core/deps.py`     | `app/core/security.py`    | decode_access_token in get_current_user         | WIRED    | deps.py:15 imports decode_access_token; called directly in get_current_user     |
| `app/users/router.py`  | `app/users/service.py`    | AuthService instantiated via _make_service()    | WIRED    | router.py:22-27 creates AuthService with UserRepository + RefreshTokenRepository |
| `app/users/router.py`  | `app/users/schemas.py`    | response_model=TokenResponse on all return routes | WIRED  | router.py:32,42,50 use response_model=TokenResponse; LoginRequest/UserCreate as request bodies |
| `app/main.py`          | `app/users/router.py`     | application.include_router(auth_router)         | WIRED    | main.py:30 imports auth_router; main.py:66 includes it in create_app()          |
| `tests/test_auth.py`   | `tests/conftest.py`       | client and db_session fixtures                  | WIRED    | test_auth.py fixtures receive `client: AsyncClient` and `db_session: AsyncSession` from conftest |

---

## Requirements Coverage

| Requirement | Source Plan(s)      | Description                                          | Status    | Evidence                                                                          |
|-------------|---------------------|------------------------------------------------------|-----------|-----------------------------------------------------------------------------------|
| AUTH-01     | 02-01, 02-02, 02-03, 02-04, 02-05 | User can sign up with email and password | SATISFIED | POST /auth/register returns 201 + token pair; UserCreate validates email+password; test_register_success passes |
| AUTH-02     | 02-02, 02-03, 02-04, 02-05 | User can log in and receive JWT access + refresh tokens | SATISFIED | POST /auth/login returns 200 + token pair; timing-safe login in service.py; test_login_success + test_login_returns_valid_jwt_claims pass |
| AUTH-03     | 02-03, 02-04, 02-05 | User can refresh expired access token using refresh token | SATISFIED | POST /auth/refresh rotates token in same family; test_refresh_success + test_refresh_revoked_token_rejected pass |
| AUTH-04     | 02-01, 02-03, 02-04, 02-05 | User can log out (refresh token revoked)          | SATISFIED | POST /auth/logout returns 204; token revoked; subsequent refresh returns 401; test_logout_success + test_refresh_after_logout_fails pass |
| AUTH-05     | 02-03, 02-04, 02-05 | Endpoints enforce role-based access (admin vs user)   | SATISFIED | oauth2_scheme returns 401 on missing header; require_admin returns 403 for user role; test_unauthenticated_returns_401 + test_user_token_on_admin_route_returns_403 + test_admin_token_on_admin_route_returns_200 pass |

No orphaned requirements: AUTH-06 is mapped to Phase 3 in REQUIREMENTS.md and was not claimed by any Phase 2 plan.

---

## Anti-Patterns Found

No blocking anti-patterns detected.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `app/users/models.py` | `hashed_password` changed to `nullable=True` vs plan spec of `nullable=False` | INFO | Intentional — Phase 3 OAuth migration `7b2f3a8c4d1e` made it nullable to support OAuth-only users. Current model correctly reflects DB state. |
| `app/users/service.py` | `oauth_login()` method added beyond plan scope | INFO | Phase 3 OAuth feature added to service. Does not affect Phase 2 correctness; original 4 methods (register/login/refresh/logout) are unmodified. |
| `app/users/router.py` | Google + GitHub OAuth endpoints added beyond plan scope | INFO | Phase 3 additions. All 4 Phase 2 auth endpoints still present with correct status codes and response models. |
| `alembic/versions/451f9697aceb_...py` | Migration uses `nullable=False` for hashed_password | INFO | Correct at time of creation; Phase 3 migration `7b2f3a8c4d1e` alters it to nullable. Migration chain is coherent. |

---

## Human Verification Required

### 1. Timing-Safe Login

**Test:** Using a tool like `time` or Burp Suite, send 100 requests to POST /auth/login with a non-existent email and 100 requests with an existing email but wrong password. Compare average response times.
**Expected:** Response times should be statistically indistinguishable (both ~50-200ms from Argon2 computation). No consistent timing difference that would reveal email existence.
**Why human:** Cannot reliably measure timing behavior via static code analysis. The DUMMY_HASH approach is correct in the code, but actual timing equality under load requires runtime measurement.

### 2. Token Theft Detection (Family Revocation)

**Test:** Register, call /auth/refresh to rotate the token, then submit the original (now-revoked) token to /auth/refresh a second time.
**Expected:** Returns 401 with code "AUTH_TOKEN_REUSE" AND the new token issued in the first rotation is also revoked (entire family revoked). Verify by attempting to use the new token from the first rotation after the reuse attempt.
**Why human:** The test_refresh_revoked_token_rejected test verifies the 401, but does not verify that the NEW token from the first rotation is also invalidated after the theft-detection revoke_family call.

---

## Summary

Phase 2 goal is fully achieved. All 11 observable truths are verified. All 5 requirements (AUTH-01 through AUTH-05) are satisfied with integration test coverage.

**Architecture note on base.py:** The plan specified model imports in `app/db/base.py`, but the implementation correctly placed them in `alembic/env.py` to avoid circular imports. The SUMMARY documented this as a deviation. The Alembic discovery chain is fully functional via `env.py` and poses no risk.

**Phase 3 forward-compatibility:** Models, service, and router were extended with OAuth support (Phase 3) while maintaining full backward compatibility with all Phase 2 auth contracts. The 17 integration tests in `tests/test_auth.py` continue to pass alongside the 108-test full suite.

---

_Verified: 2026-02-26_
_Verifier: Claude (gsd-verifier)_
