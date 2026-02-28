# Roadmap: BookStore

## Milestones

- ✅ **v1.0 MVP** — Phases 1-8 (shipped 2026-02-25)
- ✅ **v1.1 Pre-booking, Notifications & Admin** — Phases 9-12 (shipped 2026-02-26)
- ✅ **v2.0 Reviews & Ratings** — Phases 13-15 (shipped 2026-02-27)
- ✅ **v2.1 Admin Dashboard & Analytics** — Phases 16-18 (shipped 2026-02-27)
- ✅ **v3.0 Customer Storefront** — Phases 19-25 (shipped 2026-02-28)
- 🚧 **v3.1 Admin Dashboard** — Phases 26-29 (in progress)

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

### 🚧 v3.1 Admin Dashboard (In Progress)

**Milestone Goal:** A working admin dashboard at `/admin` where an authenticated admin can view KPI metrics, analyze sales, manage the book catalog, manage users, and moderate reviews — all surfacing existing backend endpoints through a clean, protected Next.js interface.

- [ ] **Phase 26: Admin Foundation** - Admin layout, route protection, and dashboard overview with KPI cards and period selector
- [ ] **Phase 27: Sales Analytics and Inventory Alerts** - Revenue chart, top-sellers table, and low-stock inventory alerts with configurable threshold
- [ ] **Phase 28: Book Catalog CRUD** - Paginated catalog table with search/filter, add/edit/delete book forms, and stock update modal
- [ ] **Phase 29: User Management and Review Moderation** - Paginated user table with deactivate/reactivate, and review moderation table with bulk delete

## Phase Details

### Phase 26: Admin Foundation
**Goal**: Admin can access a protected `/admin` section with its own layout and navigate to a dashboard overview showing current KPI metrics with period comparison
**Depends on**: Phase 25 (v3.0 storefront complete — provides the base layout structure to restructure)
**Requirements**: ADMF-01, ADMF-02, ADMF-03, ADMF-04, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Admin visiting `/admin` sees a sidebar layout separate from the customer storefront; customer Header and Footer do not appear
  2. Non-admin user navigating to any `/admin` route is redirected away — both proxy.ts and admin layout Server Component independently enforce the role check
  3. The sidebar highlights the currently active section as the admin navigates between Overview, Sales, Catalog, Users, and Reviews
  4. Admin can view KPI cards for revenue, order count, and AOV, and toggle between Today, This Week, and This Month — each card shows a colored delta badge comparing to the prior period
  5. A low-stock count card on the overview links to the Inventory Alerts section, and a top-5 best-sellers mini-table is visible without leaving the overview
**Plans**: 2 plans (Wave 1: infrastructure, Wave 2: data layer + dashboard)

Plans:
- [ ] 26-01-PLAN.md — Route group restructure, admin layout shell with sidebar, CVE-2025-29927 defense-in-depth
- [ ] 26-02-PLAN.md — Admin fetch layer, TanStack Query admin key namespace, dashboard overview page with KPI cards

### Phase 27: Sales Analytics and Inventory Alerts
**Goal**: Admin can analyze sales performance through a revenue comparison chart and top-sellers rankings, and identify low-stock books via a configurable threshold view
**Depends on**: Phase 26 (admin layout, `src/lib/admin.ts`, TanStack Query admin key namespace, `next/dynamic` SSR-disable pattern established)
**Requirements**: SALE-01, SALE-02, SALE-03, SALE-04, INVT-01, INVT-02, INVT-03
**Success Criteria** (what must be TRUE):
  1. Admin on the Sales Analytics page sees a bar chart comparing current period revenue to the prior period — the chart renders without hydration errors in production
  2. Admin can read summary stats (revenue, order count, AOV, delta percentage) on the analytics page, in addition to the chart
  3. Admin can toggle the top-sellers table between revenue ranking and volume ranking, and select a row limit of 5, 10, or 25 entries
  4. Admin on the Inventory Alerts page sees books sorted by stock ascending with red badges for out-of-stock and amber badges for low stock
  5. Admin can change the stock threshold via an input field and the table updates to reflect the new threshold; clicking "Update Stock" on any row opens the stock update modal
**Plans**: TBD

Plans:
- [ ] 27-01: Install recharts via shadcn chart CLI, `RevenueChart.tsx` wrapped with `next/dynamic { ssr: false }`, Sales Analytics page with summary stats and top-sellers table with revenue/volume toggle and limit selector
- [ ] 27-02: Inventory Alerts page with configurable threshold input, color-coded stock badges, and "Update Stock" row action linking to stock update modal

### Phase 28: Book Catalog CRUD
**Goal**: Admin can manage the entire book catalog from a paginated, searchable table — adding, editing, deleting books and updating stock quantities — with changes reflected immediately in the customer storefront
**Depends on**: Phase 26 (admin layout, admin fetch layer, query key namespace established)
**Requirements**: CATL-01, CATL-02, CATL-03, CATL-04, CATL-05, CATL-06
**Success Criteria** (what must be TRUE):
  1. Admin sees a paginated catalog table showing title, author, price, genre, stock, and action buttons; table supports debounced text search and genre filter
  2. Admin can open an add-book form, fill all required fields with validation feedback, submit, and see the new book appear in the table without a full page reload
  3. Admin can click Edit on any row to open a pre-populated form, change any field, save, and see the updated values reflected in the table
  4. Admin can click Delete on any row, confirm the action in a dialog, and have the book removed — the dialog warns that the action cannot be undone
  5. Admin can open a stock update modal on any book, enter a new quantity, save, and receive a toast notification when restocking from zero (indicating pre-booking emails will be sent); mutations invalidate both the admin catalog cache and the customer-facing books cache
**Plans**: TBD

Plans:
- [ ] 28-01: `DataTable.tsx` (TanStack Table + shadcn Table), `QUERY_KEYS` constants module, `AdminPagination.tsx`, paginated catalog table with debounced search and genre filter
- [ ] 28-02: `BookForm.tsx` (react-hook-form + zod), `ConfirmDialog.tsx` (shadcn AlertDialog), add/edit book flows, delete with confirmation, stock update modal with pre-booking toast, cross-cache invalidation

### Phase 29: User Management and Review Moderation
**Goal**: Admin can manage user accounts and moderate reviews from paginated, filterable tables — deactivating users, reactivating users, deleting single reviews, and bulk-deleting selected reviews
**Depends on**: Phase 28 (`DataTable.tsx`, `ConfirmDialog.tsx`, `QUERY_KEYS`, mutation/invalidation pattern all established)
**Requirements**: USER-01, USER-02, USER-03, USER-04, REVW-01, REVW-02, REVW-03, REVW-04
**Success Criteria** (what must be TRUE):
  1. Admin sees a paginated user table with email, role badge, active status badge, join date, and action buttons; the table can be filtered by role (all/user/admin) and active status (all/active/inactive)
  2. Admin can click Deactivate on a non-admin user row, confirm in a dialog, and have the user locked out immediately; the Deactivate button is visibly disabled for admin-role users
  3. Admin can click Reactivate on an inactive user row, confirm, and restore the user's access
  4. Admin sees a paginated review table with book title, reviewer, rating, text snippet, and date; the table supports filtering by book, user, and rating range, and sorting by date or rating
  5. Admin can delete a single review with confirmation, or select multiple reviews via checkboxes and bulk-delete them with a single confirmation dialog that states the count; selection checkboxes clear after the bulk delete completes
**Plans**: TBD

Plans:
- [ ] 29-01: User Management page — paginated user table with role/status filter badges, deactivate/reactivate actions with confirmation dialogs, admin-role deactivate guard
- [ ] 29-02: Review Moderation page — paginated review table with full filter bar (book, user, rating range, sort), single-review delete, bulk-delete with checkbox selection and confirmation modal, selection state reset on success

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
| 16. Sales Analytics | v2.1 | 2/2 | Complete | 2026-02-27 |
| 17. Inventory Analytics | v2.1 | 1/1 | Complete | 2026-02-27 |
| 18. Review Moderation Dashboard | v2.1 | 2/2 | Complete | 2026-02-27 |
| 19. Monorepo + Frontend Foundation | v3.0 | 3/3 | Complete | 2026-02-27 |
| 20. Auth Integration | v3.0 | 3/3 | Complete | 2026-02-27 |
| 21. Catalog and Search | v3.0 | 4/4 | Complete | 2026-02-27 |
| 22. Cart and Checkout | v3.0 | 5/5 | Complete | 2026-02-27 |
| 23. Orders and Account | v3.0 | 2/2 | Complete | 2026-02-27 |
| 24. Wishlist and Pre-booking | v3.0 | 3/3 | Complete | 2026-02-28 |
| 25. Reviews | v3.0 | 2/2 | Complete | 2026-02-28 |
| 26. Admin Foundation | v3.1 | 0/2 | Not started | - |
| 27. Sales Analytics and Inventory Alerts | v3.1 | 0/2 | Not started | - |
| 28. Book Catalog CRUD | v3.1 | 0/2 | Not started | - |
| 29. User Management and Review Moderation | v3.1 | 0/2 | Not started | - |
