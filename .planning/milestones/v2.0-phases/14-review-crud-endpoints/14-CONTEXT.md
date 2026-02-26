# Phase 14: Review CRUD Endpoints - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

All review endpoints (create, read, update, delete) with verified-purchase enforcement and admin moderation. Users who purchased a book can submit one review with 1-5 star rating and optional text. Users can edit/delete their own reviews. Admins can delete any review. Paginated review listing per book. Aggregates and book detail integration are Phase 15.

</domain>

<decisions>
## Implementation Decisions

### Response shape
- Each review includes full author profile: user_id, display name, and avatar URL
- Each review includes book summary: book_id, title, and cover image URL
- Timestamps in ISO 8601 format only (e.g. `2026-02-26T14:30:00Z`) — frontend handles display formatting
- Review text field capped at 2000 characters, enforced at the API validation layer
- Response includes `verified_purchase: true/false` flag per the requirements

### Error responses
- Specific, descriptive error messages — e.g. "You must purchase this book before submitting a review"
- Structured error format with codes: `{"error": "DUPLICATE_REVIEW", "detail": "...", ...}`
  - Error codes: `NOT_PURCHASED` (403), `DUPLICATE_REVIEW` (409), `REVIEW_NOT_FOUND` (404), `NOT_REVIEW_OWNER` (403)
- 403 Forbidden for ownership violations (not 404) — honest response, user knows the review exists
- 409 duplicate response includes `existing_review_id` so frontends can redirect to edit flow

### Claude's Discretion
- Pagination approach (cursor vs offset) and default page size
- Sort options beyond created_at DESC
- Admin moderation implementation (soft-delete vs hard-delete)
- Exact Pydantic schema structure and naming conventions
- Service layer architecture and dependency injection patterns

</decisions>

<specifics>
## Specific Ideas

- 409 duplicate error should feel helpful, not blocking — include the existing review ID so the frontend can say "You already reviewed this book. Edit your review?"
- Error codes are structured so frontends can match on the code string rather than parsing message text

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-review-crud-endpoints*
*Context gathered: 2026-02-26*
