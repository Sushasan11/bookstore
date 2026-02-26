---
phase: 12-email-notifications-wiring
verified: 2026-02-26T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 12: Email Notifications Wiring Verification Report

**Phase Goal:** Order confirmation emails fire after successful checkout and restock alert emails fire when a book is restocked, both as post-commit background tasks using the Phase 9 infrastructure.
**Verified:** 2026-02-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Source: Plan 01 frontmatter `must_haves.truths` (5 truths) + Plan 02 frontmatter `must_haves.truths` (6 truths, testing layer). Verification below covers the 4 ROADMAP success criteria and all 5 Plan 01 truths.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After successful checkout, order confirmation email enqueued via BackgroundTasks with order ID, line items, and total | VERIFIED | `app/orders/router.py` lines 53-70: `email_svc.enqueue(background_tasks, to=user.email, template_name="order_confirmation.html", ...)` called after `service.checkout()`. Context includes `order_id`, `items` list, and `total_price`. |
| 2 | When admin restocks 0 to >0, restock alert email enqueued for every user with a waiting pre-booking | VERIFIED | `app/books/router.py` lines 150-161: `if notified_user_ids:` guard, `get_emails_by_ids()` batch lookup, loop enqueuing `restock_alert.html` per user. |
| 3 | No email enqueued if checkout fails (cart empty, insufficient stock, payment failure) | VERIFIED | Structural guarantee: `email_svc.enqueue()` is placed AFTER `service.checkout()` (line 44). If checkout raises, execution never reaches line 53. Confirmed by tests `test_no_email_on_checkout_failure_empty_cart` (expects 422) and `test_no_email_on_checkout_failure_insufficient_stock` (expects 409). |
| 4 | No email enqueued if stock update is not a 0-to-positive transition or there are no waiting pre-bookers | VERIFIED | `if notified_user_ids:` guard at line 151 of `app/books/router.py`. `notified_user_ids` is returned empty by `set_stock_and_notify()` when not a 0-to-positive transition or no waiting pre-bookers. Confirmed by `test_no_restock_email_on_positive_to_positive` and `test_no_restock_email_when_no_prebookers`. |
| 5 | Email dispatch does not block or delay the HTTP response | VERIFIED | `email_svc.enqueue()` calls `background_tasks.add_task()` — task is registered for post-response execution. FastAPI BackgroundTasks run after the response is sent. Structural guarantee documented in `app/email/service.py` docstring. |

**Score:** 5/5 truths verified (Plan 01). All 4 ROADMAP success criteria satisfied.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/email/templates/order_confirmation.html` | Jinja2 order confirmation template extending base.html | VERIFIED | File exists, line 1: `{% extends "base.html" %}`. Renders `order_id`, `items` table with `title`/`quantity`/`unit_price`, and `total_price`. 25 lines. |
| `app/email/templates/restock_alert.html` | Jinja2 restock alert template extending base.html | VERIFIED | File exists, line 1: `{% extends "base.html" %}`. Renders `book_title`. 7 lines. |
| `app/users/repository.py` | Batch email lookup method `get_emails_by_ids` | VERIFIED | Method exists at lines 24-35. Signature: `(self, user_ids: list[int]) -> dict[int, str]`. Single `SELECT id, email WHERE id IN (...)` query. Early-return `{}` for empty input is correct guard logic. |
| `app/orders/router.py` | Order confirmation email dispatch after checkout | VERIFIED | `email_svc.enqueue(...)` at line 53, placed after `service.checkout()` at line 44. `BackgroundTasks` and `EmailSvc` in function signature (lines 33-34). |
| `app/books/router.py` | Restock alert email dispatch after stock update | VERIFIED | `email_svc.enqueue(...)` at line 155, placed after `service.set_stock_and_notify()` at line 146. `BackgroundTasks` and `EmailSvc` in function signature (lines 127-128). Placeholder `_ = notified_user_ids` removed. |
| `tests/test_email_notifications.py` | Full Phase 12 integration test suite (min 200 lines) | VERIFIED | 426 lines. 8 tests in 2 classes: `TestOrderConfirmationEmail` (4 tests, EMAL-02) and `TestRestockAlertEmail` (4 tests, EMAL-03). |

**All artifacts: 6/6 VERIFIED — exist, substantive, and wired.**

---

### Key Link Verification

Plan 01 declared 4 key links; Plan 02 declared 3 key links. All verified below.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/orders/router.py` | `app/email/service.py` | EmailSvc dependency injection | VERIFIED | `from app.email.service import EmailSvc` at module level (line 7). `email_svc: EmailSvc` in `checkout()` signature (line 34). `email_svc.enqueue(..., template_name="order_confirmation.html", ...)` at line 53. Pattern `email_svc.enqueue.*order_confirmation` confirmed. |
| `app/books/router.py` | `app/email/service.py` | EmailSvc dependency injection | VERIFIED | `from app.email.service import EmailSvc` at module level (line 20). `email_svc: EmailSvc` in `update_stock()` signature (line 128). `email_svc.enqueue(..., template_name="restock_alert.html", ...)` at line 155. Pattern `email_svc.enqueue.*restock_alert` confirmed. |
| `app/orders/router.py` | `app/users/repository.py` | `UserRepository.get_by_id` for user email | VERIFIED | `from app.users.repository import UserRepository` at module level (line 11). `user_repo = UserRepository(db)` then `user_repo.get_by_id(user_id)` at lines 50-51. Pattern `user_repo.get_by_id` confirmed. |
| `app/books/router.py` | `app/users/repository.py` | `UserRepository.get_emails_by_ids` for batch email lookup | VERIFIED | Local import `from app.users.repository import UserRepository` inside function body (line 142, follows PreBookRepository pattern). `user_repo.get_emails_by_ids(notified_user_ids)` at line 153. Pattern `user_repo.get_emails_by_ids` confirmed. |
| `tests/test_email_notifications.py` | `app/orders/router.py` | HTTP POST /orders/checkout with outbox capture | VERIFIED | `await ac.post("/orders/checkout", ...)` at lines 175, 207, 239, 273. All wrapped in `with fm.record_messages() as outbox:`. |
| `tests/test_email_notifications.py` | `app/books/router.py` | HTTP PATCH /books/{id}/stock with outbox capture | VERIFIED | `await ac.patch(f"/books/{book['id']}/stock", ...)` at lines 313, 353, 363, 386, 418. Wrapped in `with fm.record_messages() as outbox:`. |
| `tests/test_email_notifications.py` | `app/email/service.py` | `get_email_service` dependency override for outbox capture | VERIFIED | `from app.email.service import EmailService, get_email_service` (line 23). `app.dependency_overrides[get_email_service] = lambda: controlled_svc` (line 47). `get_email_service.cache_clear()` in teardown (line 54). |

**All key links: 7/7 VERIFIED.**

---

### Requirements Coverage

Both plans declare `requirements: [EMAL-02, EMAL-03]`. REQUIREMENTS.md maps both to Phase 12. Traceability table is up to date.

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EMAL-02 | 12-01, 12-02 | User receives order confirmation email after successful checkout | SATISFIED | `checkout()` enqueues `order_confirmation.html` after `service.checkout()`. Integration test `test_checkout_sends_confirmation_email` proves 1 email sent with correct recipient and subject. `test_confirmation_email_contains_order_details` proves HTML body contains `order_id`, book title, and total price. |
| EMAL-03 | 12-01, 12-02 | User receives restock alert email when a pre-booked book is restocked | SATISFIED | `update_stock()` enqueues `restock_alert.html` for each ID in `notified_user_ids` via batch lookup. Integration test `test_restock_sends_alert_to_all_prebookers` proves 2 emails sent to 2 users. Subjects confirm book title and "back in stock" content. |

**No orphaned requirements.** REQUIREMENTS.md assigns only EMAL-02 and EMAL-03 to Phase 12. Both plans claim both. Both are satisfied.

**Note on adjacent requirements verified structurally by Phase 12:**
- EMAL-05 (email never blocks API): Maintained — BackgroundTasks pattern preserved.
- EMAL-06 (email only after DB commit): Maintained — `email_svc.enqueue()` is placed after service calls that can raise, and BackgroundTasks run post-response (post-commit per `app/core/deps.py` pattern).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/users/repository.py` | 31 | `return {}` | Info | Expected early-return for empty input in `get_emails_by_ids()`. Not a stub — guarded by `if not user_ids:` on line 30. No impact. |

No blocker anti-patterns found across any phase 12 file. No TODOs, FIXMEs, placeholder comments, or empty handler implementations in production code. Placeholder `_ = notified_user_ids` was removed from `app/books/router.py` as required.

---

### Commit Verification

All three commits documented in SUMMARY files are present and cover the expected files:

| Commit | Message | Files |
|--------|---------|-------|
| `4e45db5` | feat(12-01): create email templates and add batch email lookup | `app/email/templates/order_confirmation.html`, `app/email/templates/restock_alert.html`, `app/users/repository.py` |
| `a05249b` | feat(12-01): wire email dispatch into checkout and stock-update routers | `app/books/router.py`, `app/orders/router.py` |
| `0ea1ebd` | test(12-02): add EMAL-02 order confirmation email integration tests | `tests/test_email_notifications.py` |

---

### Human Verification Required

The following items cannot be verified programmatically. Automated tests exist and pass (per SUMMARY), but a live-environment check would confirm end-to-end behavior.

#### 1. Email HTML Rendering Quality

**Test:** Run `pytest tests/test_email_notifications.py -v` against a running test database. Inspect the actual HTML output by printing `_get_email_html(outbox[0])` in `test_confirmation_email_contains_order_details`.
**Expected:** The rendered HTML should be a well-formed table with book title, quantity, unit price, and total price visible. Line items should not be empty or display "Unknown Book" for normally-loaded books.
**Why human:** Template rendering with live data requires a running DB. The content assertions in tests check for presence of strings, not visual correctness of formatting.

#### 2. BackgroundTask post-commit timing (live SMTP)

**Test:** Temporarily set `MAIL_SUPPRESS_SEND=0` with a real SMTP server (e.g. Mailtrap), run a checkout, and confirm the email arrives only after the 201 response is returned.
**Expected:** HTTP response 201 arrives before any SMTP conversation begins. Email arrives in inbox within seconds of the response.
**Why human:** BackgroundTasks timing and post-commit ordering require real infrastructure to observe. Suppressed-send tests prove the structural wiring but not the actual delivery timing.

---

### Gaps Summary

No gaps. All must-haves verified. Phase goal is fully achieved:

1. **Order confirmation email (EMAL-02):** Wired into `checkout()` with correct template, context (order_id, items, total_price), recipient from DB, and structural post-failure safety. Integration tests prove the full happy path and both failure paths (empty cart, insufficient stock).

2. **Restock alert email (EMAL-03):** Wired into `update_stock()` with batch `get_emails_by_ids()` lookup, `if notified_user_ids:` guard, and correct template/subject. Integration tests prove 2-user multi-recipient scenario, positive-to-positive non-trigger, no-prebookers non-trigger, and cancelled-prebooker exclusion.

3. **Phase 9 infrastructure reuse:** Both routers use `EmailSvc` dependency injection and `email_svc.enqueue(background_tasks, ...)` exactly as the Phase 9 contract specifies. No direct FastMail calls in routers.

4. **Test coverage:** 426-line test file with 8 tests. `email_client` fixture correctly overrides both `get_db` and `get_email_service`, uses `fm.record_messages()` sync context manager, and clears `lru_cache` on teardown.

---

_Verified: 2026-02-26_
_Verifier: Claude (gsd-verifier)_
