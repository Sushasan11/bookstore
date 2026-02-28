---
phase: 21-catalog-and-search
plan: "03"
subsystem: ui
tags: [nextjs, react, ssr, isr, seo, json-ld, open-graph, shadcn]

requires:
  - phase: 21-01
    provides: catalog.ts helpers (fetchBook, fetchBooks, fetchGenres), BookCard component, BookDetailResponse type

provides:
  - book-detail-page-isr
  - json-ld-book-schema
  - open-graph-metadata
  - breadcrumb-nav-component
  - book-detail-hero-component
  - rating-display-component
  - action-buttons-placeholder
  - more-in-genre-component

affects: [21-04-search-page, 22-cart, 24-wishlist, 25-reviews]

tech-stack:
  added: []
  patterns:
    - "React.cache() wraps fetchBook so generateMetadata and page component share the same cached request"
    - "ISR via export const revalidate = 3600 — hourly revalidation"
    - "JSON-LD XSS-safe via JSON.stringify().replace(/</g, '\\u003c')"
    - "notFound() for invalid book IDs renders Next.js 404 page"
    - "Disabled button placeholders establish layout for future phases"

key-files:
  created:
    - frontend/src/app/books/[id]/page.tsx
    - frontend/src/app/books/[id]/_components/BookDetailHero.tsx
    - frontend/src/app/books/[id]/_components/BreadcrumbNav.tsx
    - frontend/src/app/books/[id]/_components/RatingDisplay.tsx
    - frontend/src/app/books/[id]/_components/ActionButtons.tsx
    - frontend/src/app/books/[id]/_components/MoreInGenre.tsx
  modified: []

key-decisions:
  - "React.cache() deduplicates fetchBook between generateMetadata and the page component — avoids double fetch per request"
  - "ActionButtons are fully disabled placeholders — Phase 22 (cart) and Phase 24 (wishlist) will enable them"
  - "RatingDisplay uses Unicode star characters rather than SVG for simplicity; includes Phase 25 TODO comment for review section link"
  - "MoreInGenre fetches size=7 then filters out current book and slices to 6 — avoids separate count query"

patterns-established:
  - "Book detail pages use ISR (revalidate=3600) as the caching pattern"
  - "JSON-LD script tags use dangerouslySetInnerHTML with < -> \\u003c XSS escaping"
  - "generateMetadata uses React.cache-wrapped fetch to share server-side data with page component"

requirements-completed: [CATL-02, CATL-06, CATL-07]

duration: ~10min
completed: 2026-02-27
---

# Phase 21 Plan 03: Book Detail Page Summary

**ISR book detail page at /books/[id] with JSON-LD Book schema, Open Graph metadata, two-column hero layout, breadcrumb navigation, star rating display, disabled cart/wishlist placeholders, and related books section.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-27T15:53:47Z
- **Completed:** 2026-02-27T16:03:00Z
- **Tasks:** 2
- **Files modified:** 6 (all created)

## Accomplishments

- Book detail page at `/books/[id]` with ISR (revalidate=3600) and React.cache deduplication between generateMetadata and page
- JSON-LD Book schema (schema.org) with offers, aggregateRating, XSS-safe `<` escaping; Open Graph tags for social sharing
- Five sub-components: two-column hero, breadcrumb, star rating, disabled action buttons, related books grid
- Production build passes with `/books/[id]` as a dynamic ISR route

## Task Commits

Each task was committed atomically:

1. **Task 1: Create book detail page with ISR, generateMetadata, and JSON-LD** - `804c40e` (feat)
2. **Task 2: Create BookDetailHero, BreadcrumbNav, RatingDisplay, ActionButtons, MoreInGenre** - `840f1e8` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/app/books/[id]/page.tsx` - ISR page with generateMetadata (Open Graph), JSON-LD Book schema, notFound() for 404, related books fetch
- `frontend/src/app/books/[id]/_components/BookDetailHero.tsx` - Two-column cover+details layout; cover image (LCP priority) or deterministic color placeholder; price, stock badge, metadata grid
- `frontend/src/app/books/[id]/_components/BreadcrumbNav.tsx` - Home > Genre > Title breadcrumbs; genre links to /catalog?genre_id={id}; skips genre if null
- `frontend/src/app/books/[id]/_components/RatingDisplay.tsx` - 5-star display (full/half/empty) with review count; "No reviews yet" when no data
- `frontend/src/app/books/[id]/_components/ActionButtons.tsx` - Disabled "Add to Cart" (ShoppingCart icon) and "Add to Wishlist" (Heart icon) with "Coming soon" note
- `frontend/src/app/books/[id]/_components/MoreInGenre.tsx` - Responsive grid (2/4/6 cols) of up to 6 same-genre BookCards; null when empty

## Decisions Made

### Decision 1: React.cache() for Request Deduplication

**Decision:** Wrap `fetchBook` with `React.cache()` so `generateMetadata` and the page component share a single cached call per request.

**Rationale:** Without caching, the book would be fetched twice per page render — once by `generateMetadata` and once by the page component. React.cache() is the idiomatic Next.js App Router pattern for this.

### Decision 2: ActionButtons as Disabled Placeholders

**Decision:** Both "Add to Cart" and "Add to Wishlist" buttons are rendered with `disabled` attribute. No click handlers or state.

**Rationale:** CATL-07 requires these to be present as layout placeholders. Phase 22 (cart) and Phase 24 (wishlist) will enable the interactivity when those subsystems exist.

### Decision 3: MoreInGenre Fetch Strategy

**Decision:** Fetch `size=7`, filter out the current book, slice to 6.

**Rationale:** Fetching size=7 ensures that even after removing the current book, up to 6 related books remain. Avoids a separate count query or complex server-side exclusion parameter.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `/books/[id]` page is live with ISR, SEO metadata, and all layout components
- ActionButtons are placeholders — Phase 22 (cart) and Phase 24 (wishlist) enable them
- RatingDisplay has Phase 25 TODO comment for linking to the reviews section
- Phase 21 Plan 04 (search page) can proceed independently

---
*Phase: 21-catalog-and-search*
*Completed: 2026-02-27*

## Self-Check: PASSED

### Files Created
- [x] frontend/src/app/books/[id]/page.tsx — FOUND
- [x] frontend/src/app/books/[id]/_components/BookDetailHero.tsx — FOUND
- [x] frontend/src/app/books/[id]/_components/BreadcrumbNav.tsx — FOUND
- [x] frontend/src/app/books/[id]/_components/RatingDisplay.tsx — FOUND
- [x] frontend/src/app/books/[id]/_components/ActionButtons.tsx — FOUND
- [x] frontend/src/app/books/[id]/_components/MoreInGenre.tsx — FOUND

### Commits
- [x] 804c40e — Task 1 (page.tsx with ISR, generateMetadata, JSON-LD) FOUND
- [x] 840f1e8 — Task 2 (all sub-components) FOUND

### Verifications
- [x] `npx tsc --noEmit` — 0 errors
- [x] `npm run build` — Succeeded, /books/[id] registered as dynamic ISR route
