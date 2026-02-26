---
phase: 13-review-data-layer
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, postgres, repository-pattern, soft-delete]

# Dependency graph
requires:
  - phase: 01-infrastructure
    provides: DeclarativeBase in app/db/base.py; AsyncSession setup
  - phase: 02-core-auth
    provides: User model with users table FK target
  - phase: 03-book-catalog
    provides: Book model with books table FK target
provides:
  - Review SQLAlchemy model with UniqueConstraint(user_id, book_id) and CheckConstraint(rating 1-5)
  - Alembic migration a1b2c3d4e5f6 creating reviews table with all columns, constraints, and indexes
  - ReviewRepository with 7 async methods covering full CRUD, pagination, and aggregates
  - Review model registered in alembic/env.py for Alembic discovery
affects:
  - 13-review-data-layer (plan 02 - review model tests)
  - 14-review-crud-endpoints (service layer consumes ReviewRepository)
  - 15-book-detail-aggregates (get_aggregates method provides live avg/count)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Soft-delete via deleted_at nullable timestamp column
    - Sentinel object (_UNSET) to distinguish "not provided" from explicit None in update methods
    - IntegrityError catch with constraint name check for AppError(409) on duplicate
    - Paginated list query using count subquery on base_stmt.subquery()

key-files:
  created:
    - app/reviews/__init__.py
    - app/reviews/models.py
    - app/reviews/repository.py
    - alembic/versions/a1b2c3d4e5f6_create_reviews.py
  modified:
    - alembic/env.py

key-decisions:
  - "Single text field (no title/headline) with String(2000), nullable for rating-only reviews"
  - "CASCADE on both user_id and book_id FKs — reviews without a user or book are meaningless"
  - "onupdate=func.now() on updated_at is ORM-only; migration only has server_default (not onupdate)"
  - "_UNSET sentinel in update() allows passing text=None to explicitly clear review text"
  - "get_aggregates uses SQL AVG/COUNT live — not stored on books table"

patterns-established:
  - "Soft-delete pattern: deleted_at IS NULL filter in all get/list queries"
  - "IntegrityError pattern: check constraint name in orig string, raise AppError(409) for known violations, re-raise unknown"
  - "Pagination pattern: count via select(func.count()).select_from(base_stmt.subquery()), then limit/offset"

requirements-completed: [REVW-05]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 13 Plan 01: Review Data Layer Summary

**Review SQLAlchemy model with UniqueConstraint/CheckConstraint, Alembic migration (chain: f1a2b3c4d5e6 -> a1b2c3d4e5f6), and ReviewRepository with 7 async CRUD/aggregate methods using soft-delete and IntegrityError duplicate detection**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-02-26T08:49:38Z
- **Completed:** 2026-02-26T08:53:05Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Review model with UniqueConstraint(user_id, book_id), CheckConstraint(rating 1-5), soft-delete via deleted_at, and CASCADE on both FKs
- Alembic migration handwritten (revision a1b2c3d4e5f6, down_revision f1a2b3c4d5e6) with all columns, constraints, and two indexes
- ReviewRepository with all 7 async methods: create, get_by_id, get_by_user_and_book, update, soft_delete, list_for_book, get_aggregates
- Review registered in alembic/env.py — Base.metadata.tables["reviews"] confirmed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Review model and Alembic migration** - `ba2408e` (feat)
2. **Task 2: Create ReviewRepository with full CRUD and aggregate methods** - `b611f02` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/reviews/__init__.py` - Package marker for reviews module
- `app/reviews/models.py` - Review SQLAlchemy model with UniqueConstraint, CheckConstraint, soft-delete, CASCADE FKs
- `app/reviews/repository.py` - ReviewRepository: 7 async methods (create, get_by_id, get_by_user_and_book, update, soft_delete, list_for_book, get_aggregates)
- `alembic/versions/a1b2c3d4e5f6_create_reviews.py` - Migration creating reviews table (down_revision=f1a2b3c4d5e6)
- `alembic/env.py` - Added `from app.reviews.models import Review  # noqa: F401`

## Decisions Made

- **_UNSET sentinel for update()**: Uses `_UNSET = object()` so callers can pass `text=None` to explicitly clear review text, while omitting `text` leaves it unchanged.
- **CASCADE on both FKs**: Reviews are meaningless without their user or book — CASCADE chosen over SET NULL, consistent with STATE.md v2.0 research decision.
- **onupdate ORM-only**: `onupdate=func.now()` on `updated_at` is kept in the model for ORM updates but intentionally absent from the migration (migration only sets `server_default`).
- **Live aggregates**: `get_aggregates` queries SQL AVG/COUNT live — no stored column on books table to keep in sync.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — health test connection error is pre-existing (no PostgreSQL running in dev environment).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Review model and repository are fully ready for Phase 13 Plan 02 (model tests) and Phase 14 (CRUD endpoints)
- ReviewRepository provides `get_aggregates(book_id)` that Phase 15 (book detail aggregates) can consume directly
- No blockers

---
*Phase: 13-review-data-layer*
*Completed: 2026-02-26*
