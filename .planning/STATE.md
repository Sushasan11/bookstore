---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Reviews & Ratings
status: unknown
last_updated: "2026-02-26T16:53:11.918Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 14 — Review CRUD Endpoints

## Current Position

Phase: 14 of 15 (Review CRUD Endpoints)
Plan: 2 of 2
Status: Complete
Last activity: 2026-02-26 — Completed 14-02 (PATCH/DELETE endpoints, ownership enforcement, 33 integration tests)

Progress: [██████░░░░] 80% (4/5 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 3 (v2.0)
- Average duration: 3 min
- Total execution time: 10 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 13. Review Data Layer | 2/2 | 8 min | 4 min |
| 14. Review CRUD Endpoints | 2/2 | 7 min | 3.5 min |
| 15. Book Detail Aggregates | 0/1 | — | — |

*Updated after each plan completion*

## Accumulated Context

### Decisions

From v1.0 (key decisions relevant to future phases):
- [Phase 01]: app/db/base.py is the model registry — all new models must be imported here immediately on creation
- [Phase 01]: expire_on_commit=False on AsyncSessionLocal — prevents MissingGreenlet on model attribute access after commit
- [Phase 06]: SELECT FOR UPDATE with ascending book_id sort — any new locking code must follow the same pattern to prevent deadlocks
- [Phase 07]: Opaque refresh tokens (DB-persisted) — enables instant revocation at user deactivation
- [Phase 08]: CASCADE vs SET NULL on FKs — wishlist CASCADE, orders SET NULL (preserve history)

From v1.1:
- Email via fastapi-mail 1.6.2 + BackgroundTasks — no Celery/Redis at this scale
- Email as post-commit side effect only — never inside transaction, never blocking response
- Pre-booking cancel: soft delete (status=CANCELLED) for audit trail over hard delete
- Admin deactivation: revoke all refresh tokens immediately (15-min JWT window is acceptable)
- [Phase 09-01]: get_email_service() decorated with @lru_cache — FastMail reused across requests
- [Phase 09-01]: EmailSvc = Annotated[EmailService, Depends(get_email_service)] injection pattern
- [Phase 10-01]: ActiveUser dependency does one DB round-trip per protected request for is_active check
- [Phase 10-01]: get_active_user uses local import of UserRepository inside function body — avoids circular import
- [Phase 11-01]: Partial unique index on (user_id, book_id) WHERE status='waiting' — good pattern for one-active-per-pair constraints
- [Phase 11-02]: SAEnum with StrEnum requires values_callable=lambda e: [v.value for v in e]
- [Phase 12-02]: email_client fixture overrides both get_db AND get_email_service

From v2.0 research:
- reviews FK uses CASCADE (not SET NULL) — reviews without a book are meaningless
- Aggregate avg_rating/review_count computed live via SQL AVG/COUNT — not stored on books table
- func.avg().cast(Numeric) required for two-argument ROUND in PostgreSQL (DOUBLE PRECISION default from avg() incompatible)
- Cross-domain purchase check: ReviewService injects OrderRepository (not OrderService) — avoids circular import, mirrors BookService/PreBookRepository pattern

From Phase 13-01:
- _UNSET sentinel in ReviewRepository.update() distinguishes "not provided" from explicit None for text field
- onupdate=func.now() on updated_at is ORM-only — migration uses only server_default (no onupdate in SQL)
- Pagination pattern: count via select(func.count()).select_from(base_stmt.subquery()), then limit/offset

From Phase 13-02:
- has_user_purchased_book uses EXISTS subquery (not COUNT) — returns bool scalar, more efficient
- PAYMENT_FAILED orders explicitly excluded — only OrderStatus.CONFIRMED counts as purchase
- Purchase check pattern: EXISTS(Order.status==CONFIRMED, OrderItem.book_id==book_id) — reusable for any purchased-item gate

From Phase 14-01:
- DuplicateReviewError is separate from AppError (not a subclass) — its 409 body has existing_review_id which AppError handler cannot produce
- _build_review_data() builds plain dict for ReviewResponse.model_validate() — cleaner than from_attributes when ORM field names differ (book.id -> book_id, user.email -> display_name)
- display_name derived from email.split('@')[0] — User model has no display_name column (avatar_url always None)
- DuplicateReviewError handler registered before AppError in main.py — more specific handlers must precede general ones
- GET /books/{book_id}/reviews and GET /reviews/{review_id} are public — no auth required to read reviews

From Phase 14-02:
- model_fields_set sentinel pattern: text = body.text if "text" in body.model_fields_set else _UNSET — use for any PATCH endpoint where omitted != null
- Single DELETE endpoint for user and admin: is_admin = current_user.get("role") == "admin" passed to service; no separate admin endpoint needed
- Re-fetch after repo.update(): session.refresh() does not re-run selectinload — call get_by_id() again after update() to eager-load relationships
- Test fixture pattern: separate User ORM fixtures (rev_user) from header fixtures (user_headers) — allows DB-setup fixtures to access user_id without JWT parsing

### Blockers/Concerns

None.

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 14-02-PLAN.md (PATCH/DELETE endpoints, ownership enforcement, 33 integration tests)
Resume file: None
