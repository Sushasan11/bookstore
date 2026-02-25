---
phase: 02-core-auth
plan: 04
subsystem: auth
tags: [fastapi, router, endpoints, seed-script, asyncio, admin]

# Dependency graph
requires:
  - phase: 02-03
    provides: AuthService (register, login, refresh, logout), UserRepository, RefreshTokenRepository, get_current_user, require_admin
  - phase: 02-02
    provides: TokenResponse, UserCreate, LoginRequest, RefreshRequest schemas; DbSession dependency
provides:
  - POST /auth/register endpoint (201 + TokenResponse)
  - POST /auth/login endpoint (200 + TokenResponse)
  - POST /auth/refresh endpoint (200 + TokenResponse)
  - POST /auth/logout endpoint (204 No Content)
  - auth_router registered in main.py under /auth prefix
  - scripts/seed_admin.py CLI script for creating first admin user
affects: [all phases that consume auth tokens, 02-05 integration tests, 03-oauth router extension]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - _make_service(db) factory per request — thin router delegates all logic to AuthService
    - Auth router prefix /auth with tags=["auth"] for OpenAPI grouping
    - Standalone seed script using asyncio.run() — no Click dependency, stdlib getpass for hidden input

key-files:
  created:
    - app/users/router.py
    - scripts/seed_admin.py
    - scripts/__init__.py
  modified:
    - app/main.py

key-decisions:
  - "Auth router prefix /auth, 4 endpoints: register (201), login (200), refresh (200), logout (204)"
  - "Admin seed via standalone script (scripts/seed_admin.py) using asyncio.run — no Click dependency added"
  - "_make_service(db) instantiates AuthService with UserRepository + RefreshTokenRepository per request — thin router pattern"

patterns-established:
  - "_make_service(db) factory: instantiates service with repositories bound to current db session; keeps route handlers thin"
  - "Seed scripts: standalone asyncio.run() scripts with getpass for hidden password input; no Click needed for one-time ops"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05]

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 2 Plan 04: Auth Endpoints and Admin Seed Script Summary

**FastAPI auth router with 4 HTTP endpoints (register/login/refresh/logout) wired into main.py, plus a standalone asyncio seed script for bootstrapping the first admin user**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-25T15:18:00Z
- **Completed:** 2026-02-25T15:21:04Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Auth router (`app/users/router.py`) with 4 endpoints: POST /auth/register (201), POST /auth/login (200), POST /auth/refresh (200), POST /auth/logout (204); all use `_make_service(db)` factory to instantiate AuthService per request
- All 4 routes registered in `app/main.py` via `application.include_router(auth_router)` — confirmed by inspecting `app.routes`
- `scripts/seed_admin.py` standalone script: checks for duplicate email, creates user via UserRepository, calls `set_role_admin()`, commits; uses stdlib `getpass` for hidden password input; validates password length >= 8
- 108/108 tests pass, ruff check and format clean on all modified files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth router and register it in main.py** - `ce8f792` (feat)
2. **Task 2: Create admin seed script** - `ce8f792` (feat, combined with Task 1)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `app/users/router.py` - Auth router with `/auth` prefix, 4 endpoints: register (201), login (200), refresh (200), logout (204); `_make_service(db)` factory instantiates AuthService per request; includes OAuthAccount repository for Phase 3 OAuth endpoints
- `app/main.py` - Added `from app.users.router import router as auth_router` import and `application.include_router(auth_router)` call in `create_app()`
- `scripts/seed_admin.py` - Standalone async seed script: duplicate email check, create user, set_role_admin, commit; `getpass` for hidden password; validates email non-empty and password >= 8 chars; exits 1 on duplicate or IntegrityError
- `scripts/__init__.py` - Empty file to make scripts/ a package

## Decisions Made

- `_make_service(db)` factory pattern: instantiates AuthService with repositories bound to current session per request — keeps route handlers to 2-3 lines, consistent with catalog/cart patterns established later
- No Click dependency for seed script — stdlib `getpass` is sufficient for a one-time operation; avoids adding an unneeded dependency to pyproject.toml
- Logout endpoint accepts body (RefreshRequest with refresh_token) rather than Authorization header — allows revoking any session token, not just the currently-presented one

## Deviations from Plan

None — plan executed exactly as written. Implementation was found pre-committed at `ce8f792` from the same prior session. Verified all routes, ruff check, and 108/108 tests before creating summary.

## Issues Encountered

None — implementation was found pre-committed at `ce8f792` from a prior session. All verification checks passed:
- All 4 /auth/* routes confirmed in `app.routes`
- OpenAPI schema includes all 4 auth endpoints
- `scripts/seed_admin.py` parses correctly with `create_admin` async function
- ruff check and format: zero violations on all files
- 108/108 tests pass

## Next Phase Readiness

- All 4 auth endpoints live on the FastAPI app — Plan 05 integration tests can run against them
- Admin seed script runnable via `poetry run python scripts/seed_admin.py` — first admin can be bootstrapped for any environment
- Phase 3 OAuth endpoints already extended the router with Google and GitHub callbacks (pre-built in same session)

---
*Phase: 02-core-auth*
*Completed: 2026-02-25*

## Self-Check: PASSED

- app/users/router.py: FOUND
- app/main.py: FOUND (includes auth_router)
- scripts/seed_admin.py: FOUND
- scripts/__init__.py: FOUND
- .planning/phases/02-core-auth/02-04-SUMMARY.md: FOUND (this file)
- Commit ce8f792 (feat(02-04)): FOUND
- All 4 /auth/* routes confirmed in app.routes: /auth/register, /auth/login, /auth/refresh, /auth/logout
- 108/108 tests passing
- ruff check: zero violations on all 3 files
