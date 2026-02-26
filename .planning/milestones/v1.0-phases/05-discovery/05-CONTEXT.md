# Phase 5: Discovery - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Public catalog browsing and search. Any visitor can browse the book catalog with pagination and sorting, search by title/author/genre using PostgreSQL full-text search, filter by genre or author, and view a book's full details including current stock status. No authenticated features — this is a read-only public layer on top of Phase 4's catalog.

</domain>

<decisions>
## Implementation Decisions

### Search behavior
- Prefix + full-text matching: PostgreSQL tsvector for full words, plus prefix matching for partial terms (e.g., 'tolk' matches 'Tolkien')
- Search covers title, author, and genre name — the three most common search intents
- Results ranked by relevance using ts_rank when a search query is present — title matches rank higher
- When no search query, results follow the requested sort order
- Plain results — no match highlighting or matched_on metadata; same book schema as browsing

### Claude's Discretion
- Pagination style (offset vs cursor) and default page size
- Available sort options and default sort order
- Filter design (which filters, how they combine)
- Book detail response shape (stock display format, metadata included)
- tsvector column configuration (generated column vs trigger, weight assignments)
- GIN index strategy

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

*Phase: 05-discovery*
*Context gathered: 2026-02-25*
