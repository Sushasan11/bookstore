---
phase: 02-core-auth
plan: 01
subsystem: auth
tags: [sqlalchemy, postgresql, alembic, orm, uuid, enum]

# Dependency graph
requires:
  - phase: 01-infrastructure
    provides: DeclarativeBase in app/db/base.py, Alembic env.py, AsyncSessionLocal, test infrastructure
provides:
  - User SQLAlchemy model with email/hashed_password/role/is_active/created_at columns
  - RefreshToken SQLAlchemy model with token/token_family(UUID)/user_id/expires_at/revoked_at columns
  - UserRole StrEnum with USER and ADMIN values
  - Alembic migration 451f9697aceb creating users and refresh_tokens tables
  - users table and refresh_tokens table in PostgreSQL
affects: [02-core-auth, 03-oauth, all-phases]

# Tech tracking
tech-stack:
  added: [sqlalchemy.dialects.postgresql.UUID, enum.StrEnum]
  patterns: [model-aggregator-base.py, token-family-revocation, str-enum-for-db-enum]

key-files:
  created:
    - app/users/__init__.py
    - app/users/models.py
    - alembic/versions/451f9697aceb_create_users_and_refresh_tokens.py
  modified:
    - app/db/base.py

key-decisions:
  - "UserRole is a StrEnum with values 'user' and 'admin' — no roles table, no extensibility needed"
  - "RefreshToken has token_family UUID column for family-level revocation (theft detection)"
  - "hashed_password initially nullable=False in this migration; made nullable in 7b2f3a8c4d1e for OAuth"

patterns-established:
  - "Model aggregator: all model imports go in app/db/base.py (or alembic/env.py) for Alembic autogenerate discovery"
  - "Token family pattern: UUID column on RefreshToken enables full-family revocation on theft detection"
  - "StrEnum for DB enums: UserRole inherits both str and enum.Enum via StrEnum for clean SQLAlchemy SAEnum mapping"

requirements-completed: [AUTH-01, AUTH-02, AUTH-04]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 2 Plan 1: User and RefreshToken SQLAlchemy Models with Alembic Migration Summary

**User and RefreshToken ORM models with token_family UUID theft detection, UserRole StrEnum, and Alembic migration creating users and refresh_tokens PostgreSQL tables**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-25T15:15:00Z
- **Completed:** 2026-02-25T15:21:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- User model with id/email/hashed_password/role/is_active/created_at and cascade delete-orphan on refresh_tokens
- RefreshToken model with token_family UUID column for family-level theft detection, is_revoked/is_expired properties
- Alembic migration 451f9697aceb applied cleanly — creates users and refresh_tokens tables with correct indexes
- All 108 tests pass after migration is applied to head (including Phase 1 smoke tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create User and RefreshToken SQLAlchemy models** - `858ff77` (feat)
2. **Task 2: Commit users/refresh_tokens Alembic migration file** - `5cfa7bc` (feat)

**Plan metadata:** (docs commit — see state updates)

## Files Created/Modified

- `app/users/__init__.py` - Package marker for users domain (empty)
- `app/users/models.py` - User model (email/password/role/is_active), RefreshToken model (token/token_family/expires_at/revoked_at), UserRole StrEnum
- `alembic/versions/451f9697aceb_create_users_and_refresh_tokens.py` - Migration creating users and refresh_tokens tables with all indexes
- `app/db/base.py` - Added User and RefreshToken imports for Alembic model aggregation (noqa: F401)

## Decisions Made

- UserRole uses `enum.StrEnum` (Python 3.11+) rather than `str, enum.Enum` — cleaner inheritance, same DB behavior
- token_family uses PostgreSQL-native UUID type via `sqlalchemy.dialects.postgresql.UUID(as_uuid=True)` — stored as true UUID not varchar
- `is_revoked` and `is_expired` implemented as @property on RefreshToken — computed from existing columns, no extra DB storage
- Model imports placed in `app/db/base.py` with `# noqa: F401` so Alembic autogenerate discovers both tables

## Deviations from Plan

None - plan executed as written. The migration file was untracked in git from the original execution; it was committed as part of this execution run (Task 2).

## Issues Encountered

The `alembic/versions/451f9697aceb_create_users_and_refresh_tokens.py` migration file was present on disk from a prior session but was not included in git commit `858ff77`. It was committed in this execution run as `5cfa7bc`. The migration was already applied to the database so no re-application was needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- users and refresh_tokens tables are in PostgreSQL, ready for auth service implementation
- UserRole enum available for JWT claim encoding and RBAC middleware
- RefreshToken token_family ready for rotation and theft detection logic in Plan 02-03
- Base established for Phase 2 Plans 02-05: security module, auth service, endpoints, and tests

---
*Phase: 02-core-auth*
*Completed: 2026-02-25*
