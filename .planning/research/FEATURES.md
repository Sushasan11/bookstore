# Feature Research

**Domain:** Bookstore Admin Dashboard — v3.1 Next.js Admin UI
**Researched:** 2026-02-28
**Confidence:** HIGH for table stakes (well-established patterns from Shopify, WooCommerce, e-commerce admin UX research); MEDIUM for specific component recommendations (shadcn/ui chart integration verified via official shadcn docs and community); LOW for any claims about AI-driven features (deferred, not applicable here)

> **Scope note:** This file covers the v3.1 Admin Dashboard milestone ONLY.
> The v3.0 customer storefront features are documented in the previous version of this file.
> The FastAPI backend already provides all admin endpoints required:
> - `GET /admin/analytics/sales/summary` (revenue, order_count, aov, delta_percentage by period)
> - `GET /admin/analytics/sales/top-books` (ranked by revenue or volume)
> - `GET /admin/analytics/inventory/low-stock` (books at/below configurable threshold)
> - `GET /admin/users`, `PATCH /admin/users/{id}/deactivate`, `PATCH /admin/users/{id}/reactivate`
> - `GET /admin/reviews`, `DELETE /admin/reviews/bulk`
> - `POST/PUT/DELETE /books/{id}`, `PATCH /books/{id}/stock` (book catalog CRUD)
>
> This file describes what the FRONTEND must expose, how each section should behave,
> and what complexity that implies for implementation.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any admin managing an e-commerce system expects as baseline. Missing one makes the admin panel feel incomplete or unusable.

#### 1. Dashboard Overview

| Feature | Why Expected | Complexity | Backend Dependency |
|---------|--------------|------------|--------------------|
| KPI summary cards (revenue, orders, AOV) | Admins open the dashboard to get immediate operational awareness — top-line numbers at a glance. Every e-commerce admin panel (Shopify, WooCommerce, Magento) leads with KPI cards. | LOW | `GET /admin/analytics/sales/summary?period=today` |
| Period selector (Today / This Week / This Month) | Revenue data is meaningless without a time context. Period toggle is universally present — three tabs or button group is standard. | LOW | Same endpoint, `period` query param |
| Delta indicator (% change vs previous period) | Admins need trend direction, not just absolute numbers. A green/red delta badge next to each KPI is standard practice. | LOW | `delta_percentage` field already in response; backend handles null when prior period is zero |
| Low-stock count badge / alert card | Inventory health is a top-priority operational metric. Admins need to know immediately if books are running out of stock. A count card linking to the inventory section is expected on every dashboard overview. | LOW | `GET /admin/analytics/inventory/low-stock` (count from `total_low_stock`) |
| Navigation sidebar / top nav linking to each admin section | Admin panels require clear section navigation. Users must be able to jump between Overview, Catalog, Users, Reviews, and Inventory without hunting. | LOW | Frontend-only; no backend call |

#### 2. Sales Analytics Visualizations

| Feature | Why Expected | Complexity | Backend Dependency |
|---------|--------------|------------|--------------------|
| Revenue trend chart (line or bar) | Admins expect to see revenue over time plotted visually. A number card alone is insufficient — the chart answers "is it growing or declining?" | MEDIUM | `GET /admin/analytics/sales/summary` for current/prior period values; note: backend returns period totals, NOT day-by-day timeseries — chart will compare two bars (current vs prior), not a continuous line |
| Top-selling books table (ranked list) | Every e-commerce admin panel shows a "top products" section. Admins use it to understand demand patterns and make restocking decisions. | LOW | `GET /admin/analytics/sales/top-books?sort_by=revenue&limit=10` |
| Switch between revenue and volume rankings | Two dimensions of "top" are meaningful: which books generate most revenue vs which have highest unit velocity. A toggle between the two is expected. | LOW | Same endpoint, `sort_by=revenue` or `sort_by=volume` |
| Period-over-period comparison display | Showing only current period without prior context makes trends invisible. Side-by-side or delta display is expected. | LOW | `delta_percentage` from summary endpoint |

#### 3. Book Catalog Management

| Feature | Why Expected | Complexity | Backend Dependency |
|---------|--------------|------------|--------------------|
| Paginated catalog table (list all books with title, author, price, stock, genre) | Admins need to see all books in one place to find and manage them. A searchable, sortable table is standard admin pattern. | MEDIUM | `GET /books` (all existing query params available) |
| Add new book form (modal or page) | Creating new catalog entries is a core admin task. | MEDIUM | `POST /books` |
| Edit book form (inline or modal) | Updating price, description, cover URL, and other fields is routine. | MEDIUM | `PUT /books/{id}` |
| Delete book with confirmation dialog | Prevents accidental permanent deletions. Confirmation pattern is universal. | LOW | `DELETE /books/{id}` (hard delete — no soft delete on books) |
| Stock quantity update (set absolute value) | Stock management is critical for operations — admins adjust stock after receiving physical inventory. | LOW | `PATCH /books/{id}/stock` (triggers pre-booking notification emails if restocking from 0) |
| Search/filter within catalog table | With a large catalog, admins need to find specific books quickly. Full-text search and genre filter match backend capabilities. | LOW | Same `GET /books` endpoint with `q`, `genre_id`, `author` params |

#### 4. User Management

| Feature | Why Expected | Complexity | Backend Dependency |
|---------|--------------|------------|--------------------|
| Paginated user list (email, role, active status, joined date) | Admins need visibility into who uses the platform. Paginated table with status badges is universal. | LOW | `GET /admin/users?page=N&per_page=20` |
| Filter by role (user/admin) and active status | Finding specific user segments quickly is a basic operational need. | LOW | `role` and `is_active` query params on existing endpoint |
| Deactivate user with confirmation | Account suspension is a standard moderation action. Confirmation prevents accidents. Backend is idempotent. | LOW | `PATCH /admin/users/{id}/deactivate` |
| Reactivate user | Reversing a suspension is equally expected. | LOW | `PATCH /admin/users/{id}/reactivate` |
| Status badge (Active / Inactive) | Color-coded status badges are the standard way to surface account state at a glance. | LOW | `is_active` field in user response |

#### 5. Review Moderation

| Feature | Why Expected | Complexity | Backend Dependency |
|---------|--------------|------------|--------------------|
| Paginated reviews table (book title, reviewer, rating, date, text snippet) | Admins moderating reviews need to scan many at once. A table layout with key metadata is expected. | MEDIUM | `GET /admin/reviews` |
| Filter by book, user, and rating range | Finding problematic reviews (low-rated, specific book) requires filtering. Backend already supports all these params. | LOW | `book_id`, `user_id`, `rating_min`, `rating_max` params |
| Sort by date or rating | Admins often want to see newest reviews (date desc) or worst reviews (rating asc) first. | LOW | `sort_by` and `sort_dir` params |
| Single-review delete | Admins need to remove individual policy-violating reviews. | LOW | Use bulk delete endpoint with a single-item array (backend supports 1–50 IDs) |
| Bulk delete with row selection checkboxes | When a spam campaign or bot posts multiple bad reviews, deleting them one by one is impractical. Checkbox selection + bulk action button is the expected pattern. | MEDIUM | `DELETE /admin/reviews/bulk` (up to 50 IDs per request) |

#### 6. Inventory Alerts

| Feature | Why Expected | Complexity | Backend Dependency |
|---------|--------------|------------|--------------------|
| Low-stock books list (book, stock count, threshold) | Admins need a clear list of which books need restocking. Sorted by stock ascending (lowest first) is the natural order. | LOW | `GET /admin/analytics/inventory/low-stock` |
| Configurable threshold input | Different admins have different restock triggers. The backend supports any threshold >= 0. The UI should let admins set it without editing a URL. | LOW | `threshold` query param |
| "Out of stock" items prominently highlighted | Zero-stock books are the most urgent. They should be visually distinct (red badge vs yellow for low stock). | LOW | `current_stock == 0` condition in frontend |
| Quick link to edit stock from inventory list | When an admin sees a low-stock item, the next action is updating stock. A direct "Update Stock" button per row removes friction. | LOW | Links to catalog stock edit for that book_id |

---

### Differentiators (Competitive Advantage)

Features beyond the bare minimum. These improve admin efficiency but are not universally expected for a v1 admin panel.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Visual revenue comparison chart (current vs prior bar chart) | Turns the delta percentage into an intuitive visual. Admins understand "revenue is up 23%" much better when they see two bars side by side. shadcn/ui ships 53 pre-built chart components built on Recharts — a `BarChart` with two data series is <50 lines. | MEDIUM | shadcn Charts (`BarChart` with `ChartContainer`, `ChartTooltip`) built on Recharts. Two data points per period: current + prior. Not a time-series chart (backend doesn't expose day-by-day). |
| Top-sellers mini-table on overview page | Gives admins demand intelligence without navigating to the analytics section. A "top 5 books this week" card on the overview is a strong UX addition. | LOW | Reuse `GET /admin/analytics/sales/top-books?limit=5` on overview page. |
| Inline stock editing from inventory alert list | Instead of navigating to catalog to update stock, allow a number input directly in the inventory alert row. One click to update is significantly faster than navigating away. | MEDIUM | TanStack Query mutation against `PATCH /books/{id}/stock`. Optimistic update with rollback on error. |
| Sticky admin sidebar with active route highlighting | Professional admin dashboards have a fixed sidebar that shows which section is active. Improves navigation orientation and feels polished. | LOW | Next.js `usePathname()` to determine active route. shadcn's `Sidebar` component or a custom nav list. |
| Responsive table with horizontal scroll on mobile | Admin panels are primarily desktop tools, but if the admin checks stats on mobile, tables shouldn't break. | LOW | Wrap data tables in a `div` with `overflow-x-auto`. shadcn DataTable handles column visibility. |
| Review text preview with expand/collapse | Review table rows show a truncated text snippet; clicking expands the full text inline. Avoids a separate detail view for quick moderation scanning. | LOW | Controlled state per row or shadcn `Collapsible`. |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful for an admin dashboard but create scope creep, UX problems, or premature complexity given the existing backend.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Day-by-day revenue time-series chart | Admins want to see revenue trends over multiple days. | The backend `GET /admin/analytics/sales/summary` returns period totals (today, week, month), NOT day-by-day data. Building a time-series chart requires a new backend endpoint. Adding a backend endpoint is out of scope for this frontend-only milestone. | Use a period-comparison bar chart (current vs prior period) with the existing two-point data. This is honest about what the backend provides and visually communicates trend direction. Add time-series as a v3.2 backend + frontend feature if needed. |
| Real-time dashboard updates (WebSocket/polling) | Admins want "live" data. | PROJECT.md explicitly defers WebSocket infrastructure. Polling adds API load without significant benefit for a low-traffic bookstore where analytics data changes infrequently. | Manual refresh button + short-TTL TanStack Query cache (e.g., 60s staleTime). Data is fresh enough without continuous polling. |
| Admin user creation / role promotion UI | Admins want to promote users to admin role or create admin accounts from the dashboard. | The backend has no endpoint for updating user roles or creating admin accounts from the admin UI. This would require new backend work. The current backend only supports deactivate/reactivate. | Out of scope. Admin accounts are created at the database level or via a backend script. Document this constraint in the UI (tooltip or help text). |
| Bulk stock import (CSV upload) | Admins managing large catalogs want to upload stock changes via CSV. | Requires a new backend endpoint for CSV parsing and batch stock updates. Frontend-only milestone — no new backend endpoints. | Provide the per-book stock edit UI. CSV import can be a v4.0 feature when catalog scale justifies it. |
| Review content flagging / pre-moderation queue | Flagging reviews for review before they go live. | PROJECT.md explicitly rejects pre-moderation: "pre-moderation suppresses authentic reviews." The correct model is reactive admin delete. A flagging queue adds complexity without improving moderation quality. | Keep reactive moderation: admins delete policy-violating reviews after they appear. The existing bulk delete handles cleanup efficiently. |
| Sales forecasting / trend prediction | Admins want "AI insights" on future sales. | Requires ML infrastructure, historical data depth, and model serving — all out of scope for this project. Would be low-accuracy with the current data volume. | Display historical data clearly (top sellers, delta percentage). Let admins draw their own conclusions. |
| Admin-to-user messaging | Admins want to contact users from the dashboard. | Requires a messaging backend, email templating beyond the existing transactional templates, and GDPR considerations. No backend support exists. | Admins can use the user's email address (displayed in the user table) to contact them via external email. |
| Export to CSV / PDF | Admins want to export analytics data. | Adds significant frontend complexity (CSV serialization, print stylesheets or PDF generation library). The data volume at current scale doesn't justify this. | Admins can copy data from the table or use the browser's print function for a quick reference. Defer to v4.0 if demand is confirmed. |
| Dark mode for admin panel only | Admin panels often skip dark mode to reduce scope. | The customer storefront already has dark mode (PROJECT.md). Extending dark mode to the admin panel requires Tailwind dark class coverage on all new admin components — significant but not impossible overhead. However, it adds no business value and is purely cosmetic for an internal tool. | Use the existing Tailwind dark mode system (it applies globally). If the storefront dark mode already works, admin pages will inherit the dark mode behavior with minimal extra effort since shadcn/ui components support dark mode by default. LOW risk — just don't need to actively design for it. |

---

## Feature Dependencies

```
[Admin auth guard (require_admin middleware)]
    └──required by──> [All admin sections] (dashboard, analytics, catalog mgmt, users, reviews, inventory)

[Dashboard Overview page]
    └──depends on──> [Sales summary API] (GET /admin/analytics/sales/summary)
    └──depends on──> [Low-stock count] (GET /admin/analytics/inventory/low-stock, total_low_stock only)
    └──optionally shows──> [Top sellers mini-table] (GET /admin/analytics/sales/top-books?limit=5)

[Sales Analytics page]
    └──depends on──> [Sales summary API] (current + prior period values for comparison chart)
    └──depends on──> [Top books API] (GET /admin/analytics/sales/top-books)
    └──period selector──> [Controls both summary and top-books calls]

[Book Catalog Management page]
    └──depends on──> [GET /books] (list with pagination, search, filter)
    └──add form──> [POST /books]
    └──edit form──> [PUT /books/{id}]
    └──delete action──> [DELETE /books/{id}]
    └──stock update──> [PATCH /books/{id}/stock] (side effect: triggers pre-booking emails from backend)

[Inventory Alerts page]
    └──depends on──> [GET /admin/analytics/inventory/low-stock]
    └──stock update link──> [PATCH /books/{id}/stock] (shared with catalog management)

[User Management page]
    └──depends on──> [GET /admin/users]
    └──deactivate action──> [PATCH /admin/users/{id}/deactivate]
    └──reactivate action──> [PATCH /admin/users/{id}/reactivate]

[Review Moderation page]
    └──depends on──> [GET /admin/reviews]
    └──delete action──> [DELETE /admin/reviews/bulk] (used for both single and bulk deletes)

[shadcn/ui Charts (BarChart)]
    └──built on──> [Recharts] (already a transitive dependency via shadcn/ui)
    └──used by──> [Sales Analytics visualization]

[TanStack Query mutations]
    └──used by──> [Catalog CRUD actions, stock update, deactivate/reactivate, review bulk delete]
    └──pattern──> [invalidate affected query on success, rollback on error]
```

### Dependency Notes

- **Admin guard is the foundation:** All six admin sections require the `require_admin` check. In Next.js, this is handled by the existing `proxy.ts` route protection pattern (checking session role). No new auth infrastructure needed — extend existing middleware.
- **Stock update triggers side effects:** `PATCH /books/{id}/stock` may trigger restock notification emails to pre-bookers if stock transitions from 0 to > 0. The admin UI should communicate this: "Updating stock from 0 will notify pre-bookers." This is informational only — the backend handles the emails.
- **Bulk delete endpoint handles singles:** The `DELETE /admin/reviews/bulk` endpoint accepts 1–50 IDs. The frontend can use it for both "delete this one review" (single-element array) and "delete selected reviews" (multi-element array). No need for a separate single-delete endpoint.
- **Top-books endpoint is stateless:** No period context — it ranks all-time or by confirmed orders. The `sort_by` toggle changes the ranking dimension, not the time window. The UI should not imply time-period filtering on top-books (no period selector on top-books table).
- **Revenue chart is a two-point comparison, not a timeseries:** The backend provides current period total + prior period implied from delta. The chart shows two bars: "This [period]" and "Last [period]." Do not imply day-by-day granularity.
- **Book catalog list reuses the public endpoint:** `GET /books` is a public endpoint (no auth required for reading). The admin catalog table reuses this endpoint and adds the admin CRUD actions. No separate admin-only book list endpoint exists.

---

## MVP Definition

### v3.1 Must Ship

All six admin sections constitute the v3.1 milestone. All backend endpoints are already built. Frontend scope:

**Foundation:**
- [ ] Admin layout: sidebar navigation linking to Overview, Analytics, Catalog, Users, Reviews, Inventory
- [ ] Admin route guard: extend existing proxy.ts or middleware to verify admin role for `/admin/*` routes
- [ ] Shared admin data-fetching patterns: TanStack Query with admin JWT headers

**Dashboard Overview:**
- [ ] KPI cards: Revenue, Order Count, AOV — each with current value + delta badge
- [ ] Period selector: Today / This Week / This Month button group
- [ ] Low-stock alert card: count of books below threshold with link to Inventory section
- [ ] Top-5 sellers mini-table (optional but HIGH value for overview completeness)

**Sales Analytics:**
- [ ] Period-comparison bar chart: current vs prior period revenue (shadcn/ui BarChart)
- [ ] Summary stats: revenue, order count, AOV, delta — same data as overview but dedicated page
- [ ] Top-sellers table with revenue/volume toggle (sort_by param)
- [ ] Limit selector (top 5 / top 10 / top 20)

**Book Catalog Management:**
- [ ] Paginated catalog table: title, author, price, genre, stock quantity, actions
- [ ] Search input (debounced) and genre filter dropdown
- [ ] Add book: form in modal or dedicated page (title, author, price, ISBN, genre, description, cover URL, publish date)
- [ ] Edit book: same form pre-populated, accessible via row action
- [ ] Delete book: confirmation dialog before hard delete
- [ ] Update stock: number input modal accessible from row action

**User Management:**
- [ ] Paginated user table: email, role badge, active status badge, joined date, actions
- [ ] Filter by role (All / User / Admin) and active status (All / Active / Inactive)
- [ ] Deactivate: confirmation dialog + PATCH action; button disabled for admin accounts
- [ ] Reactivate: PATCH action, available for inactive users

**Review Moderation:**
- [ ] Paginated review table: book title, reviewer display name, star rating, text snippet, date
- [ ] Filter controls: book ID input, user ID input, rating range (min/max), sort by (date/rating), sort direction
- [ ] Row-level delete: confirmation before DELETE /admin/reviews/bulk with single ID
- [ ] Multi-row selection: checkboxes + "Delete Selected" bulk action button
- [ ] Bulk delete confirmation: "Delete N reviews?" before submission

**Inventory Alerts:**
- [ ] Threshold input (number field, default 10) with "Apply" button
- [ ] Low-stock books table: title, author, current stock, threshold — sorted by stock ascending
- [ ] Visual distinction: `stock == 0` rows highlighted in red/destructive; `stock > 0 but <= threshold` in amber/warning
- [ ] Quick "Update Stock" link per row (opens stock update modal from catalog management)

### Add After v3.1 Validation (v3.2)

- [ ] Day-by-day revenue timeseries chart — requires new backend endpoint (`GET /admin/analytics/sales/timeseries`)
- [ ] Review text expand/collapse — low priority quality-of-life improvement
- [ ] Inline stock editing from inventory list — reduces navigation friction

### Future Consideration (v4+)

- [ ] Sales forecasting / trend prediction — requires ML infrastructure
- [ ] CSV export of analytics data — defer until admin data volume justifies it
- [ ] Bulk stock import via CSV — requires new backend endpoint
- [ ] Admin user role management UI — requires new backend endpoint

---

## Feature Prioritization Matrix

| Feature | Admin Value | Implementation Cost | Priority |
|---------|-------------|---------------------|----------|
| KPI cards on overview | HIGH | LOW | P1 |
| Period selector | HIGH | LOW | P1 |
| Admin route guard | HIGH | LOW | P1 |
| Admin sidebar navigation | HIGH | LOW | P1 |
| Low-stock count on overview | HIGH | LOW | P1 |
| Revenue comparison chart | HIGH | MEDIUM | P1 |
| Top-sellers table | HIGH | LOW | P1 |
| Catalog table (list books) | HIGH | MEDIUM | P1 |
| Add / edit book form | HIGH | MEDIUM | P1 |
| Delete book (with confirmation) | HIGH | LOW | P1 |
| Stock update modal | HIGH | LOW | P1 |
| User table with status badges | HIGH | LOW | P1 |
| Deactivate / reactivate user | HIGH | LOW | P1 |
| Review moderation table | HIGH | MEDIUM | P1 |
| Bulk delete reviews | HIGH | MEDIUM | P1 |
| Inventory alert table | HIGH | LOW | P1 |
| Threshold input on inventory | MEDIUM | LOW | P1 |
| Revenue/volume toggle on top-sellers | MEDIUM | LOW | P2 |
| Top-5 mini-table on overview | MEDIUM | LOW | P2 |
| Inline stock edit from inventory | MEDIUM | MEDIUM | P2 |
| Review text expand/collapse | LOW | LOW | P3 |
| CSV export | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v3.1 launch
- P2: Should have — ship if time allows in same milestone
- P3: Nice to have — defer to v3.2

---

## UX Behavior Specifications

Precise expected behavior for each admin section, based on established e-commerce admin patterns (Shopify, WooCommerce) and backend constraints.

### Dashboard Overview
- Default period on load: "today"
- Delta badge: green arrow up for positive delta, red arrow down for negative, grey dash for null delta (no prior period data)
- KPI cards: Revenue (formatted as currency, 2dp), Order Count (integer), AOV (formatted as currency, 2dp)
- Low-stock card: shows `total_low_stock` count, links to `/admin/inventory` on click
- Page does not auto-refresh; provide a manual "Refresh" button or rely on TanStack Query's `staleTime`

### Sales Analytics
- Period selector affects both KPI display and top-sellers ranking context display (even if top-sellers API is not period-scoped, show the selected period as context)
- Revenue chart: two bars labeled "Current [period]" and "Previous [period]"
- Chart tooltip on hover: exact revenue value
- Top-sellers table: columns = Rank, Title, Author, Units Sold, Total Revenue; sortable by Revenue or Volume via toggle; configurable limit (5/10/25)
- Empty state: "No orders found for this period" when revenue = 0

### Book Catalog Management
- Table columns: Cover (thumbnail), Title, Author, Genre, Price, Stock (with low-stock badge), Actions (Edit, Stock, Delete)
- Search: 300ms debounced input, clears with × button
- Add/Edit form fields: Title (required), Author (required), Price (required, number, min 0), ISBN (optional, validated), Genre (dropdown from GET /genres), Description (textarea), Cover Image URL (optional), Publish Date (optional date picker)
- Delete confirmation: "Are you sure you want to delete '[title]'? This action cannot be undone."
- Stock update modal: single number input (integer, min 0), label "Set stock quantity", confirm button. Show current stock in label: "Current stock: N"
- After stock update from 0 → N: show info toast "Stock updated. Pre-booking notification emails will be sent."

### User Management
- Table columns: Email, Role (badge: "Admin" / "User"), Status (badge: "Active" / "Inactive"), Joined (date), Actions
- Deactivate button: disabled and tooltip "Cannot deactivate admin accounts" when target is an admin (`role == 'admin'`)
- Deactivate confirmation: "Deactivate [email]? Their sessions will be revoked immediately."
- Reactivate: no confirmation needed (reversible, low-risk action) — immediate PATCH on click
- Filter UI: two dropdowns (Role filter, Status filter) above the table, applied server-side via API params

### Review Moderation
- Table columns: Checkbox, Book Title, Reviewer, Rating (star display, compact), Text (truncated to 80 chars), Date, Actions (Delete)
- Row selection: individual checkboxes + "Select all on this page" header checkbox
- Bulk delete button: visible when ≥1 row selected; label "Delete (N) Reviews"
- Bulk delete confirmation modal: "You are about to permanently delete N reviews. This cannot be undone."
- Backend bulk delete is best-effort (silently skips already-deleted IDs) — after delete, show "Deleted N reviews" success toast using actual `deleted_count` from response
- Filter bar: collapsible or always-visible row above table with Book ID, User ID, Min/Max Rating inputs, Sort By dropdown, Sort Direction toggle
- Empty state: "No reviews match the current filters"

### Inventory Alerts
- Threshold input: numeric input above the table, default value 10, "Apply" button triggers refetch with new threshold
- Table columns: Title, Author, Current Stock, Status (badge), Actions (Update Stock)
- Status badge: "Out of Stock" (red/destructive) when `current_stock == 0`; "Low Stock" (amber/warning) when `0 < current_stock <= threshold`
- Table sorted ascending by `current_stock` (backend already returns this order)
- "Update Stock" action per row: opens same stock update modal as catalog management
- Total count display: "N books at or below threshold of T units"
- Empty state: "All books are well-stocked (no books at or below [threshold] units)"

---

## Existing Backend Endpoints by Admin Section

All endpoints are already implemented and tested. Frontend consumes these directly.

| Admin Section | Action | Backend Endpoint | Notes |
|--------------|--------|-----------------|-------|
| Overview | Load KPIs | `GET /admin/analytics/sales/summary?period={today\|week\|month}` | Returns revenue, order_count, aov, delta_percentage |
| Overview | Load low-stock count | `GET /admin/analytics/inventory/low-stock?threshold=10` | Use total_low_stock field only |
| Overview | Top-5 sellers | `GET /admin/analytics/sales/top-books?sort_by=revenue&limit=5` | Optional but recommended |
| Analytics | Revenue comparison | `GET /admin/analytics/sales/summary?period={period}` | Chart uses revenue + delta to compute prior value |
| Analytics | Top sellers table | `GET /admin/analytics/sales/top-books?sort_by={revenue\|volume}&limit={N}` | All-time ranking, not period-scoped |
| Catalog | List books | `GET /books?page=N&per_page=20&q=&genre_id=` | Public endpoint, no admin auth needed for reads |
| Catalog | Add book | `POST /books` | Admin only; body: BookCreate schema |
| Catalog | Edit book | `PUT /books/{id}` | Admin only; body: BookUpdate (all fields optional) |
| Catalog | Delete book | `DELETE /books/{id}` | Admin only; hard delete; 204 on success |
| Catalog | Update stock | `PATCH /books/{id}/stock` | Admin only; body: {quantity: int}; triggers pre-booking emails if from 0 |
| Catalog | List genres | `GET /genres` | Public; used to populate genre dropdown in add/edit form |
| Users | List users | `GET /admin/users?page=N&per_page=20&role=&is_active=` | Sorted by created_at DESC |
| Users | Deactivate | `PATCH /admin/users/{id}/deactivate` | 403 if target is admin; idempotent |
| Users | Reactivate | `PATCH /admin/users/{id}/reactivate` | 404 if not found; idempotent |
| Reviews | List reviews | `GET /admin/reviews?page=N&per_page=20&book_id=&user_id=&rating_min=&rating_max=&sort_by=date&sort_dir=desc` | All non-deleted reviews |
| Reviews | Delete (single or bulk) | `DELETE /admin/reviews/bulk` | Body: {review_ids: [1, 2, ...]}; max 50; best-effort |
| Inventory | Low-stock list | `GET /admin/analytics/inventory/low-stock?threshold=N` | Returns items sorted by current_stock ASC |

---

## Sources

- [shadcn/ui Charts — Official Documentation](https://ui.shadcn.com/charts) — confirms charts are built on Recharts, 53 pre-built components, copy-paste pattern (HIGH confidence — official shadcn documentation)
- [shadcn/ui Data Table — Official Docs](https://ui.shadcn.com/docs/components/data-table) — TanStack Table integration, row selection, column visibility, server-side pagination (HIGH confidence — official documentation)
- [10 Best E-commerce Dashboard Examples — Rows.com](https://rows.com/blog/post/ecommerce-dashboard) — KPI card patterns, period selectors, chart types for e-commerce (MEDIUM confidence — industry blog)
- [Must-Have Ecommerce Dashboard Examples — Databox](https://databox.com/dashboard-examples/ecommerce) — operational metrics and visualization patterns (MEDIUM confidence — analytics platform vendor, slight promotional bias)
- [Admin Dashboard UI/UX Best Practices 2025 — Medium/Carlos Smith](https://medium.com/@CarlosSmith24/admin-dashboard-ui-ux-best-practices-for-2025-8bdc6090c57d) — badge patterns, table UX, action-oriented design principles (MEDIUM confidence — community publication)
- [Status Indicator Pattern — IBM Carbon Design System](https://carbondesignsystem.com/patterns/status-indicator-pattern/) — authoritative guidance on status badges in tables (HIGH confidence — enterprise design system)
- [The Right Way to Design Table Status Badges — UX Movement](https://uxmovement.substack.com/p/why-youre-designing-table-status) — badge differentiation and priority signaling (MEDIUM confidence — UX publication)
- [Building a Next.js Dashboard with Dynamic Charts — Cube Blog](https://cube.dev/blog/building-nextjs-dashboard-with-dynamic-charts-and-ssr) — Next.js + Recharts patterns, SSR considerations for analytics (MEDIUM confidence — developer blog)
- [How to Build an Admin Dashboard with shadcn/ui — freeCodeCamp](https://www.freecodecamp.org/news/build-an-admin-dashboard-with-shadcnui-and-tanstack-start/) — concrete implementation patterns (MEDIUM confidence — community resource)
- [sadmann7/tablecn — GitHub](https://github.com/sadmann7/tablecn) — reference implementation of shadcn DataTable with server-side sort/filter/pagination (HIGH confidence — widely-referenced community reference, 3k+ stars)
- [Shopify Admin UI patterns](https://shopify.dev/docs/apps/design-guidelines/overview) — authoritative reference for e-commerce admin UX conventions (HIGH confidence — official Shopify developer documentation)

---

*Feature research for: BookStore v3.1 — Admin Dashboard Frontend*
*Researched: 2026-02-28*
