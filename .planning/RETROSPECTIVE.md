# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Pre-booking, Notifications & Admin

**Shipped:** 2026-02-26
**Phases:** 4 | **Plans:** 8 | **Sessions:** 1

### What Was Built
- Async email infrastructure with fastapi-mail, Jinja2 templates, plain-text fallback, BackgroundTasks dispatch
- Admin user management: paginated list with role/active filtering, deactivate/reactivate with immediate lockout
- Pre-booking system: reserve/view/cancel out-of-stock books, atomic restock broadcast notification
- Transactional emails: order confirmation after checkout, restock alerts to all waiting pre-bookers

### What Worked
- Wave-based parallel execution kept orchestrator context lean while subagents got fresh 200k each
- Phase verification after each execute-phase caught issues early (e.g., multipart email structure fix)
- Explicit interfaces in PLANs (exact signatures, import paths) eliminated guesswork for executors
- Batch email lookup pattern (single IN query) avoided N+1 from the start — no retrofit needed

### What Was Inefficient
- ROADMAP.md plan checkboxes not updated by executors (still showed `[ ]` after completion) — manual fix needed at milestone close
- 11-01 SUMMARY showed `requirements-completed: []` (empty) despite completing all PRBK requirements — frontmatter inconsistency caught by audit cross-reference
- Phase 12 `book_id` passed in restock email context but never rendered in template — dead-weight context key

### Patterns Established
- Email enqueue AFTER service call: structural guarantee that no email fires on failure paths
- Local imports inside function bodies for cross-module repository access (avoids circular imports)
- `get_email_service.cache_clear()` in test teardown for lru_cache-decorated singletons
- `fm.record_messages()` is a sync context manager in fastapi-mail 1.6.2 (not async)
- Partial unique index for "one active per user" constraints (pre-booking)

### Key Lessons
1. JWT payloads should stay minimal (sub + role only) — fetch user details from DB when needed for emails
2. Pydantic `@computed_field` values are only available on the schema, not the ORM model — build response before constructing email context
3. fastapi-mail wraps multipart/alternative in multipart/mixed — recursive traversal needed for HTML body extraction in tests

### Cost Observations
- Model mix: ~10% opus (orchestrator), ~90% sonnet (executors, verifiers, checkers)
- Sessions: 1 (entire milestone in single context)
- Notable: 4 phases executed, verified, and audited in one session

---

## Milestone: v2.0 — Reviews & Ratings

**Shipped:** 2026-02-27
**Phases:** 3 | **Plans:** 5 | **Sessions:** 1

### What Was Built
- Review model with unique/check constraints, full repository (7 async methods), and purchase verification gate
- Complete review CRUD endpoints: create with purchase gate + duplicate 409, list (paginated), get, update (PATCH), delete (soft-delete)
- Ownership enforcement + admin moderation bypass on update/delete
- Live avg_rating and review_count aggregates on book detail endpoint
- 62 integration tests across 3 test files covering all 10 requirements

### What Worked
- Interfaces block in PLANs (exact code snippets from codebase) gave executors zero-ambiguity context
- Phase 14 verification caught missing `selectinload(Review.book)` in list_for_book — fixed before Phase 15 started
- 3-source requirements cross-reference (VERIFICATION + SUMMARY frontmatter + traceability table) caught no gaps — clean milestone
- Single-session execution: plan + execute + verify + audit for all 3 phases without /clear

### What Was Inefficient
- ROADMAP.md Progress table formatting drifted (Phase 13-14 rows had misaligned columns) — needs standardization
- `summary-extract --fields one_liner` returned null for all summaries — extractor doesn't parse bold header lines, required manual grep
- Phase 14 VERIFICATION body said "gaps_found" but frontmatter was updated to "passed" after fix — body/frontmatter inconsistency

### Patterns Established
- `_UNSET` sentinel for PATCH endpoints: distinguishes "not provided" from explicit null via `model_fields_set`
- Cross-domain repo injection in router: ReviewRepository in books router, OrderRepository in ReviewService — avoids circular imports
- Dict-merge `model_validate({**orm_attrs, **computed})` when ORM object lacks fields needed by response schema
- DuplicateReviewError registered before AppError — specific exception handlers must precede general ones
- Re-fetch after update via `get_by_id()` instead of `session.refresh()` when selectinload is needed

### Key Lessons
1. Eager-load auditing is critical in async SQLAlchemy — every relationship access must be covered by selectinload or the query will silently work when objects are cached but fail in production
2. Exception handler registration order in FastAPI matters — more specific handlers must be added before general ones
3. Dict-based model_validate is the right pattern when response schemas include fields not present on the ORM model

### Cost Observations
- Model mix: ~10% opus (orchestrator), ~90% sonnet (executors, verifiers, checkers)
- Sessions: 1 (entire milestone in single context)
- Notable: 3 phases + audit + UAT completed in one session (~35 min total execution)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multiple | 8 | Initial project setup, established patterns |
| v1.1 | 1 | 4 | Wave-based execution, integration audit |
| v2.0 | 1 | 3 | Interfaces block in PLANs, 3-source req cross-reference |

### Cumulative Quality

| Milestone | Tests | LOC | New Tests |
|-----------|-------|-----|-----------|
| v1.0 | 121 | 6,763 | 121 |
| v1.1 | 179 | 9,473 | 58 |
| v2.0 | 240 | 12,010 | 62 |

### Top Lessons (Verified Across Milestones)

1. Explicit interface contracts in plans (signatures, imports, types) dramatically reduce executor deviations
2. Structural guarantees (ordering, guards) are more reliable than runtime checks for correctness invariants
3. Eager-load auditing is critical in async SQLAlchemy — phase verification catches missing selectinloads before they hit production
