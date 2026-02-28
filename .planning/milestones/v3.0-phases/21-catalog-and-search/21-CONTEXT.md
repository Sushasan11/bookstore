# Phase 21: Catalog and Search - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can browse, search, and filter the book catalog through SEO-optimized server-rendered pages. Includes: paginated book grid, book detail pages, full-text search, genre/price filters, URL-persisted state, JSON-LD and Open Graph SEO metadata, and ISR rendering. Does NOT include: cart functionality (Phase 22), wishlist actions (Phase 24), or review CRUD (Phase 25).

</domain>

<decisions>
## Implementation Decisions

### Catalog grid layout
- Book cover cards: prominent cover image with title, author, price below
- 4 cards per row on desktop, 2 per row on mobile
- Missing cover images: styled placeholder showing book title and author on a colored background
- No hero/banner section — page title, search bar, then straight into the grid

### Book detail page
- Cover-left, details-right layout (classic e-commerce two-column)
- Stacks vertically on mobile (cover on top, details below)
- Breadcrumbs: Home > Genre > Book Title
- Rating display: aggregate stars + review count only (clickable, but full review section is Phase 25)
- Action buttons: show "Add to Cart" and "Wishlist" as disabled placeholders — later phases enable them
- "More in this genre" section at the bottom: horizontal row of 4-6 same-genre books
- Metadata shown: ISBN, genre, publish date, description

### Search and filters UX
- Search bar at top of catalog page (not in global navbar)
- Inline dropdown filters in a horizontal bar: Genre, Price Range, Sort
- Debounced as-you-type search (~300ms after user stops typing)
- No-results state: friendly message ("No books found for X") with suggestions (check spelling, try broader search, browse genres) and popular books below

### Pagination and loading
- Classic numbered pagination (1, 2, 3... Next) with URL reflecting page number
- 20 books per page (5 rows of 4 on desktop)
- Skeleton card loading states matching grid layout while fetching
- Sort options: Relevance (default), Price low-to-high, Price high-to-low, Newest, Highest rated

### URL state persistence
- All search, filter, sort, and page state persisted in URL query params
- Bookmarkable and shareable: opening a shared URL reproduces exact results
- Example: `/catalog?q=fantasy&genre=fiction&sort=price_asc&page=2`

### SEO
- JSON-LD Book schema on detail pages
- Open Graph meta tags on detail pages
- Server-rendered with ISR for crawlability

### Claude's Discretion
- Card information density (which specific fields to show per card — cover, title, author, price are minimum; stars, stock badge, genre tag, review count are optional)
- Exact skeleton card design
- Price range filter implementation (slider vs preset ranges)
- Sort dropdown behavior details
- Breadcrumb styling
- Responsive breakpoints
- Error state handling (API failures, timeouts)

</decisions>

<specifics>
## Specific Ideas

- Cards should feel like a bookstore shelf — visual-first, cover images prominent
- Placeholder covers should use the book title and author on a styled colored background (not a generic icon)
- Disabled action buttons on detail page ensure the layout looks "complete" from day one, later phases just enable them

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-catalog-and-search*
*Context gathered: 2026-02-27*
