# Phase 13: Review Data Layer - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the `reviews` table in PostgreSQL with correct constraints, the `Review` SQLAlchemy model, `ReviewRepository` with all data-access operations, and `OrderRepository.has_user_purchased_book()` for verified-purchase checking. This phase delivers the data foundation — no API endpoints, no moderation UI, no notifications.

</domain>

<decisions>
## Implementation Decisions

### Review model fields
- Single `text` body field — no separate title/headline column
- Review text is optional (nullable) — users can submit rating-only reviews
- Max 2000 characters on review text (use `String(2000)` or `VARCHAR(2000)`)
- Soft-delete via `deleted_at` timestamp column — deleted reviews are filtered out by default but preserved for auditing
- Standard timestamps: `created_at`, `updated_at`

### Claude's Discretion
- Rating column type and constraints (integer 1-5 per roadmap success criteria)
- Repository interface design: pagination style, filter parameters, aggregate method signature
- Purchase verification logic: what order statuses qualify as "purchased"
- Default sort ordering for review list queries
- Whether aggregate computation is live query or cached

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing codebase patterns for models, repositories, and migrations.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-review-data-layer*
*Context gathered: 2026-02-26*
