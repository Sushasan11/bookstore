# Roadmap: BookStore

## Milestones

- ✅ **v1.0 MVP** — Phases 1-8 (shipped 2026-02-25)
- ✅ **v1.1 Pre-booking, Notifications & Admin** — Phases 9-12 (shipped 2026-02-26)
- ✅ **v2.0 Reviews & Ratings** — Phases 13-15 (shipped 2026-02-27)
- ✅ **v2.1 Admin Dashboard & Analytics** — Phases 16-18 (shipped 2026-02-27)
- ✅ **v3.0 Customer Storefront** — Phases 19-25 (shipped 2026-02-28)
- ✅ **v3.1 Admin Dashboard** — Phases 26-30 (shipped 2026-03-01)
- 🔄 **v4.1 Clean House** — Phases 31-32 (in progress)

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

<details>
<summary>✅ v2.1 Admin Dashboard & Analytics (Phases 16-18) — SHIPPED 2026-02-27</summary>

- [x] Phase 16: Sales Analytics (2/2 plans) — completed 2026-02-27
- [x] Phase 17: Inventory Analytics (1/1 plan) — completed 2026-02-27
- [x] Phase 18: Review Moderation Dashboard (2/2 plans) — completed 2026-02-27

</details>

<details>
<summary>✅ v3.0 Customer Storefront (Phases 19-25) — SHIPPED 2026-02-28</summary>

- [x] Phase 19: Monorepo + Frontend Foundation (3/3 plans) — completed 2026-02-27
- [x] Phase 20: Auth Integration (3/3 plans) — completed 2026-02-27
- [x] Phase 21: Catalog and Search (4/4 plans) — completed 2026-02-27
- [x] Phase 22: Cart and Checkout (5/5 plans) — completed 2026-02-27
- [x] Phase 23: Orders and Account (2/2 plans) — completed 2026-02-27
- [x] Phase 24: Wishlist and Pre-booking (3/3 plans) — completed 2026-02-28
- [x] Phase 25: Reviews (2/2 plans) — completed 2026-02-28

</details>

<details>
<summary>✅ v3.1 Admin Dashboard (Phases 26-30) — SHIPPED 2026-03-01</summary>

- [x] Phase 26: Admin Foundation (2/2 plans) — completed 2026-02-28
- [x] Phase 27: Sales Analytics and Inventory Alerts (2/2 plans) — completed 2026-02-28
- [x] Phase 28: Book Catalog CRUD (2/2 plans) — completed 2026-03-01
- [x] Phase 29: User Management and Review Moderation (2/2 plans) — completed 2026-03-01
- [x] Phase 30: Integration and Cache Fixes (1/1 plan) — completed 2026-03-01

</details>

### v4.1 Clean House (Phases 31-32)

- [x] **Phase 31: Code Quality** - Extract shared admin components, fix return type, and make top-sellers period-aware (completed 2026-03-01)
- [ ] **Phase 32: Validation and Docs** - Verify email improvements end-to-end and correct SUMMARY frontmatter

## Phase Details

### Phase 31: Code Quality
**Goal**: The admin frontend has no duplicated component implementations, correct TypeScript types, and analytics that respect the user's period selection
**Depends on**: Nothing (first phase of v4.1)
**Requirements**: COMP-01, COMP-02, TYPE-01, ANLY-01
**Success Criteria** (what must be TRUE):
  1. DeltaBadge renders identically on the overview and sales pages, sourced from a single shared component file
  2. Both the catalog table and inventory alert table use one StockBadge component that accepts a threshold parameter, with no duplicate badge implementations remaining
  3. Selecting "Today", "This Week", or "This Month" in the period selector updates the top-sellers table to show data for that period only
  4. The TypeScript compiler resolves `updateBookStock` to return `Promise<BookResponse>` without type errors or casts
**Plans:** 2/2 plans complete
Plans:
- [ ] 31-01-PLAN.md — Extract DeltaBadge + StockBadge shared components, fix updateBookStock return type
- [ ] 31-02-PLAN.md — Add period filtering to top-sellers (backend + frontend)

### Phase 32: Validation and Docs
**Goal**: Email improvements are confirmed working in a real environment and planning document history is accurate
**Depends on**: Phase 31
**Requirements**: DOCS-01, MAIL-01
**Success Criteria** (what must be TRUE):
  1. A test order confirmation email arrives with the BookStore logo displayed inline (not as an attachment) and a book cover image visible
  2. A test restock alert email arrives with the book cover loaded from Open Library when no local image is present
  3. The `requirements_completed` field in plans 26-02 and 27-01 SUMMARY frontmatter lists the correct requirement IDs that those plans delivered
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-8 | v1.0 | 24/24 | Complete | 2026-02-25 |
| 9-12 | v1.1 | 8/8 | Complete | 2026-02-26 |
| 13-15 | v2.0 | 5/5 | Complete | 2026-02-27 |
| 16-18 | v2.1 | 5/5 | Complete | 2026-02-27 |
| 19-25 | v3.0 | 22/22 | Complete | 2026-02-28 |
| 26-30 | v3.1 | 9/9 | Complete | 2026-03-01 |
| 31 | 2/2 | Complete    | 2026-03-01 | - |
| 32 | v4.1 | 0/TBD | Not started | - |
