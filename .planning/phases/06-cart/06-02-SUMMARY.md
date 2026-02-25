---
phase: 06-cart
plan: 02
subsystem: testing
tags: [cart, pytest, httpx, asyncio, integration-tests, fastapi]

# Dependency graph
requires:
  - phase: 06-cart-01
    provides: Cart/CartItem models, CartRepository, CartService, 4 REST endpoints (GET /cart, POST/PUT/DELETE /cart/items)
  - phase: 04-catalog
    provides: Book model and BookRepository used by cart fixtures (POST /books, PATCH /books/{id}/stock)
  - phase: 02-core-auth
    provides: UserRepository and hash_password used by test fixtures for user/admin creation

provides:
  - 15 integration tests covering all cart behaviors in tests/test_cart.py
  - COMM-01 coverage: add to cart, GET cart, empty cart, unauthenticated, out-of-stock, nonexistent book, duplicate, invalid quantity
  - COMM-02 coverage: update quantity, update not found, update forbidden, delete, delete not found
  - Cross-session persistence test and computed totals test (multi-item)

affects: [07-orders, regression-testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level _add_item helper for DRY cart item creation in multiple tests
    - out_of_stock_book fixture relies on default stock_quantity=0 — no PATCH needed, documents intent clearly
    - other_user_headers fixture for ownership enforcement tests (User B cannot modify User A's items)
    - Cross-session persistence test uses db_session directly for user creation, then re-logs in with new client.post(/auth/login)

key-files:
  created:
    - tests/test_cart.py
  modified: []

key-decisions:
  - "admin_headers/user_headers fixtures use module-specific email prefixes (cart_admin@, cart_user@, etc.) to avoid collisions with other test modules"
  - "out_of_stock_book fixture does not call PATCH /stock — relies on default stock_quantity=0, documents the zero-stock case with no extra HTTP call"
  - "_add_item helper asserts 201 and returns dict — used by 8 tests to avoid repeating the POST /cart/items boilerplate"
  - "total_price tolerance check uses abs(float - expected) < 0.02 — avoids floating-point exact comparison on Decimal responses"

patterns-established:
  - "Cart test fixtures: admin_headers (POST /books), user_headers (cart owner), other_user_headers (ownership enforcement)"
  - "sample_book fixture chains admin_headers and uses PATCH /books/{id}/stock to set quantity to 10 post-creation"

requirements-completed: [COMM-01, COMM-02]

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 6 Plan 2: Cart Integration Tests Summary

**15 pytest async integration tests proving COMM-01 (add/get cart) and COMM-02 (update/delete items) end-to-end through HTTP with stock validation, ownership enforcement, cross-session persistence, and computed totals**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-25T15:45:17Z
- **Completed:** 2026-02-25T15:48:24Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments
- 15 integration tests covering all 4 cart endpoints and both requirements (COMM-01, COMM-02)
- Ownership enforcement (403 CART_ITEM_FORBIDDEN) verified via two-user fixture setup
- Cross-session persistence confirmed by logging in twice with same credentials and checking cart via new token
- Computed totals verified: total_items and total_price correct across multi-book cart
- Full test suite (94 tests) passes with no regressions across Phases 1-6

## Task Commits

Each task was committed atomically:

1. **Task 1: Cart integration tests (15 tests, COMM-01 + COMM-02)** - `a1a9cc4` (test)

## Files Created/Modified
- `tests/test_cart.py` - 15 async integration tests covering all cart behaviors; admin/user/other_user/sample_book/out_of_stock_book fixtures; _add_item helper

## Decisions Made
- Email prefixes (`cart_admin@`, `cart_user@`, `cart_other@`, `cart_persist@`) isolate fixture users from other test modules sharing the same test DB schema
- `out_of_stock_book` fixture does not call `PATCH /books/{id}/stock` — default `stock_quantity=0` satisfies the test intent without an extra HTTP round-trip
- `_add_item` helper function avoids repetition across 8 tests that each need to add a cart item as setup
- `abs(float(data["total_price"]) - expected) < 0.02` tolerance avoids fragile Decimal-to-float exact comparison

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff I001 import ordering in test_cart.py**
- **Found during:** Task 1 verification (ruff check)
- **Issue:** `import pytest_asyncio` before `from httpx import AsyncClient` — ruff requires isort ordering (stdlib, then third-party, then local)
- **Fix:** `poetry run ruff check --fix tests/test_cart.py && poetry run ruff format tests/test_cart.py`
- **Files modified:** tests/test_cart.py
- **Verification:** `ruff check tests/test_cart.py` and `ruff format --check tests/test_cart.py` both pass
- **Committed in:** a1a9cc4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking lint error)
**Impact on plan:** Required for ruff check to pass per plan success criteria. No scope creep.

## Issues Encountered
None — tests passed on first run before ruff fix; ruff fix was cosmetic import ordering only.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 6 (Cart) is 100% complete: models, migration, endpoints, and integration tests all verified
- Phase 7 (Orders) can begin immediately
- Migration b2c3d4e5f6a7 remains Alembic head; Phase 7 orders migration must chain off it
- 94 tests all passing; zero regressions from adding cart tests

---
*Phase: 06-cart*
*Completed: 2026-02-25*
