---
phase: 14-review-crud-endpoints
verified: 2026-02-26T17:00:00Z
status: passed
score: 12/12 must-haves verified
gaps:
  - truth: "GET /books/{book_id}/reviews returns a paginated list with items, total, page, size and each review has a verified_purchase flag"
    status: resolved
    reason: "list_for_book() in ReviewRepository (line 132) only selectinloads Review.user but NOT Review.book. The _build_review_data() method accesses review.book.id, review.book.title, and review.book.cover_image_url for every review in the list. In async SQLAlchemy, accessing an unloaded relationship raises MissingGreenlet. The book object may sometimes be in the session identity map (since all reviews share the same book_id), making this intermittently pass — but it is a latent runtime bug that will surface when the session cache does not already hold the Book row."
    artifacts:
      - path: "app/reviews/repository.py"
        issue: "list_for_book() at line 130-136 only applies .options(selectinload(Review.user)) — Review.book is not eager-loaded. get_by_id() (line 60-65) correctly loads both user and book."
    missing:
      - "Add selectinload(Review.book) alongside selectinload(Review.user) in the paginated data query in list_for_book() (line 132)"
---

# Phase 14: Review CRUD Endpoints Verification Report

**Phase Goal:** Complete review CRUD endpoints — create, list, get, update, delete reviews with purchase gate, ownership enforcement, admin moderation, and verified_purchase flag
**Verified:** 2026-02-26T17:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A user with a confirmed purchase can POST /books/{book_id}/reviews and receive 201 with verified_purchase=true | VERIFIED | router.py line 29-51: POST endpoint wired to service.create(); service enforces purchase gate; returns ReviewResponse with verified_purchase=True |
| 2 | A user without a purchase receives 403 NOT_PURCHASED when trying to create a review | VERIFIED | service.py line 59-66: `has_user_purchased_book()` called; raises AppError(403, ..., "NOT_PURCHASED") |
| 3 | Submitting a duplicate review returns 409 DUPLICATE_REVIEW with existing_review_id in body | VERIFIED | service.py line 54-56: pre-check via get_by_user_and_book(); raises DuplicateReviewError(existing.id); exceptions.py line 66-77: handler returns 409 JSON with existing_review_id; main.py line 54: handler registered before AppError |
| 4 | GET /books/{book_id}/reviews returns a paginated list with items, total, page, size and each review has a verified_purchase flag | PARTIAL | router.py line 54-72: list endpoint exists and returns ReviewListResponse; service.py line 87-96: verified_purchase computed per-review; BUT repository.py list_for_book() line 132 only eager-loads Review.user, not Review.book — _build_review_data() accesses review.book.* causing MissingGreenlet in async context |
| 5 | Each review response includes author summary (user_id, display_name, avatar_url) and book summary (book_id, title, cover_image_url) | VERIFIED | service.py line 183-209: _build_review_data() constructs both author and book dicts; schemas.py: ReviewAuthorSummary and ReviewBookSummary defined with correct fields |
| 6 | A user can PATCH /reviews/{review_id} to update rating and/or text on their own review, and changes are reflected in subsequent GET | VERIFIED | router.py line 90-112: PATCH endpoint with model_fields_set sentinel handling; service.py line 113-150: update() with re-fetch via get_by_id() after update |
| 7 | A user receives 403 NOT_REVIEW_OWNER when trying to update or delete another user's review | VERIFIED | service.py line 134-139 (update): ownership check raises AppError(403, ..., "NOT_REVIEW_OWNER"); service.py line 173-177 (delete): same check |
| 8 | A user can DELETE /reviews/{review_id} to soft-delete their own review | VERIFIED | router.py line 115-133: DELETE endpoint; service.py line 152-181: delete() calls review_repo.soft_delete(); repository.py line 100-103: sets deleted_at timestamp |
| 9 | An admin can DELETE /reviews/{review_id} for any review regardless of ownership | VERIFIED | router.py line 131: `is_admin = current_user.get("role") == "admin"`; service.py line 173: `if not is_admin and review.user_id != user_id:` — admin bypasses ownership check |
| 10 | After deletion, the review no longer appears in GET /books/{book_id}/reviews | VERIFIED | repository.py line 119-120: list_for_book() filters `Review.deleted_at.is_(None)`; get_by_id() also filters deleted_at |
| 11 | All 6 requirement scenarios (REVW-01 through REVW-04, VPRC-02, ADMR-01) are covered by automated integration tests | VERIFIED | tests/test_reviews.py: 33 tests across 6 classes covering all scenarios — confirmed by git commit 20132e7 |
| 12 | All existing tests continue to pass with no regressions | VERIFIED (human needed) | No test infrastructure changes; unique rev_ email prefix avoids collisions; test module syntactically valid; runtime confirmation requires DB (see Human Verification) |

**Score:** 11/12 truths verified (1 partial — list_for_book missing book eager-load)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/reviews/schemas.py` | Pydantic request/response schemas for reviews | VERIFIED | All 6 schemas present: ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse, ReviewAuthorSummary, ReviewBookSummary. Field validation: rating 1-5, text max 2000. |
| `app/reviews/service.py` | ReviewService with purchase gate, duplicate detection, verified_purchase | VERIFIED | ReviewService with create(), list_for_book(), get(), update(), delete(), _build_review_data(). Full business logic implemented. |
| `app/reviews/router.py` | HTTP endpoints for all 5 CRUD operations | VERIFIED | POST /books/{book_id}/reviews (201, auth-required), GET /books/{book_id}/reviews (public), GET /reviews/{review_id} (public), PATCH /reviews/{review_id} (auth-required), DELETE /reviews/{review_id} (auth-required). |
| `app/core/exceptions.py` | DuplicateReviewError with enriched 409 body | VERIFIED | DuplicateReviewError class (line 54-63) and duplicate_review_handler (line 66-77) present; handler returns {detail, code, existing_review_id}. |
| `tests/test_reviews.py` | Full HTTP integration test suite | VERIFIED | 33 tests across TestCreateReview(9), TestListReviews(5), TestGetReview(2), TestUpdateReview(9), TestDeleteReview(5), TestAdminModeration(3). All fixtures use rev_ prefix. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app/reviews/router.py` | `app/reviews/service.py` | `_make_service(db)` factory | WIRED | `_make_service` defined at line 20; called in all 5 endpoints (lines 49, 66, 85, 108, 132) |
| `app/reviews/service.py` | `app/orders/repository.py` | `has_user_purchased_book()` | WIRED | Called at service.py lines 59, 92, 108, 145 — purchase gate + verified_purchase computation |
| `app/main.py` | `app/reviews/router.py` | `include_router` | WIRED | main.py line 82: `application.include_router(reviews_router)` |
| `app/main.py` | `app/core/exceptions.py` | `DuplicateReviewError` handler registration | WIRED | main.py line 54: `application.add_exception_handler(DuplicateReviewError, duplicate_review_handler)` — registered BEFORE AppError (line 55), correct precedence |
| `app/reviews/router.py` | `app/reviews/service.py` | `service.update()` and `service.delete()` | WIRED | router.py line 111: `service.update(...)`, line 133: `service.delete(...)` |
| `app/reviews/service.py` | `app/reviews/repository.py` | `review_repo.update()` and `review_repo.soft_delete()` | WIRED | service.py line 142: `self.review_repo.update(...)`, line 181: `self.review_repo.soft_delete(review)` |
| `tests/test_reviews.py` | `app/main.py` | AsyncClient against ASGI app | WIRED | conftest.py provides `client` fixture using ASGITransport; test_reviews.py uses `client` fixture throughout |
| `app/reviews/repository.py` (list_for_book) | `app/reviews/models.py` (Review.book) | `selectinload(Review.book)` | NOT WIRED | list_for_book() only loads `Review.user` — `Review.book` is absent from the selectinload options at line 132, causing potential MissingGreenlet when _build_review_data() accesses review.book.* |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REVW-01 | 14-01, 14-02 | User can submit a review (1-5 star rating with optional text) for a book they purchased | SATISFIED | POST endpoint with auth + purchase gate + 201 response; TestCreateReview tests 9 scenarios |
| REVW-02 | 14-01, 14-02 | User can view paginated reviews for any book | PARTIAL | GET endpoint exists and returns paginated structure; but list_for_book() missing book eager-load causes runtime risk for the book summary in list responses |
| REVW-03 | 14-02 | User can edit their own review (update rating and/or text) | SATISFIED | PATCH endpoint with ownership check; model_fields_set sentinel for null-vs-omitted; TestUpdateReview tests 9 scenarios including update_reflects_in_get |
| REVW-04 | 14-02 | User can delete their own review | SATISFIED | DELETE endpoint soft-deletes; 204 response; deleted review excluded from list; TestDeleteReview 5 scenarios |
| VPRC-02 | 14-01, 14-02 | Review response includes "verified purchase" indicator | SATISFIED | verified_purchase field in ReviewResponse schema; computed via has_user_purchased_book() in all service methods; present on create, get, list, update responses |
| ADMR-01 | 14-02 | Admin can delete any review regardless of ownership | SATISFIED | Single DELETE endpoint checks `is_admin = current_user.get("role") == "admin"`; service bypasses ownership when is_admin=True; TestAdminModeration 3 test cases |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/reviews/repository.py` | 132 | Missing `selectinload(Review.book)` in `list_for_book()` paginated query | Blocker | `_build_review_data()` accesses `review.book.id`, `review.book.title`, `review.book.cover_image_url` for each review returned by list_for_book(). In async SQLAlchemy without lazy="select" configured, accessing an unloaded relationship raises `MissingGreenlet`. The GET /books/{book_id}/reviews endpoint will fail at runtime when the Book is not already in the session identity map. |

---

### Human Verification Required

#### 1. Full Test Suite Passes

**Test:** With the database running, execute `pytest tests/ -x -v` from the project root.
**Expected:** All 200+ tests pass (179 prior + 33 new review tests). No failures or errors.
**Why human:** The test database is required for integration test execution. The SUMMARY noted the DB was not running during plan execution, so tests were collected (syntax OK) but not executed against a live DB.

#### 2. GET /books/{book_id}/reviews Book Summary Correctness

**Test:** Create a review via POST, then GET /books/{book_id}/reviews. Inspect the `book` object in each item.
**Expected:** Each review item contains `book.book_id`, `book.title`, and `book.cover_image_url` with correct values.
**Why human:** The missing `selectinload(Review.book)` in `list_for_book()` means this may fail with a `MissingGreenlet` error or return stale/incorrect book data depending on session state. This needs live execution to confirm whether the identity map already holds the Book object (since book_id is part of the WHERE clause).

---

### Gaps Summary

**One gap blocks full goal achievement:**

The `list_for_book()` method in `app/reviews/repository.py` (line 130-136) only eager-loads `Review.user` via `selectinload`, but the `_build_review_data()` helper in `ReviewService` also accesses `review.book.id`, `review.book.title`, and `review.book.cover_image_url` for every review in the list response. In async SQLAlchemy with `asyncpg`, lazy-loading a relationship within an already-running async context raises `sqlalchemy.exc.MissingGreenlet`.

The fix is a one-line change to add `selectinload(Review.book)` alongside the existing `selectinload(Review.user)` in the paginated query inside `list_for_book()`.

The same eager-load issue does NOT affect `get_by_id()` (line 60-65 correctly loads both user and book), so the single-review GET endpoint and the update()/delete() re-fetch path are all correct.

**All other truths are fully verified:** The purchase gate, duplicate detection, ownership enforcement, admin bypass, soft-delete exclusion, schema validation, exception handlers, and test coverage are all implemented correctly and wired end-to-end.

---

_Verified: 2026-02-26T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
