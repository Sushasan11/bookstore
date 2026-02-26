# Roadmap: BookStore

## Milestones

- ✅ **v1.0 MVP** - Phases 1-8 (shipped 2026-02-25)
- 🚧 **v1.1 Pre-booking, Notifications & Admin** - Phases 9-12 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-8) — SHIPPED 2026-02-25</summary>

### Phase 1: Infrastructure
**Goal**: Project scaffolding, async FastAPI + PostgreSQL stack, CI tooling, and Alembic migrations in place.
**Plans**: 4 plans

Plans:
- [x] 01-01: Project setup, Poetry, FastAPI skeleton
- [x] 01-02: PostgreSQL + SQLAlchemy async engine + Alembic
- [x] 01-03: Health-check endpoint, error handlers, logging
- [x] 01-04: Test infrastructure (pytest-asyncio, test DB)

### Phase 2: Core Auth
**Goal**: Users can register, log in with email/password, and authenticate via JWT access + refresh tokens.
**Plans**: 5 plans

Plans:
- [x] 02-01: User model + Alembic migration
- [x] 02-02: Password hashing + registration endpoint
- [x] 02-03: Login + JWT access token issuance
- [x] 02-04: Refresh token (opaque, DB-persisted, family revocation)
- [x] 02-05: Auth integration tests

### Phase 3: OAuth
**Goal**: Users can sign up and log in via Google and GitHub OAuth flows.
**Plans**: 3 plans

Plans:
- [x] 03-01: OAuth provider setup (Authlib, config)
- [x] 03-02: Google + GitHub callback handlers, OAuthAccount model
- [x] 03-03: OAuth integration tests

### Phase 4: Catalog
**Goal**: Admins can manage a full book catalog with genres, stock, and ISBN validation.
**Plans**: 3 plans

Plans:
- [x] 04-01: Book + Genre models, migrations, admin CRUD
- [x] 04-02: Stock management endpoints
- [x] 04-03: Catalog integration tests

### Phase 5: Discovery
**Goal**: Users can browse and search books by title, author, or genre with full-text search and pagination.
**Plans**: 3 plans

Plans:
- [x] 05-01: Full-text search (PostgreSQL FTS, tsvector)
- [x] 05-02: Filter + pagination endpoints
- [x] 05-03: Discovery integration tests

### Phase 6: Cart
**Goal**: Users can build a shopping cart and complete checkout with race-condition-safe stock decrement.
**Plans**: 2 plans

Plans:
- [x] 06-01: Cart model, add/remove/view endpoints
- [x] 06-02: Checkout with SELECT FOR UPDATE, stock validation

### Phase 7: Orders
**Goal**: Users can view their order history with price-at-purchase snapshots; admins can manage all orders.
**Plans**: 2 plans

Plans:
- [x] 07-01: Order + OrderItem models, checkout → order creation
- [x] 07-02: Order history endpoints + admin order management

### Phase 8: Wishlist
**Goal**: Users can add and remove books from a personal wishlist and see current price/stock.
**Plans**: 2 plans

Plans:
- [x] 08-01: Wishlist model, add/remove/view endpoints
- [x] 08-02: Wishlist integration tests

</details>

### 🚧 v1.1 Pre-booking, Notifications & Admin (In Progress)

**Milestone Goal:** Enable users to reserve out-of-stock books and receive email notifications; give admins user lifecycle management.

## Phase Details

### Phase 9: Email Infrastructure
**Goal**: A tested, reusable email service exists that sends async HTML emails via BackgroundTasks, never blocking the API and never sending before a DB commit.
**Depends on**: Phase 8 (v1.0 complete)
**Requirements**: EMAL-01, EMAL-04, EMAL-05, EMAL-06
**Success Criteria** (what must be TRUE):
  1. An email can be triggered from any router endpoint via FastAPI BackgroundTasks without delaying the HTTP response
  2. Emails render with Jinja2 HTML templates and include a plain-text fallback
  3. No real SMTP connection is made during tests (MAIL_SUPPRESS_SEND=True suppresses sending transparently)
  4. Email is never dispatched if the database transaction rolls back — only fired post-commit via BackgroundTasks
**Plans**: 2 plans

Plans:
- [ ] 09-01: Core email infrastructure — fastapi-mail, Settings, EmailService, base.html template
- [ ] 09-02: Email unit + integration tests — template rendering, BackgroundTasks pipeline, post-commit safety

### Phase 10: Admin User Management
**Goal**: Admins can view, filter, deactivate, and reactivate user accounts; deactivated users lose the ability to obtain new access tokens immediately.
**Depends on**: Phase 9
**Requirements**: ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05
**Success Criteria** (what must be TRUE):
  1. Admin can retrieve a paginated list of all users, optionally filtered by role and/or active status
  2. Admin can deactivate a user: the user's is_active flag is set to false and all their refresh tokens are revoked simultaneously
  3. Admin can reactivate a previously deactivated user so they can log in again
  4. Attempting to deactivate an admin account (including one's own) is rejected with an appropriate error
**Plans**: 2 plans

Plans:
- [ ] 10-01-PLAN.md — Admin module, repository extensions, is_active enforcement, and router registration
- [ ] 10-02-PLAN.md — Admin user management integration tests

### Phase 11: Pre-booking
**Goal**: Users can reserve out-of-stock books, view and cancel their reservations, and all waiting pre-bookers are notified (status updated) when admin restocks the book.
**Depends on**: Phase 10
**Requirements**: PRBK-01, PRBK-02, PRBK-03, PRBK-04, PRBK-05, PRBK-06
**Success Criteria** (what must be TRUE):
  1. User can pre-book an out-of-stock book; a second attempt for the same book is rejected as a duplicate
  2. Pre-booking is rejected with 409 when the book has stock_quantity > 0
  3. User can view all their pre-bookings showing current status (waiting, notified, cancelled) and notified_at timestamp
  4. User can cancel a pre-booking; the record is soft-deleted (status set to cancelled)
  5. When admin updates a book's stock from 0 to > 0, all pre-bookings with status "waiting" transition atomically to "notified" with a notified_at timestamp
**Plans**: TBD

Plans:
- [ ] 11-01: TBD

### Phase 12: Email Notifications Wiring
**Goal**: Order confirmation emails fire after successful checkout and restock alert emails fire when a book is restocked, both as post-commit background tasks using the Phase 9 infrastructure.
**Depends on**: Phase 11
**Requirements**: EMAL-02, EMAL-03
**Success Criteria** (what must be TRUE):
  1. After a successful checkout, the user receives an order confirmation email containing the order ID, line items, and total
  2. When a book is restocked, every user with a waiting pre-booking receives a restock alert email for that book
  3. No email is sent if checkout fails or the transaction rolls back
  4. Email dispatch does not delay the HTTP response on either the checkout or stock-update endpoint
**Plans**: TBD

Plans:
- [ ] 12-01: TBD

## Progress

**Execution Order:** Phases execute in numeric order: 9 → 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Infrastructure | v1.0 | 4/4 | Complete | 2026-02-25 |
| 2. Core Auth | v1.0 | 5/5 | Complete | 2026-02-25 |
| 3. OAuth | v1.0 | 3/3 | Complete | 2026-02-25 |
| 4. Catalog | v1.0 | 3/3 | Complete | 2026-02-25 |
| 5. Discovery | v1.0 | 3/3 | Complete | 2026-02-25 |
| 6. Cart | v1.0 | 2/2 | Complete | 2026-02-25 |
| 7. Orders | v1.0 | 2/2 | Complete | 2026-02-25 |
| 8. Wishlist | v1.0 | 2/2 | Complete | 2026-02-25 |
| 9. Email Infrastructure | 2/2 | Complete   | 2026-02-26 | - |
| 10. Admin User Management | 2/2 | Complete   | 2026-02-26 | - |
| 11. Pre-booking | v1.1 | 0/? | Not started | - |
| 12. Email Notifications Wiring | v1.1 | 0/? | Not started | - |
