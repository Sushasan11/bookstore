# Requirements: BookStore

**Defined:** 2026-02-27
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## v2.1 Requirements

Requirements for milestone v2.1: Admin Dashboard & Analytics. Each maps to roadmap phases.

### Sales Analytics

- [x] **SALES-01**: Admin can view revenue summary (total revenue, order count, AOV) for today, this week, or this month
- [x] **SALES-02**: Admin can view period-over-period comparison (delta % vs previous period) alongside revenue summary
- [x] **SALES-03**: Admin can view top-selling books ranked by revenue with book title, author, units sold, and total revenue
- [x] **SALES-04**: Admin can view top-selling books ranked by volume (units sold) with book title and author

### Inventory Analytics

- [x] **INV-01**: Admin can query books with stock at or below a configurable threshold, ordered by stock ascending

### Review Moderation

- [x] **MOD-01**: Admin can list all reviews with pagination, sort (by date or rating), and filter (by book, user, or rating range)
- [ ] **MOD-02**: Admin can bulk-delete reviews by providing a list of review IDs

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Sales Analytics (v2.x)

- **SALES-05**: Admin can view AOV trend over time (weekly/monthly buckets)
- **SALES-06**: Admin can view revenue breakdown by genre

### Inventory Analytics (v2.x)

- **INV-02**: Admin can view stock turnover velocity per book (units sold per period vs current stock)
- **INV-03**: Admin can view pre-booking demand ranking (most-waited-for out-of-stock books)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time streaming analytics (WebSockets) | Admin analytics are not real-time; REST endpoints with explicit refresh are correct |
| Materialized views / analytics tables | Live SQL aggregates on indexed columns are fast enough at current volume |
| Celery / Redis for analytics | Existing constraint; BackgroundTasks sufficient, analytics are synchronous queries |
| User cohort analysis | BI tool feature, not operational admin panel; requires complex query surface |
| Revenue forecasting / demand prediction | Insufficient data history; manual judgment with velocity signals is correct |
| Automated review flagging / AI moderation | External API cost + false-positive management unjustified at current review volume |
| CSV/PDF export | API-first project; consumers handle formatting; adds file-gen complexity |
| Pre-moderation review queue | Already rejected in v2.0; reactive admin-delete is correct pattern |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SALES-01 | Phase 16 | Complete (16-01) |
| SALES-02 | Phase 16 | Complete (16-01) |
| SALES-03 | Phase 16 | Complete |
| SALES-04 | Phase 16 | Complete |
| INV-01 | Phase 17 | Complete |
| MOD-01 | Phase 18 | Complete |
| MOD-02 | Phase 18 | Pending |

**Coverage:**
- v2.1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after 16-01 completion (SALES-01, SALES-02 marked complete)*
