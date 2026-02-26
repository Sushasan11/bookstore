---
phase: 12-email-notifications-wiring
plan: 02
subsystem: testing
tags: [fastapi-mail, pytest, integration-tests, email, outbox, background-tasks]

# Dependency graph
requires:
  - phase: 12-01-email-notifications-wiring
    provides: email dispatch wired into checkout and update_stock routers, EmailService.enqueue pattern
  - phase: 11-01-pre-booking-data-layer
    provides: PreBookRepository.notify_waiting_by_book, restock notification broadcast

provides:
  - Integration test suite proving order confirmation emails fire after checkout (EMAL-02)
  - Integration test suite proving restock alert emails fire after stock replenishment (EMAL-03)
  - email_client fixture: AsyncClient + EmailService dependency override for outbox capture
  - Verified: no email sent on any failure/error path (EMAL-06)

affects: [future-email-features, ci-pipeline, emal-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "email_client fixture overrides both get_db AND get_email_service to give test control over outbox"
    - "_get_email_html() recursively traverses nested multipart/mixed > multipart/alternative structure"
    - "fm.record_messages() wrapped only around the target HTTP call to isolate email capture per test"

key-files:
  created:
    - tests/test_email_notifications.py
  modified: []

key-decisions:
  - "email_client overrides get_email_service with lambda (not fixture) — ensures exact EmailService instance is captured before AsyncClient context opens"
  - "get_email_service.cache_clear() called in email_client teardown to reset lru_cache between tests"
  - "_get_email_html uses recursive traversal — fastapi-mail wraps multipart/alternative in outer multipart/mixed envelope"
  - "fm.record_messages() context wraps only the restock PATCH call — pre-book POSTs do not send emails so isolation is clean"

patterns-established:
  - "TestOrderConfirmationEmail / TestRestockAlertEmail class grouping matches EMAL requirement IDs"
  - "enotif_ prefix on all email notification test email addresses prevents DB contamination with other modules"

requirements-completed: [EMAL-02, EMAL-03]

# Metrics
duration: 9min
completed: 2026-02-26
---

# Phase 12 Plan 02: Email Notifications Wiring — Integration Tests Summary

**8-test integration suite proving order confirmation and restock alert emails fire through the real HTTP stack with fm.record_messages() outbox capture, including all failure/non-email paths**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-26T12:17:09Z
- **Completed:** 2026-02-26T12:26:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created `tests/test_email_notifications.py` (426 lines) with `email_client` fixture overriding both `get_db` and `get_email_service`
- Proved EMAL-02: checkout sends exactly 1 confirmation email with correct recipient, subject, order_id, title, and total_price
- Proved EMAL-03: restock sends alert to all 2 waiting pre-bookers; no email on positive-to-positive, no pre-bookers, or cancelled pre-booking
- All 178 tests in full suite pass with zero failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Create email notification integration test fixtures and order confirmation tests (EMAL-02)** - `0ea1ebd` (test)

Note: Both EMAL-02 (Task 1) and EMAL-03 (Task 2) test classes were written in a single file during Task 1 execution. Both classes are present in the commit `0ea1ebd`.

**Plan metadata:** (docs commit — see state updates below)

## Files Created/Modified

- `tests/test_email_notifications.py` - Full email notification integration test suite with `email_client` fixture, helper functions, `TestOrderConfirmationEmail` (4 tests), and `TestRestockAlertEmail` (4 tests)

## Decisions Made

- `_get_email_html()` uses recursive traversal because fastapi-mail wraps `multipart/alternative` inside a `multipart/mixed` outer envelope — simple list iteration over the top-level payload only reached the outer wrapper object
- `get_email_service.cache_clear()` added to `email_client` teardown to prevent lru_cache from leaking the test-controlled EmailService instance into subsequent tests
- `fm.record_messages()` context is placed only around the specific HTTP call being tested (e.g., the restock PATCH), never around pre-booking setup calls — prevents false positives from unrelated background emails

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `_get_email_html()` for nested multipart message structure**

- **Found during:** Task 1 (test_confirmation_email_contains_order_details was failing)
- **Issue:** fastapi-mail wraps `multipart/alternative` in an outer `multipart/mixed` envelope. The original `_get_email_html()` iterated only the top-level payload parts, reaching the `MIMEMultipart` wrapper object instead of the `text/html` content part.
- **Fix:** Rewrote `_get_email_html()` to recursively traverse all nesting levels until `text/html` content-type is found
- **Files modified:** `tests/test_email_notifications.py`
- **Verification:** `test_confirmation_email_contains_order_details` passes and HTML body correctly contains order_id, book title, and total_price
- **Committed in:** `0ea1ebd` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Auto-fix was essential for body content assertions to work. No scope creep.

## Issues Encountered

- **Test database not available on configured port 5433:** Docker Desktop was not running. A local PostgreSQL 18 instance was running on port 5432 with password 'admin'. Tests were run with `TEST_DATABASE_URL=postgresql+asyncpg://postgres:admin@127.0.0.1:5432/bookstore_test` environment variable override. The `bookstore_test` database already existed on this instance.

## User Setup Required

None - no external service configuration required beyond the test database already available.

## Next Phase Readiness

- Phase 12 is now fully complete (both plan 01 and plan 02 done)
- All email requirements (EMAL-01 through EMAL-06) are validated
- Full test suite (178 tests) passes — project is ready for v1.0 milestone conclusion

## Self-Check

- [x] `tests/test_email_notifications.py` exists (426 lines, above 200 minimum)
- [x] Commit `0ea1ebd` exists with test file
- [x] 8 email notification tests pass
- [x] Full suite (178 tests) passes

---
*Phase: 12-email-notifications-wiring*
*Completed: 2026-02-26*
