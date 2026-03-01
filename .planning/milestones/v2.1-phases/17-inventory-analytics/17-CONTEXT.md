# Phase 17: Inventory Analytics - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Admins can answer "what do I need to restock?" by querying books at or below a configurable stock threshold. Delivers a single endpoint: `GET /admin/analytics/inventory/low-stock`. Sales velocity, restock recommendations, and supplier integration are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Response data shape
- Minimal fields per book: book_id, title, author, current_stock, threshold
- No extended fields (price, category, ISBN) — keep it focused on restocking decisions
- Include `total_low_stock` count at the top level for dashboard summary use

### Default threshold
- Default threshold value: 10 when `?threshold=` parameter is not provided
- Threshold is optional query parameter, not required

### Zero-stock handling
- No special distinction between out-of-stock (0) and low-stock (>0 but below threshold)
- All books at or below threshold in one flat list, ordered by stock ascending
- Zero-stock books naturally sort to top — no extra flag needed

### Claude's Discretion
- Pagination strategy (if needed based on typical catalog size)
- Response schema naming conventions (match existing analytics patterns from Phase 16)
- Repository query approach (reuse existing book queries or dedicated method)
- Error handling for invalid threshold values

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow patterns established in Phase 16 sales analytics.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-inventory-analytics*
*Context gathered: 2026-02-27*
