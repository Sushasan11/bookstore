---
phase: 18-review-moderation-dashboard
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, admin, reviews, bulk-delete, testing, integration-tests]

# Dependency graph
requires:
  - phase: 18-01
    provides: GET /admin/reviews endpoint, BulkDeleteRequest/BulkDeleteResponse schemas, ReviewRepository.list_all_admin()
provides:
  - DELETE /admin/reviews/bulk endpoint (MOD-02)
  - ReviewRepository.bulk_soft_delete() method
  - 32 integration tests covering MOD-01 and MOD-02 completely
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - bulk_soft_delete() uses single UPDATE...WHERE IN with synchronize_session="fetch" — O(1) DB round-trips
    - httpx DELETE requests with JSON body use client.request("DELETE", url, json=...) — client.delete() does not accept json kwarg
    - review_data fixture uses a third user (user3) to avoid uq_reviews_user_book conflicts in multi-review test data

key-files:
  created:
    - tests/test_review_moderation.py
  modified:
    - app/reviews/repository.py
    - app/admin/reviews_router.py

key-decisions:
  - "bulk_soft_delete() returns rowcount — DB-reported count of actually affected rows, not input list length"
  - "Empty list guard in bulk_soft_delete() returns 0 immediately — no unnecessary DB call"
  - "httpx AsyncClient.delete() does not accept json kwarg — use client.request('DELETE', url, json=...) in tests"
  - "r5 assigned to user3 (revmod_reader) to avoid uq_reviews_user_book constraint with user2's r3 on book_a"

patterns-established:
  - "Bulk delete endpoint: router-level auth, Pydantic body validation (min/max), direct repo call, return rowcount"
  - "Integration test fixture: revmod_ email prefix for isolation, review_data fixture returns dict of all entities"

requirements-completed: [MOD-02]

# Metrics
duration: 5min
completed: 2026-02-27
---

# Phase 18 Plan 02: Bulk Delete Endpoint and Integration Tests Summary

**DELETE /admin/reviews/bulk with single-UPDATE soft-delete and 32 integration tests covering all MOD-01/MOD-02 behavior including auth, filters, sort, pagination, and best-effort bulk delete semantics**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-27T07:24:24Z
- **Completed:** 2026-02-27T07:29:24Z
- **Tasks:** 2
- **Files modified:** 3 (repository.py, reviews_router.py, new test_review_moderation.py)

## Accomplishments

- `ReviewRepository.bulk_soft_delete(review_ids)` uses a single `UPDATE ... WHERE id IN (...) AND deleted_at IS NULL` with `synchronize_session="fetch"`, returning the actual rowcount of affected rows
- `DELETE /admin/reviews/bulk` endpoint on the admin reviews router, protected by router-level `Depends(require_admin)`, accepting `BulkDeleteRequest` (min 1, max 50 IDs), returning `BulkDeleteResponse(deleted_count=int)`
- 32 integration tests across 8 test classes: auth gates (401/403), basic list behavior, pagination, all filter combinations (book_id, user_id, rating_min/max), AND-combined filters, all sort options (date/rating x asc/desc), 422 validation, and 7 bulk delete behavior tests covering best-effort semantics
- Phase 18 and the v2.1 milestone complete

## Task Commits

Each task was committed atomically:

1. **Task 1: Add bulk_soft_delete() to ReviewRepository and DELETE /admin/reviews/bulk endpoint** - `98b6192` (feat)
2. **Task 2: Create comprehensive integration tests for admin review moderation (MOD-01 and MOD-02)** - `d0c2ff2` (feat)

**Plan metadata:** *(final docs commit)*

## Files Created/Modified

- `app/reviews/repository.py` - Added `update` to sqlalchemy imports; added `bulk_soft_delete(review_ids)` method after `list_all_admin()`
- `app/admin/reviews_router.py` - Added `DELETE /bulk` endpoint (`bulk_delete_reviews`) after `list_reviews`
- `tests/test_review_moderation.py` - 32 integration tests: 8 classes, revmod_ email prefix, review_data fixture with 3 non-admin users and 5 reviews (4 active, 1 pre-deleted)

## Decisions Made

- `bulk_soft_delete()` returns `result.rowcount` (DB-reported affected rows), not `len(review_ids)` — correctly reflects best-effort semantics where missing/already-deleted IDs are silently skipped.
- Empty list guard in `bulk_soft_delete()` returns 0 immediately without hitting the DB — consistent with Pydantic min_length=1 validation but also defensive.
- Test fixture `r5` assigned to `user3` (`revmod_reader@example.com`) rather than `user2` — avoids the `uq_reviews_user_book` unique constraint since `user2` already has `r3` on `book_a`.
- `client.request("DELETE", url, json=...)` used instead of `client.delete(url, json=...)` — httpx's `AsyncClient.delete()` does not accept a `json` keyword argument.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test data unique constraint violation in review_data fixture**
- **Found during:** Task 2 (integration tests)
- **Issue:** Plan's review data spec assigned Review 3 (user2, book_a) and Review 5 (user2, book_a) to the same user+book pair, violating `uq_reviews_user_book`. First test run failed with `IntegrityError: duplicate key value violates unique constraint "uq_reviews_user_book"`.
- **Fix:** Created a third user (`revmod_reader@example.com` / `user3`) and assigned r5 to `user3` instead of `user2`. All expected filter counts remain correct (book_a has 3 active reviews: r1/user1, r3/user2, r5/user3).
- **Files modified:** tests/test_review_moderation.py
- **Verification:** All 32 tests pass.
- **Committed in:** d0c2ff2 (Task 2 commit)

**2. [Rule 1 - Bug] Used client.request("DELETE") instead of client.delete() for JSON body**
- **Found during:** Task 2 (integration tests — TestBulkDeleteAuth)
- **Issue:** `httpx.AsyncClient.delete()` does not accept a `json` keyword argument. Test failed with `TypeError: AsyncClient.delete() got an unexpected keyword argument 'json'`.
- **Fix:** Replaced all `client.delete(url, json=...)` calls with `client.request("DELETE", url, json=...)` across all 9 DELETE test cases.
- **Files modified:** tests/test_review_moderation.py
- **Verification:** All 32 tests pass including all bulk delete behavior tests.
- **Committed in:** d0c2ff2 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs in plan spec and test tooling)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep. All expected test counts preserved.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 18 complete. MOD-01 and MOD-02 both delivered and fully tested.
- v2.1 Admin Dashboard & Analytics milestone complete.
- No blockers.

---
*Phase: 18-review-moderation-dashboard*
*Completed: 2026-02-27*

## Self-Check: PASSED

- FOUND: app/reviews/repository.py
- FOUND: app/admin/reviews_router.py
- FOUND: tests/test_review_moderation.py
- FOUND: .planning/phases/18-review-moderation-dashboard/18-02-SUMMARY.md
- FOUND commit: 98b6192 (Task 1)
- FOUND commit: d0c2ff2 (Task 2)
