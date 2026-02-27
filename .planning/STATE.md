---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Admin Dashboard & Analytics
status: in_progress
last_updated: "2026-02-27"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 5
  completed_plans: 1
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** v2.1 Admin Dashboard & Analytics — Phase 16: Sales Analytics

## Current Position

Phase: 16 of 18 (Sales Analytics)
Plan: 1 of 2
Status: In progress
Last activity: 2026-02-27 — Completed 16-01: Analytics stack (repository, service, schemas, router)

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 1 (this milestone)
- Average duration: ~2 min
- Total execution time: ~2 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 16-sales-analytics | 1/2 | ~2 min | ~2 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

From 16-01:
- AOV returns 0.0 (not null) when order_count is 0 — consistent zero-state semantics
- delta_percentage returns null when prior period revenue is 0 — avoids division by zero
- Period end for current period is always datetime.now(timezone.utc), not forced midnight — partial period
- Router-level Depends(require_admin) protects all analytics endpoints automatically
- float(round(val, 2)) for all money values — avoids Pydantic v2 Decimal-as-string serialization

From v2.0 (key decisions relevant to v2.1):
- Live SQL aggregates (not stored) — avg_rating/review_count via SQL AVG/COUNT; same pattern for analytics
- func.avg().cast(Numeric) for PostgreSQL ROUND compatibility — apply to revenue aggregates too
- Cross-domain repo injection pattern — AnalyticsRepository reads Order/OrderItem/Book/PreBooking directly
- Review soft-delete: deleted_at column (not status flag) — list_all_admin() must filter deleted_at IS NULL

From research/SUMMARY.md (v2.1):
- All analytics are read-only against existing tables; no Alembic migrations needed
- CONFIRMED orders only — every revenue query must filter Order.status == OrderStatus.CONFIRMED
- LEFT JOIN books on order_items — book_id can be NULL (SET NULL on delete); use "[Deleted Book]" fallback
- datetime.now(timezone.utc) for all period bounds — never naive datetime
- bulk_delete uses single UPDATE ... WHERE id IN (...) with synchronize_session="fetch" — no per-row loops
- AdminUser dependency set at APIRouter constructor level — protects all endpoints automatically
- Decimal fields serialized as float in all response schemas

### Blockers/Concerns

None.

### Pending Todos

None.

## Session Continuity

Last session: 2026-02-27
Stopped at: Completed 16-01-PLAN.md — analytics stack established, Phase 16 Plan 2 ready
Resume file: None
