---
status: complete
phase: 12-email-notifications-wiring
source: 12-01-SUMMARY.md, 12-02-SUMMARY.md
started: 2026-02-26T13:00:00Z
updated: 2026-02-26T13:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Order confirmation email after checkout
expected: After a successful checkout (POST /orders/checkout), exactly one email is sent to the user's email address. The subject contains "confirmed". The email HTML body contains the order ID, book title(s), quantities, prices, and total price.
result: pass

### 2. No email on failed checkout (empty cart)
expected: When checkout is attempted with an empty cart, the request fails (422) and no email is sent at all.
result: pass

### 3. No email on failed checkout (insufficient stock)
expected: When checkout is attempted with more items than available stock, the request fails (409) and no email is sent.
result: pass

### 4. Restock alert emails to all pre-bookers
expected: When an admin restocks a book from 0 to a positive quantity, every user who has a waiting pre-booking for that book receives a restock alert email. Subject mentions the book title. Two pre-bookers should receive two separate emails.
result: pass

### 5. No restock email on positive-to-positive stock update
expected: When an admin updates stock from one positive value to another positive value (e.g., 5 to 10), no restock alert email is sent — only the 0-to-positive transition triggers emails.
result: pass

### 6. No restock email when no pre-bookers exist
expected: When an admin restocks a book from 0 to positive but nobody has pre-booked it, no email is sent.
result: pass

### 7. Cancelled pre-bookers not emailed on restock
expected: When a user pre-books a book and then cancels, and the admin later restocks that book from 0 to positive, the cancelled pre-booker does NOT receive an email.
result: pass

### 8. Email dispatch does not block HTTP response
expected: The checkout and stock-update endpoints return their HTTP response without waiting for email delivery. Emails are dispatched via FastAPI BackgroundTasks, so response times are unaffected.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
