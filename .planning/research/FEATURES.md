# Feature Research

**Domain:** Bookstore E-Commerce — v2.1 Milestone (Admin Dashboard & Analytics)
**Researched:** 2026-02-27
**Confidence:** HIGH for table stakes analytics patterns (well-established across Shopify, WooCommerce, commercetools); MEDIUM for exact complexity estimates on SQL aggregates (depend on query plan and index coverage); LOW for caching necessity (depends on actual data volume)

> **Scope note:** v1.0, v1.1, and v2.0 built auth, catalog, FTS, cart, checkout, orders,
> wishlist, pre-booking, email notifications, admin user management, reviews with
> verified-purchase gate, and live rating aggregates.
> This file focuses exclusively on the new features for v2.1:
> Sales analytics, inventory analytics, and review moderation dashboard.
> All rely on querying existing tables — no new domain models required.

---

## Feature Landscape

### Table Stakes (Admins Expect These)

Features admins assume exist in any operational e-commerce backend. Missing these makes the admin experience feel blind.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Revenue summary (total today / week / month) | Every e-commerce admin dashboard leads with revenue — it is the primary operational signal. Shopify, WooCommerce, and commercetools all surface it as the first metric. | LOW | `SUM(order_items.quantity * order_items.unit_price)` on `orders` filtered by `created_at` range and `status = 'confirmed'`. Three parallel queries or one query with CASE expressions. |
| Period-over-period comparison | Raw revenue numbers are meaningless without context. "+12% vs last week" is the standard pattern across every analytics tool from Google Analytics to Shopify admin. Admins expect this automatically alongside the revenue figure. | MEDIUM | Run same SUM query for both current period and prior period. Compute delta as `(current - prior) / prior * 100`. Handle division-by-zero when prior period = 0. No external library needed — pure SQL arithmetic. |
| Top-selling books by revenue | Standard inventory intelligence. Amazon Seller Central, Shopify, and WooCommerce all provide it. Admins use it to decide restocking priorities and promotions. | LOW | `SELECT book_id, SUM(quantity * unit_price) AS revenue FROM order_items JOIN orders ... GROUP BY book_id ORDER BY revenue DESC LIMIT N`. `book_id` may be NULL (book deleted); filter or handle gracefully. |
| Top-selling books by volume (units sold) | Revenue ranking can be skewed by a single expensive book. Unit-volume ranking shows true demand breadth. Both views are expected simultaneously. | LOW | Same query but `SUM(quantity) AS units_sold`. Share the same join structure as the revenue query — can be combined or run separately. |
| Average order value (AOV) | AOV is a canonical e-commerce KPI alongside revenue and order count. Standard formula: total revenue / confirmed order count. | LOW | `SELECT COUNT(*) AS order_count, SUM(...) AS total_revenue, SUM(...)/COUNT(*) AS aov FROM orders WHERE status = 'confirmed'`. Round to 2 decimal places. |
| Low-stock alerts (books below threshold) | Admins need to know before stockouts happen. Every inventory system has a low-stock query. Without it, stockouts are discovered by customers, not admins. | LOW | `SELECT * FROM books WHERE stock_quantity <= :threshold ORDER BY stock_quantity ASC`. Threshold should be a query parameter (default 10), not a hardcoded constant. |
| Admin review listing with sort and filter | Admin needs visibility into all reviews to find problematic content. Sorting by date and rating, filtering by book or user, are standard moderation-view requirements. | MEDIUM | `GET /admin/reviews?book_id=&user_id=&rating_min=&rating_max=&sort_by=created_at&order=desc&page=1&per_page=20`. Joins to `books` and `users` for display context. Use SQLAlchemy `select()` with dynamic `where()` clauses. |
| Admin review delete (single) | Already delivered in v2.0 as a P1 feature (`DELETE /admin/reviews/{id}`). This is confirmed table stakes — admins need reactive moderation authority. | LOW | Already implemented. |

### Differentiators (Competitive Advantage)

Features beyond bare minimum that add meaningful operational value. Not universally expected at this project scale, but meaningfully useful.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Stock turnover rate per book | Tells admins which books are moving quickly vs. sitting idle. "Sold 50 units against 200 in stock = 25% turnover" is actionable intelligence that raw stock counts don't provide. Useful for reorder timing. | MEDIUM | Formula: `units_sold_in_period / avg_stock_quantity`. "Average stock" is not tracked historically in this schema — simplify to `units_sold / current_stock_quantity` as a velocity proxy. Frame it as "units sold per week" (a sales velocity figure) rather than a formal accounting turnover ratio, which requires COGS. |
| Pre-booking demand ranking (most-waited-for books) | Out-of-stock books with many waiting pre-bookers are the highest-priority restock targets. Showing this ranking directly connects inventory decisions to demonstrated demand — qualitatively different from just showing low stock. | LOW | `SELECT book_id, COUNT(*) AS waitlist_count FROM pre_bookings WHERE status = 'waiting' GROUP BY book_id ORDER BY waitlist_count DESC LIMIT N`. Join to `books` for title/author. |
| AOV trend over time | A single AOV number is less useful than seeing whether it is rising or falling. Trending it weekly or monthly reveals pricing and bundle effects. | MEDIUM | Group `orders` by time bucket (DATE_TRUNC('week', created_at)) and compute AOV per bucket. Returns an array of `{period, aov}` objects. Client renders as a line chart. |
| Bulk review delete | When spam hits (a user posts identical reviews on many books, or a coordinated fake review campaign), admins need to remove N reviews without N sequential API calls. | MEDIUM | `DELETE FROM reviews WHERE id = ANY(:ids)`. Accept `ids: list[int]` in request body. Add admin-only guard. Return count of deleted records and list of IDs not found. PostgreSQL `= ANY()` is efficient with an indexed PK. |
| Revenue breakdown by genre | Tells admins which categories drive the most revenue. Useful for catalog expansion decisions and promotional focus. Rare in small storefronts but appears in mid-tier tools. | MEDIUM | `JOIN order_items → books → genres`, `GROUP BY genre_id`. Requires genres to be populated; returns NULL genre as "Uncategorized". |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem natural for an analytics dashboard but create problems at this scale and scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time streaming analytics / WebSockets | "Live" dashboards feel modern; admins want to see numbers update without refreshing | WebSockets add connection management complexity, require ASGI broadcast infrastructure, and provide no real value for business metrics that are meaningful over hours not seconds. Admin analytics are not a trading floor. | Simple REST endpoints with explicit refresh. A page that reloads data on demand is correct for this use case. |
| Materialized views / analytics tables | At scale, pre-aggregating data is the right answer; reads from a summary table are faster than full-table scans | This project has at most thousands of orders. Live SQL aggregates on indexed columns are trivially fast. Materialized views add a refresh job (cron/Celery), stale-data risk, and migration complexity that is entirely unjustified at this volume. | Run live SQL aggregates. Add materialized views only when query time exceeds 200ms under real load. |
| Celery/Redis background jobs for analytics | "Offload expensive aggregations to a background worker" | The existing stack explicitly excludes Celery/Redis (PROJECT.md constraint). BackgroundTasks is in scope. Analytics queries at this scale do not require async processing. | Run synchronously in FastAPI route. If a query takes >500ms, optimize it with an index rather than offloading it. |
| User cohort analysis | "See revenue from users acquired in different months" | Cohort analysis requires `user_created_at` retention calculations and a substantially more complex query surface. It is a BI tool feature, not an operational admin panel feature. No user acquisition date → cohort mapping exists in the current schema. | Export raw order/user data to a BI tool (even a spreadsheet) for cohort analysis. Not an API concern. |
| Revenue forecasting / demand prediction | "Predict how much stock we'll need next month" | Forecasting requires historical volume sufficient for statistical signal (minimum 12-24 months of data), a prediction algorithm, and a confidence interval model. This system has insufficient data history and the PROJECT.md out-of-scope list includes recommendation engines. | Use turnover velocity + pre-booking demand as leading indicators. Manual judgment with these signals is correct at this stage. |
| Pre-moderation review queue | "Review every review before it goes live" | Already analyzed and rejected in v2.0 research. Creates latency, queue-management UI complexity, and suppresses authentic negative reviews. Reactive admin-delete is the correct moderation pattern at this scale. | Admin review listing with filter/sort enables reactive moderation efficiently. |
| Automated review flagging / AI moderation | "Auto-flag suspicious reviews before admin sees them" | Requires external API (OpenAI, ModerAPI, etc.), adds a network call on every review creation, costs money per review, introduces false-positive rate management. At this review volume, an admin scanning the list directly is faster and cheaper. | Admin review list sorted by recent; manual inspection. |
| Export to CSV / PDF | "I want to download my revenue report" | File generation in-process blocks the request thread for large datasets. Streaming CSV is doable but non-trivial. PDF generation requires a library (reportlab, weasyprint) with system dependencies. Out of scope for an API-first project where the consumer can format data themselves. | Return JSON from analytics endpoints; the client (curl, Postman, a spreadsheet plugin, or a frontend) handles formatting and export. |

---

## Feature Dependencies

```
[Existing: orders table (confirmed orders, created_at)]
    └──required by──> [Revenue summary] (SUM on filtered orders)
    └──required by──> [AOV calculation] (SUM / COUNT on confirmed orders)
    └──required by──> [AOV trend over time] (GROUP BY time bucket)

[Existing: order_items table (book_id, quantity, unit_price)]
    └──required by──> [Revenue summary] (line-item revenue calculation)
    └──required by──> [Top sellers by revenue] (GROUP BY book_id, SUM revenue)
    └──required by──> [Top sellers by volume] (GROUP BY book_id, SUM quantity)
    └──required by──> [Stock turnover velocity] (units_sold for velocity calculation)

[orders + order_items JOIN]
    └──required by──> [All sales analytics] (join required to correlate items with order status/date)

[Existing: books table (stock_quantity, genre_id)]
    └──required by──> [Low-stock alerts] (WHERE stock_quantity <= threshold)
    └──required by──> [Stock turnover velocity] (current_stock_quantity as denominator)
    └──required by──> [Top sellers] (JOIN to get book title/author for display)
    └──required by──> [Revenue by genre] (JOIN to genres via genre_id)

[Existing: pre_bookings table (book_id, status = 'waiting')]
    └──required by──> [Pre-booking demand ranking] (COUNT waiting pre_bookings per book)

[Pre-booking demand ranking]
    └──enhances──> [Low-stock alerts] (together reveal which low-stock books have active demand)

[Existing: reviews table + users table + books table]
    └──required by──> [Admin review listing] (JOIN all three for display context)
    └──required by──> [Bulk review delete] (DELETE WHERE id = ANY(:ids))

[Admin review listing]
    └──prerequisite for──> [Bulk review delete] (admin discovers IDs to bulk-delete from the listing)

[Existing: admin auth dependency (AdminUser)]
    └──required by──> [All analytics endpoints] (admin-only gate)
    └──required by──> [Admin review listing] (admin-only)
    └──required by──> [Bulk review delete] (admin-only)
```

### Dependency Notes

- **All sales analytics require `status = 'confirmed'` filter on orders:** `payment_failed` orders must be excluded from all revenue calculations. This constraint applies everywhere — revenue summary, top sellers, AOV, and turnover velocity all need this WHERE clause.
- **`order_items.book_id` is nullable (SET NULL on book delete):** Top-seller and turnover queries must handle NULL book_id gracefully. Rows with NULL book_id represent deleted books and should be excluded or aggregated as "Deleted book" in the response.
- **`order_items.unit_price` is a snapshot, not a live price:** This is correct — analytics must use the price-at-purchase, not the current book price. Do not JOIN to `books.price` for revenue calculations. The snapshot in `order_items.unit_price` is the authoritative source.
- **Pre-booking demand ranking only shows `status = 'waiting'` pre-bookings:** `NOTIFIED` and `CANCELLED` pre-bookings represent resolved demand and should be excluded from the demand ranking — they are no longer actionable.
- **Bulk review delete operates on the soft-deleted reviews model:** The `reviews` table has a `deleted_at` field. Bulk delete should set `deleted_at = NOW()` (soft-delete), consistent with existing admin delete behavior. Confirm the v2.0 implementation is soft-delete before applying this.
- **Low-stock threshold is a query parameter, not a system setting:** Do not store the threshold in the database. A query parameter `?threshold=10` with a sensible default is correct. Different admins may want different thresholds in the same session.

---

## MVP Definition

### This Milestone (v2.1) — Launch With

All of the following must ship together. They constitute the milestone deliverables.

**Sales Analytics:**
- [ ] `GET /admin/analytics/sales/summary?period=today|week|month` — revenue total, order count, AOV, and period-over-period delta for the selected period
- [ ] `GET /admin/analytics/sales/top-books?limit=10&sort_by=revenue|volume` — top-N books by revenue or unit volume with book title, author, units sold, and revenue total
- [ ] `GET /admin/analytics/sales/aov-trend?period=week|month&buckets=N` — AOV per time bucket (N weeks or months) for trend visualization

**Inventory Analytics:**
- [ ] `GET /admin/analytics/inventory/low-stock?threshold=10` — books with stock at or below threshold, ordered by stock ascending; include book title, author, current stock, and waitlist count (pre-booking demand integrated here)
- [ ] `GET /admin/analytics/inventory/turnover?limit=10&days=30` — top-N books by sales velocity (units sold in last N days / current stock), ordered by velocity descending
- [ ] `GET /admin/analytics/inventory/prebook-demand?limit=10` — books with most active pre-bookings (`status = 'waiting'`), ordered by waitlist count descending

**Review Moderation Dashboard:**
- [ ] `GET /admin/reviews?book_id=&user_id=&rating_min=&rating_max=&sort_by=created_at|rating&order=asc|desc&page=1&per_page=20` — paginated admin review listing with filter support; includes reviewer email (or username), book title, rating, text, created_at
- [ ] `DELETE /admin/reviews/bulk` with body `{"ids": [1, 2, 3]}` — bulk delete reviews by ID list; return count deleted and any IDs not found

### Add After Validation (v2.x)

- [ ] Revenue breakdown by genre — `GET /admin/analytics/sales/by-genre` — useful once genre data is populated; depends on admin adding genres to books
- [ ] AOV trend — if v2.1 launches without this, add here; it is a differentiator not a table stake
- [ ] Review export (JSON download) — if an admin consumer requests it; the API response already provides the data, this is just a `Content-Disposition: attachment` header

### Future Consideration (v3+)

- [ ] Materialized view caching for analytics — only if live queries exceed 200ms under real production load; evaluate after 6 months of data
- [ ] Analytics webhooks — notify external systems when thresholds are crossed (e.g., stock drops below threshold)
- [ ] Cohort analysis or user lifetime value — requires external BI tool or substantially more complex query surface

---

## Feature Prioritization Matrix

| Feature | Admin Value | Implementation Cost | Priority |
|---------|-------------|---------------------|----------|
| Revenue summary (today/week/month) | HIGH | LOW | P1 |
| Period-over-period comparison | HIGH | LOW | P1 (comes free with summary query) |
| Top sellers by revenue | HIGH | LOW | P1 |
| Top sellers by volume | HIGH | LOW | P1 (same query, different ORDER) |
| Average order value | HIGH | LOW | P1 |
| Low-stock alerts | HIGH | LOW | P1 |
| Admin review listing with filter/sort | HIGH | MEDIUM | P1 |
| Pre-booking demand ranking | MEDIUM | LOW | P1 (integrates into low-stock response) |
| Bulk review delete | MEDIUM | MEDIUM | P1 (spam response capability) |
| Stock turnover velocity | MEDIUM | MEDIUM | P1 (key inventory intelligence) |
| AOV trend over time | MEDIUM | MEDIUM | P2 |
| Revenue by genre | LOW | MEDIUM | P2 |
| Review export | LOW | LOW | P3 |
| Materialized views | LOW | HIGH | P3 (premature optimization) |

**Priority key:**
- P1: Must have for v2.1 milestone
- P2: Should have, add after P1 is stable
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Reference implementations from established e-commerce platforms and their admin analytics approaches:

| Feature | Shopify Admin | WooCommerce | Our v2.1 Approach |
|---------|---------------|-------------|-------------------|
| Revenue summary | Today / week / month / year, selectable | Custom date range | Today / week / month with period-over-period delta |
| Period comparison | Built-in "vs. prior period" toggle | Plugin-dependent | Built-in as part of summary response |
| Top sellers | By revenue, quantity, sell-through rate | By revenue or quantity | Both in single endpoint with `sort_by` param |
| AOV | Displayed on overview page | Displayed in reports | Included in summary response |
| Low stock alerts | Threshold per product, configurable | Global threshold setting | Query parameter threshold, default 10 |
| Turnover / velocity | "Sell-through rate" in inventory reports | Via plugin | Units sold per N days / current stock |
| Pre-booking demand | No native equivalent (backorder queue) | Backorder reports | Waitlist count per book from `pre_bookings` |
| Review listing for admin | All reviews with sort/filter | Via WooCommerce admin | Paginated listing with book/user/rating filters |
| Bulk review actions | Bulk approve/spam/trash | Bulk mark spam/trash | Bulk delete (reactive moderation only) |

---

## Existing System Integration Points

The complete mapping of where new v2.1 features attach to the existing codebase.

| New Feature | Queries | Integration Point |
|-------------|---------|-------------------|
| Revenue summary | `orders` (status, created_at), `order_items` (quantity, unit_price) | New `AnalyticsRepository` or `SalesRepository`; new router at `/admin/analytics/` |
| Top sellers | `order_items` (book_id, quantity, unit_price) JOIN `books` (title, author) JOIN `orders` (status filter) | Same `SalesRepository` |
| AOV / AOV trend | `orders` (created_at, status) + `order_items` aggregates | Same `SalesRepository` |
| Low-stock alerts | `books` (stock_quantity) LEFT JOIN `pre_bookings` (waitlist count) | New `InventoryRepository` |
| Turnover velocity | `order_items` + `orders` (date-windowed) JOIN `books` (current stock) | Same `InventoryRepository` |
| Pre-booking demand | `pre_bookings` (status = 'waiting') JOIN `books` | Same `InventoryRepository` |
| Admin review listing | `reviews` JOIN `books` JOIN `users` | New methods on existing `ReviewRepository` (already exists in v2.0) |
| Bulk review delete | `reviews` WHERE `id = ANY(:ids)` | New method on existing `ReviewRepository`; new route under `/admin/reviews/bulk` |
| Auth guard | Existing `AdminUser` dependency | Inject `_admin: AdminUser` on every new analytics route — same pattern as `/admin/users` |

---

## Sources

- [Shopify Admin API — Orders resource](https://shopify.dev/docs/api/admin-rest/2025-01/resources/order) — revenue and order analytics patterns from the leading e-commerce platform; period filtering, status filtering (HIGH confidence — official documentation)
- [commercetools Reports and Analytics](https://docs.commercetools.com/api/) — composable commerce analytics API design patterns (MEDIUM confidence — official documentation, scope partially overlaps)
- [DashThis: 15 Essential E-Commerce Metrics](https://dashthis.com/blog/10-essential-ecommerce-metrics-for-your-reporting-dashboard/) — canonical list of dashboard metrics that admins expect; revenue, AOV, top sellers (MEDIUM confidence — analytics industry reference)
- [ThoughtSpot: 15 Essential E-Commerce KPIs](https://www.thoughtspot.com/data-trends/ecommerce-kpis-metrics) — KPI taxonomy including period-over-period comparison as table stakes (MEDIUM confidence)
- [Moesif: REST API Design — Filtering, Sorting, and Pagination](https://www.moesif.com/blog/technical/api-design/REST-API-Design-Filtering-Sorting-and-Pagination/) — standard query parameter patterns for admin list endpoints (HIGH confidence — widely cited API design reference)
- [NetSuite: Inventory Turnover Ratio](https://www.netsuite.com/portal/resource/articles/inventory-management/inventory-turnover-ratio.shtml) — inventory turnover formula and its variants; basis for sales velocity adaptation (HIGH confidence — ERP vendor official documentation)
- [Corporate Finance Institute: Inventory Turnover](https://corporatefinanceinstitute.com/resources/accounting/inventory-turnover/) — COGS-based turnover formula and why a simplified velocity proxy is appropriate without COGS tracking (HIGH confidence — financial education reference)
- [REST API Bulk Operations Patterns — Microsoft Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design) — bulk delete via request body with ID list is the established REST pattern (HIGH confidence — official architecture documentation)
- [Moderation API — November 2025 Updates](https://blog.moderationapi.com/blog/product-updates-november-2025/) — current state of review moderation tooling; confirms reactive admin-delete with admin listing is the standard pattern at this scale (LOW confidence — vendor blog, single source)

---

*Feature research for: BookStore v2.1 — Admin Dashboard & Analytics*
*Researched: 2026-02-27*
