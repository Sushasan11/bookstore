---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Admin Dashboard & Analytics
status: in_progress
last_updated: "2026-02-27"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 5
  completed_plans: 2
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** v2.1 Admin Dashboard & Analytics — Phase 16: Sales Analytics

## Current Position

Phase: 16 of 18 (Sales Analytics) — COMPLETE
Plan: 2 of 2 — COMPLETE
Status: Phase 16 complete, ready for Phase 17
Last activity: 2026-02-27 — Completed 16-02: Top-books endpoint and integration tests

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (this milestone)
- Average duration: ~3.5 min
- Total execution time: ~7 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 16-sales-analytics | 2/2 COMPLETE | ~7 min | ~3.5 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

From 16-01:
- AOV returns 0.0 (not null) when order_count is 0 — consistent zero-state semantics
- delta_percentage returns null when prior period revenue is 0 — avoids division by zero
- Period end for current period is always datetime.now(timezone.utc), not forced midnight — partial period
- Router-level Depends(require_admin) protects all analytics endpoints automatically
- float(round(val, 2)) for all money values — avoids Pydantic v2 Decimal-as-string serialization

From 16-02:
- Top-books goes directly to repository (no service layer) — no period/delta logic needed
- INNER JOIN to Book safe after book_id IS NOT NULL filter — no ghost groups from NULL book_ids
- Test data design: Book A (2x$50=$100 rev), Book B (8x$10=$80 rev), Book C (3x$30=$90 rev) proves revenue ≠ volume ordering

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
Stopped at: Completed 16-02-PLAN.md — Phase 16 Sales Analytics complete, all 4 requirements implemented and tested
Resume file: None
