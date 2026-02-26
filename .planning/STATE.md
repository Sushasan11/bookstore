---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Pre-booking, Notifications & Admin
status: ready_to_plan
last_updated: "2026-02-26"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 9 — Email Infrastructure

## Current Position

Phase: 9 of 12 (Email Infrastructure)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-26 — 09-01 Email infrastructure core (EmailService, MAIL_* settings, base.html) complete

Progress: [████████░░░░░░░░░░░░] 42% (v1.0 complete — 8/12 phases done)

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

### Blockers/Concerns

- [Phase 12 pre-work]: JWT payload contains sub (user_id) and role but not email. Order confirmation and restock alert require user email. Decide before Phase 12 planning: add email to JWT claims vs. DB fetch at router. Both are correct — must be decided explicitly.

### Pending Todos

None yet.

## Session Continuity

Last session: 2026-02-26
Stopped at: 09-01-PLAN.md complete — EmailService, MAIL_* config, base.html template. Next: 09-02 integration tests
Resume file: None
