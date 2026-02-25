---
phase: 06-cart
plan: 01
subsystem: api
tags: [cart, sqlalchemy, fastapi, pydantic, alembic, postgresql]

# Dependency graph
requires:
  - phase: 04-catalog
    provides: Book model and BookRepository with get_by_id and stock_quantity
  - phase: 02-core-auth
    provides: CurrentUser dependency (JWT sub claim) and AppError structured exceptions
  - phase: 05-discovery
    provides: migration head a1b2c3d4e5f6 that b2c3d4e5f6a7 chains off

provides:
  - Cart and CartItem SQLAlchemy models (carts and cart_items tables)
  - Alembic migration b2c3d4e5f6a7 creating carts and cart_items
  - CartRepository with get_or_create (ON CONFLICT DO NOTHING) and get_with_items (selectinload)
  - CartItemRepository with add (IntegrityError -> CART_ITEM_DUPLICATE), get_by_id, update_quantity, delete
  - CartService with stock validation, ownership checks, virtual empty cart on GET
  - GET /cart, POST /cart/items (201), PUT /cart/items/{id}, DELETE /cart/items/{id} (204)

affects: [07-orders, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - pg INSERT ON CONFLICT DO NOTHING for race-condition-safe get-or-create
    - selectinload chaining (Cart.items -> CartItem.book) for eager relationship loading
    - Virtual empty cart pattern — GET does not create DB row, only POST /cart/items does
    - _make_service(db) factory pattern continued from catalog phase

key-files:
  created:
    - app/cart/models.py
    - app/cart/schemas.py
    - app/cart/repository.py
    - app/cart/service.py
    - app/cart/router.py
    - alembic/versions/b2c3d4e5f6a7_create_carts_and_cart_items.py
  modified:
    - alembic/env.py
    - app/main.py
    - alembic/versions/a1b2c3d4e5f6_add_books_search_vector.py

key-decisions:
  - "pg INSERT ON CONFLICT DO NOTHING for get_or_create — race-condition-safe one-cart-per-user without SELECT then INSERT"
  - "Virtual empty cart on GET — CartService.get_cart returns CartResponse(items=[]) when no DB row exists, avoids creating DB rows on read"
  - "CartItem.book loaded via refresh() after add flush — required for CartItemResponse serialization without N+1"
  - "TYPE_CHECKING guard for Book import in cart/models.py — prevents circular import (cart -> books -> ...) while preserving Mapped[Book] annotation"
  - "int(current_user['sub']) cast in every route handler — JWT sub is always string, must cast to int for user_id comparison"

patterns-established:
  - "Ownership check pattern: get item by ID with selectinload(CartItem.cart), compare item.cart.user_id != user_id, raise 403"
  - "Stock validation before cart creation: check book exists + stock_quantity > 0 before get_or_create"
  - "IntegrityError catch pattern: rollback session then re-raise as AppError after string-matching constraint name"

requirements-completed: [COMM-01, COMM-02]

# Metrics
duration: 6min
completed: 2026-02-25
---

# Phase 6 Plan 1: Cart Summary

**Full cart vertical slice — Cart/CartItem models, pg ON CONFLICT get-or-create repository, stock/ownership-enforcing service, and 4 FastAPI endpoints (GET /cart, POST/PUT/DELETE /cart/items)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-25T15:35:24Z
- **Completed:** 2026-02-25T15:41:xx Z
- **Tasks:** 2
- **Files modified:** 9 (6 created, 3 modified)

## Accomplishments
- Cart and CartItem SQLAlchemy models with UniqueConstraints (one cart per user, one item per book per cart)
- Race-condition-safe CartRepository.get_or_create using PostgreSQL INSERT ON CONFLICT DO NOTHING
- CartItemRepository with IntegrityError -> CART_ITEM_DUPLICATE conversion for duplicate book adds
- CartService enforcing stock > 0 on add_item, ownership check on update/remove, virtual empty cart on GET
- All 4 REST endpoints registered in app — GET /cart, POST /cart/items (201), PUT /cart/items/{id}, DELETE /cart/items/{id} (204)
- 79 existing tests pass (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Cart/CartItem models, migration b2c3d4e5f6a7, env.py imports** - `19bc63d` (feat)
2. **Task 2: schemas, repository, service, router, main.py registration** - `80a0be8` (feat)
3. **Deviation fix: ruff import ordering in migration files** - `e13f921` (fix)

## Files Created/Modified
- `app/cart/models.py` - Cart (uq_carts_user_id) and CartItem (uq_cart_items_cart_book) models with TYPE_CHECKING Book import
- `app/cart/schemas.py` - CartItemAdd, CartItemUpdate, BookSummary, CartItemResponse, CartResponse with computed_field totals
- `app/cart/repository.py` - CartRepository (get_or_create, get_with_items) and CartItemRepository (add, get_by_id, update_quantity, delete)
- `app/cart/service.py` - CartService with add_item (stock check), update/remove_item (ownership), get_cart (virtual empty)
- `app/cart/router.py` - APIRouter prefix=/cart with 4 endpoints, _make_service factory
- `alembic/versions/b2c3d4e5f6a7_create_carts_and_cart_items.py` - Migration chained off a1b2c3d4e5f6
- `alembic/env.py` - Added Cart, CartItem imports for Alembic model discovery
- `app/main.py` - Registered cart_router after books_router, fixed import ordering

## Decisions Made
- pg INSERT ON CONFLICT DO NOTHING for CartRepository.get_or_create — race-condition-safe, no SELECT-then-INSERT gap
- Virtual empty cart on GET — CartService.get_cart returns `CartResponse(items=[])` when no DB row exists (GET does not create rows)
- session.refresh(item, ["book"]) after add flush — loads book relationship for CartItemResponse without extra query or selectinload on insert
- TYPE_CHECKING guard for Book import in cart/models.py — avoids circular import while keeping Mapped[Book] annotation available at type-check time
- int(current_user["sub"]) cast in every route handler — JWT sub is string; must cast to int for all user_id comparisons

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff UP037 quoted type annotations in cart/models.py**
- **Found during:** Task 2 verification (ruff check)
- **Issue:** `Mapped[list["CartItem"]]`, `Mapped["Cart"]`, `Mapped["Book"]` — quotes redundant with `from __future__ import annotations`
- **Fix:** Removed quotes: `Mapped[list[CartItem]]`, `Mapped[Cart]`, `Mapped[Book]`
- **Files modified:** app/cart/models.py
- **Verification:** `ruff check app/cart/` passes
- **Committed in:** 80a0be8 (Task 2 commit after ruff format)

**2. [Rule 3 - Blocking] Fixed ruff I001 import ordering in main.py**
- **Found during:** Task 2 verification (ruff check)
- **Issue:** Adding `from app.cart.router import router as cart_router` between existing imports triggered I001 — `app.books.*` must come before `app.core.*` alphabetically
- **Fix:** Rewrote main.py imports with correct alphabetical order (books -> cart -> core -> users)
- **Files modified:** app/main.py
- **Verification:** `ruff check app/main.py` passes
- **Committed in:** 80a0be8

**3. [Rule 3 - Blocking] Fixed ruff I001 import ordering in migration files**
- **Found during:** Overall plan verification (`ruff check alembic/`)
- **Issue:** `import sqlalchemy as sa` and `from alembic import op` were in same import block — ruff requires stdlib before first-party grouping
- **Fix:** `poetry run ruff check --fix` applied to both b2c3d4e5f6a7 and pre-existing a1b2c3d4e5f6 migration
- **Files modified:** alembic/versions/b2c3d4e5f6a7_create_carts_and_cart_items.py, alembic/versions/a1b2c3d4e5f6_add_books_search_vector.py
- **Verification:** `ruff check alembic/` passes
- **Committed in:** e13f921

---

**Total deviations:** 3 auto-fixed (all Rule 3 - blocking lint errors)
**Impact on plan:** All fixes required for ruff check to pass per plan success criteria. No scope creep.

## Issues Encountered
- ruff format produced output that made the verification dict comprehension `{r.path: list(r.methods)}` appear to show only DELETE for `/cart/items/{item_id}` — confirmed by iterating routes individually that PUT is correctly registered

## Next Phase Readiness
- Cart feature is fully functional: models, migration, endpoints all wired
- Phase 6 Plan 2 (cart tests) can be executed immediately — all endpoints available for integration testing
- Migration b2c3d4e5f6a7 is the new Alembic head; Phase 7 (orders) migration must chain off it

---
*Phase: 06-cart*
*Completed: 2026-02-25*
