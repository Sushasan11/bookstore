---
phase: 08-wishlist
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, postgresql, wishlist]

# Dependency graph
requires:
  - phase: 06-cart
    provides: "_make_service factory pattern, CartItem/Book relationship pattern, session.refresh(item, ['book']) after flush"
  - phase: 07-orders
    provides: "d4e5f6a7b8c9 migration head, OrderItem SET NULL vs CASCADE FK decision context"
  - phase: 04-catalog
    provides: "BookRepository.get_by_id, Book model, books table"
provides:
  - "WishlistItem SQLAlchemy model with UNIQUE(user_id, book_id) constraint and CASCADE on both FKs"
  - "Migration e5f6a7b8c9d0 chained off d4e5f6a7b8c9 (orders head)"
  - "WishlistRepository: add with IntegrityError->409, get_all_for_user (selectinload), get_by_user_and_book, delete"
  - "WishlistService: book existence check (404), duplicate guard via repo (409), list, remove"
  - "POST /wishlist (201), GET /wishlist (200), DELETE /wishlist/{book_id} (204) — all auth-protected"
affects: [09-prebooking, integration-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_make_service(db) factory pattern (same as cart and orders)"
    - "IntegrityError catch by string-matching e.orig for constraint violations"
    - "session.refresh(item, ['book']) after flush to load relationship inline"
    - "selectinload for list queries to avoid N+1"

key-files:
  created:
    - app/wishlist/models.py
    - app/wishlist/schemas.py
    - app/wishlist/repository.py
    - app/wishlist/service.py
    - app/wishlist/router.py
    - alembic/versions/e5f6a7b8c9d0_create_wishlist_items.py
  modified:
    - alembic/env.py
    - app/main.py

key-decisions:
  - "WishlistItem.book_id uses CASCADE on delete (not SET NULL like OrderItem) — wishlist item is meaningless without its book"
  - "DELETE /wishlist/{book_id} uses book_id as path param (natural key) — avoids exposing internal item IDs"
  - "BookSummary includes stock_quantity — success criteria require showing current price and stock visibility"
  - "No quantity column — a book is either on the wishlist or not (binary membership)"

patterns-established:
  - "Wishlist domain follows exact cart vertical slice pattern: model -> migration -> repository -> service -> router"

requirements-completed: [ENGM-01, ENGM-02]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 8 Plan 1: Wishlist Summary

**Full wishlist vertical slice: WishlistItem model + migration e5f6a7b8c9d0, repository with duplicate-guard, service with book-existence validation, and 3 auth-protected REST endpoints (POST/GET/DELETE /wishlist)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-25T19:03:29Z
- **Completed:** 2026-02-25T19:08:43Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- WishlistItem model with UNIQUE(user_id, book_id) constraint and CASCADE on both FKs; migration chains off d4e5f6a7b8c9
- WishlistRepository handles IntegrityError → 409 WISHLIST_ITEM_DUPLICATE; WishlistService validates book existence (404) before adding
- All 3 endpoints registered and auth-protected; GET /wishlist returns items with current book price and stock_quantity; 108/108 existing tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: WishlistItem model and Alembic migration** - `314b7c0` (feat)
2. **Task 2: Schemas, repository, service, router, and main.py registration** - `6ff990f` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `app/wishlist/models.py` - WishlistItem SQLAlchemy model with UNIQUE(user_id, book_id), CASCADE on both FKs, book relationship
- `app/wishlist/schemas.py` - WishlistAdd, BookSummary (with stock_quantity), WishlistItemResponse, WishlistResponse Pydantic schemas
- `app/wishlist/repository.py` - WishlistRepository: add (IntegrityError->409), get_all_for_user (selectinload), get_by_user_and_book, delete
- `app/wishlist/service.py` - WishlistService: add (404 book check), list, remove (404 item check)
- `app/wishlist/router.py` - POST /wishlist (201), GET /wishlist (200), DELETE /wishlist/{book_id} (204)
- `alembic/versions/e5f6a7b8c9d0_create_wishlist_items.py` - Migration chaining off d4e5f6a7b8c9 with UniqueConstraint and indexes
- `alembic/env.py` - Added WishlistItem import for metadata discovery
- `app/main.py` - Registered wishlist_router after orders_admin_router, alphabetical import order maintained

## Decisions Made
- WishlistItem.book_id uses CASCADE on delete (not SET NULL like OrderItem) — wishlist item is meaningless without its book
- DELETE /wishlist/{book_id} uses book_id as path param (natural key) — avoids exposing internal item IDs
- BookSummary includes stock_quantity — success criteria require showing current price and stock visibility
- No quantity column — a book is either on the wishlist or not (binary membership)

## Deviations from Plan

None - plan executed exactly as written. One minor auto-format deviation: ruff reformatted the @router.post decorator across two lines (line length), corrected with `ruff format` before commit.

## Issues Encountered
None — all 108 existing tests passed on first run. ruff check and format clean after auto-format fix.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wishlist domain complete (ENGM-01, ENGM-02 satisfied)
- Phase 9 pre-booking can use WishlistRepository and WishlistItem model for notification coupling
- Migration e5f6a7b8c9d0 must be applied to production DB before deploying

## Self-Check: PASSED

All created files exist on disk. Both task commits (314b7c0, 6ff990f) verified in git log.

---
*Phase: 08-wishlist*
*Completed: 2026-02-26*
