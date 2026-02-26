---
phase: 01-infrastructure
plan: 03
subsystem: database
tags: [alembic, asyncpg, postgresql, migrations, async]

# Dependency graph
requires:
  - phase: 01-02
    provides: Async SQLAlchemy engine, DeclarativeBase (Base) in app/db/base.py, get_settings() in app/core/config.py

provides:
  - Alembic initialized with async template for asyncpg-based migrations
  - env.py configured with Base.metadata for autogenerate model discovery
  - env.py reads DATABASE_URL from pydantic-settings (single source of truth)
  - compare_type=True enabled for column type change detection
  - alembic upgrade head verified against PostgreSQL via asyncpg

affects: [01-04, phase-02-auth, phase-03-oauth, phase-04-catalog, phase-05-search, phase-06-cart, phase-07-orders, phase-08-wishlist, phase-09-prebooks]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Alembic async template with async_engine_from_config and NullPool for migration connections"
    - "env.py overrides alembic.ini URL at runtime via get_settings().DATABASE_URL"
    - "target_metadata = Base.metadata ensures autogenerate sees all models imported in app/db/base.py"
    - "compare_type=True in both offline and online migration contexts for column type change detection"

key-files:
  created:
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/.gitkeep
  modified: []

key-decisions:
  - "env.py reads DATABASE_URL from get_settings() at runtime, not from alembic.ini -- single source of truth for database configuration"
  - "alembic.ini retains a placeholder URL (driver://user:pass@localhost/dbname) that is never used at runtime"
  - "compare_type=True in both offline and online modes ensures Alembic detects column type changes during autogenerate"

patterns-established:
  - "Pattern: All future model files must be imported in app/db/base.py for Alembic autogenerate to detect their tables"
  - "Pattern: Never edit sqlalchemy.url in alembic.ini for environment config -- use .env and pydantic-settings instead"
  - "Pattern: Migration connections use NullPool (not the app's connection pool) to avoid pool exhaustion during migrations"

requirements-completed: [INFRA-ALEMBIC]

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 1 Plan 03: Alembic Async Migration Setup Summary

**Async Alembic with env.py importing Base.metadata from app.db.base, reading DATABASE_URL from pydantic-settings, and compare_type=True for full autogenerate support**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-25
- **Completed:** 2026-02-25
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Alembic initialized with async template using async_engine_from_config and NullPool for migration connections to asyncpg/PostgreSQL
- env.py imports Base from app.db.base ensuring autogenerate detects all registered models (critical for preventing empty/destructive migrations)
- env.py reads DATABASE_URL from get_settings() at runtime, overriding the placeholder in alembic.ini (single source of truth)
- compare_type=True enabled in both offline and online migration contexts for column type change detection
- alembic upgrade head and alembic check verified against running PostgreSQL via Docker Compose

## Task Commits

Each task was committed atomically:

1. **Task 1: Initialize Alembic with async template and configure env.py** - `4ad87f9` (feat)
2. **Task 2: Verify Alembic connects to database and migration system works** - verification-only task (no code changes; validated via `alembic upgrade head` and `alembic check`)

**Plan metadata:** (docs commit -- see below)

## Files Created/Modified

- `alembic.ini` - Alembic configuration entry point with script_location and placeholder URL
- `alembic/env.py` - Async migration runner with Base import, settings-based URL, and compare_type=True
- `alembic/script.py.mako` - Migration file template with upgrade/downgrade functions
- `alembic/versions/.gitkeep` - Ensures versions directory is tracked by git

## Decisions Made

- env.py reads DATABASE_URL from get_settings() at runtime, not from alembic.ini -- maintains single source of truth for database configuration across the application
- alembic.ini retains a placeholder URL that is never used at runtime -- this is standard Alembic practice when env.py overrides the URL
- compare_type=True added in both offline and online migration modes -- ensures column type changes are detected during autogenerate, not just table/column additions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - Docker Compose and PostgreSQL were already configured in Plan 01-01.

## Next Phase Readiness

- Alembic migration system complete; autogenerate ready for model changes starting in Phase 2
- All future phases create models that inherit from Base -- adding the import to app/db/base.py is the only step needed for Alembic to detect them
- Plan 01-04 (testing/tooling) is unblocked and can proceed
- No open concerns for Plan 01-04

## Self-Check: PASSED

- FOUND: alembic.ini
- FOUND: alembic/env.py
- FOUND: alembic/script.py.mako
- FOUND: alembic/versions/.gitkeep
- FOUND: .planning/phases/01-infrastructure/01-03-SUMMARY.md
- VERIFIED: env.py contains `from app.db.base import Base`
- VERIFIED: env.py contains `get_settings`
- VERIFIED: env.py contains `compare_type=True` (2 occurrences)
- VERIFIED: env.py contains `async_engine_from_config`
- VERIFIED: env.py contains `target_metadata = Base.metadata`
- VERIFIED: alembic.ini contains `script_location`
- COMMIT: Task 1 at `4ad87f9` (confirmed from git log)

---
*Phase: 01-infrastructure*
*Completed: 2026-02-25*
