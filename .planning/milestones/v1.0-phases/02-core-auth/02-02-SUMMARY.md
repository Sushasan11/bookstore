---
phase: 02-core-auth
plan: 02
subsystem: auth
tags: [jwt, argon2, pwdlib, pyjwt, pydantic, security]

# Dependency graph
requires:
  - phase: 02-01
    provides: User and RefreshToken SQLAlchemy models, UserRole StrEnum, AppError exception class
  - phase: 01-04
    provides: Test infrastructure, AppError exception class in app/core/exceptions.py
provides:
  - hash_password / verify_password async functions (Argon2id via asyncio.to_thread)
  - create_access_token / decode_access_token (HS256 JWT with sub/role/jti/iat/exp)
  - generate_refresh_token (opaque secrets.token_urlsafe 512-bit entropy)
  - UserCreate, LoginRequest, RefreshRequest, TokenResponse, UserResponse Pydantic schemas
  - SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS in Settings
affects: [02-03, 02-04, 02-05, all auth-dependent phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncio.to_thread for CPU-intensive Argon2 hashing (non-blocking event loop)
    - algorithms=["HS256"] explicit list in jwt.decode (prevents algorithm confusion attack)
    - opaque refresh tokens (not JWTs) stored in DB for simple revocation
    - from None on re-raised exceptions to suppress original exception context

key-files:
  created: []
  modified:
    - app/core/security.py
    - app/core/exceptions.py

key-decisions:
  - "Password hashing uses asyncio.to_thread to avoid blocking the event loop; algorithms=['HS256'] explicit in jwt.decode to prevent algorithm confusion"
  - "Refresh tokens are opaque strings (secrets.token_urlsafe(64)), NOT JWTs — simpler DB revocation"
  - "validation_exception_handler serializes Pydantic ctx objects to strings to avoid JSON serialization failures on ValidationError"

patterns-established:
  - "CPU-intensive security ops (Argon2 hash/verify) always wrapped in asyncio.to_thread"
  - "jwt.decode always receives algorithms=['HS256'] — never relying on token header alg"
  - "Exception re-raises use 'from None' to suppress chained exception context"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04]

# Metrics
duration: 10min
completed: 2026-02-25
---

# Phase 2 Plan 02: JWT Security Module and Auth Schemas Summary

**Argon2id password hashing via asyncio.to_thread, HS256 JWT access tokens with algorithm-confusion protection, opaque refresh tokens, and 5 Pydantic auth schemas**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-25T17:50:00Z
- **Completed:** 2026-02-25T17:59:57Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- JWT security module with 5 functions: hash_password, verify_password (async via asyncio.to_thread), create_access_token (HS256, 5 claims), decode_access_token (algorithm confusion protection), generate_refresh_token (512-bit entropy)
- Pydantic auth schemas: UserCreate (email + min_length=8 password, no role field), LoginRequest, RefreshRequest, TokenResponse (bearer default), UserResponse (from_attributes=True)
- app/core/config.py already has SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES=15, REFRESH_TOKEN_EXPIRE_DAYS=7
- validation_exception_handler improved to safely serialize Pydantic ctx objects (non-serializable ValueError etc.)
- All 108 tests pass, ruff check and format clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement JWT security module and extend config** - `b18ded4` (feat)
2. **Task 2: Create Pydantic schemas for auth endpoints** - already in HEAD (schemas.py committed via earlier work, verified passing)

## Files Created/Modified

- `app/core/security.py` - JWT security module: hash_password/verify_password (async, asyncio.to_thread), create_access_token (HS256 with sub/role/jti/iat/exp), decode_access_token (AppError 401 on failure, algorithms=["HS256"]), generate_refresh_token (secrets.token_urlsafe)
- `app/core/exceptions.py` - validation_exception_handler improved: safely converts non-serializable Pydantic ctx objects to strings
- `app/core/config.py` - already had SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES=15, REFRESH_TOKEN_EXPIRE_DAYS=7 (no changes needed)
- `app/users/schemas.py` - already complete: UserCreate (no role field), LoginRequest, RefreshRequest, TokenResponse, UserResponse (no changes needed)

## Decisions Made

- Password hashing uses asyncio.to_thread — Argon2 is CPU-intensive (~50-200ms), must not block the event loop
- jwt.decode always uses algorithms=["HS256"] explicit list — prevents algorithm confusion attack (alg:none bypass)
- Refresh tokens are opaque strings not JWTs — simpler revocation (just mark DB row as revoked)
- `from None` added to re-raised exceptions in decode_access_token — suppresses original jwt exception context, cleaner error reporting

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Improved Pydantic validation error serialization**
- **Found during:** Task 1 (reviewing exceptions.py during security module work)
- **Issue:** validation_exception_handler called exc.errors() directly which can return non-serializable objects (e.g., ValueError in ctx.error), causing JSON serialization failures on some validation errors
- **Fix:** Added loop to convert ctx dict values to strings if not a JSON-safe primitive type
- **Files modified:** app/core/exceptions.py
- **Verification:** ruff check passes, all 108 tests pass
- **Committed in:** b18ded4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical / bug fix)
**Impact on plan:** Auto-fix prevents JSON serialization failures on validation errors. No scope creep.

## Issues Encountered

None — implementations for security.py and schemas.py were previously completed (orphaned commit df50136 from earlier session). Task 1 commit adds `from None` exception chaining improvements to security.py and the validation handler fix to exceptions.py. Task 2 (schemas.py) was already committed and verified.

## Next Phase Readiness

- Security module and auth schemas complete — Plan 03 (repository + service) and Plan 04 (endpoints) can proceed
- All 5 security functions verified: hash_password, verify_password, create_access_token, decode_access_token, generate_refresh_token
- All 5 Pydantic schemas verified: UserCreate rejects invalid email and short passwords, no role field
- 108/108 tests passing

---
*Phase: 02-core-auth*
*Completed: 2026-02-25*

## Self-Check: PASSED

- app/core/security.py: FOUND
- app/core/exceptions.py: FOUND
- app/core/config.py: FOUND
- app/users/schemas.py: FOUND
- .planning/phases/02-core-auth/02-02-SUMMARY.md: FOUND
- Commit b18ded4: FOUND
- 108/108 tests passing
