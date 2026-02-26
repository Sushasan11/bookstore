---
phase: 11-pre-booking
plan: "01"
subsystem: pre-booking
tags: [pre-booking, sqlalchemy, fastapi, alembic, migration, repository-pattern]
dependency_graph:
  requires: [app/books/repository.py, app/books/models.py, app/wishlist/repository.py, app/core/deps.py, app/db/base.py]
  provides: [app/prebooks/models.py, app/prebooks/repository.py, app/prebooks/service.py, app/prebooks/router.py, app/prebooks/schemas.py]
  affects: [app/books/service.py, app/books/router.py, app/main.py, alembic/env.py]
tech_stack:
  added: [PreBooking SQLAlchemy model, PreBookStatus StrEnum, Alembic migration with partial unique index]
  patterns: [StrEnum+SAEnum pattern (from orders), partial unique index with postgresql_where, bulk UPDATE with RETURNING, local import to avoid circular deps, same-transaction atomic notification]
key_files:
  created:
    - app/prebooks/__init__.py
    - app/prebooks/models.py
    - app/prebooks/repository.py
    - app/prebooks/service.py
    - app/prebooks/router.py
    - app/prebooks/schemas.py
    - alembic/versions/f1a2b3c4d5e6_create_pre_bookings.py
  modified:
    - alembic/env.py
    - app/books/service.py
    - app/books/router.py
    - app/main.py
decisions:
  - "Partial unique index on (user_id, book_id) WHERE status='waiting' enforces one active pre-booking per book per user while allowing re-reservation after cancellation"
  - "PreBookRepository.notify_waiting_by_book uses bulk UPDATE with RETURNING clause for atomic batch transition and user_id collection"
  - "PreBookRepository imported locally inside router function body to avoid circular import with books package"
  - "set_stock_and_notify fires notification ONLY on 0-to-positive stock transition (not any restock)"
  - "Soft-delete on cancel (status=CANCELLED with cancelled_at) preserves audit trail per STATE.md decision"
  - "get_all_for_user returns all statuses (waiting/notified/cancelled) — no server-side filtering, client decides"
metrics:
  duration: "316 seconds (~5 min)"
  completed_date: "2026-02-26"
  tasks_completed: 3
  files_created: 7
  files_modified: 4
---

# Phase 11 Plan 01: Pre-Booking Data Layer and API Summary

**One-liner:** PreBooking CRUD API with partial-unique-index duplicate guard, soft-cancel, and atomic restock-to-notification broadcast via bulk UPDATE RETURNING.

## What Was Built

Complete pre-booking feature: SQLAlchemy model with Alembic migration, full CRUD repository, business logic service, three REST endpoints, and BookService extension for atomic restock notification.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create PreBooking model, migration, and register in model discovery | bcc883b | app/prebooks/models.py, alembic/versions/f1a2b3c4d5e6_create_pre_bookings.py, alembic/env.py |
| 2 | Create PreBookRepository, PreBookService, schemas, and router | e1c71ff | app/prebooks/repository.py, app/prebooks/service.py, app/prebooks/schemas.py, app/prebooks/router.py, app/main.py |
| 3 | Extend BookService.set_stock with restock notification broadcast | 1a48743 | app/books/service.py, app/books/router.py |

## Architecture Decisions

1. **Partial unique index** (`uq_pre_bookings_user_book_waiting`) on `(user_id, book_id) WHERE status='waiting'` is the critical constraint — enforces one active pre-booking per (user, book) at DB level while allowing unlimited historical records after cancellation.

2. **Atomic notification** — `notify_waiting_by_book` uses a single bulk `UPDATE ... RETURNING user_id` within the same transaction as the stock update. If stock update fails, notifications are rolled back automatically.

3. **Local circular import avoidance** — `PreBookRepository` is imported inside the `update_stock` function body in `app/books/router.py` (pattern from `get_active_user` in `app/core/deps.py`). `TYPE_CHECKING` guard used in `app/books/service.py` for the type hint.

4. **0-to-positive transition only** — `set_stock_and_notify` checks `old_qty == 0 and quantity > 0`. Restocking a book that already has stock does NOT re-notify (avoids spam for subsequent quantity adjustments).

5. **Soft-delete cancel** — `status=CANCELLED` with `cancelled_at` timestamp preserves audit trail; the partial unique index allows re-reservation because the WAITING constraint no longer applies to CANCELLED records.

6. **Phase 12 wiring** — `notified_user_ids` captured in `update_stock` endpoint but not yet used. Comment documents exactly where email enqueueing goes in Phase 12.

## API Endpoints

| Method | Path | Auth | Status | Description |
|--------|------|------|--------|-------------|
| POST | /prebooks | ActiveUser | 201 | Create pre-booking for out-of-stock book |
| GET | /prebooks | ActiveUser | 200 | List all user's pre-bookings (all statuses) |
| DELETE | /prebooks/{id} | ActiveUser | 204 | Cancel (soft-delete) a pre-booking |

## Business Rules Enforced

- **409 PREBOOK_BOOK_IN_STOCK** — Cannot pre-book a book with stock > 0 (add to cart instead)
- **409 PREBOOK_DUPLICATE** — Cannot create duplicate active pre-booking for same book (partial unique index)
- **404 PREBOOK_NOT_FOUND** — Cancelling non-existent or other user's pre-booking returns 404 (ownership without disclosure)
- **409 PREBOOK_ALREADY_CANCELLED** — Cannot cancel an already-cancelled pre-booking

## Deviations from Plan

None — plan executed exactly as written. All locked decisions from STATE.md followed:
- Local import pattern for circular import avoidance
- 0-to-positive transition trigger only
- Soft-delete cancel with audit trail
- Same-transaction atomic notification

## Self-Check

Files created verification:
- `app/prebooks/models.py` — FOUND
- `app/prebooks/repository.py` — FOUND
- `app/prebooks/service.py` — FOUND
- `app/prebooks/router.py` — FOUND
- `app/prebooks/schemas.py` — FOUND
- `alembic/versions/f1a2b3c4d5e6_create_pre_bookings.py` — FOUND

Commits verified:
- bcc883b — Task 1 feat commit
- e1c71ff — Task 2 feat commit
- 1a48743 — Task 3 feat commit

## Self-Check: PASSED
