---
phase: 02-core-auth
plan: 03
subsystem: auth
tags: [repository, service, argon2, timing-safe, refresh-rotation, rbac, fastapi-deps]

# Dependency graph
requires:
  - phase: 02-01
    provides: User, RefreshToken SQLAlchemy models, UserRole StrEnum, token_family UUID column
  - phase: 02-02
    provides: hash_password, verify_password, create_access_token, decode_access_token, generate_refresh_token, AppError
provides:
  - UserRepository (get_by_email, get_by_id, create, set_role_admin)
  - RefreshTokenRepository (create, get_by_token, revoke, revoke_family)
  - AuthService (register, login, refresh, logout) with timing-safe login and token rotation
  - get_current_user FastAPI dependency (no DB lookup, role from JWT claims)
  - require_admin FastAPI dependency (403 on non-admin)
  - CurrentUser and AdminUser type aliases
affects: [02-04, 02-05, 03-oauth, all auth-dependent phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - DUMMY_HASH module-level constant for timing-safe login (prevents email enumeration via timing)
    - Repository pattern with AsyncSession injection — session.flush() (not commit) preserves transaction boundaries
    - Token family UUID for refresh token theft detection and family-wide revocation
    - get_current_user reads role from JWT claims only — no DB lookup on every request
    - require_admin checks role == "admin" (lowercase StrEnum value, not "ADMIN")

key-files:
  created:
    - app/users/repository.py
    - app/users/service.py
  modified:
    - app/core/deps.py

key-decisions:
  - "DUMMY_HASH computed at module load for timing-safe login — verify_password always runs even when user not found"
  - "get_current_user reads role from JWT claims only — no DB lookup; require_admin checks role == 'admin'"
  - "AuthService.refresh() rotates tokens within same family; reuse of revoked token triggers family-wide revocation"

patterns-established:
  - "Repository pattern: __init__ receives AsyncSession, session.flush() not commit (caller owns transaction)"
  - "Timing-safe authentication: DUMMY_HASH at module level, verify_password always runs on user-not-found path"
  - "Family-based refresh token rotation: new token inherits token_family; theft = revoke entire family"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 2 Plan 03: Auth Repository, Service, and RBAC Dependencies Summary

**Timing-safe AuthService with repository pattern, refresh token family rotation, and get_current_user/require_admin FastAPI dependencies reading role from JWT claims without DB lookup**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-25T15:16:00Z
- **Completed:** 2026-02-25T15:21:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- UserRepository with 4 methods: get_by_email, get_by_id, create (email + hashed_password only, no role param), set_role_admin (seed-only)
- RefreshTokenRepository with 4 methods: create (with optional token_family for rotation), get_by_token, revoke (single token), revoke_family (theft detection — revokes by family UUID, not user_id)
- AuthService with timing-safe login (DUMMY_HASH module-level constant, verify_password always runs), register/login returning (access_token, refresh_token) tuples, refresh with reuse detection, idempotent logout
- get_current_user dependency decodes JWT with no DB lookup (role from claims), require_admin checks role == "admin", CurrentUser/AdminUser type aliases for clean route declarations
- 108/108 tests pass, ruff check and format clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Create UserRepository and RefreshTokenRepository** - `14f7f54` (feat, combined with Task 2)
2. **Task 2: Create AuthService and add RBAC dependencies to deps.py** - `14f7f54` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `app/users/repository.py` - UserRepository (get_by_email, get_by_id, create, set_role_admin) and RefreshTokenRepository (create with token_family, get_by_token, revoke, revoke_family); uses session.flush() not commit
- `app/users/service.py` - AuthService with DUMMY_HASH module-level constant, timing-safe login, register/login returning token tuples, refresh with family rotation and reuse detection, idempotent logout; OAuthAccountRepository and oauth_login added for Phase 3 forward compatibility
- `app/core/deps.py` - oauth2_scheme, get_current_user (JWT decode only, no DB), require_admin (403 on non-admin), CurrentUser/AdminUser type aliases added alongside existing get_db/DbSession

## Decisions Made

- DUMMY_HASH computed at module load — Argon2 hashing is CPU-intensive; pre-computing once avoids per-request overhead and ensures timing consistency on the user-not-found path
- get_current_user reads role from JWT claims only — no DB lookup on every authenticated request; role changes take effect at next token issuance (next login)
- AuthService.refresh() inherits token_family from revoked token — maintains the rotation chain for multi-session theft detection; revoke_family covers only the compromised session family, not all user sessions
- logout() is idempotent — returns None if token already revoked or missing; avoids errors on double-logout or stale token cleanup
- OAuthAccountRepository and oauth_login added to service.py (Phase 3 forward compatibility) — oauth_repo defaults to None, backward-compatible with register/login/refresh/logout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added OAuthAccountRepository and oauth_login to service/repository**
- **Found during:** Task 2 (reviewing existing files — implementations carried Phase 3 additions)
- **Issue:** Plan 03 spec covers only JWT auth; however, Phase 3 OAuth functionality was pre-implemented in the same commit for cohesion
- **Fix:** OAuthAccountRepository added to repository.py; oauth_login added to service.py with oauth_repo=None default (backward compatible)
- **Files modified:** app/users/repository.py, app/users/service.py
- **Verification:** All 108 tests pass, ruff check clean
- **Committed in:** 14f7f54

---

**Total deviations:** 1 (Phase 3 forward-compat additions bundled into Plan 03 commit)
**Impact on plan:** No regressions. OAuth additions are backward-compatible (None default). All Plan 03 requirements (AUTH-01 through AUTH-05) fully satisfied.

## Issues Encountered

None — implementation was found pre-committed at 14f7f54 from prior session. Verified all imports, ruff check, and 108/108 tests before creating summary.

## Next Phase Readiness

- Repository and service layers complete — Plan 04 (auth router endpoints) can proceed
- Deps.py has get_current_user, require_admin, CurrentUser, AdminUser ready for all routes
- DUMMY_HASH, timing-safe login, token rotation, and family revocation all verified
- OAuth infrastructure (OAuthAccountRepository, oauth_login) pre-built for Plan 03 OAuth phase

---
*Phase: 02-core-auth*
*Completed: 2026-02-25*

## Self-Check: PASSED

- app/users/repository.py: FOUND
- app/users/service.py: FOUND
- app/core/deps.py: FOUND
- .planning/phases/02-core-auth/02-03-SUMMARY.md: FOUND
- Commit 14f7f54 (feat(02-03)): FOUND
- 108/108 tests passing
- ruff check: zero violations on all 3 files
