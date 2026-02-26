---
phase: 14-review-crud-endpoints
plan: 01
subsystem: api
tags: [fastapi, pydantic, reviews, purchase-gate, verified-purchase]

# Dependency graph
requires:
  - phase: 13-review-data-layer
    provides: ReviewRepository with full CRUD, aggregates, and soft-delete support
  - phase: 13-review-data-layer
    provides: has_user_purchased_book() in OrderRepository for purchase gate
provides:
  - POST /books/{book_id}/reviews endpoint with auth, purchase gate, and duplicate detection
  - GET /books/{book_id}/reviews public paginated endpoint with verified_purchase per review
  - GET /reviews/{review_id} public single-review endpoint
  - ReviewService with create(), list_for_book(), get(), _build_review_data()
  - DuplicateReviewError exception with enriched 409 body (existing_review_id)
  - All 6 Pydantic schemas: ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse, ReviewAuthorSummary, ReviewBookSummary
affects:
  - 14-review-crud-endpoints (Plan 14-02 builds edit/delete/admin endpoints on top of this)
  - 15-book-detail-aggregates (uses ReviewRepository.get_aggregates())

# Tech tracking
tech-stack:
  added: []
  patterns:
    - _make_service(db) factory pattern for router-level service instantiation
    - Plain dict construction via _build_review_data() for ReviewResponse.model_validate() — avoids from_attributes complexity with mismatched field names
    - DuplicateReviewError as separate exception from AppError for enriched 409 body with non-standard field

key-files:
  created:
    - app/reviews/schemas.py
    - app/reviews/service.py
    - app/reviews/router.py
  modified:
    - app/core/exceptions.py
    - app/main.py

key-decisions:
  - "DuplicateReviewError is a separate exception (not AppError subclass) — its 409 body has existing_review_id which AppError handler cannot produce"
  - "_build_review_data() builds plain dict instead of using model_validate(orm_obj, update={}) — cleaner handling of mismatched ORM field names (book.id -> book_id, user.email -> display_name)"
  - "display_name derived from email.split('@')[0] — User model has no display_name column"
  - "avatar_url is always None — no profile image feature yet"
  - "GET /books/{book_id}/reviews and GET /reviews/{review_id} are public — no auth required to read reviews"
  - "DuplicateReviewError handler registered before AppError in main.py — more specific handler must precede general one"

patterns-established:
  - "_make_service(db) factory: instantiate service with all repos bound to current session (matches wishlist pattern)"
  - "Purchase gate pattern: pre-check via get_by_user_and_book() before create() — avoids IntegrityError, enables enriched 409"
  - "verified_purchase computed per review via N+1 OrderRepository.has_user_purchased_book() calls — accepted for page size <= 20"

requirements-completed: [REVW-01, REVW-02, VPRC-02]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 14 Plan 01: Review CRUD Endpoints Summary

**POST /books/{book_id}/reviews with purchase gate + duplicate detection, GET list and single endpoints, DuplicateReviewError 409 with existing_review_id, and verified_purchase flag on every response**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T16:13:06Z
- **Completed:** 2026-02-26T16:15:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ReviewService enforces purchase gate (403 NOT_PURCHASED), book existence (404 BOOK_NOT_FOUND), and pre-checks for duplicate before DB write (raises DuplicateReviewError with existing_review_id for enriched 409)
- Three review endpoints registered: POST (auth-required) and GET list (public) at /books/{book_id}/reviews, plus GET single at /reviews/{review_id}
- All 6 Pydantic schemas created with proper field validation (rating 1-5, text max 2000 chars), including ReviewAuthorSummary and ReviewBookSummary for nested response objects
- DuplicateReviewError handler registered in main.py before AppError handler, producing structured 409 with existing_review_id field for frontend redirect-to-edit flows

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DuplicateReviewError, Pydantic schemas, and ReviewService** - `147340f` (feat)
2. **Task 2: Create review router, register in main.py, and wire DuplicateReviewError handler** - `c4f8f93` (feat)

## Files Created/Modified
- `app/reviews/schemas.py` - ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse, ReviewAuthorSummary, ReviewBookSummary
- `app/reviews/service.py` - ReviewService with create(), list_for_book(), get(), _build_review_data()
- `app/reviews/router.py` - POST /books/{book_id}/reviews, GET /books/{book_id}/reviews, GET /reviews/{review_id}
- `app/core/exceptions.py` - Added DuplicateReviewError class and duplicate_review_handler
- `app/main.py` - Added DuplicateReviewError handler registration and reviews_router include

## Decisions Made
- DuplicateReviewError is a separate exception class (not an AppError subclass) because its 409 response body contains `existing_review_id` — a field that the generic AppError handler cannot produce
- _build_review_data() constructs a plain dict rather than using model_validate(orm_obj, update={}) — this is cleaner when ORM field names differ from schema field names (book.id becomes book_id, user.email becomes display_name)
- display_name derived from email.split('@')[0] since User model has no display_name column
- DuplicateReviewError handler is registered before AppError handler in main.py (more specific handler must precede general one for FastAPI exception dispatch)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All review read/create endpoints are operational and ready for Plan 14-02 (edit/delete/admin endpoints)
- ReviewService.get() is already implemented and will be used by PATCH and DELETE endpoints in 14-02
- ReviewUpdate schema is already defined in schemas.py for use in 14-02
- No blockers

---
*Phase: 14-review-crud-endpoints*
*Completed: 2026-02-26*
