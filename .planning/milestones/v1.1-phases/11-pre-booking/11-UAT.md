---
status: complete
phase: 11-pre-booking
source: [11-01-SUMMARY.md, 11-02-SUMMARY.md]
started: 2026-02-26T12:00:00Z
updated: 2026-02-26T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Pre-book an out-of-stock book
expected: POST /prebooks with a book_id for a book with stock_quantity=0 returns 201. Response body includes id, book_id, status "waiting", and created_at timestamp.
result: pass

### 2. Reject pre-booking for in-stock book
expected: POST /prebooks with a book_id for a book with stock_quantity > 0 returns 409 with error code "PREBOOK_BOOK_IN_STOCK".
result: pass

### 3. Reject duplicate pre-booking
expected: POST /prebooks twice for the same out-of-stock book. First returns 201, second returns 409 with error code "PREBOOK_DUPLICATE".
result: pass

### 4. List all pre-bookings
expected: GET /prebooks returns 200 with a list of the user's pre-bookings. Each entry includes book_title, book_author, status, and created_at. All statuses (waiting, notified, cancelled) are shown.
result: pass

### 5. Cancel a pre-booking
expected: DELETE /prebooks/{id} for an owned waiting pre-booking returns 204. Subsequent GET /prebooks shows that pre-booking with status "cancelled".
result: pass

### 6. Re-reserve after cancellation
expected: After cancelling a pre-booking for a book, POST /prebooks with the same book_id returns 201 (new pre-booking created). The partial unique index allows this because the old record is cancelled.
result: pass

### 7. Restock notification broadcast
expected: Admin PATCHes /books/{id}/stock from 0 to a positive number. All pre-bookings with status "waiting" for that book atomically transition to status "notified" with a notified_at timestamp. GET /prebooks reflects the updated statuses.
result: pass

### 8. No notification on non-zero restock
expected: Admin PATCHes /books/{id}/stock on a book that already has stock > 0 (e.g., from 5 to 10). Any pre-bookings for that book remain unchanged — no status transitions occur.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
