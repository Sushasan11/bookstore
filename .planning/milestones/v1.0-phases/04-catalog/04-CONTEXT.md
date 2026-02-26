# Phase 4: Catalog - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin CRUD for books and genre taxonomy with stock quantity tracking. This phase creates the data foundation that all downstream features (discovery, cart, orders, wishlist, pre-booking) depend on. No public-facing endpoints — those belong in Phase 5 (Discovery).

</domain>

<decisions>
## Implementation Decisions

### Book metadata & validation
- Required fields on creation: title, author, price
- Optional fields: ISBN, genre, description, cover image URL, publish date
- ISBN validated for ISBN-10 or ISBN-13 format with checksum when provided; rejected on invalid format
- Price must be > 0, stored as Numeric(10,2) — no free books
- ISBN has a unique constraint (when provided); titles are not unique — different editions of the same book are valid
- Cover image stored as URL string, not file upload

### Claude's Discretion
- Genre taxonomy design (flat vs hierarchical, single vs multi-genre per book)
- Stock management approach (absolute set vs increment/decrement on PATCH endpoint)
- Deletion strategy (hard delete vs soft delete, handling of referenced books)
- Response payload structure and pagination for admin list endpoints
- Validation error message format (consistent with existing auth error patterns)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing project patterns from Phase 2/3 (repository pattern, service layer, Pydantic schemas, require_admin dependency).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-catalog*
*Context gathered: 2026-02-25*
