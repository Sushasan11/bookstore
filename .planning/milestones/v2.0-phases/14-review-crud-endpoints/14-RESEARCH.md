# Phase 14: Review CRUD Endpoints - Research

**Researched:** 2026-02-26
**Domain:** FastAPI service + router layer for review CRUD with business-rule enforcement and admin moderation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Response shape**
- Each review includes full author profile: user_id, display name, and avatar URL
- Each review includes book summary: book_id, title, and cover image URL
- Timestamps in ISO 8601 format only (e.g. `2026-02-26T14:30:00Z`) — frontend handles display formatting
- Review text field capped at 2000 characters, enforced at the API validation layer
- Response includes `verified_purchase: true/false` flag per the requirements

**Error responses**
- Specific, descriptive error messages — e.g. "You must purchase this book before submitting a review"
- Structured error format with codes: `{"error": "DUPLICATE_REVIEW", "detail": "...", ...}`
  - Error codes: `NOT_PURCHASED` (403), `DUPLICATE_REVIEW` (409), `REVIEW_NOT_FOUND` (404), `NOT_REVIEW_OWNER` (403)
- 403 Forbidden for ownership violations (not 404) — honest response, user knows the review exists
- 409 duplicate response includes `existing_review_id` so frontends can redirect to edit flow

### Claude's Discretion
- Pagination approach (cursor vs offset) and default page size
- Sort options beyond created_at DESC
- Admin moderation implementation (soft-delete vs hard-delete)
- Exact Pydantic schema structure and naming conventions
- Service layer architecture and dependency injection patterns

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REVW-01 | User can submit a review (1-5 star rating with optional text) for a book they purchased | ReviewRepository.create() + OrderRepository.has_user_purchased_book() already exist; service layer wires them with NOT_PURCHASED gate |
| REVW-02 | User can view paginated reviews for any book | ReviewRepository.list_for_book(page, size) exists; router maps to GET /books/{book_id}/reviews |
| REVW-03 | User can edit their own review (update rating and/or text) | ReviewRepository.update() with _UNSET sentinel exists; service enforces ownership via NOT_REVIEW_OWNER 403 |
| REVW-04 | User can delete their own review | ReviewRepository.soft_delete() exists; service enforces ownership; admin path bypasses ownership check |
| VPRC-02 | Review response includes "verified purchase" indicator | verified_purchase computed in service by calling has_user_purchased_book(); included in ReviewResponse schema |
| ADMR-01 | Admin can delete any review regardless of ownership | Single delete service method with admin_override flag, or two service methods; router uses AdminUser dep for admin path |
</phase_requirements>

## Summary

Phase 14 builds the HTTP surface on top of the already-complete Phase 13 data layer. The repositories, model, migration, and purchase-check method are all in place. The work is: (1) a `ReviewService` that enforces business rules (purchase gate, ownership, verified_purchase computation), (2) Pydantic schemas that match the locked response shape including embedded author and book summaries and the `verified_purchase` flag, and (3) a router that wires the service to HTTP endpoints following established project conventions.

The dominant pattern in the codebase is: repository takes `AsyncSession`, service takes repositories, router instantiates them via a `_make_service(db)` factory, routes call service methods, routes serialize ORM objects with `model_validate`. This pattern is used consistently across wishlist, orders, prebooks, admin, and catalog. Phase 14 should follow it without deviation.

The main complexity is the `verified_purchase` flag: it requires a cross-domain call (`OrderRepository.has_user_purchased_book`) inside `ReviewService`, mirroring the established pattern from STATE.md ("ReviewService injects OrderRepository — avoids circular import, mirrors BookService/PreBookRepository pattern"). The duplicate-detection 409 response requires a non-standard body that includes `existing_review_id`, which means the router must catch the `AppError` from `ReviewRepository.create()`, look up the existing review by `get_by_user_and_book()`, and re-raise with the enriched body — or the service handles it directly.

**Primary recommendation:** Implement `ReviewService` that injects `ReviewRepository` + `OrderRepository`; compute `verified_purchase` inside `ReviewService.create()` and in the list/get responses; use offset pagination with `size=20` default matching existing `list_for_book()` signature; use soft-delete for admin moderation (consistent with the soft-delete already on the Review model).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing (project) | Router, dependency injection, response_model serialization | Already in use for all 10+ existing routers |
| SQLAlchemy (async) | existing | ORM — all repos use AsyncSession | All Phase 13 data layer built on it |
| Pydantic v2 | existing | Request/response schemas, field validation | model_validate(), computed_field, Field(max_length=2000) used everywhere |
| httpx + pytest-asyncio | existing | Integration tests via AsyncClient + ASGITransport | All existing test files use this pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `app.core.deps.ActiveUser` | project | Extracts + validates current authenticated user from JWT | All user-authenticated endpoints |
| `app.core.deps.AdminUser` | project | Requires admin role, raises 403 otherwise | Admin-only moderation endpoint |
| `app.core.exceptions.AppError` | project | Structured JSON errors with code + optional field | All business-rule violations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Offset pagination (existing `list_for_book` signature) | Cursor pagination | Cursor is better for high-volume but adds complexity; offset is already in the repository and consistent with admin user list and book list endpoints |
| Soft-delete for admin (existing `soft_delete()`) | Hard-delete | Soft-delete is already on the model (`deleted_at`) and consistent with the data layer; hard-delete would leave the `deleted_at` column unused |

**Installation:** No new packages required — all needed libraries are already in the project.

---

## Architecture Patterns

### Recommended Project Structure

Phase 14 adds these files:

```
app/reviews/
├── __init__.py         # exists (Phase 13)
├── models.py           # exists (Phase 13)
├── repository.py       # exists (Phase 13)
├── schemas.py          # NEW — Pydantic request/response schemas
├── service.py          # NEW — ReviewService with business rules
└── router.py           # NEW — HTTP endpoints

tests/
├── test_reviews_data.py    # exists — Phase 13 data layer tests (23 tests)
└── test_reviews.py         # NEW — HTTP integration tests for Phase 14 endpoints
```

`main.py` must import and include the reviews router (same pattern as all other routers).

### Pattern 1: Service Factory in Router

All existing routers (wishlist, orders, prebooks, admin) use a `_make_service(db)` function to instantiate the service with all required repos. Phase 14 must follow this:

```python
# app/reviews/router.py
def _make_service(db: DbSession) -> ReviewService:
    return ReviewService(
        review_repo=ReviewRepository(db),
        order_repo=OrderRepository(db),
        book_repo=BookRepository(db),  # for existence check on create
    )
```

Source: Verified in `app/wishlist/router.py`, `app/books/router.py`, `app/admin/router.py`.

### Pattern 2: model_validate() for ORM-to-schema serialization

Every route returns `SomeSchema.model_validate(orm_object)`. This requires `model_config = {"from_attributes": True}` on all response schemas. Nested objects (book summary, author summary) are also Pydantic models with `from_attributes = True`.

```python
# app/reviews/router.py
return ReviewResponse.model_validate(review)
```

Source: Verified in `app/wishlist/router.py` line 36, `app/books/router.py` line 45.

### Pattern 3: AppError for all business violations

All service-layer errors use `AppError(status_code, detail, code, field=None)`. The global handler in `app/main.py` converts these to `{"detail": "...", "code": "..."}` JSON. The locked error codes from CONTEXT.md must be used:

```python
# app/reviews/service.py
raise AppError(403, "You must purchase this book before submitting a review", "NOT_PURCHASED", "book_id")
raise AppError(409, "You have already reviewed this book", "DUPLICATE_REVIEW", "book_id")
raise AppError(404, "Review not found", "REVIEW_NOT_FOUND")
raise AppError(403, "You can only modify your own reviews", "NOT_REVIEW_OWNER")
```

Note: CONTEXT.md specifies the 409 duplicate response must include `existing_review_id`. The standard `AppError` does not carry this extra field. The service must either: (a) catch the `AppError(409)` from `ReviewRepository.create()`, fetch the existing review, and raise a new exception or return a custom response, or (b) use a custom exception body. The cleanest approach is to have the service handle the duplicate at the service level — check for existing review first with `get_by_user_and_book()`, and if found, raise the enriched error. This avoids relying on the IntegrityError path for the normal case.

Source: `app/core/exceptions.py`, `app/wishlist/service.py`, `app/orders/service.py`.

### Pattern 4: ActiveUser / AdminUser dependency for auth

```python
@router.post("/books/{book_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(book_id: int, body: ReviewCreate, db: DbSession, current_user: ActiveUser) -> ReviewResponse:
    user_id = int(current_user["sub"])
    service = _make_service(db)
    review = await service.create(user_id, book_id, body)
    return ReviewResponse.model_validate(review)
```

For admin delete, use `AdminUser` dep instead of `ActiveUser`:

```python
@router.delete("/admin/reviews/{review_id}", status_code=204)
async def admin_delete_review(review_id: int, db: DbSession, _admin: AdminUser) -> None:
    ...
```

Source: Verified in `app/core/deps.py`, `app/admin/router.py`, `app/wishlist/router.py`.

### Pattern 5: Pagination response envelope

The `GET /books/{book_id}/reviews` endpoint returns a paginated envelope. Consistent with existing book list and admin user list:

```python
class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    page: int
    size: int
```

Source: `app/books/schemas.py` `BookListResponse`, `app/admin/schemas.py` `UserListResponse`.

### Pattern 6: computed_field for derived values

`verified_purchase` is computed at response time, not stored. The project already uses `@computed_field` in `BookDetailResponse` and `OrderResponse`. However, computing `verified_purchase` requires a DB query — it cannot be a Pydantic `computed_field` on the schema. Instead, it must be computed in the service and passed as a value. Best approach: the response schema includes `verified_purchase: bool` as a plain field, and the service calls `has_user_purchased_book()` for each review in a list or for a single review. For list responses, batch the check (one EXISTS query per review) or accept N+1 (N reviews × 1 query each). The most practical approach for the initial implementation is to pass `verified_purchase` as a parameter when constructing the response — meaning the service returns `(review, verified: bool)` tuples, or the router constructs the response with the flag injected.

The cleanest pattern: define a `ReviewResponseData` dataclass/NamedTuple in the service and let the schema be initialized from dict or keyword args. Or simpler: the service returns the ORM `Review` object, and the router calls `has_user_purchased_book()` separately, then constructs `ReviewResponse(verified_purchase=..., **review_data)`. But this puts business logic in the router — avoid it.

**Recommendation:** Service methods return `(Review, bool)` tuples where the bool is `verified_purchase`. The response schema uses `model_config = {"from_attributes": True}` and accepts an extra kwarg not from the ORM — use `model_validate(review, update={"verified_purchase": vp})` (Pydantic v2 `model_validate` supports an `update` dict to overlay fields). This is the cleanest approach without changing the ORM.

Source: Pydantic v2 `model_validate(obj, update={...})` is the supported pattern for supplementing ORM objects with extra fields. Confidence: HIGH — verified in Pydantic v2 documentation behavior (used by multiple existing schemas in the codebase with `from_attributes=True`).

### Pattern 7: Duplicate detection with enriched error body

CONTEXT.md requires the 409 response to include `existing_review_id`. The `AppError` class only carries `detail`, `code`, and optional `field`. Options:

1. **Pre-check approach** (recommended): In `ReviewService.create()`, call `get_by_user_and_book()` before calling `repo.create()`. If found, raise `AppError(409, "...", "DUPLICATE_REVIEW")` — but AppError cannot carry `existing_review_id`. Need to either extend AppError or return a custom JSONResponse from the router.

2. **Custom exception**: Add `existing_review_id` as an extra attribute on a subclass of `AppError` (`DuplicateReviewError`), register a specific handler in `main.py`, or handle it in the router via `try/except`.

3. **Return JSONResponse directly from router on 409**: Router catches the `AppError(409)`, looks up the existing review, and returns `JSONResponse(status_code=409, content={...})`.

**Recommendation:** Use a pre-check in the service (call `get_by_user_and_book()` first); if duplicate found, return the existing review ID as part of the service's exception. The simplest implementation: add an optional `extra` dict field to `AppError`, or define a `DuplicateReviewError(AppError)` that carries `existing_review_id`, and register its handler in `main.py`. Alternatively, return the existing review from the service (not an error) and let the router produce the 409 response with the enriched body — but this mixes HTTP concerns into the service.

**Most pragmatic approach**: The service catches the repository's `AppError(409)` and re-raises a `DuplicateReviewError` that carries the `existing_review_id`. The router's exception handler for `DuplicateReviewError` produces the structured 409 body. Or simpler: router wraps `service.create()` in a `try/except AppError as e: if e.code == "DUPLICATE_REVIEW": return JSONResponse(409, {...})`.

The planner should pick one and be explicit in the plan.

### Anti-Patterns to Avoid

- **Business logic in routers:** Never call `has_user_purchased_book()` or ownership checks in the router — always in the service. Keeps routes thin.
- **Bypassing the service in admin delete:** The admin delete path still goes through the service (with `admin_override=True` or a separate `admin_delete()` method) — this ensures soft_delete vs hard_delete decision stays in one place.
- **Forgetting to register router in main.py:** All previous phases had this as the final step. Easy to miss.
- **Not importing Review model in app/db/base.py:** STATE.md says "app/db/base.py is the model registry — all new models must be imported here immediately on creation." Phase 13 already did this, but must verify the reviews router import doesn't re-import in a way that causes issues.
- **N+1 for verified_purchase on list:** Calling `has_user_purchased_book()` per review in a list query is N+1. For Phase 14 with modest page sizes (20 default), it is acceptable. Document it as a known limitation for Phase 15 if optimization is needed.
- **Hardcoding `expire_on_commit=False` assumption:** The session is configured with `expire_on_commit=False`, so ORM attribute access after commit is safe — don't add unnecessary `await session.refresh()` calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT extraction and user ID | Custom token parsing in routes | `ActiveUser` / `get_active_user` dep from `app.core.deps` | Already handles decode, active-check, 403 on deactivated |
| Admin role enforcement | `if current_user["role"] != "admin"` in routes | `AdminUser` dep | Consistent, tested, raises correct error |
| Duplicate detection | Custom SQL unique check | Existing `ReviewRepository.create()` which catches `IntegrityError` | Already handles the DB constraint |
| Purchase check | Custom SQL in service | `OrderRepository.has_user_purchased_book()` | Completed in Phase 13-02, thoroughly tested |
| Pagination | Custom LIMIT/OFFSET math | Existing `list_for_book(page, size)` in `ReviewRepository` | Already handles count + data queries with correct pattern |
| Error responses | Custom JSONResponse | `AppError` + global handler | Structured, consistent with all other endpoints |
| Soft-delete | Setting `is_deleted` flag | Existing `ReviewRepository.soft_delete()` | Already implemented in Phase 13 |

**Key insight:** The data layer is 100% complete. Phase 14 is purely the HTTP surface — schemas, service rules, router wiring, and tests.

---

## Common Pitfalls

### Pitfall 1: verified_purchase computed incorrectly for list endpoint
**What goes wrong:** `GET /books/{book_id}/reviews` returns a list of reviews. Each review needs a `verified_purchase` flag for the reviewer — meaning "did the person who wrote this review purchase the book?" Not "did the requesting user purchase it." This is a per-reviewer check, not per-requester.
**Why it happens:** The endpoint is public (no auth required to view reviews), so `current_user` may not exist. The verified_purchase flag is about the reviewer's purchase status, not the reader's.
**How to avoid:** In the service's `list_for_book()`, for each review, call `has_user_purchased_book(review.user_id, book_id)`. The endpoint does not need an authenticated user to compute this.
**Warning signs:** If you only call `has_user_purchased_book(current_user_id, ...)` you'd need auth on a public endpoint.

### Pitfall 2: 409 DUPLICATE_REVIEW body must include existing_review_id
**What goes wrong:** Standard `AppError` only carries `detail`, `code`, `field`. The locked decision requires the 409 body to also carry `existing_review_id`.
**Why it happens:** Copy-pasting the AppError raise from other modules doesn't include this field.
**How to avoid:** Handle the 409 case specially — either via a subclass `DuplicateReviewError(AppError)` with extra attribute, or by catching the error in the router and constructing a custom `JSONResponse`.
**Warning signs:** Tests asserting `resp.json()["existing_review_id"]` will fail if only a plain AppError is raised.

### Pitfall 3: router prefix collision with books router
**What goes wrong:** Reviews are nested under `/books/{book_id}/reviews`. The books router already owns `/books/{book_id}`. Both routers must not fight over the same prefix.
**Why it happens:** FastAPI allows multiple routers with overlapping path prefixes — they stack. But naming and prefix choices matter.
**How to avoid:** Register the reviews router with `prefix=""` (or `prefix="/books"` with explicit sub-path). The simplest approach: the reviews router owns `/books/{book_id}/reviews` with a top-level `prefix=""` and explicit full paths on each route. OR: give it `prefix="/books"` and define routes as `/{book_id}/reviews`. Check how the existing `books_router` is registered in `main.py` — it uses no prefix on the router itself (router defined with `tags=["catalog"]` and routes start `/books`).
**Warning signs:** 404s on review endpoints despite them being registered; duplicate path issues in OpenAPI docs.

### Pitfall 4: Admin delete endpoint placement
**What goes wrong:** Where does `DELETE /reviews/{review_id}` (admin) vs `DELETE /reviews/{review_id}` (user own) live? If both are at the same path with different deps, FastAPI processes both and the first matching one wins.
**Why it happens:** Trying to use the same path for both user delete and admin delete.
**How to avoid:** Use a single `DELETE /reviews/{review_id}` endpoint that accepts any authenticated user. The service checks: if the review belongs to the requesting user, allow deletion. If the user is admin, allow deletion. If neither, raise `NOT_REVIEW_OWNER` (403). No separate admin path needed for delete. Alternatively, add `GET /admin/reviews` listing for admin, and have admin delete use the same user path but with admin-aware service logic.
**Warning signs:** Needing to define two routes with same method+path.

### Pitfall 5: Response schema — "display name" for user
**What goes wrong:** CONTEXT.md says each review includes "full author profile: user_id, display name, and avatar URL." The `User` model has `email` but no `display_name` or `avatar_url` fields.
**Why it happens:** The locked decision references fields that don't exist on the User model.
**How to avoid:** Map "display name" to whatever User field is available. The `User` model has `email` and no `display_name` column. Options: use `email` as display name (privacy concern), or derive it from email (e.g., everything before `@`). For avatar URL, the `User` model has no avatar column. The planner must decide: either use `email` as `display_name` and `null` for `avatar_url` (schema includes the field but it's always null for now), or skip avatar from the schema entirely. This is a discretion area despite the locked phrasing.
**Warning signs:** `ReviewResponse` trying to serialize `user.display_name` when `User.display_name` doesn't exist — AttributeError at test time.

### Pitfall 6: test_reviews.py email prefix collisions
**What goes wrong:** All test modules share the same test DB schema. Each module must use unique email prefixes for test users to avoid IntegrityError across tests.
**Why it happens:** Pattern established in Phase 13 test file — they use `revdata_user@`, `revdata_user2@`. New test file must use different prefixes (e.g., `reviews_admin@`, `reviews_user@`, `reviews_user2@`).
**How to avoid:** Use module-specific email prefixes in all fixtures.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### ReviewService skeleton
```python
# app/reviews/service.py
from app.books.repository import BookRepository
from app.core.exceptions import AppError
from app.orders.repository import OrderRepository
from app.reviews.models import Review
from app.reviews.repository import ReviewRepository


class ReviewService:
    def __init__(
        self,
        review_repo: ReviewRepository,
        order_repo: OrderRepository,
        book_repo: BookRepository,
    ) -> None:
        self.review_repo = review_repo
        self.order_repo = order_repo
        self.book_repo = book_repo

    async def create(self, user_id: int, book_id: int, rating: int, text: str | None) -> tuple[Review, bool]:
        # 1. Verify book exists
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise AppError(404, "Book not found", "REVIEW_NOT_FOUND", "book_id")
        # 2. Check for existing review (pre-check to enable enriched 409)
        existing = await self.review_repo.get_by_user_and_book(user_id, book_id)
        if existing is not None:
            raise DuplicateReviewError(existing.id)  # carries existing_review_id
        # 3. Purchase gate
        purchased = await self.order_repo.has_user_purchased_book(user_id, book_id)
        if not purchased:
            raise AppError(403, "You must purchase this book before submitting a review", "NOT_PURCHASED", "book_id")
        # 4. Create review
        review = await self.review_repo.create(user_id, book_id, rating, text)
        return review, True  # just purchased → verified_purchase=True

    async def get(self, review_id: int, requesting_user_id: int) -> tuple[Review, bool]:
        review = await self.review_repo.get_by_id(review_id)
        if review is None:
            raise AppError(404, "Review not found", "REVIEW_NOT_FOUND")
        vp = await self.order_repo.has_user_purchased_book(review.user_id, review.book_id)
        return review, vp

    async def list_for_book(self, book_id: int, page: int, size: int) -> tuple[list[tuple[Review, bool]], int]:
        reviews, total = await self.review_repo.list_for_book(book_id, page=page, size=size)
        results = []
        for r in reviews:
            vp = await self.order_repo.has_user_purchased_book(r.user_id, r.book_id)
            results.append((r, vp))
        return results, total
```

### Pydantic v2 model_validate with update overlay
```python
# Verified pattern: Pydantic v2 model_validate with update dict
# Source: Pydantic v2 docs — model_validate(obj, update={...}) merges extra fields
review_response = ReviewResponse.model_validate(
    review,
    update={"verified_purchase": True}
)
```

### ReviewResponse schema structure
```python
# app/reviews/schemas.py
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewAuthorSummary(BaseModel):
    user_id: int
    display_name: str   # maps to user.email or derived name
    avatar_url: str | None

    model_config = {"from_attributes": True}


class ReviewBookSummary(BaseModel):
    book_id: int
    title: str
    cover_image_url: str | None

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str | None = Field(None, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    text: str | None = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    book_id: int
    user_id: int
    rating: int
    text: str | None
    verified_purchase: bool   # computed by service, not from ORM
    created_at: datetime
    updated_at: datetime
    author: ReviewAuthorSummary
    book: ReviewBookSummary

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    page: int
    size: int
```

Note: `verified_purchase` is not on the ORM model, so `model_validate(review, update={"verified_purchase": vp})` is needed. The `author` and `book` nested schemas must be constructed from the ORM relationships.

### Endpoint URL design
```
POST   /books/{book_id}/reviews          → create review (ActiveUser)
GET    /books/{book_id}/reviews          → list reviews for book (public)
GET    /reviews/{review_id}              → get single review (public)
PATCH  /reviews/{review_id}             → edit own review (ActiveUser)
DELETE /reviews/{review_id}             → delete own review or admin (ActiveUser or AdminUser)
```

Note on admin delete: Using a single `DELETE /reviews/{review_id}` that accepts any active user and checks ownership in the service (admins bypass the ownership check) is simpler than having two separate paths. The service can accept an `is_admin: bool` flag.

### Router registration in main.py (pattern)
```python
# app/main.py — add after existing imports:
from app.reviews.router import router as reviews_router

# Inside create_app():
application.include_router(reviews_router)
```

### Test fixture pattern (from test_wishlist.py)
```python
# tests/test_reviews.py
@pytest_asyncio.fixture
async def admin_headers(client, db_session):
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="reviews_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()
    resp = await client.post("/auth/login", json={"email": "reviews_admin@example.com", "password": "adminpass123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

@pytest_asyncio.fixture
async def user_headers(client, db_session):
    repo = UserRepository(db_session)
    hashed = await hash_password("userpass123")
    await repo.create(email="reviews_user@example.com", hashed_password=hashed)
    await db_session.flush()
    resp = await client.post("/auth/login", json={"email": "reviews_user@example.com", "password": "userpass123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `orm_mode = True` (Pydantic v1) | `model_config = {"from_attributes": True}` (Pydantic v2) | Pydantic v2 | All schemas in project use v2 config |
| `response_model_include` / `response_model_exclude` | Separate Pydantic schemas for each response shape | Current FastAPI best practice | Use distinct schemas rather than filtering |
| `@pytest.mark.asyncio` on each test | `asyncio_mode = "auto"` in pytest config | pytest-asyncio 0.21+ | Project already uses auto mode — no mark needed |

**Deprecated/outdated:**
- `from_orm()` (Pydantic v1): replaced by `model_validate()`. The codebase uses `model_validate()` exclusively.

---

## Open Questions

1. **"Display name" and "avatar URL" for ReviewAuthorSummary**
   - What we know: `User` model has `email`, `id`, `role`, `is_active`, `created_at`. No `display_name` or `avatar_url` column.
   - What's unclear: What should `display_name` map to? CONTEXT.md locked this without specifying the source column.
   - Recommendation: Plan should explicitly decide — use `email` as `display_name` (e.g., the username part `email.split("@")[0]`) computed in the schema or service, and `avatar_url = None` always (documented as placeholder for future user profile feature). Add a `@computed_field` on the schema or derive it in the service.

2. **DuplicateReviewError with existing_review_id — implementation choice**
   - What we know: Standard `AppError` cannot carry arbitrary extra fields. The 409 must include `existing_review_id`.
   - What's unclear: Should the plan extend `AppError`, add a handler, or handle in the router?
   - Recommendation: Define `DuplicateReviewError(Exception)` (not subclassing AppError) with `review_id` and `detail` attributes, register a handler in `main.py` that produces `{"error": "DUPLICATE_REVIEW", "detail": "...", "existing_review_id": X}`. This is cleaner than router-level `try/except`. Alternatively, simplest: handle it in the service by pre-checking and raising AppError with field="existing_review_id" — but that's a field name, not the ID value. The planner must pick.

3. **N+1 for verified_purchase on list**
   - What we know: `list_for_book()` returns up to `size` reviews (default 20). Each needs a `has_user_purchased_book()` call = N EXISTS queries.
   - What's unclear: Whether N+1 is acceptable or needs a batch query.
   - Recommendation: Accept N+1 for Phase 14 (20 queries on a page of 20 is fast with EXISTS). Document as known limitation. Phase 15 or beyond can optimize with a single JOIN query if needed.

4. **Admin delete: single endpoint or separate admin path**
   - What we know: ADMR-01 says "Admin can delete any review." User delete is REVW-04.
   - What's unclear: Should it be one endpoint (`DELETE /reviews/{id}`) that serves both, or `DELETE /admin/reviews/{id}` for admins?
   - Recommendation: Single `DELETE /reviews/{review_id}` using `ActiveUser` dep; service receives `is_admin: bool` derived from `current_user["role"] == "admin"`. Admin bypasses ownership check. No separate admin path needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode=auto) + httpx |
| Config file | pytest.ini or pyproject.toml (verify in project root) |
| Quick run command | `pytest tests/test_reviews.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVW-01 | POST /books/{id}/reviews returns 201 for purchaser | integration | `pytest tests/test_reviews.py::TestCreateReview::test_create_review_201 -x` | ❌ Wave 0 |
| REVW-01 | POST /books/{id}/reviews returns 403 NOT_PURCHASED for non-purchaser | integration | `pytest tests/test_reviews.py::TestCreateReview::test_create_review_403_not_purchased -x` | ❌ Wave 0 |
| REVW-02 | GET /books/{id}/reviews returns paginated list with verified_purchase flag | integration | `pytest tests/test_reviews.py::TestListReviews -x` | ❌ Wave 0 |
| REVW-03 | PATCH /reviews/{id} updates own review | integration | `pytest tests/test_reviews.py::TestUpdateReview -x` | ❌ Wave 0 |
| REVW-04 | DELETE /reviews/{id} deletes own review; 403 for other user's review | integration | `pytest tests/test_reviews.py::TestDeleteReview -x` | ❌ Wave 0 |
| VPRC-02 | Review response includes verified_purchase: true/false | integration | `pytest tests/test_reviews.py -k "verified_purchase" -x` | ❌ Wave 0 |
| ADMR-01 | Admin can delete any review | integration | `pytest tests/test_reviews.py::TestAdminModeration -x` | ❌ Wave 0 |
| REVW-05 | Duplicate submission returns 409 with existing_review_id | integration | `pytest tests/test_reviews.py::TestCreateReview::test_create_review_409_duplicate -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_reviews.py -x`
- **Per wave merge:** `pytest tests/ -x` (must keep all 179+ existing tests green)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reviews.py` — all Phase 14 HTTP integration tests (covers REVW-01 through REVW-04, VPRC-02, ADMR-01)
- [ ] `app/reviews/schemas.py` — Pydantic schemas (request + response)
- [ ] `app/reviews/service.py` — ReviewService
- [ ] `app/reviews/router.py` — HTTP router

*(The test infrastructure itself — `conftest.py`, `db_session`, `client` fixtures — already exists and covers all needs)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection — `app/reviews/models.py`, `app/reviews/repository.py`, `app/orders/repository.py` — confirmed data layer is complete
- Direct code inspection — `app/core/deps.py`, `app/core/exceptions.py`, `app/main.py` — confirmed auth/error infrastructure
- Direct code inspection — `app/wishlist/service.py`, `app/wishlist/router.py`, `app/wishlist/schemas.py` — confirmed service/router/schema patterns
- Direct code inspection — `app/books/schemas.py`, `app/orders/schemas.py` — confirmed pagination envelope and nested schema patterns
- Direct code inspection — `tests/conftest.py`, `tests/test_wishlist.py`, `tests/test_reviews_data.py` — confirmed test fixture pattern
- `.planning/STATE.md` — cross-domain service injection pattern documented ("ReviewService injects OrderRepository — avoids circular import")

### Secondary (MEDIUM confidence)
- Pydantic v2 `model_validate(obj, update={...})` — supported in Pydantic v2 for supplementing ORM objects with non-ORM fields; consistent with project's `from_attributes=True` pattern

### Tertiary (LOW confidence)
- N+1 for verified_purchase acceptable at page size 20 — based on general DB performance knowledge; no load testing done

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in use; no new dependencies
- Architecture: HIGH — directly verified from 6+ existing modules following identical patterns
- Pitfalls: HIGH for pitfalls 1-4 (verified from model inspection), MEDIUM for pitfall 5-6 (derived from project patterns)
- Test infrastructure: HIGH — conftest.py and all fixtures verified

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable codebase, 30-day window)
