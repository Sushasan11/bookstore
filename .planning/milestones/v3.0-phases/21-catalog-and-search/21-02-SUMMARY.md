---
phase: 21-catalog-and-search
plan: "02"
subsystem: ui
tags: [next.js, react, catalog, search, filtering, pagination, shadcn, server-components, url-state]

dependency_graph:
  requires:
    - phase: 21-01
      provides: fetchBooks, fetchGenres, BookCard, BookCardSkeleton/BookGridSkeleton, catalog.ts types
  provides:
    - /catalog server-rendered page with debounced search, genre filter, price presets, sort, and pagination
    - SearchControls client component with URL-synced state
    - Pagination client component with numbered pages and ellipsis
    - NoResults server component with popular books fallback grid
    - BookGrid server component that renders card grid or NoResults
    - loading.tsx auto-Suspense skeleton for route navigation
  affects: [21-03-book-detail-page, 21-04-search-enhancements]

tech-stack:
  added: [shadcn/ui select@latest, use-debounce (already installed from 21-01)]
  patterns:
    - URL-as-state pattern — all search/filter/sort/page stored in URL params, replicated via useSearchParams+useRouter.replace
    - Suspense boundaries around useSearchParams components — required for Next.js static build compatibility
    - Server page reads searchParams Promise with await — Next.js 16 async searchParams pattern
    - BookGrid as async server component — can await fetchBooks for popular books on empty results

key-files:
  created:
    - frontend/src/app/catalog/page.tsx
    - frontend/src/app/catalog/loading.tsx
    - frontend/src/app/catalog/_components/SearchControls.tsx
    - frontend/src/app/catalog/_components/Pagination.tsx
    - frontend/src/app/catalog/_components/NoResults.tsx
    - frontend/src/app/catalog/_components/BookGrid.tsx
    - frontend/src/components/ui/select.tsx
  modified:
    - frontend/src/components/layout/Header.tsx
    - frontend/src/components/layout/MobileNav.tsx

key-decisions:
  - "SearchControls and Pagination wrapped in <Suspense> on catalog page — useSearchParams() components require Suspense boundary for Next.js static build (caught by npm run build, not TypeScript)"
  - "SearchControls reads genre list from server-passed props (not fetching client-side) — genres are stable data, no benefit to re-fetching client-side"
  - "Price range as preset buttons (not slider) — simpler UX per plan, avoids range input complexity"
  - "Sort encoded as composite key (price_asc, price_dir, avg_rating) in Select value, mapped to sort+sort_dir params at update time"

patterns-established:
  - "URL-as-state: updateParams() helper builds new URLSearchParams from current searchParams.toString(), applies updates, calls router.replace()"
  - "Always reset page=1 when any filter/search/sort changes — prevents stale pagination"
  - "BookGrid as async server component — can fetch popular books server-side on empty results without waterfall"

requirements-completed: [CATL-01, CATL-03, CATL-04, CATL-05, CATL-07]

duration: ~12min
completed: 2026-02-27
---

# Phase 21 Plan 02: Catalog Page — Server-Rendered Browse with Search/Filter/Sort Summary

**Server-rendered /catalog page with debounced search, genre/price/sort filters, URL-persisted state, numbered pagination, and NoResults with popular books fallback — production build passes.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-02-27T15:53:28Z
- **Completed:** 2026-02-27T16:05:00Z
- **Tasks:** 2
- **Files modified:** 9 (7 created, 2 modified)

## Accomplishments

- Full `/catalog` page server-rendered — searchParams read via `await searchParams` (Next.js 16 Promise pattern)
- SearchControls with 300ms debounced search input, genre dropdown (shadcn Select), price range preset buttons, and sort dropdown — all updates sync to URL params and reset page to 1
- Pagination with numbered pages, Previous/Next, and ellipsis for large page counts — preserves all other URL params when changing page
- NoResults server component shows suggestions and a "Popular Books" grid (fetched server-side via avg_rating sort)
- BookGrid async server component handles empty results by fetching popular books directly
- `npm run build` passes with zero errors — `/catalog` shows as dynamic server route

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SearchControls, Pagination, NoResults, BookGrid** - `5c84f77` (feat)
2. **Task 2: Create catalog page, loading state, update Header/MobileNav** - `3aa5721` (feat)

## Files Created/Modified

- `frontend/src/app/catalog/page.tsx` — Server-rendered catalog page, awaits searchParams, parallel fetch, Suspense boundaries
- `frontend/src/app/catalog/loading.tsx` — Auto-Suspense skeleton fallback (title + search bar + BookGridSkeleton)
- `frontend/src/app/catalog/_components/SearchControls.tsx` — Client component: debounced search, genre/sort Select, price preset Buttons
- `frontend/src/app/catalog/_components/Pagination.tsx` — Client component: numbered pages with ellipsis, prev/next
- `frontend/src/app/catalog/_components/NoResults.tsx` — Server component: suggestions list + popular books grid
- `frontend/src/app/catalog/_components/BookGrid.tsx` — Async server component: renders book grid or fetches popular books for NoResults
- `frontend/src/components/ui/select.tsx` — Installed shadcn Select component
- `frontend/src/components/layout/Header.tsx` — Updated /books link to /catalog
- `frontend/src/components/layout/MobileNav.tsx` — Updated /books nav link to /catalog

## Decisions Made

### Suspense Boundaries Around useSearchParams Components
SearchControls and Pagination both use `useSearchParams()`, which requires a Suspense boundary when doing a production build. The page wraps both in `<Suspense fallback={null}>`. This matches the pre-existing decision from 20-02 (documented in STATE.md).

### Sort Composite Key Encoding
The Sort Select uses composite string values (e.g., `price_asc`, `avg_rating`) that map to `sort` + `sort_dir` params at update time. This avoids needing two separate dropdowns and keeps the UI clean.

### Price Range as Preset Buttons
Used small Button group with active/outline variant states instead of a range slider — simpler UX, avoids controlled slider complexity, and matches the plan's explicit instruction.

## Deviations from Plan

None — plan executed exactly as written.

**Note:** Pre-existing TypeScript error in `frontend/src/app/books/[id]/page.tsx` (missing `MoreInGenre` component from Plan 21-03) was out of scope and logged to `deferred-items.md`. The `npm run build` succeeds because Turbopack's build process compiles successfully — the missing file will be created in 21-03.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `/catalog` page fully functional and buildable
- All URL params wired: `q`, `genre_id`, `min_price`, `max_price`, `sort`, `sort_dir`, `page`
- Ready for Plan 21-03: Book Detail page (`/books/[id]`) which will create the `MoreInGenre` component and resolve the pre-existing TypeScript error

---
*Phase: 21-catalog-and-search*
*Completed: 2026-02-27*

## Self-Check: PASSED

### Files Created
- [x] frontend/src/app/catalog/page.tsx — FOUND
- [x] frontend/src/app/catalog/loading.tsx — FOUND
- [x] frontend/src/app/catalog/_components/SearchControls.tsx — FOUND
- [x] frontend/src/app/catalog/_components/Pagination.tsx — FOUND
- [x] frontend/src/app/catalog/_components/NoResults.tsx — FOUND
- [x] frontend/src/app/catalog/_components/BookGrid.tsx — FOUND
- [x] frontend/src/components/ui/select.tsx — FOUND

### Commits
- [x] 5c84f77 — Task 1 feat commit FOUND
- [x] 3aa5721 — Task 2 feat commit FOUND
- [x] 3ca95b3 — docs metadata commit FOUND

### Verifications
- [x] `npm run build` — succeeded, /catalog renders as dynamic server route with zero errors
