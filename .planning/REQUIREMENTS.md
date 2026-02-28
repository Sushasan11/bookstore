# Requirements: BookStore v3.1 — Admin Dashboard

**Defined:** 2026-02-28
**Core Value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## v3.1 Requirements

Requirements for the admin dashboard frontend. Each maps to roadmap phases.

### Admin Foundation

- [x] **ADMF-01**: Admin can access a dedicated admin section at `/admin` with a sidebar navigation layout separate from the customer storefront
- [x] **ADMF-02**: Admin route is protected by role check in both proxy.ts and admin layout Server Component (defense-in-depth against CVE-2025-29927)
- [x] **ADMF-03**: Non-admin users are redirected away from `/admin` routes
- [x] **ADMF-04**: Admin sidebar highlights the currently active section

### Dashboard Overview

- [x] **DASH-01**: Admin can view KPI cards showing revenue, order count, and AOV for the selected period
- [x] **DASH-02**: Admin can switch period between Today, This Week, and This Month
- [x] **DASH-03**: Each KPI card shows a delta badge (green up / red down / grey dash) comparing to the previous period
- [x] **DASH-04**: Admin can see a low-stock count card that links to the inventory alerts section
- [x] **DASH-05**: Admin can view a top-5 best-selling books mini-table on the overview page

### Sales Analytics

- [x] **SALE-01**: Admin can view a revenue comparison bar chart showing current vs previous period
- [x] **SALE-02**: Admin can view summary stats (revenue, order count, AOV, delta) on the analytics page
- [x] **SALE-03**: Admin can view a top-sellers table ranked by revenue or volume via a toggle
- [x] **SALE-04**: Admin can configure the top-sellers table limit (5, 10, or 25 entries)

### Book Catalog Management

- [ ] **CATL-01**: Admin can view a paginated catalog table showing title, author, price, genre, stock, and actions
- [ ] **CATL-02**: Admin can search books with debounced text input and filter by genre
- [ ] **CATL-03**: Admin can add a new book via a form with full field validation (title, author, price, ISBN, genre, description, cover URL, publish date)
- [ ] **CATL-04**: Admin can edit an existing book via a pre-populated form
- [ ] **CATL-05**: Admin can delete a book with a confirmation dialog
- [ ] **CATL-06**: Admin can update a book's stock quantity via a modal, with a toast notification when restocking from zero triggers pre-booking emails

### User Management

- [ ] **USER-01**: Admin can view a paginated user table showing email, role badge, active status badge, join date, and actions
- [ ] **USER-02**: Admin can filter users by role (all/user/admin) and active status (all/active/inactive)
- [ ] **USER-03**: Admin can deactivate a user with a confirmation dialog (disabled for admin accounts)
- [ ] **USER-04**: Admin can reactivate an inactive user

### Review Moderation

- [ ] **REVW-01**: Admin can view a paginated review table showing book title, reviewer, rating, text snippet, and date
- [ ] **REVW-02**: Admin can filter reviews by book, user, rating range, and sort by date or rating
- [ ] **REVW-03**: Admin can delete a single review with confirmation
- [ ] **REVW-04**: Admin can select multiple reviews via checkboxes and bulk-delete them with confirmation

### Inventory Alerts

- [ ] **INVT-01**: Admin can view a low-stock books table sorted by stock ascending with color-coded status badges (red for out-of-stock, amber for low)
- [ ] **INVT-02**: Admin can configure the stock threshold via an input field
- [ ] **INVT-03**: Admin can click "Update Stock" on any row to open the stock update modal

## Future Requirements (v3.2+)

### Sales Analytics Enhancements

- **SALE-05**: Admin can view a day-by-day revenue timeseries chart (requires new backend endpoint)
- **REVW-05**: Admin can expand/collapse review text inline in the moderation table
- **INVT-04**: Admin can edit stock inline from the inventory alerts table without navigating to catalog

### Admin Tooling (v4+)

- **ADMIN-01**: Admin can export analytics data to CSV
- **ADMIN-02**: Admin can bulk-import stock quantities via CSV upload
- **ADMIN-03**: Admin can promote/demote user roles from the dashboard

## Out of Scope

| Feature | Reason |
|---------|--------|
| Day-by-day revenue timeseries chart | Backend provides period totals only, not daily data; requires new endpoint |
| Real-time dashboard updates (WebSocket/polling) | WebSocket infrastructure deferred per PROJECT.md; manual refresh sufficient |
| Admin user creation / role promotion | No backend endpoint for role changes; admin accounts created at DB level |
| Bulk stock import via CSV | Requires new backend endpoint; per-book stock edit sufficient for current scale |
| Review pre-moderation queue | PROJECT.md explicitly rejects pre-moderation; reactive admin delete is correct model |
| Sales forecasting / trend prediction | Requires ML infrastructure; out of scope for this project |
| Admin-to-user messaging | No messaging backend; admins use email addresses from user table |
| CSV/PDF export | Data volume doesn't justify complexity; browser print/copy sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ADMF-01 | Phase 26 | Complete |
| ADMF-02 | Phase 26 | Complete |
| ADMF-03 | Phase 26 | Complete |
| ADMF-04 | Phase 26 | Complete |
| DASH-01 | Phase 26 | Complete |
| DASH-02 | Phase 26 | Complete |
| DASH-03 | Phase 26 | Complete |
| DASH-04 | Phase 26 | Complete |
| DASH-05 | Phase 26 | Complete |
| SALE-01 | Phase 27 | Complete |
| SALE-02 | Phase 27 | Complete |
| SALE-03 | Phase 27 | Complete |
| SALE-04 | Phase 27 | Complete |
| INVT-01 | Phase 27 | Pending |
| INVT-02 | Phase 27 | Pending |
| INVT-03 | Phase 27 | Pending |
| CATL-01 | Phase 28 | Pending |
| CATL-02 | Phase 28 | Pending |
| CATL-03 | Phase 28 | Pending |
| CATL-04 | Phase 28 | Pending |
| CATL-05 | Phase 28 | Pending |
| CATL-06 | Phase 28 | Pending |
| USER-01 | Phase 29 | Pending |
| USER-02 | Phase 29 | Pending |
| USER-03 | Phase 29 | Pending |
| USER-04 | Phase 29 | Pending |
| REVW-01 | Phase 29 | Pending |
| REVW-02 | Phase 29 | Pending |
| REVW-03 | Phase 29 | Pending |
| REVW-04 | Phase 29 | Pending |

**Coverage:**
- v3.1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after roadmap creation — all 28 requirements mapped to phases 26-29*
