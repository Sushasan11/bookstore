# Phase 11: Pre-booking - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can reserve out-of-stock books, view and cancel their reservations, and all waiting pre-bookers are notified (status updated) when admin restocks the book. Email notifications for restock alerts are wired in Phase 12 — this phase handles the data model, status transitions, and API endpoints only.

</domain>

<decisions>
## Implementation Decisions

### Reservation behavior
- Pre-booking is ONLY allowed when book stock_quantity == 0; reject with 409 if stock > 0 ("Book is in stock — add to cart instead")
- Duplicate pre-booking for the same book by the same user is rejected (one active pre-booking per user per book)
- Cancellation is non-permanent: a user who cancels can re-reserve the same book (new pre-booking record) as long as the book is still out of stock
- Status update only on restock — no auto-add to cart; user must manually add to cart after being notified

### Restock notification flow
- Notify ALL waiting pre-bookers when stock transitions from 0 to >0 (not limited to stock quantity; first-come-first-served at cart/checkout)
- Restock trigger fires ONLY on 0→>0 transition; adding stock to an already-in-stock book does nothing to pre-bookings
- Status transition (waiting → notified with notified_at timestamp) happens atomically in the SAME DB transaction as the stock update
- Once notified is final: subsequent restocks do NOT re-notify already-notified pre-bookings; only 'waiting' status transitions

### Claude's Discretion
- Max pre-bookings per user limit (if any) — Claude picks a reasonable approach
- Pre-booking list sorting and detail level
- Cancellation soft-delete implementation details (status field values, timestamps)
- Whether cancelled pre-bookings appear in the user's list or are filtered out by default

</decisions>

<specifics>
## Specific Ideas

- Pre-booking cancel uses soft delete (status=CANCELLED) for audit trail — locked decision from v1.1 planning in STATE.md
- BookService.update_stock() calls PreBookRepository.notify_waiting_by_book() in the same transaction, returns email list to router for background task enqueueing — locked decision from v1.1 planning in STATE.md (avoids circular imports)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-pre-booking*
*Context gathered: 2026-02-26*
