---
phase: 31-code-quality
plan: "02"
subsystem: admin-analytics
tags: [analytics, period-filtering, top-books, react-query, sqlalchemy]
dependency_graph:
  requires: [31-01]
  provides: [period-aware-top-sellers]
  affects: [admin-overview-page, admin-sales-page]
tech_stack:
  added: []
  patterns: [optional-query-param, react-query-cache-key-parameterization, sqlalchemy-conditional-where]
key_files:
  created: []
  modified:
    - backend/app/admin/analytics_repository.py
    - backend/app/admin/analytics_router.py
    - frontend/src/lib/admin.ts
    - frontend/src/app/admin/overview/page.tsx
    - frontend/src/app/admin/sales/page.tsx
decisions:
  - period param is optional on backend endpoint — backward compatible, no period returns all-time data
  - period included in React Query key for automatic cache separation per period
  - router imports _period_bounds directly from analytics_service (no new service method needed)
metrics:
  duration: "~2 minutes"
  completed_date: "2026-03-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 31 Plan 02: Period-Filtered Top-Sellers Analytics Summary

**One-liner:** Top-sellers table now respects period selector by threading period from UI through React Query key, fetchTopBooks, and backend SQL date range filter on Order.created_at.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add period filtering to backend top-books endpoint | 65ae8c7 | analytics_repository.py, analytics_router.py |
| 2 | Wire frontend to pass period through query key and fetch function | 36850c9 | admin.ts, overview/page.tsx, sales/page.tsx |

## What Was Built

### Backend (Task 1)

**analytics_repository.py** — `top_books()` now accepts two optional keyword params:
- `period_start: datetime | None` — when provided, adds `Order.created_at >= period_start`
- `period_end: datetime | None` — when provided, adds `Order.created_at < period_end`
- Both must be non-None for filter to apply; when either is None, the query is unchanged (all-time data)

**analytics_router.py** — `GET /admin/analytics/sales/top-books` now accepts:
- `period: str | None = Query(None, pattern="^(today|week|month)$")` — optional period filter
- When period is set, computes bounds via the existing `_period_bounds()` utility and passes to repository
- When period is omitted, passes None bounds (backward compatible)

### Frontend (Task 2)

**lib/admin.ts** — Two changes:
- `adminKeys.sales.topBooks` key factory gains optional `period?: string` parameter — period included as last element in the cache key array, ensuring React Query uses separate cache entries per period
- `fetchTopBooks` gains optional `period?: string` parameter — uses `URLSearchParams` to build query string, only appends `period` param when truthy

**overview/page.tsx** — `topBooksQuery` now passes `period` state to both `queryKey` and `queryFn`, so the "Top 5 Best Sellers" mini-table refreshes when the period selector changes.

**sales/page.tsx** — `topBooksQuery` now passes `period` state to both `queryKey` and `queryFn`, so the "Top Sellers" full table refreshes when the period selector changes.

## Verification

All plan verification checks passed:
1. `npx tsc --noEmit` — exits with 0, no type errors
2. `grep -n "period" analytics_router.py` — period param on get_top_books confirmed
3. `grep -n "period_start" analytics_repository.py` — period filtering in top_books confirmed
4. `grep -n "period" admin.ts` — period in topBooks key factory and fetchTopBooks confirmed
5. `grep -n "period" overview/page.tsx` — period passed to topBooksQuery confirmed
6. `grep -n "period" sales/page.tsx` — period passed to topBooksQuery confirmed
7. `python -c "from app.admin.analytics_router import get_top_books; print('OK')"` — OK

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- FOUND: backend/app/admin/analytics_repository.py
- FOUND: backend/app/admin/analytics_router.py
- FOUND: frontend/src/lib/admin.ts
- FOUND: frontend/src/app/admin/overview/page.tsx
- FOUND: frontend/src/app/admin/sales/page.tsx

Commits exist:
- FOUND: 65ae8c7 (Task 1 — backend period filtering)
- FOUND: 36850c9 (Task 2 — frontend period wiring)
