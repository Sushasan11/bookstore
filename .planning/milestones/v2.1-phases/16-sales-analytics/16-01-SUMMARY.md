---
phase: 16-sales-analytics
plan: 1
subsystem: admin-analytics
tags: [analytics, repository, service, pydantic, fastapi, admin]
dependency_graph:
  requires: []
  provides: [analytics-stack, sales-summary-endpoint]
  affects: [app/main.py]
tech_stack:
  added: []
  patterns: [cross-domain-repository, router-level-admin-dependency, float-schema-for-decimal]
key_files:
  created:
    - app/admin/analytics_repository.py
    - app/admin/analytics_service.py
    - app/admin/analytics_schemas.py
    - app/admin/analytics_router.py
  modified:
    - app/main.py
decisions:
  - "AOV returns 0.0 (not null) when order_count is 0 — per locked product decision"
  - "delta_percentage returns null when prior period revenue is 0 — avoids division by zero and is semantically correct"
  - "Period end for current period is always datetime.now(timezone.utc), not midnight — partial period tracking"
  - "Admin protection applied at router level via Depends(require_admin) — all analytics endpoints protected automatically"
  - "All money values converted via float(round(val, 2)) before returning — avoids Decimal serialization issues in Pydantic v2"
metrics:
  duration_minutes: 2
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 16 Plan 1: Analytics Stack (Repository, Service, Schemas, Router) Summary

**One-liner:** Full analytics data stack — AnalyticsRepository with CONFIRMED-only revenue queries, AdminAnalyticsService with UTC period bounds and delta calculation, SalesSummaryResponse schema, and GET /admin/analytics/sales/summary endpoint.

## What Was Built

The complete analytics foundation for Phase 16: four new files establishing a repository, service, schema, and router, plus registration in main.py.

**AnalyticsRepository** (`app/admin/analytics_repository.py`) reads directly from `orders` and `order_items` tables using a single aggregate query. It filters exclusively on `OrderStatus.CONFIRMED`, uses `func.coalesce(..., Decimal("0"))` so empty periods return zero instead of None, and counts distinct order IDs to avoid double-counting from the join.

**AdminAnalyticsService** (`app/admin/analytics_service.py`) owns all period boundary logic. Module-level helper functions `_period_bounds` and `_prior_period_bounds` compute UTC-aware start/end datetimes for today, week (ISO Monday), and month. The service calls the repository twice (current + prior period), computes AOV and delta_percentage following locked product decisions, and converts all Decimal values to float before returning.

**SalesSummaryResponse** (`app/admin/analytics_schemas.py`) is a straightforward Pydantic BaseModel. Money fields (`revenue`, `aov`) are `float` to avoid Pydantic v2's default Decimal-as-string serialization. `delta_percentage` is `float | None`.

**Analytics Router** (`app/admin/analytics_router.py`) is created with `prefix="/admin/analytics"`, `tags=["admin-analytics"]`, and `dependencies=[Depends(require_admin)]` protecting all routes. The single endpoint `GET /sales/summary` uses a `period` query parameter validated against `^(today|week|month)$` — invalid values automatically return 422 via FastAPI's built-in validation.

**main.py** updated to import and register `analytics_router` after `admin_users_router`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create AnalyticsRepository, AdminAnalyticsService, and SalesSummaryResponse | a5ab75e | analytics_repository.py, analytics_service.py, analytics_schemas.py |
| 2 | Create analytics router and register in main.py | 3845d93 | analytics_router.py, main.py |

## Verification Results

All checks passed:
- All four new files exist in `app/admin/`
- `/admin/analytics/sales/summary` present in `app.routes`
- Import chain works: router -> service -> repository -> models (no circular imports)
- `OrderStatus.CONFIRMED` filter confirmed in analytics_repository.py (line 45)
- All datetime usage is `datetime.now(timezone.utc)` — no naive datetimes
- Money fields in schema are `float`, not `Decimal`

## Decisions Made

- **AOV = 0.0 when no orders:** Per locked product decision. Returns `0.0` not `null` — consistent with "zero revenue, zero orders" state.
- **delta_percentage = null when prior revenue is zero:** Mathematically undefined, semantically correct. Avoids division by zero.
- **Period end is always `now`:** Current period is always partial (up to this moment), not forced to midnight. Prior period uses full start-to-end boundaries.
- **Router-level admin guard:** `dependencies=[Depends(require_admin)]` at the `APIRouter` constructor means all future endpoints added to this router are automatically protected.
- **float for money in schema:** Pydantic v2 serializes `Decimal` as a string in JSON by default. All money values converted via `float(round(val, 2))` in the service layer, and schema uses `float` fields.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- FOUND: app/admin/analytics_repository.py
- FOUND: app/admin/analytics_service.py
- FOUND: app/admin/analytics_schemas.py
- FOUND: app/admin/analytics_router.py

Commits verified:
- FOUND: a5ab75e (feat(16-01): create AnalyticsRepository, AdminAnalyticsService, and SalesSummaryResponse schema)
- FOUND: 3845d93 (feat(16-01): create analytics router and register GET /admin/analytics/sales/summary)
