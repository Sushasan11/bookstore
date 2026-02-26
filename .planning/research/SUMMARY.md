# Project Research Summary

**Project:** BookStore API v2.1 — Admin Dashboard & Analytics
**Domain:** Admin analytics API with review moderation for an existing FastAPI bookstore backend
**Researched:** 2026-02-27
**Confidence:** HIGH

## Executive Summary

This is an additive milestone on top of a working v2.0 FastAPI/PostgreSQL/SQLAlchemy 2.0 codebase (12,010 LOC, 240 passing tests, 5-file domain module pattern). The v2.1 scope is three feature groups — sales analytics, inventory analytics, and review moderation dashboard — all read-only, admin-only endpoints querying existing tables. No new database tables, no new infrastructure, and no new frameworks are needed. PostgreSQL's native aggregation functions (`date_trunc`, `SUM`, `COUNT`, `LAG`, window functions) accessed via the already-installed SQLAlchemy 2.0 `func` namespace handle every analytics requirement. The recommended approach is a single new `app/admin/analytics_repository.py` for all cross-domain aggregate SQL, a thin `app/admin/analytics_service.py` for period-comparison orchestration, a new `app/admin/analytics_router.py`, and two new admin-list/bulk-delete methods added to the existing `ReviewRepository`.

The recommended phase order is: (1) Sales Analytics — establishes the analytics infrastructure, (2) Inventory Analytics — extends the same infrastructure with additional models, (3) Review Moderation Dashboard — isolated change to the existing `ReviewRepository`. All three phases can deliver independently. The highest-value P1 features (revenue summary with period-over-period, top sellers, AOV, low-stock alerts, admin review listing, bulk review delete) are well-documented patterns with low implementation risk. The anti-features list is equally important: real-time WebSockets, Celery/Redis workers, Pandas/DuckDB, materialized views, and AI review moderation are all explicitly out of scope at this scale.

The primary risks are all silent data quality errors, not crashes: including `PAYMENT_FAILED` orders in revenue calculations, joining `order_items → books` with INNER JOIN (dropping deleted-book revenue), missing `deleted_at IS NULL` on the admin review query, and using `datetime.now()` instead of `datetime.now(timezone.utc)` for period bounds. A secondary risk is the N+1 for bulk review delete — must use a single `UPDATE ... WHERE id IN (...)` statement with `synchronize_session="fetch"`, not a loop over individual `session.delete()` calls. All eight critical pitfalls have clear, tested prevention strategies documented in PITFALLS.md.

---

## Key Findings

### Recommended Stack

The existing stack is fully sufficient for v2.1. FastAPI 0.133, SQLAlchemy 2.0.47 (asyncio), asyncpg 0.31, Pydantic v2.12, PostgreSQL (docker-compose), Alembic 1.18, and pytest-asyncio are locked and proven. No new core packages are required. The one optional addition is a manual TTL cache (Python-level `dict` + `time.monotonic()`) at the service layer to avoid re-aggregating expensive queries on every admin page refresh. `cachetools 7.0.1` can be used if preferred, but `asyncache` (the bridge library) must be avoided — it is Python 3.8–3.10 only and incompatible with this project's Python 3.13 target.

**Core technologies:**
- **PostgreSQL (existing):** `date_trunc`, `FILTER` clause on aggregates, `SUM`/`COUNT`/`AVG`, `LAG`/`RANK` window functions — all native, no extra tooling
- **SQLAlchemy 2.0 (existing):** `func.date_trunc()`, `func.sum()`, `func.count()`, `case()`, `over()` for windows, `update().where().in_()` for bulk soft-delete
- **asyncpg 0.31 (existing):** Passes all SQL constructs through to PostgreSQL; TIMESTAMPTZ columns require timezone-aware Python datetimes
- **Pydantic v2 (existing):** Response schemas for structured analytics payloads; `Decimal` fields serialize to string by default — must use `float` or `PlainSerializer(float)` for numeric JSON output
- **Manual TTL dict (no install):** `dict[str, tuple[Any, float]]` + `time.monotonic()` — sufficient for admin-frequency analytics requests; Redis/Celery explicitly out of scope

**What not to use:** Pandas/Polars (full-table pull into Python), DuckDB (duplicate of PostgreSQL), Redis/fastapi-cache2 (out of scope), asyncache (Python 3.10 max), TimescaleDB/InfluxDB (OLAP overkill), Celery (out of scope), SQLModel (schema divergence risk).

### Expected Features

All v2.1 features are delivered from existing tables — no schema migrations needed.

**Must have — Sales Analytics (P1):**
- `GET /admin/analytics/sales/summary?period=today|week|month` — revenue total, order count, AOV, and period-over-period delta; period-over-period comes free with the summary query
- `GET /admin/analytics/sales/top-books?limit=10&sort_by=revenue|volume` — top-N books by revenue (SUM unit_price * quantity) or volume (SUM quantity); these are two distinct metrics that must produce distinct rankings
- `GET /admin/analytics/sales/aov-trend?period=week|month&buckets=N` — AOV per time bucket for trend visualization (MEDIUM complexity, can be deferred to P2)

**Must have — Inventory Analytics (P1):**
- `GET /admin/analytics/inventory/low-stock?threshold=10` — books at or below threshold, ordered by stock ascending; threshold is a query param, not hardcoded; includes waitlist count from pre-bookings
- `GET /admin/analytics/inventory/turnover?limit=10&days=30` — units sold in the period (sales velocity, not a ratio to current stock — avoids division by zero on out-of-stock books)
- `GET /admin/analytics/inventory/prebook-demand?limit=10` — books with most WAITING pre-bookings only (`status = 'waiting'` filter mandatory)

**Must have — Review Moderation (P1):**
- `GET /admin/reviews?book_id=&user_id=&rating_min=&rating_max=&sort_by=&order=&page=&per_page=` — paginated admin review listing; uses a new `AdminReviewResponse` schema (not the user-facing `ReviewResponse`) to avoid N+1 `verified_purchase` lookups
- `DELETE /admin/reviews/bulk` with body `{"ids": [...]}` — bulk soft-delete (sets `deleted_at`, not hard DELETE); returns count actually deleted

**Should have / defer (P2):**
- `GET /admin/analytics/sales/by-genre` — revenue breakdown by genre; useful only when genre data is populated
- AOV trend — can ship as P2 if P1 is already ambitious

**Defer to v3+:**
- Materialized views (only if live queries exceed 200ms under real load)
- Analytics webhooks, cohort analysis, CSV/PDF export, real-time WebSockets

**Anti-features explicitly rejected:** Real-time streaming analytics, Celery/Redis background jobs, pre-moderation review queue, AI review moderation, user cohort analysis, revenue forecasting.

### Architecture Approach

v2.1 is an integration problem, not a greenfield build. The established 5-file module pattern is locked. All new analytics code lives in `app/admin/` as four new files (`analytics_repository.py`, `analytics_service.py`, `analytics_router.py`, `analytics_schemas.py`). The existing `ReviewRepository` gains two new methods (`list_all_admin()` and `bulk_delete()`). No existing files are structurally changed except `app/main.py` (one `include_router` line) and `app/reviews/repository.py` (two new method additions). No new database tables or Alembic migrations are required.

**Major components:**
1. **AnalyticsRepository (NEW):** All cross-domain aggregate SQL — reads `Order`, `OrderItem`, `Book`, `PreBooking` models directly; does NOT extend or wrap any existing domain repository; owned by `app/admin/analytics_repository.py`
2. **AdminAnalyticsService (NEW):** Orchestrates multi-query results; owns period-bound computation using `datetime.now(timezone.utc)` and period-over-period delta calculation; passes concrete `datetime` objects to the repository (not string period names); owned by `app/admin/analytics_service.py`
3. **Analytics Router (NEW):** All GET endpoints under `/admin/analytics/` plus admin review endpoints; `AdminUser` dependency set at the router level — no individual endpoint can be accidentally unprotected; owned by `app/admin/analytics_router.py`
4. **Analytics Schemas (NEW):** `RevenueSummaryResponse`, `TopSellersResponse`, `LowStockResponse`, `TurnoverResponse`, `PreBookDemandResponse`, `AdminReviewListResponse`, `BulkDeleteResponse`; `Decimal` fields serialized as `float`; owned by `app/admin/analytics_schemas.py`
5. **ReviewRepository (MODIFIED):** Gains `list_all_admin()` (paginated, sorted, filtered, always includes `Review.deleted_at.is_(None)`) and `bulk_delete()` (single `UPDATE ... WHERE id IN (...)` statement with `synchronize_session="fetch"`)

**Key patterns:** Period-bound computation belongs in the service layer, not the repository. The repository receives only concrete `datetime` parameters. Analytics queries use PostgreSQL-level `GROUP BY` and `SUM` — never load ORM objects into Python for arithmetic. Bulk operations use set-based SQL (`WHERE id IN (...)`), not per-row ORM loops.

### Critical Pitfalls

1. **PAYMENT_FAILED orders included in revenue** — every revenue/sales query must filter `Order.status == OrderStatus.CONFIRMED`; missing this silently overstates revenue; verify by creating a PAYMENT_FAILED order and asserting it does not appear in the summary
2. **NULL book_id dropped by INNER JOIN** — when a book is deleted, `OrderItem.book_id` becomes `NULL` via `SET NULL`; using `INNER JOIN books ON order_items.book_id = books.id` silently drops those sales from revenue totals; use `LEFT JOIN` and handle `NULL` title with a `"[Deleted Book]"` fallback
3. **Naive datetime for period bounds** — `datetime.now()` without timezone returns a naive datetime; always use `datetime.now(timezone.utc)`; "today's revenue" silently returns 0 after 8pm EST in production if UTC is not used consistently
4. **Soft-delete filter missing from admin review list** — the new `list_all_admin()` method must include `Review.deleted_at.is_(None)` matching all 4 existing `ReviewRepository` methods; missing it causes deleted reviews to reappear in the moderation dashboard
5. **N+1 bulk soft-delete** — bulk review delete must use a single `UPDATE reviews SET deleted_at = NOW() WHERE id IN (:ids) AND deleted_at IS NULL` with `synchronize_session="fetch"`; per-row `session.delete()` loop requires 2N database round-trips
6. **Pre-booking demand counts all statuses** — must filter `PreBooking.status == PreBookStatus.WAITING`; counting `NOTIFIED` and `CANCELLED` pre-bookings overstates current demand and produces incorrect restocking signals
7. **Stock turnover division by zero** — `units_sold / current_stock_quantity` crashes when `stock_quantity = 0`; express turnover as raw sales velocity (units sold in period) not a ratio; use `NULLIF(stock_quantity, 0)` if a ratio is required
8. **Admin analytics router missing `AdminUser` dependency** — set `dependencies=[Depends(get_admin_user)]` at the `APIRouter(prefix="/admin")` constructor level; any endpoint accidentally created without a per-endpoint dependency is still protected

---

## Implications for Roadmap

Based on research, the natural phase structure follows the architectural build order defined in ARCHITECTURE.md. Three phases are warranted, each independently shippable.

### Phase 1: Sales Analytics

**Rationale:** Establishes the `AnalyticsRepository` + `AdminAnalyticsService` + `analytics_router` + `analytics_schemas` infrastructure that Phase 2 extends. Sales analytics are the highest-value features (revenue, top sellers, AOV) and the most straightforward — `orders` and `order_items` are well-understood. The period-comparison and admin auth patterns established here are reused in all subsequent phases.

**Delivers:** Revenue summary with period-over-period comparison, top sellers by revenue and volume, average order value. Admin can answer "how is the store performing?" for the first time.

**Addresses features from FEATURES.md:** `GET /admin/analytics/sales/summary`, `GET /admin/analytics/sales/top-books`, `GET /admin/analytics/sales/aov-trend`

**Avoids pitfalls from PITFALLS.md:**
- Establish `Order.status == OrderStatus.CONFIRMED` filter as the baseline for all queries (Pitfall 1)
- Use `LEFT JOIN books` pattern with NULL title fallback for deleted-book items (Pitfall 1, Bug A)
- Compute period bounds with `datetime.now(timezone.utc)` in `AdminAnalyticsService` (Pitfall 2)
- Set `AdminUser` dependency at router constructor level (Pitfall 8)
- Serialize `Decimal` aggregates as `float` in all response schemas

### Phase 2: Inventory Analytics

**Rationale:** Extends the analytics infrastructure from Phase 1 with additional model imports (`Book`, `PreBooking`). The query patterns are the same as Phase 1 but involve more join complexity. Low-stock alerts integrate pre-booking demand counts, making the combined view more useful than either feature alone. Can be developed in parallel with Phase 3 after Phase 1 is complete.

**Delivers:** Low-stock alerts with waitlist count integration, stock turnover velocity (units sold per N days), pre-booking demand ranking. Admin can answer "what do I need to restock?" for the first time.

**Addresses features from FEATURES.md:** `GET /admin/analytics/inventory/low-stock`, `GET /admin/analytics/inventory/turnover`, `GET /admin/analytics/inventory/prebook-demand`

**Avoids pitfalls from PITFALLS.md:**
- Express turnover as units sold (velocity), not a ratio to current stock — avoids division by zero when `stock_quantity = 0` (Pitfall 6)
- Filter `PreBooking.status == PreBookStatus.WAITING` — avoids overstating demand with resolved pre-bookings (Pitfall 7)
- Use `LEFT JOIN` for turnover query to include all confirmed-order books (Pitfall 1)
- Cap the `limit` query parameter at `le=100` to prevent unbounded aggregation

### Phase 3: Review Moderation Dashboard

**Rationale:** Isolated change — modifies the existing `ReviewRepository` rather than the analytics repository, making it independently deployable and independently testable. Review moderation is a separate operational concern from analytics. The admin list endpoint requires a new `AdminReviewResponse` schema to avoid inheriting the N+1 `verified_purchase` behavior from the user-facing review list.

**Delivers:** Paginated, sortable, filterable admin review listing with reviewer context; bulk soft-delete for spam response. Admin can answer "are there problematic reviews?" and act on them efficiently.

**Addresses features from FEATURES.md:** `GET /admin/reviews` with sort/filter/paginate, `DELETE /admin/reviews/bulk`

**Avoids pitfalls from PITFALLS.md:**
- `list_all_admin()` must include `Review.deleted_at.is_(None)` — soft-delete filter mandatory (Pitfall 3)
- `bulk_delete()` must use single `UPDATE ... WHERE id IN (...)` with `synchronize_session="fetch"` — no per-row ORM loop (Pitfall 4)
- Use a new `AdminReviewResponse` schema (not `ReviewResponse`) to omit `verified_purchase` and eliminate N+1 (Pitfall 8)
- Implement as soft-delete (`UPDATE SET deleted_at`) not hard DELETE — preserves audit trail

### Phase Ordering Rationale

- **Phase 1 first** because it creates the four new files (`analytics_repository`, `analytics_service`, `analytics_router`, `analytics_schemas`) that Phase 2 extends by adding methods and schemas to the same files. Phase 2 cannot start until Phase 1 establishes the file and infrastructure structure.
- **Phase 2 second** because it uses the same repository/router/schema pattern from Phase 1, adding different model imports and join logic. No new architectural decisions are needed.
- **Phase 3 last (or parallel to Phase 2)** because it touches a different module (`app/reviews/repository.py`) and has no dependency on Phase 1 or 2 infrastructure beyond the shared `AdminUser` auth dependency.
- **No new migrations** across all three phases — all queries are read-only against existing tables (the `bulk_delete` UPDATE writes to an existing `deleted_at` column introduced in v2.0).

### Research Flags

Phases with standard patterns (skip `/gsd:research-phase`):
- **Phase 1 (Sales Analytics):** SQLAlchemy aggregate query patterns are extensively documented; period-comparison is straightforward Python arithmetic; all patterns are provided with concrete code examples in STACK.md and ARCHITECTURE.md.
- **Phase 2 (Inventory Analytics):** Extends Phase 1 patterns with `LEFT JOIN` and `NULLIF`; no novel patterns required.
- **Phase 3 (Review Moderation):** SQLAlchemy bulk UPDATE pattern is documented with exact code in ARCHITECTURE.md and PITFALLS.md; straightforward extension of existing `ReviewRepository`.

No phases require a `/gsd:research-phase` call — the existing research provides sufficient implementation detail including concrete code patterns for every endpoint.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All claims verified against official SQLAlchemy 2.0 docs and PyPI; version compatibility confirmed; asyncache incompatibility with Python 3.13 verified directly from PyPI |
| Features | HIGH (table stakes), MEDIUM (complexity estimates) | Feature set based on Shopify/WooCommerce/commercetools analysis; complexity estimates depend on index coverage; whether caching is necessary depends on actual data volume (currently LOW confidence) |
| Architecture | HIGH | Derived from direct codebase inspection of all relevant source files; module pattern, dependency injection, soft-delete convention all confirmed from actual code |
| Pitfalls | HIGH | All 8 critical pitfalls verified against actual model definitions — `OrderStatus`, `OrderItem.book_id SET NULL`, `Review.deleted_at`, `PreBookStatus.WAITING`; SQLAlchemy async DML `synchronize_session` issue cross-referenced with official SQLAlchemy GitHub discussion |

**Overall confidence:** HIGH

### Gaps to Address

- **Caching necessity:** Whether TTL caching is needed at all depends on admin access frequency and data volume — currently no production data exists to make this call. Recommendation: implement Phase 1 without caching; add a manual TTL dict only if admin dashboard response times exceed 200ms under real usage.
- **`aov-trend` endpoint scope:** Grouping by time bucket with `date_trunc` is straightforward SQL, but the default number of buckets and the exact response shape (`{period, aov}` list) involve UX decisions not fully specified. Validate with stakeholders before committing to the schema; this is a P2 candidate if the decision is unclear.
- **Genre data availability for revenue-by-genre (P2):** The genre breakdown feature depends on books having populated `genre_id` values. If genres are sparsely populated, the feature will show mostly NULL/"Uncategorized" results. Assess genre data coverage before scheduling this endpoint.
- **Admin review list `verified_purchase` field:** PITFALLS.md identifies N+1 risk at page_size >= 50. The recommended schema omits `verified_purchase`, which removes the N+1 entirely. Confirm with stakeholders that `verified_purchase` is not needed in the admin moderation view — if it is required, a batch EXISTS query must be designed before Phase 3 implementation begins.

---

## Sources

### Primary (HIGH confidence)

- SQLAlchemy 2.0 SQL Functions docs — `func.*`, FILTER clause on aggregates, `over()` for window functions
- SQLAlchemy 2.0 ORM DML Guide — bulk DELETE/UPDATE patterns, `synchronize_session` strategies
- SQLAlchemy 2.0 Column Elements — `case()`, `label()`, `FunctionFilter` construct
- asyncpg 0.31.0 PyPI — version confirmed Feb 2026; PostgreSQL feature passthrough confirmed
- cachetools 7.0.1 PyPI — Python 3.13 compatible; zero dependencies; manual TTL pattern documented
- Direct codebase inspection — `app/admin/router.py`, `app/orders/models.py`, `app/reviews/repository.py`, `app/prebooks/models.py`, `app/core/deps.py`, `app/main.py`
- Moesif: REST API Design (Filtering, Sorting, Pagination) — query parameter patterns for admin list endpoints
- Microsoft Azure Architecture Center — bulk delete via request body with ID list is the established REST pattern

### Secondary (MEDIUM confidence)

- Shopify Admin API Orders resource — revenue and order analytics patterns; period filtering and status filtering patterns
- DashThis: 15 Essential E-Commerce Metrics — canonical admin dashboard metric set; basis for P1 feature selection
- ThoughtSpot: 15 Essential E-Commerce KPIs — period-over-period comparison as table stakes
- NetSuite / Corporate Finance Institute: Inventory Turnover — basis for simplified sales velocity approach
- Crunchy Data: Window Functions for Data Analysis with PostgreSQL — LAG, RANK, date_trunc patterns
- Crunchy Data: 4 Ways to Create Date Bins in Postgres — date bucketing approaches

### Tertiary (LOW confidence)

- asyncache PyPI — version 0.3.1, last released Nov 2022; Python <=3.10 only — verified as incompatible (this is a negative finding; confidence in the rejection is HIGH)
- Moderation API blog (Nov 2025) — reactive admin-delete as standard moderation pattern at this scale (single vendor source)
- commercetools Reports and Analytics API — composable commerce analytics design patterns (partial scope overlap)

---

*Research completed: 2026-02-27*
*Ready for roadmap: yes*
