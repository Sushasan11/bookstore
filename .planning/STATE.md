---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Admin Dashboard & Analytics
status: ready_to_plan
last_updated: "2026-02-27"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 5
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** v2.1 Admin Dashboard & Analytics — Phase 16: Sales Analytics

## Current Position

Phase: 16 of 18 (Sales Analytics)
Plan: 0 of 2
Status: Ready to plan
Last activity: 2026-02-27 — Roadmap created for v2.1 (3 phases, 7 requirements)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

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
Stopped at: Roadmap created — Phase 16 ready to plan
Resume file: None
