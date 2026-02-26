---
phase: 08-wishlist
plan: 02
subsystem: testing
tags: [pytest, httpx, asyncio, wishlist, integration-tests]

# Dependency graph
requires:
  - phase: 08-01
    provides: "WishlistItem model, WishlistRepository (add/list/delete), WishlistService, POST/GET/DELETE /wishlist endpoints"
  - phase: 06-cart
    provides: "module-scoped email prefix pattern, pytest_asyncio.fixture pattern, admin_headers/user_headers fixture shape"
provides:
  - "tests/test_wishlist.py: 13 integration tests covering ENGM-01 and ENGM-02"
  - "TestAddToWishlist: success (201 + structure), duplicate (409), nonexistent (404), unauthenticated (401)"
  - "TestViewWishlist: items with stock_quantity (200), empty (200), unauth (401), user isolation, multi-item ordering"
  - "TestRemoveFromWishlist: success (204 + empty list), not on wishlist (404), unauthenticated (401)"
affects: [integration-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "wishlist_ email prefix for all fixture users — avoids collisions with other test modules"
    - "TestClass grouping by HTTP verb/behavior (TestAddToWishlist, TestViewWishlist, TestRemoveFromWishlist)"
    - "_add_to_wishlist helper asserts 201 — same helper pattern as _add_item in test_cart.py"

key-files:
  created:
    - tests/test_wishlist.py
  modified:
    - app/wishlist/repository.py

key-decisions:
  - "get_all_for_user adds id DESC secondary tiebreaker — added_at timestamps are identical on fast test inserts; without id DESC the ORDER BY is non-deterministic and the ordering test is flaky"
  - "Ordering test uses strict book_id assertion (not set membership) because id DESC tiebreaker makes the sort fully deterministic even with identical timestamps"
  - "sample_book and sample_book2 fixtures use default stock=0 — wishlist does not require stock; tests verify stock_quantity appears in response without setting a non-zero value"

patterns-established:
  - "Auto-fix Rule 1: add stable secondary sort key (id DESC) when primary sort key (timestamp) is non-unique — same lesson as test_list_books_sort_created_at"

requirements-completed: [ENGM-01, ENGM-02]

# Metrics
duration: 6min
completed: 2026-02-26
---

# Phase 8 Plan 2: Wishlist Integration Tests Summary

**13 integration tests covering ENGM-01 and ENGM-02 via httpx AsyncClient: add/duplicate/nonexistent/unauth for POST, list/empty/unauth/isolation/ordering for GET, remove/not-found/unauth for DELETE — all 121 tests pass**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-25T19:12:38Z
- **Completed:** 2026-02-25T19:18:47Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- 13 integration tests covering all ENGM-01 and ENGM-02 behaviors across 3 test classes
- TestAddToWishlist verifies full response structure (id, book_id, added_at, embedded book with stock_quantity and cover_image_url)
- TestViewWishlist proves user isolation (User B sees empty wishlist after User A adds books) and descending ordering stability
- Auto-fixed non-deterministic ORDER BY with id DESC tiebreaker; full suite of 121 tests passes (108 existing + 13 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wishlist integration tests (tests/test_wishlist.py) + repo ordering fix** - `7cf1a8e` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `tests/test_wishlist.py` - 13 integration tests in TestAddToWishlist, TestViewWishlist, TestRemoveFromWishlist
- `app/wishlist/repository.py` - Added id DESC secondary tiebreaker to get_all_for_user ORDER BY clause

## Decisions Made
- `get_all_for_user` secondary sort `id DESC` added — inserted items within the same millisecond share identical `added_at` values making strict ORDER BY flaky; `id` is always unique and monotonically increasing, making the sort fully deterministic
- `sample_book` and `sample_book2` fixtures do NOT set stock via PATCH /stock — wishlist has no stock requirement, and the test verifies `stock_quantity` appears in the response (value may be 0)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed non-deterministic ORDER BY in get_all_for_user**
- **Found during:** Task 1 (test execution — ordering test failed)
- **Issue:** `ORDER BY added_at DESC` is non-deterministic when two items are inserted within the same millisecond (same timestamp). Test `test_get_wishlist_ordering_most_recent_first` asserted `items[0]["book_id"] == sample_book2["id"]` but got `sample_book["id"]` because sort order was undefined on tie
- **Fix:** Added `.order_by(WishlistItem.added_at.desc(), WishlistItem.id.desc())` — id is always unique and strictly increasing, making the sort stable
- **Files modified:** `app/wishlist/repository.py`
- **Verification:** All 13 wishlist tests pass including the ordering test; full suite 121/121
- **Committed in:** `7cf1a8e` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Auto-fix was necessary for correct deterministic ordering. No scope creep — repository behavior matches plan intent (newest first), now with a tiebreaker.

## Issues Encountered
None beyond the ordering tiebreaker auto-fix above. All 108 existing tests continued to pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 8 complete: wishlist vertical slice (08-01) + integration tests (08-02) both done
- Phase 9 pre-booking can use WishlistRepository and WishlistItem model for notification coupling
- 121 tests passing provides solid regression coverage baseline for Phase 9

## Self-Check: PASSED

All files verified on disk. Task commit 7cf1a8e confirmed in git log.

---
*Phase: 08-wishlist*
*Completed: 2026-02-26*
