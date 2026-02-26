---
phase: 07-orders
plan: 01
subsystem: api
tags: [orders, checkout, stock-locking, select-for-update, postgresql, alembic, sqlalchemy, fastapi]

# Dependency graph
requires:
  - phase: 06-cart
    provides: CartRepository.get_with_items and CartItem model for cart loading at checkout
  - phase: 04-catalog
    provides: Book model with stock_quantity and price for stock locking and unit_price snapshot
  - phase: 02-auth
    provides: CurrentUser and AdminUser dependency injection for route authorization

provides:
  - Order and OrderItem SQLAlchemy models with OrderStatus StrEnum (CONFIRMED, PAYMENT_FAILED)
  - Alembic migration d4e5f6a7b8c9 creating orders and order_items tables
  - OrderRepository with SELECT FOR UPDATE ascending-ID lock for deadlock-safe stock management
  - MockPaymentService with configurable force_fail for deterministic test control
  - OrderService with single-transaction checkout orchestration (lock -> validate -> pay -> create -> clear cart)
  - POST /orders/checkout (201), GET /orders, GET /orders/{id}, GET /admin/orders endpoints
affects: [07-orders-tests, phase-08, phase-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SELECT FOR UPDATE with ascending ID order for multi-resource deadlock prevention
    - unit_price snapshot on OrderItem at time of purchase (not current book price)
    - nullable book_id FK with SET NULL on delete to preserve order history when books removed from catalog
    - _make_service factory pattern in router for per-request dependency injection
    - MockPaymentService with force_fail for test-controllable randomness

key-files:
  created:
    - app/orders/models.py
    - app/orders/schemas.py
    - app/orders/repository.py
    - app/orders/service.py
    - app/orders/router.py
    - alembic/versions/d4e5f6a7b8c9_create_orders_and_order_items.py
  modified:
    - alembic/env.py
    - app/main.py

key-decisions:
  - "OrderItem.book_id uses SET NULL on delete — preserves order history when book removed from catalog"
  - "lock_books uses SELECT FOR UPDATE with ORDER BY Book.id ascending — book_ids must be pre-sorted by caller for deadlock prevention"
  - "MockPaymentService with force_fail=True allows deterministic test control of 90% success rate payment simulation"
  - "Cart items are deleted (not the cart row) on successful checkout — consistent with get_or_create pattern"
  - "unit_price copied from book.price at checkout time — order history immune to future price changes"

patterns-established:
  - "SELECT FOR UPDATE ascending-ID: book_ids sorted ascending before lock_books to prevent deadlocks in concurrent checkouts"
  - "Stock snapshot: unit_price stored on OrderItem at purchase time, not referenced from Book.price"
  - "Nullable FK with SET NULL: book_id nullable on OrderItem — book deletion preserves order history"

requirements-completed: [COMM-03, COMM-04, COMM-05, ENGM-06]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 7 Plan 1: Orders Vertical Slice Summary

**Full orders domain with SELECT FOR UPDATE stock locking, MockPaymentService, single-transaction checkout orchestration, and 4 REST endpoints (POST /orders/checkout, GET /orders, GET /orders/{id}, GET /admin/orders)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-25T16:40:32Z
- **Completed:** 2026-02-25T16:46:16Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Order and OrderItem SQLAlchemy models with OrderStatus StrEnum and unit_price price-snapshot design
- Alembic migration d4e5f6a7b8c9 creating orders and order_items tables chaining off cart migration b2c3d4e5f6a7
- OrderRepository.lock_books() using SELECT FOR UPDATE with ascending ID ordering for deadlock prevention
- OrderService.checkout() — complete single-transaction orchestration: cart validation, stock locking, stock validation, payment, order creation, stock decrement, cart clearing
- All 4 endpoints registered and tested: 94/94 existing tests still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Order/OrderItem models, OrderStatus enum, and Alembic migration** - `aa596f0` (feat)
2. **Task 2: Schemas, repository, service, router, and main.py registration** - `9a62b44` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `app/orders/models.py` - Order and OrderItem models with OrderStatus StrEnum, nullable book_id FK
- `app/orders/schemas.py` - CheckoutRequest, OrderItemBookSummary, OrderItemResponse, OrderResponse (with computed total_price), InsufficientStockItem
- `app/orders/repository.py` - OrderRepository with lock_books (SELECT FOR UPDATE), create_order, list_for_user, list_all, get_by_id_for_user
- `app/orders/service.py` - MockPaymentService (90% success + force_fail) and OrderService with full checkout orchestration
- `app/orders/router.py` - POST /orders/checkout (201), GET /orders, GET /orders/{id}, GET /admin/orders with AdminUser dependency
- `alembic/versions/d4e5f6a7b8c9_create_orders_and_order_items.py` - Migration creating orders/order_items tables with FK constraints, indexes, orderstatus enum
- `alembic/env.py` - Added Order and OrderItem imports for Alembic model discovery
- `app/main.py` - Registered orders_router and orders_admin_router

## Decisions Made
- `OrderItem.book_id` uses `ondelete="SET NULL"` and `nullable=True` — order history is preserved even when a book is deleted from the catalog
- `lock_books()` requires pre-sorted ascending book IDs from the caller — enforces consistent lock acquisition order across concurrent transactions to prevent deadlocks
- MockPaymentService with `force_fail=True` parameter enables deterministic test control of the 90% success simulation
- Cart items deleted (not the cart row itself) on successful checkout — consistent with get_or_create single-cart pattern
- `unit_price` copied from `book.price` at checkout time — order totals remain accurate regardless of future catalog price changes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed import ordering in models.py and migration file**
- **Found during:** Task 1 (ruff check)
- **Issue:** Ruff I001 import block un-sorted; UP035 `typing.Sequence` should come from `collections.abc`; UP007 `Union[X, Y]` should use `X | Y` syntax
- **Fix:** Ran `ruff check --fix` to auto-sort imports and modernize type annotations
- **Files modified:** `app/orders/models.py`, `alembic/versions/d4e5f6a7b8c9_create_orders_and_order_items.py`, `alembic/env.py`
- **Verification:** `ruff check` and `ruff format --check` both pass with zero violations
- **Committed in:** `aa596f0` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed import ordering in main.py and router.py formatting**
- **Found during:** Task 2 (ruff check)
- **Issue:** Ruff I001 import block un-sorted in main.py after adding orders imports; router.py whitespace formatting
- **Fix:** Ran `ruff check --fix` and `ruff format` to auto-correct
- **Files modified:** `app/main.py`, `app/orders/router.py`
- **Verification:** `ruff check` and `ruff format --check` both pass with zero violations
- **Committed in:** `9a62b44` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - import ordering detected by ruff)
**Impact on plan:** All auto-fixes are style/import ordering corrections. No logic changes, no scope creep.

## Issues Encountered
None — both tasks executed cleanly, all verification steps passed on first attempt after ruff auto-fix.

## User Setup Required
None - no external service configuration required. MockPaymentService requires no credentials.

## Next Phase Readiness
- Orders domain fully implemented and ready for integration testing (Phase 07 Plan 02)
- All 4 endpoints operational: checkout, user order history, order detail, admin all-orders view
- SELECT FOR UPDATE deadlock prevention confirmed: ascending ID sort in lock_books()
- MockPaymentService force_fail enables deterministic test control without external dependencies
- 94/94 existing tests pass — no regressions

---
*Phase: 07-orders*
*Completed: 2026-02-25*

## Self-Check: PASSED

- FOUND: app/orders/models.py
- FOUND: app/orders/schemas.py
- FOUND: app/orders/repository.py
- FOUND: app/orders/service.py
- FOUND: app/orders/router.py
- FOUND: alembic/versions/d4e5f6a7b8c9_create_orders_and_order_items.py
- FOUND: .planning/phases/07-orders/07-01-SUMMARY.md
- FOUND: commit aa596f0 (Task 1)
- FOUND: commit 9a62b44 (Task 2)
