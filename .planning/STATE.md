---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Pre-booking, Notifications & Admin
status: unknown
last_updated: "2026-02-26T11:36:51.408Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 12 — Email Notifications Wiring

## Current Position

Phase: 12 of 12 (Email Notifications Wiring)
Plan: 1 of 2 in current phase — COMPLETE
Status: In progress
Last activity: 2026-02-26 — 12-01 Email notifications wiring (2 tasks, 5 files; order confirmation and restock alert emails wired into routers) complete.

Progress: [█████████████░░░░░░░] 67% (v1.0 complete — 8/12 phases done; Phase 11 fully complete; Phase 12 plan 1 of 2 complete)

## Accumulated Context

### Decisions

From v1.0 (key decisions relevant to v1.1):
- [Phase 01]: app/db/base.py is the model registry — all new models must be imported here immediately on creation
- [Phase 01]: expire_on_commit=False on AsyncSessionLocal — prevents MissingGreenlet on model attribute access after commit
- [Phase 06]: SELECT FOR UPDATE with ascending book_id sort — any new locking code must follow the same pattern to prevent deadlocks
- [Phase 07]: Opaque refresh tokens (DB-persisted) — enables instant revocation at user deactivation
- [Phase 08]: CASCADE vs SET NULL on FKs — wishlist CASCADE, orders SET NULL (preserve history)

From v1.1 planning:
- Email via fastapi-mail 1.6.2 + BackgroundTasks — no Celery/Redis at this scale
- Email as post-commit side effect only — never inside transaction, never blocking response
- Pre-booking cancel: soft delete (status=CANCELLED) for audit trail over hard delete
- Admin deactivation: revoke all refresh tokens immediately (15-min JWT window is acceptable for bookstore threat model)
- BookService.update_stock() calls PreBookRepository.notify_waiting_by_book() in the same transaction, returns email list to router for background task enqueueing (avoids circular imports)

From Phase 09 plan 01:
- [Phase 09-01]: MAIL_SUPPRESS_SEND defaults to 1 — safe for dev/test; production sets to 0 via env var
- [Phase 09-01]: plain-text fallback auto-generated via _strip_html() on rendered HTML — no separate .txt template files
- [Phase 09-01]: get_email_service() decorated with @lru_cache — FastMail reused across requests; tests call cache_clear() to reset
- [Phase 09-01]: EmailSvc = Annotated[EmailService, Depends(get_email_service)] is the injection pattern for all routers

From Phase 09 plan 02:
- [Phase 09-02]: record_messages() is a sync context manager in fastapi-mail 1.6.2 — use `with`, not `async with`, for outbox capture in tests
- [Phase 09-02]: _strip_html() bug fixed — block-level closing tags replaced with space before stripping to prevent text concatenation
- [Phase 09-02]: Integration email tests use an isolated FastAPI() with only AppError handler — no DB dependency for email-only tests

From Phase 10 plan 01:
- [Phase 10-01]: ActiveUser dependency does one DB round-trip per protected request for is_active check — accepted trade-off for immediate lockout (no JWT blacklisting needed)
- [Phase 10-01]: is_active check in login() placed AFTER password verification — prevents timing-based account status enumeration attacks
- [Phase 10-01]: get_active_user uses local import of UserRepository inside function body — avoids circular import since deps.py is a widely-imported shared module
- [Phase 10-01]: Admin deactivation is blanket — ANY admin account (self or other) cannot be deactivated; returns 403 ADMN_CANNOT_DEACTIVATE_ADMIN
- [Phase 10-01]: Deactivation atomically sets is_active=False AND revokes ALL refresh tokens via bulk UPDATE — refresh endpoint also checks is_active so existing tokens are invalidated

From Phase 10 plan 02:
- [Phase 10-02]: Lockout tests use GET /cart as the access-token probe — cart uses ActiveUser so it enforces is_active on every request
- [Phase 10-02]: Self-deactivation test creates its own admin fixture inline to prevent test ordering dependencies on shared fixtures
- [Phase 10-02]: Test emails use unique prefixes per test class/case to avoid cross-test DB contamination within session-scoped engine

From Phase 11 plan 01:
- [Phase 11-01]: Partial unique index on (user_id, book_id) WHERE status='waiting' enforces one active pre-booking per book per user at DB level; allows re-reservation after cancellation
- [Phase 11-01]: notify_waiting_by_book uses bulk UPDATE with RETURNING clause — single atomic query transitions all waiting pre-bookings and returns user_ids for Phase 12 email dispatch
- [Phase 11-01]: PreBookRepository imported locally inside update_stock function body to avoid circular import (same pattern as get_active_user/UserRepository in deps.py)
- [Phase 11-01]: 0-to-positive transition check (old_qty == 0 and quantity > 0) prevents spurious re-notifications on subsequent quantity adjustments

From Phase 11 plan 02:
- [Phase 11-02]: SAEnum with StrEnum requires values_callable=lambda e: [v.value for v in e] — SQLAlchemy defaults to enum member names (uppercase) but Alembic migration creates lowercase values; model must match migration
- [Phase 11-02]: BookCreate schema has no stock_quantity field — in_stock_book fixture must POST book then PATCH /books/{id}/stock to set stock > 0
- [Phase 11-02]: Ordering assertions on created_at use set membership not positional — server_default=func.now() at millisecond granularity produces identical timestamps in fast sequential inserts

From Phase 12 plan 01:
- [Phase 12-01]: Email enqueue placed AFTER service.checkout()/set_stock_and_notify() — structural guarantee that no email fires on any failure path (EMAL-06 compliance)
- [Phase 12-01]: JWT payload has only sub+role (no email) — checkout fetches user from DB via UserRepository.get_by_id(user_id) to get recipient email address
- [Phase 12-01]: UserRepository.get_emails_by_ids() uses single IN query for batch email lookup in update_stock() — avoids N+1 queries for restock alerts
- [Phase 12-01]: UserRepository imported at module level in orders/router.py; local import inside update_stock() body in books/router.py following PreBookRepository pattern to avoid circular imports
- [Phase 12-01]: total_price is a Pydantic @computed_field on OrderResponse, not on ORM model — build OrderResponse.model_validate(order) BEFORE constructing email context

### Blockers/Concerns

None.

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-02-26
Stopped at: 12-01-PLAN.md complete — Email wiring (2 tasks, 5 files: 2 templates + UserRepository.get_emails_by_ids + checkout email + update_stock email). Phase 12 plan 1 of 2 done. Next: Phase 12-02 (email integration tests)
Resume file: None
