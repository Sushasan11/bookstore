# Milestones

## v1.0 MVP (Shipped: 2026-02-25)

**Phases completed:** 8 phases, 24 plans, 0 tasks

**Key accomplishments:**
- Async FastAPI + PostgreSQL infrastructure with Alembic migrations and full tooling
- JWT auth with access/refresh tokens, family-based revocation, and Google/GitHub OAuth
- Admin-managed book catalog with genre taxonomy, stock tracking, and ISBN validation
- Full-text search with pagination, filtering, and relevance ranking
- DB-persisted shopping cart with stock validation and race-condition-safe checkout (SELECT FOR UPDATE)
- Order history with price-at-purchase snapshots and admin order management
- Personal wishlist with current book price and stock visibility

**Known Gaps (deferred to v1.1):**
- ENGM-03: Pre-booking for out-of-stock books
- ENGM-04: In-app notification when reserved book restocked
- ENGM-05: View/cancel reservations

**Stats:** 6,763 LOC Python, 121 tests passing, 25 feat commits

---


## v1.1 Pre-booking, Notifications & Admin (Shipped: 2026-02-26)

**Phases completed:** 4 phases, 8 plans
**Stats:** 9,473 LOC Python, 179 tests passing

**Key accomplishments:**
- Async email infrastructure with fastapi-mail + BackgroundTasks (post-commit dispatch, never blocks API)
- Jinja2 HTML email templates with plain-text fallback for order confirmation and restock alerts
- Admin paginated user list with role/active filtering, deactivate/reactivate with immediate token revocation
- Pre-booking for out-of-stock books (reserve, view, cancel) with partial unique index
- Atomic restock notification broadcast to all waiting pre-bookers via batch email lookup

---


## v2.0 Reviews & Ratings (Shipped: 2026-02-27)

**Phases completed:** 3 phases, 5 plans
**Stats:** 12,010 LOC Python, 240 tests passing, 15 commits, 24 files changed (+3,301/-259)
**Audit:** 10/10 requirements satisfied, 5/5 E2E flows verified

**Key accomplishments:**
- Review model with UniqueConstraint(user_id, book_id) + CheckConstraint(rating 1-5) and full repository (7 async methods)
- Verified-purchase gate using EXISTS-based query on confirmed orders only
- Complete review CRUD endpoints: create (with purchase gate + duplicate 409), list (paginated), get, update (PATCH with model_fields_set sentinel), delete (soft-delete)
- Ownership enforcement (403 NOT_REVIEW_OWNER) + admin moderation bypass on update/delete
- Live avg_rating (rounded to 1 decimal) and review_count aggregates on GET /books/{id}
- 62 integration tests across 3 test files covering all 10 requirements

---


## v2.1 Admin Dashboard & Analytics (Shipped: 2026-02-27)

**Phases completed:** 3 phases, 5 plans, 10 tasks
**Stats:** 13,743 LOC Python, 66 new integration tests, 19 files changed (+2,791/-152)
**Audit:** 7/7 requirements satisfied, 3/3 phases verified, 14/14 integrations wired, 7/7 E2E flows complete

**Key accomplishments:**
- Full sales analytics stack — revenue summary with period comparison (today/week/month), AOV, and delta percentage
- Top-selling books endpoint with dual revenue/volume rankings proving distinct orderings
- Low-stock inventory endpoint with configurable threshold, ascending ordering, and per-item threshold echo
- Admin review moderation with paginated list, AND-combined filters (book/user/rating range), and date/rating sort
- Bulk review soft-delete with best-effort semantics (single UPDATE...WHERE IN, silently skips missing/deleted IDs)
- 66 integration tests across 3 test files covering all admin analytics and moderation endpoints

---

