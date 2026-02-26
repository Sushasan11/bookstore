---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Pre-booking, Notifications & Admin
status: unknown
last_updated: "2026-02-26T05:35:40.347Z"
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 10 — Admin User Management

## Current Position

Phase: 10 of 12 (Admin User Management)
Plan: 1 of 1 in current phase — COMPLETE
Status: In progress
Last activity: 2026-02-26 — 10-01 Admin user management (admin /users endpoints, ActiveUser lockout, repo extensions) complete

Progress: [█████████░░░░░░░░░░░] 50% (v1.0 complete — 8/12 phases done; Phases 9-10 plan 01 complete)

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

### Blockers/Concerns

- [Phase 12 pre-work]: JWT payload contains sub (user_id) and role but not email. Order confirmation and restock alert require user email. Decide before Phase 12 planning: add email to JWT claims vs. DB fetch at router. Both are correct — must be decided explicitly.

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-02-26
Stopped at: 10-01-PLAN.md complete — Admin user management endpoints, ActiveUser lockout enforcement, repository extensions. Phase 10 plan 01 complete. Next: Phase 10 plan 02 or next phase
Resume file: None
