
# Roadmap: BookStore

## Overview

Build a FastAPI + PostgreSQL bookstore API from greenfield to a complete commerce system. The journey starts with an async-correct infrastructure foundation (eliminating the async pitfalls that would otherwise cascade through every phase), then gates all authenticated features behind a stable JWT + OAuth auth layer, builds the admin-managed book catalog that every commerce feature depends on, adds the public discovery layer, implements the cart-to-checkout commerce loop with race-condition-safe stock management, and finishes with the engagement features (wishlist and pre-booking with in-app notifications) that differentiate this bookstore from a plain CRUD app.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Infrastructure** - Async FastAPI app with PostgreSQL, Alembic, pydantic-settings, and all tooling configured correctly before any feature work begins
- [x] **Phase 2: Core Auth** - Email/password registration and login with JWT access + refresh tokens, token revocation, and role-based access control
- [x] **Phase 3: OAuth** - Google and GitHub OAuth login integrated into the existing auth layer
- [ ] **Phase 4: Catalog** - Admin CRUD for books and genre taxonomy with stock quantity tracking
- [ ] **Phase 5: Discovery** - Public catalog browse with pagination, full-text search, filtering, and book detail
- [ ] **Phase 6: Cart** - DB-persisted shopping cart with per-user enforcement and stock validation
- [ ] **Phase 7: Orders** - Checkout with mock payment and race-condition-safe stock decrement, order history for users and admin
- [ ] **Phase 8: Wishlist** - Personal wishlist for saving books outside the cart
- [ ] **Phase 9: Pre-Booking** - Reservation system for out-of-stock books with in-app notification when stock arrives

## Phase Details

### Phase 1: Infrastructure
**Goal**: The async FastAPI application exists with a correctly configured PostgreSQL connection, Alembic migrations, and all tooling — making every subsequent phase safe to build on
**Depends on**: Nothing (first phase)
**Requirements**: None (infrastructure phase — no v1 requirements map here; all 26 requirements depend on this foundation)
**Success Criteria** (what must be TRUE):
  1. `GET /health` returns 200 and confirms database connectivity
  2. `alembic upgrade head` runs cleanly and `alembic check` reports no pending migrations
  3. `pytest` discovers and runs async tests using `asyncio_mode = "auto"` with no import errors
  4. `ruff check` and `ruff format --check` pass on the project with zero violations
  5. Environment config loads from `.env` via pydantic-settings with no hardcoded secrets
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffold: Poetry setup, directory structure, pydantic-settings config, FastAPI app factory with exception handlers
- [x] 01-02-PLAN.md — Database layer: async engine with postgresql+asyncpg://, AsyncSessionLocal with expire_on_commit=False, get_db dependency
- [x] 01-03-PLAN.md — Alembic setup: async env.py with correct model import pattern, database connectivity verification
- [x] 01-04-PLAN.md — Tooling: pytest-asyncio conftest.py with async fixtures, smoke tests, ruff verification

### Phase 2: Core Auth
**Goal**: Users can register and log in with email/password, stay authenticated across sessions with refresh tokens, log out with token revocation, and all endpoints enforce admin vs user roles
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):
  1. A new user can POST to `/auth/register` with email + password and receive a 201 with their user record
  2. A registered user can POST to `/auth/login` and receive both an access token (15-min TTL) and a refresh token
  3. A user with an expired access token can POST to `/auth/refresh` and receive a new access token without re-entering credentials
  4. A logged-in user can POST to `/auth/logout` and subsequent use of their refresh token is rejected with 401
  5. An unauthenticated request to a protected endpoint returns 401; a user-token request to an admin endpoint returns 403
**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — User domain: User + RefreshToken SQLAlchemy models with UserRole enum, Alembic migration creating users and refresh_tokens tables
- [x] 02-02-PLAN.md — Security layer: app/core/security.py with HS256 JWT (hash_password, create_access_token, decode_access_token, generate_refresh_token) and Pydantic schemas
- [x] 02-03-PLAN.md — Repository + service + RBAC: UserRepository, RefreshTokenRepository, AuthService (timing-safe login, token rotation, family revocation), get_current_user and require_admin deps
- [x] 02-04-PLAN.md — Auth endpoints + admin seed: POST /auth/register, /login, /refresh, /logout router wired into main.py; scripts/seed_admin.py for first admin
- [x] 02-05-PLAN.md — Integration tests (TDD): tests/test_auth.py covering all 4 endpoints + RBAC; 12+ test cases verifying success + error paths

### Phase 3: OAuth
**Goal**: Users can authenticate with their Google or GitHub account and receive the same JWT token pair as email/password users, with the accounts linked if the email already exists
**Depends on**: Phase 2
**Requirements**: AUTH-06
**Success Criteria** (what must be TRUE):
  1. A user can initiate OAuth login for Google via `GET /auth/google` and be redirected to Google's consent screen
  2. A user can initiate OAuth login for GitHub via `GET /auth/github` and be redirected to GitHub's authorization screen
  3. After completing the OAuth flow, the user receives a JWT access + refresh token pair identical in structure to email/password login tokens
  4. If the OAuth email matches an existing account, the OAuth login authenticates to that existing account (no duplicate user created)
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — OAuth foundation: OAuthAccount model, hashed_password nullable migration, Authlib provider registry (Google OIDC + GitHub OAuth2), SessionMiddleware, config settings
- [x] 03-02-PLAN.md — OAuth service and endpoints: OAuthAccountRepository, AuthService.oauth_login(), login guard for OAuth-only users, GET /auth/google, /auth/google/callback, /auth/github, /auth/github/callback
- [x] 03-03-PLAN.md — OAuth integration tests: tests/test_oauth.py with mocked Authlib providers covering redirects, callbacks, account linking, OAuth-only users, error cases

### Phase 4: Catalog
**Goal**: An admin can fully manage the book catalog — creating, editing, and deleting books with all metadata and stock quantities, and managing the genre taxonomy — so there is data for all downstream features to work with
**Depends on**: Phase 2
**Requirements**: CATL-01, CATL-02, CATL-03, CATL-04, CATL-05
**Success Criteria** (what must be TRUE):
  1. An admin can POST to `/books` with full book metadata (title, author, price, ISBN, genre, description, cover image URL, publish date) and the book appears in the database
  2. An admin can PUT to `/books/{id}` to update any field and GET the book to confirm the change
  3. An admin can DELETE `/books/{id}` and the book is no longer retrievable
  4. An admin can PATCH `/books/{id}/stock` to set stock quantity and the updated quantity is reflected immediately
  5. An admin can POST to `/genres` to add a genre and GET `/genres` to list all genres
**Plans**: TBD

Plans:
- [ ] 04-01: Books domain — `books` and `genres` table migrations, Book and Genre models with `stock_quantity` field and `CHECK CONSTRAINT (stock_quantity >= 0)`
- [ ] 04-02: Admin book endpoints — POST/PUT/DELETE `/books`, BookRepository, BookService with `require_admin` guard
- [ ] 04-03: Stock and genre management — PATCH `/books/{id}/stock`, POST/GET `/genres`, GenreRepository

### Phase 5: Discovery
**Goal**: Any visitor can browse the book catalog with pagination and sorting, search by title, author, or genre using full-text search, filter by genre or author, and view a book's full details including current stock status
**Depends on**: Phase 4
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04
**Success Criteria** (what must be TRUE):
  1. GET `/books` returns a paginated list of books with `page`, `size`, and `sort` query parameters working correctly
  2. GET `/books?q=tolkien` returns books matching the search term across title, author, and genre via PostgreSQL full-text search
  3. GET `/books?genre=fantasy&author=Tolkien` returns only books matching both filters
  4. GET `/books/{id}` returns the book's full details including current `stock_quantity` and an `in_stock` boolean
**Plans**: TBD

Plans:
- [ ] 05-01: Full-text search — `tsvector` generated column on books, GIN index migration, `to_tsvector` configuration for title + author + genre
- [ ] 05-02: Discovery endpoints — GET `/books` (pagination, sort, search, filter), GET `/books/{id}` with stock status; BookRepository query methods

### Phase 6: Cart
**Goal**: An authenticated user has a persistent shopping cart where they can add books, update quantities, and remove items, with stock availability checked on add
**Depends on**: Phase 4, Phase 2
**Requirements**: COMM-01, COMM-02
**Success Criteria** (what must be TRUE):
  1. An authenticated user can POST to `/cart/items` with a `book_id` and `quantity` and GET `/cart` to see the item in their cart
  2. A user can PUT to `/cart/items/{id}` to change quantity and the cart reflects the updated quantity
  3. A user can DELETE `/cart/items/{id}` and the item is removed from their cart
  4. Adding an out-of-stock book to the cart returns a 409 with a clear error message
  5. A user's cart persists across sessions — logging out and back in shows the same cart contents
**Plans**: TBD

Plans:
- [ ] 06-01: Cart domain — `carts` and `cart_items` table migrations with `UNIQUE(cart_id, book_id)`, Cart and CartItem models, one-cart-per-user enforcement
- [ ] 06-02: Cart endpoints — GET `/cart`, POST `/cart/items`, PUT `/cart/items/{id}`, DELETE `/cart/items/{id}`; CartService with stock availability check

### Phase 7: Orders
**Goal**: An authenticated user can checkout their cart with a mock payment to create an order, view their order history, and an admin can view all orders placed on the platform
**Depends on**: Phase 6
**Requirements**: COMM-03, COMM-04, COMM-05, ENGM-06
**Success Criteria** (what must be TRUE):
  1. A user can POST to `/orders/checkout` and receive an order confirmation with order ID, line items, and total — and their cart is cleared
  2. After checkout, the stock quantity for each purchased book is decremented by the quantity ordered
  3. Concurrent checkouts for the same book do not result in negative stock (race condition safety verified)
  4. A user can GET `/orders` to view their complete order history with line items and prices at time of purchase
  5. An admin can GET `/admin/orders` to view all orders placed by all users
**Plans**: TBD

Plans:
- [ ] 07-01: Orders domain — `orders` and `order_items` table migrations with `unit_price` snapshot field, Order and OrderItem models
- [ ] 07-02: Checkout endpoint — POST `/orders/checkout` with single-transaction `SELECT FOR UPDATE` on book stock rows (locked in ascending ID order to prevent deadlocks), mock payment confirmation, cart clear
- [ ] 07-03: Order history endpoints — GET `/orders` (user's orders), GET `/orders/{id}` (order detail), GET `/admin/orders` (admin all orders)

### Phase 8: Wishlist
**Goal**: An authenticated user can maintain a personal wishlist of books they want to remember but are not ready to purchase
**Depends on**: Phase 4, Phase 2
**Requirements**: ENGM-01, ENGM-02
**Success Criteria** (what must be TRUE):
  1. An authenticated user can POST to `/wishlist` with a `book_id` and the book appears when they GET `/wishlist`
  2. A user can DELETE `/wishlist/{book_id}` and the book is removed from their wishlist
  3. A user's wishlist shows the current price and stock status of each saved book
  4. Adding a book that is already on the wishlist returns a 409 rather than creating a duplicate entry
**Plans**: TBD

Plans:
- [ ] 08-01: Wishlist domain — `wishlist_items` table migration with `UNIQUE(user_id, book_id)`, WishlistItem model, WishlistRepository, WishlistService
- [ ] 08-02: Wishlist endpoints — POST `/wishlist`, GET `/wishlist`, DELETE `/wishlist/{book_id}`

### Phase 9: Pre-Booking
**Goal**: An authenticated user can reserve an out-of-stock book and be notified in-app when stock arrives; the admin stock update flow triggers the notification automatically
**Depends on**: Phase 4, Phase 2
**Requirements**: ENGM-03, ENGM-04, ENGM-05
**Success Criteria** (what must be TRUE):
  1. A user can POST to `/prebooks` for an out-of-stock book and the reservation is created with status WAITING
  2. When an admin updates stock for a book that has WAITING reservations, those reservations automatically transition to status NOTIFIED
  3. A user can GET `/prebooks` and see the current status (WAITING or NOTIFIED) for each of their reservations
  4. A user can DELETE `/prebooks/{id}` to cancel a reservation with status WAITING or NOTIFIED
  5. Concurrent reservation attempts for the same book by the same user result in exactly one reservation, not duplicates
**Plans**: TBD

Plans:
- [ ] 09-01: Pre-booking domain — `prebooks` table migration with `UNIQUE(user_id, book_id)` and status enum (WAITING/NOTIFIED/FULFILLED/CANCELLED), PreBook model, PreBookRepository with `SELECT FOR UPDATE SKIP LOCKED` in fulfillment
- [ ] 09-02: Pre-booking endpoints — POST `/prebooks`, GET `/prebooks`, DELETE `/prebooks/{id}`; status lifecycle logic in PreBookService
- [ ] 09-03: Stock update notification trigger — wire admin PATCH `/books/{id}/stock` in BookService to call `PreBookRepository.notify_waiting(book_id)` in the same transaction; integration test covering the full stock-arrives-to-notification flow

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure | 4/4 | Complete | 2026-02-25 |
| 2. Core Auth | 5/5 | Complete | 2026-02-25 |
| 3. OAuth | 3/3 | Complete | 2026-02-25 |
| 4. Catalog | 0/3 | Not started | - |
| 5. Discovery | 0/2 | Not started | - |
| 6. Cart | 0/2 | Not started | - |
| 7. Orders | 0/3 | Not started | - |
| 8. Wishlist | 0/2 | Not started | - |
| 9. Pre-Booking | 0/3 | Not started | - |
