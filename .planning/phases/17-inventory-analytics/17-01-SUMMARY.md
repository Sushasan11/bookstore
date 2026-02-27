---
phase: 17-inventory-analytics
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, postgres, analytics, inventory]

# Dependency graph
requires:
  - phase: 16-sales-analytics
    provides: AnalyticsRepository class, analytics_router with admin auth, analytics_schemas patterns
provides:
  - GET /admin/analytics/inventory/low-stock endpoint with configurable threshold
  - AnalyticsRepository.low_stock_books(threshold) method
  - LowStockBookEntry and LowStockResponse Pydantic schemas
  - 15 integration tests covering all INV-01 boundary conditions
affects:
  - 17-inventory-analytics (future plans extending inventory analytics)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-table inventory query using SQLAlchemy asc() for ascending sort"
    - "Threshold echoed per-item — dashboard can show '5 units (threshold: 10)' without extra API call"
    - "Query(10, ge=0) pattern for non-negative integer query params with FastAPI automatic 422"

key-files:
  created:
    - tests/test_inventory_analytics.py
  modified:
    - app/admin/analytics_repository.py
    - app/admin/analytics_schemas.py
    - app/admin/analytics_router.py

key-decisions:
  - "threshold echoed in both top-level LowStockResponse and each LowStockBookEntry item — allows dashboard rendering without second API call"
  - "current_stock is int (not float) — stock_quantity is Integer in Book model, no Decimal conversion needed"
  - "total_low_stock=len(items) avoids second DB query since all results returned (no pagination)"
  - "Query(10, ge=0) on threshold — FastAPI returns 422 automatically for negative values"

patterns-established:
  - "Inventory analytics: single-table read-only query (no joins to orders), direct repo call from router"
  - "Fixture isolation: stock_books creates 5 books with specific stock values covering all boundary conditions"

requirements-completed: [INV-01]

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 17 Plan 01: Inventory Analytics — Low-Stock Endpoint Summary

**GET /admin/analytics/inventory/low-stock with configurable threshold, ascending stock ordering, per-item threshold echo, and 15 integration tests covering auth, filtering, ordering, and boundary conditions**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-27T09:10:03Z
- **Completed:** 2026-02-27T09:13:31Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `low_stock_books(threshold)` method to `AnalyticsRepository` — single-table Book query with `<=` filter and `asc()` ordering
- Added `LowStockBookEntry` and `LowStockResponse` Pydantic schemas with threshold echoed at both top-level and per-item
- Added `GET /admin/analytics/inventory/low-stock` endpoint with `Query(10, ge=0)` default (auto-422 for negatives)
- Created 15 integration tests covering auth gates, threshold filtering, exact boundary (`<=` not `<`), ascending ordering, zero-stock first, echoed threshold, and empty catalog

## Task Commits

Each task was committed atomically:

1. **Task 1: Repository method, schemas, and endpoint** - `68c51e8` (feat)
2. **Task 2: Comprehensive integration tests** - `83dda5a` (feat)

## Files Created/Modified
- `app/admin/analytics_repository.py` - Added `asc` import and `low_stock_books(threshold)` method
- `app/admin/analytics_schemas.py` - Added `LowStockBookEntry` and `LowStockResponse` schemas
- `app/admin/analytics_router.py` - Updated schema imports, added `GET /inventory/low-stock` endpoint
- `tests/test_inventory_analytics.py` - Created: 15 integration tests for INV-01 (279 lines)

## Decisions Made
- `threshold` echoed in `LowStockBookEntry` per-item — allows dashboard to show "5 units (threshold: 10)" without a second API call
- `current_stock` is `int` (not `float`) — `stock_quantity` is `Integer` in `Book` model, no Decimal conversion needed
- `total_low_stock=len(items)` — avoids second DB query since all matching results are returned (no pagination)
- `Query(10, ge=0)` — FastAPI automatically returns 422 for `threshold < 0`, no manual validation needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- INV-01 delivered: admins can query "what do I need to restock?" with configurable thresholds
- Inventory analytics foundation ready for any additional INV-0x requirements in Phase 17
- All 269 tests pass (no regressions in Phase 16 or any prior phase)

---
*Phase: 17-inventory-analytics*
*Completed: 2026-02-27*
