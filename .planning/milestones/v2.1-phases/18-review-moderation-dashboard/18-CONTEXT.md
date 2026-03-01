# Phase 18: Review Moderation Dashboard - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin endpoints to list, filter, sort, and bulk-delete reviews for catalog quality moderation. Admins can view all non-deleted reviews with reviewer and book context, filter by book/user/rating range, sort by date or rating, and bulk soft-delete reviews. This phase builds on the existing Review model, soft-delete convention, and ReviewRepository from Phase 15.

</domain>

<decisions>
## Implementation Decisions

### Admin access control
- Any user with is_admin=True can access review moderation endpoints — matches existing admin endpoint pattern
- No superadmin or role hierarchy required
- No rate limiting on moderation endpoints
- No audit logging — soft-deleted reviews already have timestamps, audit trail is a separate concern

### Bulk delete semantics
- Maximum 50 review IDs per bulk delete request
- Best-effort deletion: delete what can be deleted, silently skip missing or already-deleted IDs
- Response returns count of successfully deleted reviews

### Claude's Discretion
- Response shape for admin review list (what reviewer/book context to include per review)
- Filter interaction semantics (AND vs OR for combined filters)
- Default sort order for the review list
- Error response format for invalid filter values
- Pagination implementation details

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-review-moderation-dashboard*
*Context gathered: 2026-02-27*
