# Phase 18: Review Moderation Dashboard - Research

**Researched:** 2026-02-27
**Domain:** FastAPI admin endpoints — paginated filtering, multi-column sorting, bulk soft-delete
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Admin access control**
- Any user with is_admin=True can access review moderation endpoints — matches existing admin endpoint pattern
- No superadmin or role hierarchy required
- No rate limiting on moderation endpoints
- No audit logging — soft-deleted reviews already have timestamps, audit trail is a separate concern

**Bulk delete semantics**
- Maximum 50 review IDs per bulk delete request
- Best-effort deletion: delete what can be deleted, silently skip missing or already-deleted IDs
- Response returns count of successfully deleted reviews

### Claude's Discretion
- Response shape for admin review list (what reviewer/book context to include per review)
- Filter interaction semantics (AND vs OR for combined filters)
- Default sort order for the review list
- Error response format for invalid filter values
- Pagination implementation details

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MOD-01 | Admin can list all reviews with pagination, sort (by date or rating), and filter (by book, user, or rating range) | Pattern: `list_paginated()` in `UserRepository` — conditional `.where()` clauses for filters; conditional `.order_by()` for sort; subquery count for total; new `list_all_admin()` method on `ReviewRepository` |
| MOD-02 | Admin can bulk-delete reviews by providing a list of review IDs | Pattern: single `UPDATE reviews SET deleted_at=now() WHERE id IN (...) AND deleted_at IS NULL`; return count of affected rows via `rowcount`; max 50 IDs validated via Pydantic `Field(max_length=50)` |
</phase_requirements>

---

## Summary

Phase 18 builds two admin endpoints entirely on existing infrastructure. The Review model (Phase 15) already has `deleted_at` for soft-delete, indexed `user_id` and `book_id` foreign keys, a `rating` integer column, and eager-loaded `user` and `book` relationships via `selectinload`. No database migrations are needed.

The admin list endpoint (`GET /admin/reviews`) follows the exact pattern established by `UserRepository.list_paginated()` — build a base `select(Review).where(Review.deleted_at.is_(None))`, conditionally append `.where()` clauses for each filter, conditionally swap `.order_by()` for sorting, run a subquery count for the total, then paginate. A new `list_all_admin()` method goes on `ReviewRepository` (not a new repository). The router goes in `app/admin/` as a new file (`reviews_router.py`) mirroring `analytics_router.py`.

The bulk delete endpoint (`DELETE /admin/reviews/bulk`) accepts a JSON body with a list of IDs (max 50, enforced by Pydantic). It issues a single `UPDATE ... WHERE id IN (...) AND deleted_at IS NULL`, uses `synchronize_session="fetch"` (the STATE.md documented pattern), and returns `{"deleted_count": N}`. Best-effort: IDs not found or already soft-deleted are silently skipped; the count reflects only rows actually updated.

**Primary recommendation:** Add `list_all_admin()` and `bulk_soft_delete()` to the existing `ReviewRepository`, create `app/admin/reviews_router.py` with two routes protected by `Depends(require_admin)` at the router level (matching `analytics_router.py`), add new schemas to `app/admin/analytics_schemas.py` or a new `app/admin/reviews_schemas.py`, and register the router in `app/main.py`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | ^0.133.0 | HTTP routing, Query/Body params, dependency injection | Already used throughout |
| SQLAlchemy (async) | ^2.0.47 | ORM, conditional filtering, bulk UPDATE | Already used throughout; `.where()` composition is the project pattern |
| Pydantic v2 | ^2.12.5 | Request/response schemas, Field validation for max list size | Already used throughout |
| asyncpg | ^0.31.0 | Async PostgreSQL driver | Already in stack |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `math` (stdlib) | — | `math.ceil(total / per_page)` for total_pages | Used in `app/admin/router.py` |
| `datetime` (stdlib) | — | `datetime.now(UTC)` for soft-delete timestamps | Used in `ReviewRepository.soft_delete()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single UPDATE...WHERE IN | Per-row soft_delete() loop | Loop is O(N) DB round-trips; single UPDATE is O(1); bulk is the correct choice |
| New AdminReviewRepository | Extend existing ReviewRepository | New repo adds indirection with no benefit; ReviewRepository already owns all Review persistence |
| Separate reviews_schemas.py in admin/ | Add to analytics_schemas.py | New file is cleaner separation; analytics_schemas.py is already domain-specific |

**Installation:** No new packages required — all dependencies are already in the project.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── admin/
│   ├── analytics_repository.py   # existing — no changes
│   ├── analytics_router.py       # existing — no changes
│   ├── analytics_schemas.py      # existing — no changes
│   ├── reviews_router.py         # NEW — GET /admin/reviews, DELETE /admin/reviews/bulk
│   ├── reviews_schemas.py        # NEW — AdminReviewEntry, AdminReviewListResponse, BulkDeleteRequest, BulkDeleteResponse
│   ├── router.py                 # existing — no changes
│   ├── schemas.py                # existing — no changes
│   └── service.py                # existing — no changes
├── reviews/
│   ├── models.py                 # existing — no changes (Review already has deleted_at, user/book relationships)
│   ├── repository.py             # EXTEND — add list_all_admin() and bulk_soft_delete()
│   └── ...
└── main.py                       # EXTEND — include reviews_admin_router
tests/
└── test_review_moderation.py     # NEW — integration tests for MOD-01 and MOD-02
```

### Pattern 1: Admin List with Conditional Filters (MOD-01)

**What:** Build a base SQLAlchemy `select` statement, conditionally append `where()` clauses for each optional filter parameter, swap `order_by()` based on sort parameter, run a subquery count, then paginate.

**When to use:** Any admin list endpoint with optional multi-field filtering and sorting.

**Example (from `UserRepository.list_paginated()` — verified in codebase):**
```python
# Source: app/users/repository.py
async def list_paginated(self, *, page, per_page, role=None, is_active=None):
    stmt = select(User).order_by(User.created_at.desc())
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await self.session.scalar(count_stmt)
    offset = (page - 1) * per_page
    stmt = stmt.limit(per_page).offset(offset)
    result = await self.session.execute(stmt)
    return list(result.scalars().all()), total
```

**Adaptation for `ReviewRepository.list_all_admin()`:**
```python
# New method on ReviewRepository
async def list_all_admin(
    self,
    *,
    page: int = 1,
    per_page: int = 20,
    book_id: int | None = None,
    user_id: int | None = None,
    rating_min: int | None = None,
    rating_max: int | None = None,
    sort_by: str = "date",
    sort_dir: str = "desc",
) -> tuple[list[Review], int]:
    stmt = (
        select(Review)
        .where(Review.deleted_at.is_(None))
        .options(selectinload(Review.user), selectinload(Review.book))
    )
    # Conditional filters — all combine as AND (simplest, correct for moderation)
    if book_id is not None:
        stmt = stmt.where(Review.book_id == book_id)
    if user_id is not None:
        stmt = stmt.where(Review.user_id == user_id)
    if rating_min is not None:
        stmt = stmt.where(Review.rating >= rating_min)
    if rating_max is not None:
        stmt = stmt.where(Review.rating <= rating_max)
    # Sort column and direction
    sort_col = Review.created_at if sort_by == "date" else Review.rating
    order_expr = desc(sort_col) if sort_dir == "desc" else asc(sort_col)
    stmt = stmt.order_by(order_expr, Review.id.desc())  # id as stable tiebreaker
    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await self.session.execute(count_stmt)).scalar_one()
    # Paginate
    result = await self.session.execute(
        stmt.limit(per_page).offset((page - 1) * per_page)
    )
    return list(result.scalars().all()), total
```

### Pattern 2: Bulk Soft-Delete via Single UPDATE (MOD-02)

**What:** Single `UPDATE reviews SET deleted_at = now() WHERE id IN (:ids) AND deleted_at IS NULL`. Returns `rowcount` as the count of successfully soft-deleted reviews.

**When to use:** Any bulk write operation where best-effort semantics are required (skip what's not found or already processed).

**Example (from STATE.md documented pattern, SQLAlchemy 2.x async):**
```python
# New method on ReviewRepository
async def bulk_soft_delete(self, review_ids: list[int]) -> int:
    """Soft-delete reviews by ID list. Skips already-deleted or missing IDs.

    Returns the count of reviews actually soft-deleted.
    """
    from datetime import UTC, datetime
    from sqlalchemy import update

    if not review_ids:
        return 0
    result = await self.session.execute(
        update(Review)
        .where(Review.id.in_(review_ids), Review.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount
```

**Key:** `synchronize_session="fetch"` is the project-established pattern (documented in STATE.md: `bulk_delete uses single UPDATE ... WHERE id IN (...) with synchronize_session="fetch"`).

### Pattern 3: Admin Router with Dependency at Router Level

**What:** Set `dependencies=[Depends(require_admin)]` at `APIRouter(...)` constructor level so every route in the file is protected automatically.

**When to use:** All admin routers in this project.

**Example (from `app/admin/analytics_router.py` — verified in codebase):**
```python
# Source: app/admin/analytics_router.py
router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin-reviews"],
    dependencies=[Depends(require_admin)],
)
```

### Pattern 4: Pagination Envelope (admin convention)

**What:** Admin list endpoints use `items`, `total_count`, `page`, `per_page`, `total_pages`. `total_pages = math.ceil(total / per_page) if total > 0 else 0`.

**Example (from `app/admin/schemas.py` and `app/admin/router.py` — verified in codebase):**
```python
# Source: app/admin/schemas.py
class UserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total_count: int
    page: int
    per_page: int
    total_pages: int

# Source: app/admin/router.py
return UserListResponse(
    items=[...],
    total_count=total,
    page=page,
    per_page=per_page,
    total_pages=math.ceil(total / per_page) if total > 0 else 0,
)
```

### Pattern 5: DELETE with JSON Body

**What:** FastAPI DELETE endpoints do not natively accept query parameters for list inputs. The standard pattern for bulk delete with a request body is to use a Pydantic model as the `Body(...)` parameter.

**Example (FastAPI standard pattern — verified against FastAPI docs behavior):**
```python
from fastapi import Body
from pydantic import BaseModel, Field

class BulkDeleteRequest(BaseModel):
    review_ids: list[int] = Field(min_length=1, max_length=50)

@router.delete("/bulk", response_model=BulkDeleteResponse)
async def bulk_delete_reviews(
    db: DbSession,
    _admin: AdminUser,
    body: BulkDeleteRequest,
) -> BulkDeleteResponse:
    ...
```

### Anti-Patterns to Avoid

- **Filtering with OR instead of AND:** Combined filters (e.g., `?book_id=5&rating_min=1`) should be AND semantics. OR semantics would return all reviews for any book OR any rating, which is not useful for moderation. AND is correct and simpler to implement.
- **Per-row soft-delete loop for bulk:** Calling `soft_delete()` N times in a loop is N DB round-trips. Single `UPDATE...WHERE IN` is O(1).
- **`synchronize_session=False` for bulk UPDATE:** SQLAlchemy async requires `synchronize_session="fetch"` (or `"evaluate"`) to keep the identity map consistent. `False` can cause stale in-memory objects.
- **Raising 404 for missing IDs in bulk delete:** Best-effort semantics (user decision) — silently skip, do not raise. Only return the count of what was actually deleted.
- **Eager-loading relationships in bulk_soft_delete:** The bulk method only updates timestamps; it does not need relationship data. Omit `selectinload` for performance.
- **Including `verified_purchase` in admin review list:** The admin moderation view does not need verified_purchase (that's a user-facing concern). Omit it from `AdminReviewEntry` to avoid the N+1 order queries seen in `ReviewService.list_for_book()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk soft-delete count | Per-row loop counting successes | `UPDATE...WHERE IN` + `result.rowcount` | `rowcount` is the DB-reported count of affected rows — exact, one query |
| Pagination total | Separate `SELECT COUNT(*)` with different filters | `select(func.count()).select_from(stmt.subquery())` | Reuses same filter logic as data query — eliminates filter divergence bugs |
| Sort direction | If/else building two full statements | `desc(col) if sort_dir == "desc" else asc(col)` inline expression | SQLAlchemy `asc()`/`desc()` wrap any column expression cleanly |
| Admin auth check | Manual `if role != "admin"` in each route | `dependencies=[Depends(require_admin)]` at router level | Router-level dependency applies to ALL routes in the file automatically |

**Key insight:** The bulk UPDATE pattern (`UPDATE...WHERE IN`) handles best-effort semantics correctly by design — non-matching IDs (already deleted or nonexistent) simply don't match the `WHERE` clause and `rowcount` reflects only what changed.

---

## Common Pitfalls

### Pitfall 1: Forgetting `deleted_at.is_(None)` in Admin List

**What goes wrong:** Admin sees soft-deleted reviews in the list because the `WHERE` clause was not applied.
**Why it happens:** `list_for_book()` in `ReviewRepository` filters soft-deletes; a new admin list method might forget this filter.
**How to avoid:** Every `select(Review)` in this phase MUST include `.where(Review.deleted_at.is_(None))`.
**Warning signs:** Test for "soft-deleted reviews do not reappear" (success criterion 5) catches this immediately.

### Pitfall 2: `synchronize_session` Missing on Bulk UPDATE

**What goes wrong:** SQLAlchemy raises `InvalidRequestError` or silently produces stale in-memory objects after bulk UPDATE.
**Why it happens:** Async SQLAlchemy requires explicit `synchronize_session` when using `update()` with `.where()`.
**How to avoid:** Always add `.execution_options(synchronize_session="fetch")` to bulk UPDATE statements.
**Warning signs:** Tests that read reviews after bulk delete see stale data or SQLAlchemy warns about session state.

### Pitfall 3: `rating_min`/`rating_max` Validation Not Enforced

**What goes wrong:** Caller passes `rating_min=0` or `rating_max=6`, which are outside the DB constraint (1-5). The query succeeds but returns wrong results or misleads callers.
**Why it happens:** FastAPI Query parameters don't auto-validate against business rules unless `ge`/`le` are specified.
**How to avoid:** Declare `rating_min: int | None = Query(None, ge=1, le=5)` and `rating_max: int | None = Query(None, ge=1, le=5)`. FastAPI returns 422 automatically for out-of-range values.
**Warning signs:** No tests for invalid rating range values.

### Pitfall 4: Subquery Count Includes Incorrect Filters

**What goes wrong:** The `total_count` in the paginated response doesn't match the number of items returned (e.g., count ignores filters, items respect filters).
**Why it happens:** Count query is built separately from the data query and misses some filter conditions.
**How to avoid:** Use the `select(func.count()).select_from(stmt.subquery())` pattern — `stmt` is the same statement object used for data (with all filters applied). Count uses `stmt` as a subquery, so filters are guaranteed to match.
**Warning signs:** Paginated response shows `total_count: 100` but only 3 items match the applied filter.

### Pitfall 5: `selectinload` on Bulk Delete Query

**What goes wrong:** `bulk_soft_delete()` unnecessarily loads `user` and `book` relationships, adding wasted DB queries.
**Why it happens:** Copying from `list_all_admin()` without removing `options(selectinload(...))`.
**How to avoid:** `bulk_soft_delete()` is a write-only operation. No `options()` needed — just the `update()` statement.

### Pitfall 6: `max_length` vs `max_items` in Pydantic v2

**What goes wrong:** `Field(max_length=50)` on a `list[int]` raises a Pydantic validation error because `max_length` is for strings; for lists, the correct constraint is `max_length=50` (Pydantic v2 actually uses `max_length` for lists too, treating it as max items — but be explicit in docs).
**Why it happens:** Pydantic v2 uses `max_length` for both strings and sequences. No issue, but worth being aware of.
**How to avoid:** `review_ids: list[int] = Field(min_length=1, max_length=50)` — Pydantic v2 accepts this for lists.

---

## Code Examples

Verified patterns from official sources or confirmed in-codebase usage:

### Admin Review List Response Schema

```python
# app/admin/reviews_schemas.py
import math
from pydantic import BaseModel, Field
from datetime import datetime


class AdminReviewAuthor(BaseModel):
    user_id: int
    display_name: str  # email.split('@')[0] — same as ReviewAuthorSummary


class AdminReviewBook(BaseModel):
    book_id: int
    title: str


class AdminReviewEntry(BaseModel):
    """Single review in the admin moderation list.

    Omits verified_purchase (admin concern is content, not purchase status).
    Omits avatar_url and cover_image_url (not needed for moderation).
    """
    id: int
    rating: int
    text: str | None
    created_at: datetime
    updated_at: datetime
    author: AdminReviewAuthor
    book: AdminReviewBook

    model_config = {"from_attributes": True}


class AdminReviewListResponse(BaseModel):
    items: list[AdminReviewEntry]
    total_count: int
    page: int
    per_page: int
    total_pages: int


class BulkDeleteRequest(BaseModel):
    review_ids: list[int] = Field(min_length=1, max_length=50)


class BulkDeleteResponse(BaseModel):
    deleted_count: int
```

### Admin Reviews Router

```python
# app/admin/reviews_router.py
import math

from fastapi import APIRouter, Depends, Query

from app.admin.reviews_schemas import (
    AdminReviewEntry,
    AdminReviewListResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from app.core.deps import AdminUser, DbSession, require_admin
from app.reviews.repository import ReviewRepository

router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin-reviews"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AdminReviewListResponse)
async def list_reviews(
    db: DbSession,
    _admin: AdminUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    book_id: int | None = Query(None),
    user_id: int | None = Query(None),
    rating_min: int | None = Query(None, ge=1, le=5),
    rating_max: int | None = Query(None, ge=1, le=5),
    sort_by: str = Query("date", pattern="^(date|rating)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> AdminReviewListResponse:
    repo = ReviewRepository(db)
    reviews, total = await repo.list_all_admin(
        page=page, per_page=per_page,
        book_id=book_id, user_id=user_id,
        rating_min=rating_min, rating_max=rating_max,
        sort_by=sort_by, sort_dir=sort_dir,
    )
    items = [
        AdminReviewEntry.model_validate({
            "id": r.id,
            "rating": r.rating,
            "text": r.text,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "author": {"user_id": r.user.id, "display_name": r.user.email.split("@")[0]},
            "book": {"book_id": r.book.id, "title": r.book.title},
        })
        for r in reviews
    ]
    return AdminReviewListResponse(
        items=items,
        total_count=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.delete("/bulk", response_model=BulkDeleteResponse)
async def bulk_delete_reviews(
    body: BulkDeleteRequest,
    db: DbSession,
    _admin: AdminUser,
) -> BulkDeleteResponse:
    repo = ReviewRepository(db)
    deleted_count = await repo.bulk_soft_delete(body.review_ids)
    return BulkDeleteResponse(deleted_count=deleted_count)
```

### main.py Registration

```python
# app/main.py — add alongside existing admin router registrations
from app.admin.reviews_router import router as reviews_admin_router

# In create_app():
application.include_router(reviews_admin_router)
```

### Sorting Pattern (verified SQLAlchemy 2.x)

```python
from sqlalchemy import asc, desc

sort_col = Review.created_at if sort_by == "date" else Review.rating
order_expr = desc(sort_col) if sort_dir == "desc" else asc(sort_col)
stmt = stmt.order_by(order_expr, Review.id.desc())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate `SELECT COUNT(*)` query | `select(func.count()).select_from(stmt.subquery())` | This project convention | Guarantees count and data use identical filters |
| `synchronize_session=False` | `synchronize_session="fetch"` | SQLAlchemy 2.x async best practice | Keeps SQLAlchemy identity map consistent after bulk writes |
| Row-level deletes in loop | Single `UPDATE...WHERE IN` | Standard SQL optimization | O(1) DB round-trips vs O(N) |

**Deprecated/outdated:**
- Per-row delete loop for bulk operations: Correct for single-record endpoints (`soft_delete()`), wrong for bulk. Phase 18 introduces the first bulk write in this project.

---

## Open Questions

1. **`total_pages` field name in admin review list response**
   - What we know: `UserListResponse` uses `total_pages`, `ReviewListResponse` uses only `total`+`page`+`size` (no `total_pages`)
   - What's unclear: Which convention to follow for the admin review list
   - Recommendation: Follow the admin convention (`total_pages` field using `math.ceil`) since this is an admin endpoint. The planner should note this for the schema definition.

2. **`sort_dir` parameter: validate with `pattern` or `Literal`?**
   - What we know: Existing code uses `Query(..., pattern="^(...)$")` regex validation for string enums
   - What's unclear: Whether to use `Literal["asc", "desc"]` type annotation instead
   - Recommendation: Stay consistent with project convention — use `pattern="^(asc|desc)$"` on `Query()`.

3. **`AdminReviewEntry` builder: inline dict vs `_build_review_data()`-style method?**
   - What we know: `ReviewService._build_review_data()` builds dicts for user-facing endpoints; admin view needs a simpler subset
   - What's unclear: Whether to add a similar helper to the router or keep it inline
   - Recommendation: Keep the dict construction inline in the router (or a module-level helper function) — no service class needed for a read-only admin list that goes direct to repository.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — skipping this section.

---

## Test Infrastructure (for Wave 0 planning)

**Existing infrastructure (no gaps):**
- pytest-asyncio with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` decorators needed
- `conftest.py` provides `client` (httpx AsyncClient), `db_session` (rolls back after each test), `test_engine` (session-scoped)
- Pattern for admin fixtures: create user via `UserRepository`, `set_role_admin()`, flush, login via `/auth/login`, return `{"Authorization": "Bearer ..."}` headers
- Test file goes in `tests/test_review_moderation.py`

**Test file email prefix convention (avoid collisions):**
- Use `revmod_` prefix for test user emails: `revmod_admin@example.com`, `revmod_user@example.com`

**Test data design for MOD-01:**
- Create 3+ reviews across 2 books, 2 users, varying ratings (e.g., 1, 3, 5)
- Soft-delete one review directly via ORM before tests to verify it's excluded
- Verify filter combinations: `?book_id=X`, `?user_id=Y`, `?rating_min=1&rating_max=2`, combined `?book_id=X&rating_min=3`
- Verify sort: `?sort_by=rating&sort_dir=asc` vs `?sort_by=date&sort_dir=desc`
- Verify pagination: `?page=1&per_page=1` with 3 reviews → `total_count=3`, `total_pages=3`, 1 item returned

**Test data design for MOD-02:**
- Create 5 reviews, soft-delete one before test
- Bulk delete [id1, id2, already_deleted_id, nonexistent_id=99999] → `deleted_count` should be 2
- Verify deleted reviews don't appear in subsequent `GET /admin/reviews`
- Verify list size >50 returns 422

---

## Sources

### Primary (HIGH confidence)

- Verified in codebase: `app/users/repository.py::list_paginated()` — pagination + conditional filter pattern
- Verified in codebase: `app/admin/analytics_router.py` — router-level `Depends(require_admin)` pattern
- Verified in codebase: `app/admin/router.py` + `app/admin/schemas.py` — `total_pages`, `total_count`, `per_page` admin pagination envelope
- Verified in codebase: `app/reviews/repository.py::soft_delete()` — `datetime.now(UTC)` soft-delete pattern
- Verified in codebase: `app/reviews/models.py` — `deleted_at`, `user`/`book` relationships, indexed `user_id`/`book_id`
- Verified in codebase: `app/reviews/service.py::_build_review_data()` — reviewer dict construction pattern
- Verified in STATE.md: `bulk_delete uses single UPDATE ... WHERE id IN (...) with synchronize_session="fetch"`

### Secondary (MEDIUM confidence)

- SQLAlchemy 2.x `update().where().values().execution_options(synchronize_session="fetch")` — standard async bulk write pattern; confirmed via STATE.md documentation and SQLAlchemy 2.x async API conventions

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns verified in existing codebase
- Architecture: HIGH — directly mirrors existing admin patterns (`analytics_router.py`, `admin/router.py`, `UserRepository.list_paginated()`)
- Pitfalls: HIGH — derived from codebase inspection and project-established patterns (STATE.md)

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable — no external dependencies, pure codebase research)
