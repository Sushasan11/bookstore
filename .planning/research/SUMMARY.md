# Project Research Summary

**Project:** BookStore API v2.0 — Reviews & Ratings
**Domain:** E-commerce bookstore backend — adding review system to an existing FastAPI service
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

This is a well-scoped v2.0 milestone, not a greenfield project. The existing v1.1 system (9,473 LOC, 179 passing tests) provides all the infrastructure needed: FastAPI, async SQLAlchemy 2.0, PostgreSQL, Pydantic v2, JWT auth with role-based dependencies, and an established module pattern. No new libraries are required. The recommended approach is to follow the existing five-file module pattern (`models → schemas → repository → service → router`) for a new `app/reviews/` module, with minimal targeted modifications to three existing files (`OrderRepository`, `BookDetailResponse`, and the book detail router endpoint). Every feature maps cleanly to existing patterns already in use for cart, wishlist, orders, and pre-booking.

The key architectural decisions are: (1) compute `average_rating` and `review_count` live from the `reviews` table at read time via SQL aggregates — not stored denormalized columns on `books`, which would require cache invalidation on every review mutation; (2) enforce the one-review-per-user-per-book rule at both the DB level (`UniqueConstraint`) and service layer for race-condition safety; (3) enforce the verified-purchase gate by joining `order_items` to `orders` and filtering `orders.status = 'confirmed'`, injecting `OrderRepository` into `ReviewService` to avoid circular imports. Cross-domain reads use repository injection (not service injection), consistent with the `BookService`/`PreBookRepository` pattern already in the codebase.

The primary risks are all technical implementation details, not architectural unknowns. The most impactful pitfall is the verified-purchase query: querying only `orders` (which has no `book_id`) or forgetting the `status = 'confirmed'` filter would allow unverified reviews through. The second critical pitfall is the model registry: adding `app/reviews/models.py` without importing it in `app/db/base.py` causes test suite failures. Both are easily prevented by following the established codebase patterns. All seven critical pitfalls identified have clear prevention strategies requiring no major design changes.

---

## Key Findings

### Recommended Stack

The existing locked stack covers every v2.0 requirement without additions. The analysis evaluated and rejected `fastapi-pagination` (inconsistent with existing manual pagination), `sqlalchemy-utils` aggregated attributes (ORM event complexity for a two-line aggregate), `bleach` (JSON API has no XSS risk), and `slowapi` (out of scope). The only non-trivial stack caveat is the PostgreSQL `ROUND` function: two-argument `ROUND(value, places)` requires a `NUMERIC` cast because `func.avg()` returns `DOUBLE PRECISION` by default — `func.round(func.avg(Review.rating).cast(Numeric), 1)` is required. This is documented but not yet exercised in this specific codebase (MEDIUM confidence).

**Core technologies:**
- **FastAPI 0.133.0:** Routing, dependency injection, OpenAPI docs — no change from v1.1
- **SQLAlchemy 2.0.47 (async):** ORM model, `UniqueConstraint`, `CheckConstraint`, `func.avg()`, `func.count()`, `exists()` subquery for verified-purchase — all standard patterns already in use
- **Pydantic 2.12.5:** `Field(ge=1, le=5)` for rating validation; `| None` union types for optional fields; `model_config = {"from_attributes": True}` for ORM serialization
- **PostgreSQL:** Constraint enforcement, indexed FK scans for aggregates, CASCADE delete on reviews when book/user deleted
- **Alembic 1.18.4:** One new migration: `CREATE TABLE reviews` with `UniqueConstraint`, `CheckConstraint`, indexes on `(book_id)` and `(user_id)`
- **asyncpg 0.31.0:** Async driver; `IntegrityError` wraps `UniqueViolationError` — must be caught and converted to 409 in the repository

### Expected Features

**Must have (table stakes — all P1 for v2.0):**
- Submit star rating (1-5) with optional text body — `POST /books/{book_id}/reviews`
- One review per user per book — DB `UniqueConstraint` + service 409 response
- Verified-purchase gate — `orders` + `order_items` EXISTS check, `confirmed` status only
- Edit own review — `PATCH /reviews/{review_id}`, owner-only, updates `updated_at`
- Delete own review — `DELETE /books/{book_id}/reviews/{review_id}`, owner-only
- Admin delete any review — same endpoint, role check in service layer (`actor_role == "admin"`)
- Average rating on book detail — `avg_rating: float | None` + `review_count: int` via SQL aggregate
- Paginated review list — `GET /books/{book_id}/reviews?page=1&size=20`, sorted `created_at DESC`
- `user_has_reviewed` flag on book detail — boolean for authenticated users, LOW complexity, high UX value

**Should have (differentiators — P2 for v2.x after validation):**
- Rating distribution breakdown (`rating_breakdown: {1: N, ..., 5: N}`) — trust signal, one extra GROUP BY aggregate
- Reviewer display name — available from existing `User` model, no new table

**Defer to v3+ (out of scope for v2.0):**
- Helpfulness voting — requires `review_votes` table, vote deduplication, sort-by-helpful; review volume too low to justify
- Review photo/media uploads — requires S3, CDN, thumbnail generation; separate infrastructure milestone
- Sort reviews by helpfulness — depends on helpfulness voting first
- Email prompt after order delivery to leave a review — depends on stable review system + email template work

**Explicit anti-features (do not build):**
- Anonymous reviews — breaks verified-purchase gate entirely
- Pre-moderation queue — latency hurts UX; reactive admin delete is sufficient at this scale
- Incentivized reviews — FTC 2024 rules, up to $51,744/violation
- Weighted average — opaque to users, no practical benefit at this scale

### Architecture Approach

The `app/reviews/` module follows the identical five-file pattern established across all existing domains. Integration is additive: five new files plus one migration, with targeted modifications to exactly four existing locations (`OrderRepository`, `BookDetailResponse`, the book detail router endpoint, and `main.py` for router registration). Cross-domain concerns are resolved at the service layer through constructor injection — `ReviewService` accepts `OrderRepository` for the verified-purchase check, mirroring the `BookService`/`PreBookRepository` pattern in v1.1. Aggregate data (`avg_rating`, `review_count`) is computed via SQL `AVG()`/`COUNT()` at read time, fetched by `ReviewRepository.get_avg_and_count()` and passed explicitly to `BookDetailResponse` alongside `model_validate(book)` — never stored as denormalized columns.

**Major components:**
1. **`app/reviews/models.py`** — `Review` ORM model: `UniqueConstraint("user_id", "book_id")`, `CheckConstraint("rating >= 1 AND rating <= 5")`, `CASCADE` on both FKs (not `SET NULL`)
2. **`app/reviews/repository.py`** — CRUD operations: `create`, `get_by_id`, `get_by_user_and_book`, `update`, `delete`, `list_for_book` (paginated), `get_avg_and_count`
3. **`app/reviews/service.py`** — Business rules: verified-purchase check (via injected `OrderRepository`), duplicate review guard, ownership check for edit/delete, admin bypass for delete
4. **`app/reviews/router.py`** — Endpoints: `POST /books/{id}/reviews`, `GET /books/{id}/reviews`, `PATCH /reviews/{id}`, `DELETE /books/{id}/reviews/{id}` — all using `ActiveUser` with role branching in service
5. **`app/orders/repository.py` (modified)** — One new method: `has_user_purchased_book(user_id, book_id) -> bool` using `EXISTS` subquery
6. **`app/books/schemas.py` (modified)** — Two new fields on `BookDetailResponse`: `avg_rating: float | None`, `review_count: int`
7. **`app/books/router.py` (modified)** — `GET /books/{id}` instantiates `ReviewRepository(db)` and calls `get_avg_and_count(book_id)`, passing result explicitly to response constructor

### Critical Pitfalls

1. **Verified-purchase query missing `order_items` join or `status = 'confirmed'` filter** — Always join `order_items → orders` and filter `orders.status = OrderStatus.CONFIRMED` (import the enum, never hardcode the string). Test: user with `payment_failed` order must get 403, not 201.

2. **Review model not imported in `app/db/base.py`** — Add `from app.reviews.models import Review  # noqa: F401` as the first step after creating the model file. Verify with `pytest tests/test_health.py` before writing any service code. Missing this causes `UndefinedTableError` mid-suite and `alembic --autogenerate` produces an empty migration.

3. **No `UniqueConstraint` in migration — duplicate reviews under concurrent requests** — Always define `UniqueConstraint("user_id", "book_id")` in the migration; catch `IntegrityError` wrapping `UniqueViolationError` and re-raise as `AppError(409)`. Application pre-check alone is not race-condition safe.

4. **`Review.book_id` FK uses `SET NULL` (copied from `OrderItem` pattern) instead of `CASCADE`** — Reviews without a book are meaningless; use `ondelete="CASCADE"` and `nullable=False`. Test: delete a book and verify its reviews are deleted and no `NULL book_id` rows remain.

5. **`BookDetailResponse` aggregate fields silent-default to `None`/`0` because router still calls `model_validate(book)` alone** — Never rely on `model_validate(orm_object)` for computed aggregate fields. Fetch aggregates separately and pass explicitly: `BookDetailResponse(**model_validate(book).model_dump(), avg_rating=avg, review_count=count)`. Test: create a review, call `GET /books/{id}`, assert `avg_rating` is not null.

6. **No index on `reviews(book_id)` — full table scan on every book detail request** — Add `Index("ix_reviews_book_id", "book_id")` in the initial migration alongside table creation; a covering index `("book_id", "rating")` is even better.

7. **Admin delete endpoint uses `ActiveUser` instead of `AdminUser`** — Use `AdminUser` dependency on the admin delete route. Test: call admin delete with a regular-user JWT and assert 403.

---

## Implications for Roadmap

Based on research, the build order has clear technical dependencies: DB schema before repository, repository before service, service before router, book detail integration last. Research converges on three natural phases matching the architecture's own dependency graph.

### Phase 1: Data Layer — Review Model, Migration, and Repository

**Rationale:** All service and router logic depends on the repository; the repository depends on the schema; the schema migration must run before any query can succeed. The `OrderRepository` purchase-check method belongs here because `ReviewService` depends on it at service construction time. This is also the phase where the most irreversible decisions are made (FK behavior, constraints, indexes) — getting these right from the start prevents expensive data migrations later.

**Delivers:** Working `reviews` table in PostgreSQL with correct constraints and indexes; `ReviewRepository` with all CRUD + aggregate methods; `OrderRepository.has_user_purchased_book()`; model registered in `app/db/base.py`; Alembic migration verified with `alembic upgrade head`

**Addresses features:** Foundation for all review CRUD, verified-purchase gate, one-per-user enforcement, aggregate rating

**Avoids pitfalls:** Missing model registry (#2), missing `UniqueConstraint` (#3), wrong FK `SET NULL` (#4), missing `book_id` index (#6)

### Phase 2: Core Review CRUD — Service, Router, and Full Test Coverage

**Rationale:** Service and router depend on the repository from Phase 1. All user-facing and admin review endpoints are developed and tested together because they share the same authorization model (ownership check vs. admin bypass). Testing the full CRUD cycle here validates the verified-purchase gate, duplicate constraint handling, and confirms the 179 existing tests still pass before book detail integration begins.

**Delivers:** All review endpoints operational: `POST` (create with verified-purchase gate), `GET` (list, paginated, `created_at DESC`), `PATCH` (edit own), `DELETE` (user + admin via service role check); complete auth model; `user_has_reviewed` flag; full regression suite passing

**Addresses features:** Submit review, edit own review, delete own review, admin delete, paginated review list, `user_has_reviewed` flag

**Avoids pitfalls:** Wrong verified-purchase query (#1), admin endpoint uses wrong auth dep (#7), `user_id` from request body (security), no pagination from day one

### Phase 3: Book Detail Integration — Aggregate Surface

**Rationale:** This phase is intentionally last because it is a read-only extension of existing functionality — it does not block the core review system and can be shipped independently. It is the smallest phase (two file modifications) but carries the most common silent-failure mistake: `model_validate(book)` not passing computed aggregate values. Testing this phase requires real review data from Phase 2.

**Delivers:** `GET /books/{id}` returns correct `avg_rating` and `review_count` that reflect the live state of the reviews table; `BookDetailResponse` schema updated; values are `None`/`0` (not absent) when no reviews exist

**Addresses features:** Average rating on book detail, review count on book detail

**Avoids pitfalls:** `BookDetailResponse` silent null defaults (#5)

### Phase Ordering Rationale

- Phase 1 must come first: every layer above it depends on it; migration must run before any query; `app/db/base.py` import must exist before `alembic --autogenerate` produces a non-empty migration.
- Phase 2 before Phase 3: (a) core review CRUD is the primary deliverable; (b) book detail aggregate integration requires actual review data to test correctly; (c) separating phases limits blast radius — a bug in review submission does not block testing the aggregate display.
- Phase 3 last: non-blocking read-only enhancement; the book detail endpoint continues to work without ratings while Phase 2 is being built and tested.

### Research Flags

Phases with well-documented patterns — skip additional research during planning:
- **Phase 1:** All patterns (UniqueConstraint, CheckConstraint, FK CASCADE, Index) are standard SQLAlchemy 2.0 declarative ORM — HIGH confidence, official docs verified, patterns used elsewhere in the codebase (`ck_books_price_positive`, wishlist `UniqueConstraint`).
- **Phase 2:** Auth patterns (ActiveUser, AdminUser, AppError), service/repository constructor injection, IntegrityError handling — all established in existing codebase at HIGH confidence.
- **Phase 3:** `model_validate` + explicit aggregate passing — explicitly documented in PITFALLS.md with code example; no additional research needed.

Phases that may benefit from one targeted validation during implementation (not blocking):
- **Phase 1 / Phase 3 (minor):** The `func.avg().cast(Numeric)` pattern for two-argument `ROUND` — MEDIUM confidence (verified in PostgreSQL docs but not yet exercised in this codebase's asyncpg version). Validate with a quick integration test when the aggregate query is first written. Fallback: Python-side rounding `round(float(avg), 1) if avg else None`.
- **Phase 2 (minor):** `asyncpg.exceptions.UniqueViolationError` as `exc.orig` — confirm the exact import path during implementation; existing codebase uses asyncpg as the driver so `from asyncpg.exceptions import UniqueViolationError` is expected correct.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies locked and validated in v1.1; no new libraries; every pattern mapped to existing codebase usage. One MEDIUM point: `func.avg().cast(Numeric)` for ROUND not yet exercised in this specific stack combination. |
| Features | HIGH | Core CRUD, verified-purchase gate, and one-per-user constraint are well-established e-commerce patterns; confirmed against Goodreads guidelines, commercetools API docs, FTC rules. Helpfulness voting and distribution breakdown (deferred features) are MEDIUM. |
| Architecture | HIGH | Direct codebase inspection; all integration points derived from actual source files (`app/orders/models.py`, `app/core/deps.py`, `app/books/schemas.py`, etc.). Module pattern is locked and consistent across all 7 existing domains. |
| Pitfalls | HIGH | Pitfalls derived from codebase inspection, not assumptions. Specific model paths, column names, status enum values, and FK patterns verified against actual source. Recovery strategies provided for all critical pitfalls. |

**Overall confidence: HIGH**

### Gaps to Address

- **`func.avg().cast(Numeric)` for 2-arg ROUND:** MEDIUM confidence — documented in PostgreSQL docs and SQLAlchemy docs but not exercised in this codebase's asyncpg version. Validate with an integration test when the aggregate query is first written in Phase 1 or 3. Fallback: `round(float(avg), 1) if avg else None` in Python.
- **`asyncpg.exceptions.UniqueViolationError` import path:** Confirm the exact import path during Phase 2 implementation. The codebase uses asyncpg as the driver — `from asyncpg.exceptions import UniqueViolationError` is expected correct, but verify against the `asyncpg 0.31.0` API.
- **`GET /books` (list view) per-book aggregates:** Research covers `GET /books/{id}` aggregate integration only. If the book list endpoint also needs `avg_rating` per book (identified as a UX improvement in PITFALLS.md), this requires a single GROUP BY subquery — not N separate aggregate calls. This is a v2.x enhancement, not in v2.0 scope per FEATURES.md, but should be designed to allow easy addition later.

---

## Sources

### Primary (HIGH confidence)
- Existing codebase — `app/orders/models.py`, `app/books/schemas.py`, `app/core/deps.py`, `app/books/router.py`, `app/wishlist/models.py`, `app/db/base.py`, `app/main.py` — direct source verification
- [SQLAlchemy 2.0 Constraints and Indexes](https://docs.sqlalchemy.org/en/20/core/constraints.html) — UniqueConstraint, CheckConstraint
- [SQLAlchemy 2.0 SELECT / scalar_subquery](https://docs.sqlalchemy.org/en/20/tutorial/data_select.html) — aggregate query patterns
- [SQLAlchemy 2.0 SQL Functions](https://docs.sqlalchemy.org/en/20/core/functions.html) — func.avg, func.count, func.round
- [Pydantic v2 Fields](https://docs.pydantic.dev/latest/concepts/fields/) — `ge`/`le` integer constraints
- [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) — CheckConstraint syntax
- [Goodreads Review Guidelines](https://www.goodreads.com/review/guidelines) — book-specific review platform policy decisions
- [FTC Fake Reviews Rule 2024](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials) — legal constraints on incentivized reviews
- [commercetools Reviews API](https://docs.commercetools.com/api/projects/reviews) — production review API design patterns
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/) — DI patterns

### Secondary (MEDIUM confidence)
- [Smashing Magazine — Product Reviews and Ratings UX (2023)](https://www.smashingmagazine.com/2023/01/product-reviews-ratings-ux/) — UX patterns, verified-purchase credibility, anti-patterns
- [PostgreSQL ROUND Function (Neon)](https://neon.com/postgresql/postgresql-math-functions/postgresql-round) — NUMERIC type requirement for two-argument ROUND
- [Handling Race Conditions in PostgreSQL MVCC (Bufisa)](https://bufisa.com/2025/07/17/handling-race-conditions-in-postgresql-mvcc/) — TOCTOU and duplicate insert patterns
- [SQLAlchemy UniqueViolation handling (Rollbar)](https://rollbar.com/blog/python-psycopg2-errors-uniqueviolation/) — IntegrityError catch pattern
- [PostgreSQL Aggregation Best Practices (TigerData)](https://www.tigerdata.com/learn/postgresql-aggregation-best-practices) — index-driven aggregate queries

### Tertiary (LOW confidence)
- [FastAPI SQLAlchemy 2.0 Async Patterns (Medium 2025)](https://dev-faizan.medium.com/fastapi-sqlalchemy-2-0-modern-async-database-patterns-7879d39b6843) — async aggregate update patterns; unverified blog post, treat as illustrative only

---

*Research completed: 2026-02-26*
*Ready for roadmap: yes*
