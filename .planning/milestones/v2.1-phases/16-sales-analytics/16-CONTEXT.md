# Phase 16: Sales Analytics - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

API endpoints that let admins answer "how is the store performing?" through revenue summary with period-over-period comparison and top-seller rankings. Two endpoints: sales summary and top-selling books. Only CONFIRMED orders count.

</domain>

<decisions>
## Implementation Decisions

### Period Definitions
- All periods are UTC-based (no timezone configuration)
- "today" = UTC midnight (00:00) of current day to now
- "week" = ISO week, Monday 00:00 UTC to now; previous week = full Mon-Sun
- "month" = calendar month, 1st of month 00:00 UTC to now; previous month = full prior calendar month
- Period comparison (delta %) compares current partial period against full previous period

### Revenue Calculation
- Revenue = unit_price × quantity from order_items (price at time of order, not current catalog price)
- No discounts or tax exist in the system — revenue is straightforward sum
- AOV = total revenue / order count (simple division, no exclusions)
- Revenue figures returned as decimals with 2 decimal places (e.g., 149.99), using Decimal type to avoid float issues

### Edge Cases & Zero-data
- Zero orders in a period → return zeroed response: {revenue: 0.00, order_count: 0, aov: 0.00, delta_percentage: null}
- Previous period has zero revenue, current has revenue → delta_percentage: null (can't calculate % change from zero)
- Top-books: default limit 10, accept ?limit=N up to max 50
- Top-books: all-time rankings only (no period filter) — matches requirements scope

### Claude's Discretion
- Query optimization strategy (raw SQL vs ORM aggregation)
- Response schema field naming conventions
- Error handling for invalid period values
- Test data setup approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing codebase patterns for admin endpoints (established in Phase 10).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-sales-analytics*
*Context gathered: 2026-02-27*
