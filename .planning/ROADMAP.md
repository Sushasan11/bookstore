# Roadmap: BookStore

## Milestones

- ✅ **v1.0 MVP** - Phases 1-8 (shipped 2026-02-25)
- ✅ **v1.1 Pre-booking, Notifications & Admin** - Phases 9-12 (shipped 2026-02-26)
- 🚧 **v2.0 Reviews & Ratings** - Phases 13-15 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-8) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: Infrastructure (4/4 plans) — completed 2026-02-25
- [x] Phase 2: Core Auth (5/5 plans) — completed 2026-02-25
- [x] Phase 3: OAuth (3/3 plans) — completed 2026-02-25
- [x] Phase 4: Catalog (3/3 plans) — completed 2026-02-25
- [x] Phase 5: Discovery (3/3 plans) — completed 2026-02-25
- [x] Phase 6: Cart (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Orders (2/2 plans) — completed 2026-02-25
- [x] Phase 8: Wishlist (2/2 plans) — completed 2026-02-25

</details>

<details>
<summary>✅ v1.1 Pre-booking, Notifications & Admin (Phases 9-12) — SHIPPED 2026-02-26</summary>

- [x] Phase 9: Email Infrastructure (2/2 plans) — completed 2026-02-26
- [x] Phase 10: Admin User Management (2/2 plans) — completed 2026-02-26
- [x] Phase 11: Pre-booking (2/2 plans) — completed 2026-02-26
- [x] Phase 12: Email Notifications Wiring (2/2 plans) — completed 2026-02-26

</details>

### v2.0 Reviews & Ratings (In Progress)

**Milestone Goal:** Let verified purchasers rate and review books, with admin moderation and aggregate ratings surfaced on book detail.

- [x] **Phase 13: Review Data Layer** - Review model, migration, and repository (with verified-purchase query)
- [x] **Phase 14: Review CRUD Endpoints** - All review endpoints with auth, verified-purchase gate, and admin moderation (completed 2026-02-26)
- [ ] **Phase 15: Book Detail Aggregates** - Average rating and review count on book detail response

## Phase Details

### Phase 13: Review Data Layer
**Goal**: The reviews table exists in PostgreSQL with correct constraints, and all data-access operations are available through a repository
**Depends on**: Phase 12 (existing codebase foundation)
**Requirements**: REVW-05, VPRC-01
**Success Criteria** (what must be TRUE):
  1. A migration runs cleanly with `alembic upgrade head` creating the `reviews` table with `UniqueConstraint(user_id, book_id)` and `CheckConstraint(rating >= 1 AND rating <= 5)`
  2. Attempting to insert two reviews for the same user/book pair raises a database-level integrity error (not just an application check)
  3. `ReviewRepository` exposes create, get, update, delete, paginated list, and aggregate methods that the service layer can call
  4. `OrderRepository` exposes `has_user_purchased_book(user_id, book_id)` returning `True` only for users with a confirmed order containing that book
  5. The `Review` model is registered in `app/db/base.py` and `pytest tests/test_health.py` passes without `UndefinedTableError`
**Plans:** 2/2 plans complete

Plans:
- [x] 13-01-PLAN.md — Review model, Alembic migration, and ReviewRepository (wave 1)
- [x] 13-02-PLAN.md — OrderRepository purchase-check method and integration tests (wave 2)

### Phase 14: Review CRUD Endpoints
**Goal**: Users can submit, view, edit, and delete reviews through the API, with verified-purchase enforcement and admin moderation working correctly
**Depends on**: Phase 13
**Requirements**: REVW-01, REVW-02, REVW-03, REVW-04, VPRC-02, ADMR-01
**Success Criteria** (what must be TRUE):
  1. A user who completed an order containing a book can submit a 1-5 star rating with optional text, and receives 201; a user without a qualifying purchase receives 403
  2. Submitting a second review for the same book returns 409 — duplicate is rejected at both application and database level
  3. A user can update their own review's rating and/or text via PATCH and see the changes reflected in subsequent GET requests
  4. A user can delete their own review; attempting to delete another user's review returns 403
  5. An admin can delete any review regardless of who submitted it; the review response includes a `verified_purchase: true/false` flag
  6. `GET /books/{book_id}/reviews` returns paginated reviews sorted by `created_at DESC` with 179 existing tests still passing
**Plans**: 2 plans

Plans:
- [x] 14-01-PLAN.md — ReviewService, Pydantic schemas, router for create + list endpoints with DuplicateReviewError (wave 1)
- [x] 14-02-PLAN.md — Update, delete, admin moderation endpoints with full integration test suite (wave 2)

### Phase 15: Book Detail Aggregates
**Goal**: Book detail responses include a live average rating and review count reflecting the current state of the reviews table
**Depends on**: Phase 14
**Requirements**: AGGR-01, AGGR-02
**Success Criteria** (what must be TRUE):
  1. `GET /books/{id}` returns `avg_rating` rounded to one decimal place (e.g., `4.3`) and `review_count` as an integer
  2. When no reviews exist for a book, `avg_rating` is `null` and `review_count` is `0` — the endpoint does not error
  3. After a review is submitted, the next `GET /books/{id}` call reflects the updated aggregate without any manual cache invalidation
**Plans**: TBD

Plans:
- [ ] 15-01: BookDetailResponse schema update and aggregate integration

## Progress

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
| 9. Email Infrastructure | v1.1 | 2/2 | Complete | 2026-02-26 |
| 10. Admin User Management | v1.1 | 2/2 | Complete | 2026-02-26 |
| 11. Pre-booking | v1.1 | 2/2 | Complete | 2026-02-26 |
| 12. Email Notifications Wiring | v1.1 | 2/2 | Complete | 2026-02-26 |
| 13. Review Data Layer | v2.0 | Complete    | 2026-02-26 | 2026-02-26 |
| 14. Review CRUD Endpoints | v2.0 | Complete    | 2026-02-26 | 2026-02-26 |
| 15. Book Detail Aggregates | v2.0 | 0/1 | Not started | - |
