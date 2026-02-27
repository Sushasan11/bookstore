# Roadmap: BookStore

## Milestones

- ✅ **v1.0 MVP** - Phases 1-8 (shipped 2026-02-25)
- ✅ **v1.1 Pre-booking, Notifications & Admin** - Phases 9-12 (shipped 2026-02-26)
- ✅ **v2.0 Reviews & Ratings** - Phases 13-15 (shipped 2026-02-27)
- 🚧 **v2.1 Admin Dashboard & Analytics** - Phases 16-18 (in progress)
- 📋 **v3.0 Frontend (Next.js + TypeScript)** - Phases TBD (planned, after backend completes)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-8) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: Infrastructure (4/4 plans) — completed 2026-02-25
- [x] Phase 2: Core Auth (5/5 plans) — completed 2026-02-25
- [x] Phase 3: OAuth (3/3 plans) — completed 2026-02-25
- [x] Phase 4: Catalog (3/3 plans) — completed 2026-02-25
- [x] Phase 5: Discovery (3/3 plans) — completed 2026-02-25
- [x] Phase 6: Cart (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Orders (2/2 plans) — completed 2026-02-25
- [x] Phase 8: Wishlist (2/2 plans) — completed 2026-02-25

</details>

<details>
<summary>✅ v1.1 Pre-booking, Notifications & Admin (Phases 9-12) — SHIPPED 2026-02-26</summary>

- [x] Phase 9: Email Infrastructure (2/2 plans) — completed 2026-02-26
- [x] Phase 10: Admin User Management (2/2 plans) — completed 2026-02-26
- [x] Phase 11: Pre-booking (2/2 plans) — completed 2026-02-26
- [x] Phase 12: Email Notifications Wiring (2/2 plans) — completed 2026-02-26

</details>

<details>
<summary>✅ v2.0 Reviews & Ratings (Phases 13-15) — SHIPPED 2026-02-27</summary>

- [x] Phase 13: Review Data Layer (2/2 plans) — completed 2026-02-26
- [x] Phase 14: Review CRUD Endpoints (2/2 plans) — completed 2026-02-26
- [x] Phase 15: Book Detail Aggregates (1/1 plan) — completed 2026-02-27

</details>

### 🚧 v2.1 Admin Dashboard & Analytics (In Progress)

**Milestone Goal:** Give admins operational visibility into sales performance, inventory health, and review quality through API endpoints.

- [ ] **Phase 16: Sales Analytics** - Revenue summary with period comparison, top-selling books by revenue and volume
- [ ] **Phase 17: Inventory Analytics** - Low-stock alerts with configurable threshold
- [ ] **Phase 18: Review Moderation Dashboard** - Admin review listing with filters and bulk delete

## Phase Details

### Phase 16: Sales Analytics
**Goal**: Admins can answer "how is the store performing?" through revenue summary, period-over-period comparison, and top-seller rankings
**Depends on**: Phase 15 (existing orders/order_items tables, AdminUser dependency)
**Requirements**: SALES-01, SALES-02, SALES-03, SALES-04
**Success Criteria** (what must be TRUE):
  1. Admin can call `GET /admin/analytics/sales/summary?period=today` and receive total revenue, order count, and AOV for the requested period
  2. Admin can call `GET /admin/analytics/sales/summary?period=week` and see a delta percentage comparing current week revenue to the previous week
  3. Admin can call `GET /admin/analytics/sales/top-books?sort_by=revenue` and receive books ranked by total revenue with title, author, units sold, and revenue per book
  4. Admin can call `GET /admin/analytics/sales/top-books?sort_by=volume` and receive books ranked by units sold — distinct ordering from revenue ranking when the two diverge
  5. Only CONFIRMED orders appear in all analytics; PAYMENT_FAILED orders are silently excluded
**Plans**: 2 plans

Plans:
- [x] 16-01-PLAN.md — AnalyticsRepository, AdminAnalyticsService, schemas, and revenue summary endpoint
- [ ] 16-02-PLAN.md — Top-books endpoint and integration tests for all sales analytics

### Phase 17: Inventory Analytics
**Goal**: Admins can answer "what do I need to restock?" by querying books at or below a configurable stock threshold
**Depends on**: Phase 16 (analytics infrastructure: router, schemas, repository base)
**Requirements**: INV-01
**Success Criteria** (what must be TRUE):
  1. Admin can call `GET /admin/analytics/inventory/low-stock?threshold=10` and receive all books with stock at or below 10, ordered by stock ascending
  2. The threshold parameter is configurable per request — changing from `threshold=5` to `threshold=20` returns a different, correctly filtered set
  3. Books with zero stock appear at the top of the low-stock list (ordered by stock ascending)
**Plans**: TBD

Plans:
- [ ] 17-01: Low-stock endpoint and integration tests

### Phase 18: Review Moderation Dashboard
**Goal**: Admins can list, filter, and bulk-delete reviews to maintain review quality across the catalog
**Depends on**: Phase 15 (Review model, soft-delete convention, ReviewRepository)
**Requirements**: MOD-01, MOD-02
**Success Criteria** (what must be TRUE):
  1. Admin can call `GET /admin/reviews?page=1&per_page=20` and receive a paginated list of all non-deleted reviews with reviewer and book context
  2. Admin can filter reviews by book, user, or rating range — e.g. `?book_id=5&rating_min=1&rating_max=2` returns only low-rated reviews for that book
  3. Admin can sort review results by date or rating in ascending or descending order
  4. Admin can call `DELETE /admin/reviews/bulk` with a list of review IDs and have all matching non-deleted reviews soft-deleted in a single operation
  5. Soft-deleted reviews do not reappear in subsequent calls to `GET /admin/reviews`
**Plans**: TBD

Plans:
- [ ] 18-01: AdminReviewResponse schema, list_all_admin() repository method, and admin review list endpoint
- [ ] 18-02: bulk_delete() repository method, bulk delete endpoint, and integration tests

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure | v1.0 | 4/4 | Complete | 2026-02-25 |
| 2. Core Auth | v1.0 | 5/5 | Complete | 2026-02-25 |
| 3. OAuth | v1.0 | 3/3 | Complete | 2026-02-25 |
| 4. Catalog | v1.0 | 3/3 | Complete | 2026-02-25 |
| 5. Discovery | v1.0 | 3/3 | Complete | 2026-02-25 |
| 6. Cart | v1.0 | 2/2 | Complete | 2026-02-25 |
| 7. Orders | v1.0 | 2/2 | Complete | 2026-02-25 |
| 8. Wishlist | v1.0 | 2/2 | Complete | 2026-02-25 |
| 9. Email Infrastructure | v1.1 | 2/2 | Complete | 2026-02-26 |
| 10. Admin User Management | v1.1 | 2/2 | Complete | 2026-02-26 |
| 11. Pre-booking | v1.1 | 2/2 | Complete | 2026-02-26 |
| 12. Email Notifications Wiring | v1.1 | 2/2 | Complete | 2026-02-26 |
| 13. Review Data Layer | v2.0 | 2/2 | Complete | 2026-02-26 |
| 14. Review CRUD Endpoints | v2.0 | 2/2 | Complete | 2026-02-26 |
| 15. Book Detail Aggregates | v2.0 | 1/1 | Complete | 2026-02-27 |
| 16. Sales Analytics | v2.1 | 1/2 | In progress | - |
| 17. Inventory Analytics | v2.1 | 0/1 | Not started | - |
| 18. Review Moderation Dashboard | v2.1 | 0/2 | Not started | - |
