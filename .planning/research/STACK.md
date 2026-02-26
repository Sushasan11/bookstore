# Stack Research

**Domain:** Reviews & Ratings feature addition to existing FastAPI bookstore API
**Researched:** 2026-02-26
**Confidence:** HIGH

## Context: Subsequent Milestone, Not Greenfield

This is v2.0 added to a working v1.1 system (9,473 LOC, 179 tests). The existing stack
is validated and locked. Research scope is strictly: what new library/pattern additions,
if any, are needed for reviews & ratings. The answer is: **none**. Every requirement
maps cleanly onto the existing stack.

---

## Existing Stack (Validated — Do Not Re-Research)

| Technology | Locked Version | Role |
|------------|---------------|------|
| FastAPI | 0.133.0 | HTTP layer, routing, dependency injection |
| SQLAlchemy | 2.0.47 (async) | ORM, query building, aggregate functions |
| Alembic | 1.18.4 | DB schema migrations |
| Pydantic | 2.12.5 | Schema validation, request/response models |
| PostgreSQL | (docker-compose) | Persistence, constraint enforcement |
| asyncpg | 0.31.0 | Async PostgreSQL driver |
| pytest + pytest-asyncio | 9.0.2 / 1.3.0 | Test framework |
| httpx | 0.28.1 | Async test client |

---

## New Libraries Needed

**None.** Every reviews & ratings capability is covered by the existing stack.

The table below documents the analysis that led to this conclusion:

| Capability Needed | Provided By | Mechanism | Confidence |
|-------------------|-------------|-----------|------------|
| 1-5 integer constraint (API layer) | Pydantic 2.12.5 | `Field(ge=1, le=5)` on `rating: int` | HIGH |
| 1-5 integer constraint (DB layer) | SQLAlchemy + PostgreSQL | `CheckConstraint("rating >= 1 AND rating <= 5")` in `__table_args__` | HIGH |
| One review per user per book | SQLAlchemy + PostgreSQL | `UniqueConstraint("user_id", "book_id", name="uq_reviews_user_book")` in `__table_args__` | HIGH |
| Verified purchase check | SQLAlchemy 2.0 | `exists()` subquery against `order_items` JOIN `orders` — same async session pattern already in use | HIGH |
| Average rating aggregate | SQLAlchemy `func.avg()` | Scalar subquery via `.scalar_subquery()` embedded in book detail query | HIGH |
| Review count aggregate | SQLAlchemy `func.count()` | Scalar subquery via `.scalar_subquery()` embedded in book detail query | HIGH |
| Rounding avg to 1 decimal | SQLAlchemy `func.round()` + PostgreSQL NUMERIC cast | `func.round(func.avg(Review.rating).cast(Numeric), 1)` — NUMERIC cast required for 2-arg ROUND in PostgreSQL | MEDIUM |
| User edit own review | Existing `ActiveUser` dep + repo update | Same pattern as cart item update | HIGH |
| User delete own review | Existing `ActiveUser` dep + repo delete | Same pattern as wishlist item removal | HIGH |
| Admin delete any review | Existing `AdminUser` dep + repo delete | Same pattern as admin book/user management | HIGH |
| Paginated review listing | Manual `page` + `size` Query params | Same pattern as `GET /books` — no library needed | HIGH |
| Reviews table migration | Alembic 1.18.4 | `alembic revision --autogenerate` — standard workflow | HIGH |

---

## Core Technologies — Reviews-Specific Patterns

### SQLAlchemy 2.0 — Model with Composite Unique + Check Constraint

```python
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_reviews_user_book"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

**Why both Pydantic and DB constraint for rating range:** Pydantic validates at the API
boundary (fast, user-friendly 422 response). DB `CheckConstraint` is the safety net for
any path that bypasses the API (migrations, scripts). Defense in depth — consistent with
`ck_books_stock_non_negative` and `ck_books_price_positive` already in the codebase.

**Why `UniqueConstraint` over application-layer duplicate check:** A DB constraint is the
only reliable guard against race conditions (two concurrent requests from the same user).
Application-layer check alone allows double-submit. The DB raises `IntegrityError` which
the repository catches and re-raises as `AppError(409)` — same pattern as ISBN uniqueness
in `BookRepository`.

**Trailing comma in `__table_args__` tuple is required** — without it Python treats
`(UniqueConstraint(...))` as a simple parenthesized expression, not a tuple, and
SQLAlchemy silently ignores it.

### SQLAlchemy 2.0 — Aggregate Queries for Book Detail

The existing stack already uses `func.now()`, `select()`, and async `session.execute()`.
Rating aggregates extend this naturally:

```python
from sqlalchemy import func, select
from sqlalchemy.types import Numeric

# Average rating (rounded to 1 decimal, returns NULL when no reviews)
avg_subq = (
    select(func.round(func.avg(Review.rating).cast(Numeric), 1))
    .where(Review.book_id == book_id)
    .scalar_subquery()
)

# Review count
count_subq = (
    select(func.count())
    .select_from(Review)
    .where(Review.book_id == book_id)
    .scalar_subquery()
)

# Embed both in book detail query — one round-trip
result = await session.execute(
    select(Book, avg_subq.label("avg_rating"), count_subq.label("review_count"))
    .where(Book.id == book_id)
)
```

**Why scalar_subquery over separate queries:** One DB round-trip instead of three. The
scalar subquery is correlated automatically when embedded in the enclosing `select()`.
This is the recommended SQLAlchemy 2.0 pattern for inline aggregates on related entities.

**Why `.cast(Numeric)` for ROUND:** PostgreSQL's two-argument `ROUND(value, places)` only
accepts `NUMERIC` type. `func.avg()` returns `DOUBLE PRECISION` by default. The cast
avoids a `ProgrammingError` at runtime. Confidence MEDIUM — verified via PostgreSQL docs,
not yet exercised in this specific codebase.

### SQLAlchemy 2.0 — Verified Purchase EXISTS Check

```python
from sqlalchemy import exists, select

async def has_purchased(session: AsyncSession, user_id: int, book_id: int) -> bool:
    stmt = select(
        exists().where(
            OrderItem.book_id == book_id,
            OrderItem.order_id == Order.id,
            Order.user_id == user_id,
            Order.status == OrderStatus.CONFIRMED,
        )
    )
    return bool((await session.execute(stmt)).scalar())
```

**Why EXISTS over JOIN:** EXISTS is a semi-join — it short-circuits on the first matching
row. For a binary yes/no check (has this user bought this book?), EXISTS is faster than
an INNER JOIN that would return rows needing deduplication. Standard PostgreSQL pattern
per documentation.

### Pydantic 2.12.5 — Rating Field Constraint

```python
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5, description="Star rating: 1 (worst) to 5 (best)")
    body: str | None = Field(None, max_length=5000)

class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    body: str | None = Field(None, max_length=5000)
```

`ge`/`le` are the correct Pydantic v2 field constraints. They generate correct JSON
Schema min/maximum for OpenAPI docs automatically. The deprecated `minimum`/`maximum`
kwargs generate warnings in Pydantic v2 — use `ge`/`le` exclusively.

---

## Supporting Libraries

No new supporting libraries are needed.

| Library Considered | Decision | Rationale |
|-------------------|----------|-----------|
| `fastapi-pagination` | **Reject** | Adds a dependency for functionality already implemented manually throughout the codebase (`page`/`size` pattern in `GET /books`). Consistency with existing patterns outweighs marginal convenience; no new capability gained. |
| `sqlalchemy-utils` aggregated attributes | **Reject** | `AggregatedAttribute` maintains a denormalized cache column updated via ORM events. Reviews are low write-frequency — computing avg/count inline with scalar_subquery is simpler, correct, and adds zero new infrastructure. |
| `bleach` / HTML sanitizer | **Defer** | Review body is stored and returned as plain text in a JSON API. No XSS risk for a backend-only service returning JSON. Add only if HTML/Markdown rendering is introduced. |
| `slowapi` (rate limiting) | **Defer** | Out of scope per PROJECT.md. No real-traffic scale concern at v2.0. |

---

## Installation

No new packages to install. All capabilities are in existing dependencies.

```bash
# Nothing to run — existing environment covers all requirements.
# The only new artifacts are source code files and one migration.
```

New artifacts for v2.0 reviews & ratings:

| Artifact | Type | Notes |
|----------|------|-------|
| `app/reviews/` | New module | models, schemas, repository, service, router |
| `alembic/versions/<hash>_add_reviews_table.py` | Migration | `alembic revision --autogenerate -m "add_reviews_table"` |
| `tests/test_reviews.py` | Test file | Covers all CRUD + auth + constraint paths |

---

## Alternatives Considered

| Capability | Recommended Approach | Alternative | Why Not |
|------------|---------------------|-------------|---------|
| Avg rating storage | Compute inline via scalar_subquery on every book detail request | Denormalized `avg_rating` + `review_count` columns on `books` table | Denormalized columns require an update trigger or explicit recalculation on every review write/edit/delete. At v2.0 scale, live computation is negligible. Denormalize only after profiling proves it's a bottleneck. |
| One-review enforcement | DB `UniqueConstraint` + catch `IntegrityError` → 409 | Application-layer check only (query before insert) | Application check is vulnerable to concurrent requests. DB constraint is atomic — the only correct guard. |
| Rating range enforcement | Both Pydantic `Field(ge=1, le=5)` + `CheckConstraint` | Application layer only | Defense in depth; mirrors existing pattern (`ck_books_price_positive`). DB constraint catches any bypass path. |
| Verified purchase | EXISTS subquery per review creation request | Store `purchased=True` flag on user-book join table | Additional table adds schema complexity. The EXISTS query against `orders`/`order_items` is already indexed (foreign keys) and fast for point lookups. |
| Review listing sort | `created_at DESC` (newest first) | Helpfulness score / upvotes | No upvote system in scope. Newest-first is the correct default for a simple single-criterion list. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `sqlalchemy-utils` | `AggregatedAttribute` adds ORM event magic and a heavy dependency for a simple aggregate that two lines of `func.avg()` handle | `func.avg()` + `func.count()` scalar subqueries inline |
| `fastapi-pagination` | Inconsistent with existing manual pagination pattern in `GET /books`; adds coupling to an opinionated external library | Manual `page: int = Query(1, ge=1)` / `size: int = Query(20, ge=1, le=100)` — exact same pattern as existing endpoints |
| `bleach` or markdown parser | Review body is plain text; no HTML rendering in a JSON API | Store `body` as raw `Text` column; return as-is |
| Denormalized `avg_rating` column on `books` | Premature optimization; requires trigger or explicit recalc on every review mutation | Inline scalar subquery; denormalize only after profiling |
| Review "helpful" / upvote columns | Explicitly out of scope per PROJECT.md: "Social features beyond reviews (commenting, following users) — not a social platform" | Not in v2.0 |
| Separate `verified_purchase` boolean stored on review | Redundant data that can drift from order history; derive from EXISTS query at write time | Check at review creation time; reject if no confirmed purchase |

---

## Stack Patterns by Variant

**For the book detail endpoint adding avg_rating + review_count:**
- Embed scalar subqueries in the existing book detail query — returns `avg_rating: float | None` (None when no reviews) and `review_count: int`
- Add fields to `BookDetailResponse` Pydantic schema with `from_attributes = True`

**For `GET /books/{book_id}/reviews` (paginated list):**
- Reuse `page` + `size` Query params with same defaults as `GET /books` (page=1, size=20, max=100)
- Sort `created_at DESC` (newest first) — consistent with order history
- No cursor pagination needed at this scale

**For the 409 conflict on duplicate review attempt:**
- Catch `IntegrityError` (from asyncpg) in the repository `create_review` method
- Check that the constraint name in the error message matches `uq_reviews_user_book`
- Re-raise as `AppError(status_code=409, detail="You have already reviewed this book.", code="REVIEW_ALREADY_EXISTS")`
- Same pattern as ISBN conflict handling in `BookRepository`

**For the 403 / 422 on non-purchaser attempting to review:**
- Check `has_purchased()` in the service layer before calling `repo.create_review()`
- Raise `AppError(status_code=403, detail="Purchase required to leave a review.", code="REVIEW_PURCHASE_REQUIRED")`

**For admin delete (any review) vs user delete (own review only):**
- Two separate endpoints or one endpoint with branched auth:
  - `DELETE /reviews/{id}` with `ActiveUser` dep: verify `review.user_id == current_user["sub"]`
  - `DELETE /admin/reviews/{id}` with `AdminUser` dep: no ownership check
- Consistent with how admin book/user management is separated from user-facing routes

---

## Version Compatibility

All combinations already validated in the running v1.1 system. No new version
compatibility surface introduced by v2.0.

| Component | Version | Notes |
|-----------|---------|-------|
| SQLAlchemy 2.0.47 | asyncpg 0.31.0 | Working in production (v1.1 confirmed) |
| Pydantic 2.12.5 | FastAPI 0.133.0 | Working in production (v1.1 confirmed) |
| `func.avg().cast(Numeric)` | PostgreSQL (any modern) | `.cast(Numeric)` required for 2-arg ROUND; standard PostgreSQL behavior; MEDIUM confidence (not yet exercised in this codebase) |
| `UniqueConstraint` in `__table_args__` | SQLAlchemy 2.0 | Standard declarative pattern; trailing comma in tuple required |
| `exists()` subquery | SQLAlchemy 2.0 async | Same session.execute() pattern used throughout existing repositories |

---

## Sources

- [SQLAlchemy 2.0 Constraints and Indexes](https://docs.sqlalchemy.org/en/20/core/constraints.html) — UniqueConstraint, CheckConstraint patterns (HIGH confidence)
- [SQLAlchemy 2.0 SELECT Statements](https://docs.sqlalchemy.org/en/20/tutorial/data_select.html) — scalar_subquery, func.avg, func.count (HIGH confidence)
- [SQLAlchemy 2.0 SQL Functions](https://docs.sqlalchemy.org/en/20/core/functions.html) — func.avg, func.count, func.round (HIGH confidence)
- [Pydantic v2 Fields](https://docs.pydantic.dev/latest/concepts/fields/) — `ge`/`le` integer constraints for 1-5 range (HIGH confidence)
- [PostgreSQL ROUND Function](https://neon.com/postgresql/postgresql-math-functions/postgresql-round) — NUMERIC type requirement for two-argument ROUND (MEDIUM confidence — not yet tested against this specific asyncpg version)
- [PostgreSQL Unique Indexes](https://www.postgresql.org/docs/current/indexes-unique.html) — composite unique constraint enforcement (HIGH confidence)
- [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) — CheckConstraint syntax (HIGH confidence)
- Existing codebase analysis — `app/books/models.py` (CheckConstraint pattern), `app/orders/models.py` + `app/orders/repository.py` (Order/OrderItem FK structure for EXISTS query), `app/core/deps.py` (ActiveUser/AdminUser dependency pattern), `app/books/schemas.py` (Field constraint + computed_field pattern), `poetry.lock` (confirmed exact library versions) — (HIGH confidence — verified by direct source reading)

---

*Stack research for: BookStore API v2.0 — Reviews & Ratings*
*Researched: 2026-02-26*
