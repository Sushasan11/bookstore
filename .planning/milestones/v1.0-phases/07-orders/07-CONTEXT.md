# Phase 7: Orders - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Checkout with mock payment and race-condition-safe stock decrement, order history for users and admin. Covers COMM-03, COMM-04, COMM-05, ENGM-06. Cart (Phase 6) is already built; wishlist and pre-booking are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Checkout flow
- Single-step checkout: one POST `/orders/checkout` validates cart, processes mock payment, creates order, decrements stock, clears cart — all in one call
- No preview/confirm step — the mock payment context makes a single step sufficient

### Mock payment behavior
- Simulated outcomes — mock payment can succeed or fail (not always-approve)
- Support a mechanism for triggering failure (e.g., random ~10% failure rate or a test-friendly trigger like a special field)
- On payment failure: order is not created, stock is not decremented, cart is preserved
- Order gets a status reflecting the payment result

### Pre-checkout validations
- Cart must not be empty — reject with clear error if no items
- All cart items must have sufficient stock at checkout time (checked within the transaction after `SELECT FOR UPDATE`)
- If any item has insufficient stock: reject the entire order, return which items are short and available quantity
- No partial fulfillment — user must adjust cart and retry

### Stock insufficient handling
- Reject entire order (no partial fulfillment)
- Response should indicate which specific items failed and what stock is actually available, so the user can fix their cart

### Claude's Discretion
- Order status model (e.g., PENDING/CONFIRMED/PAYMENT_FAILED or simpler)
- Order confirmation response structure and fields
- Order history pagination, sorting, and detail level
- Admin orders endpoint — filtering, search, pagination approach
- Mock payment implementation details (random vs deterministic trigger)
- Exact error response shapes for checkout failures

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The roadmap already specifies `SELECT FOR UPDATE` with ascending ID order to prevent deadlocks and a `unit_price` snapshot field on order items.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-orders*
*Context gathered: 2026-02-25*
