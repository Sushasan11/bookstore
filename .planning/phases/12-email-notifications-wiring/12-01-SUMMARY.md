---
phase: 12-email-notifications-wiring
plan: 01
subsystem: api
tags: [email, fastapi-mail, jinja2, background-tasks, orders, catalog]

# Dependency graph
requires:
  - phase: 09-email-infrastructure
    provides: EmailService.enqueue(), EmailSvc dependency alias, Jinja2 template rendering
  - phase: 11-prebooks
    provides: set_stock_and_notify() returns notified_user_ids for email dispatch
  - phase: 07-orders
    provides: checkout() service, OrderResponse schema with computed total_price
provides:
  - order_confirmation.html Jinja2 email template
  - restock_alert.html Jinja2 email template
  - UserRepository.get_emails_by_ids() batch lookup method
  - checkout() router wired with order confirmation email dispatch
  - update_stock() router wired with restock alert email dispatch
affects: [12-email-notifications-wiring/12-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Email enqueue placed AFTER service call — structural guarantee that email never fires on failure paths"
    - "total_price computed from OrderResponse (Pydantic computed_field), not ORM model — build OrderResponse before building email context"
    - "UserRepository.get_emails_by_ids() for batch email lookup — single IN query avoids N+1 per notified user"
    - "UserRepository imported at module level in orders/router.py; local import inside update_stock() body in books/router.py to avoid circular imports"

key-files:
  created:
    - app/email/templates/order_confirmation.html
    - app/email/templates/restock_alert.html
  modified:
    - app/users/repository.py
    - app/orders/router.py
    - app/books/router.py

key-decisions:
  - "Email enqueue is structurally after service call — if checkout/set_stock_and_notify raises, execution never reaches enqueue (EMAL-06 compliance)"
  - "DB fetch for user email in checkout (user_repo.get_by_id) since JWT payload has only sub+role, not email"
  - "Batch get_emails_by_ids() for restock alerts — single IN query for all notified users, not N individual get_by_id calls"
  - "UserRepository imported at module level in orders/router.py (no circular risk); local import in books/router.py update_stock() body following existing PreBookRepository pattern"

patterns-established:
  - "Order confirmation email: build OrderResponse first (for total_price computed_field), then enqueue with order_id, items list, total_price context"
  - "Restock alert email: guard with if notified_user_ids before batch lookup — skips query when no pre-bookers notified"

requirements-completed: [EMAL-02, EMAL-03]

# Metrics
duration: 3min
completed: 2026-02-26
---

# Phase 12 Plan 01: Email Notifications Wiring Summary

**Order confirmation email wired into checkout via BackgroundTasks, and restock alert emails wired into stock-update with batch user email lookup — closing EMAL-02 and EMAL-03**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T12:10:13Z
- **Completed:** 2026-02-26T12:13:50Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Created two Jinja2 HTML email templates (order_confirmation.html, restock_alert.html) extending base.html
- Added UserRepository.get_emails_by_ids() batch query method for N+1-free email lookup
- Wired checkout() in orders/router.py to enqueue order confirmation email with order_id, items, and total_price after successful checkout
- Wired update_stock() in books/router.py to enqueue restock alert emails for all notified pre-bookers using a single IN query

## Task Commits

Each task was committed atomically:

1. **Task 1: Create email templates and add batch email lookup to UserRepository** - `4e45db5` (feat)
2. **Task 2: Wire email dispatch into checkout and stock-update routers** - `a05249b` (feat)

**Plan metadata:** (docs commit after summary)

## Files Created/Modified
- `app/email/templates/order_confirmation.html` - Jinja2 order confirmation template with order_id, items table (title/qty/price), and total_price
- `app/email/templates/restock_alert.html` - Jinja2 restock alert template with book_title and link prompt
- `app/users/repository.py` - Added get_emails_by_ids() method — single IN query returning {user_id: email} dict
- `app/orders/router.py` - checkout() now has BackgroundTasks + EmailSvc params; enqueues order_confirmation.html after service.checkout() succeeds
- `app/books/router.py` - update_stock() now has BackgroundTasks + EmailSvc params; enqueues restock_alert.html for each notified user via batch email lookup

## Decisions Made
- Email enqueue is placed AFTER service.checkout() / service.set_stock_and_notify() — structural guarantee that no email fires on error paths (cart empty, insufficient stock, payment failure, etc.)
- JWT payload does not contain email; checkout fetches user from DB via UserRepository.get_by_id(user_id) to get recipient address
- Batch get_emails_by_ids() used in update_stock() — single SQL IN query for all notified_user_ids rather than looping get_by_id(); returns empty dict for empty input (guard is handled at if notified_user_ids level)
- UserRepository imported at module level in orders/router.py (no circular import risk); imported locally inside update_stock() function body in books/router.py following the existing PreBookRepository local-import pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test suite (test_orders.py, test_prebooks.py, test_catalog.py) requires a running PostgreSQL server (ConnectionRefusedError). This is a pre-existing infrastructure constraint — Docker DB not running in this environment. The email tests (test_email.py) which do not require DB all pass (10/10). Code imports verified via `poetry run python -c "from ... import ..."` assertions.

## User Setup Required

None - no external service configuration required. MAIL_SUPPRESS_SEND defaults to 1 in dev/test.

## Next Phase Readiness
- Email wiring complete. Order confirmation (EMAL-02) and restock alert (EMAL-03) are fully wired.
- Phase 12 Plan 02 can proceed — integration tests for the email dispatch in checkout and stock-update flows.
- Templates render via Jinja2 (verified). Router signatures confirmed correct via reflection.

## Self-Check: PASSED

All files exist, all commits found, all content artifacts verified:
- app/email/templates/order_confirmation.html: FOUND, extends base.html
- app/email/templates/restock_alert.html: FOUND, extends base.html
- app/users/repository.py: FOUND, get_emails_by_ids method present
- app/orders/router.py: FOUND, email_svc.enqueue present
- app/books/router.py: FOUND, email_svc.enqueue present, placeholder removed
- Commit 4e45db5: FOUND
- Commit a05249b: FOUND

---
*Phase: 12-email-notifications-wiring*
*Completed: 2026-02-26*
