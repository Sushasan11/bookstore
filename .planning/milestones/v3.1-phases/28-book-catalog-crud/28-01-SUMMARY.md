---
phase: 28-book-catalog-crud
plan: "01"
subsystem: ui
tags: [react, nextjs, tanstack-table, react-hook-form, shadcn, admin, catalog]

# Dependency graph
requires:
  - phase: 27-sales-analytics-and-inventory-alerts
    provides: adminKeys hierarchy and established admin page patterns (debounce, mutation, toast)
  - phase: 26-admin-foundation
    provides: admin layout, sidebar, shared UI components (Button, Badge, Input, Select, Dialog)
provides:
  - Generic DataTable<TData> component using TanStack Table v8 with loading skeletons and empty state
  - AdminPagination component with Showing X-Y of Z text and Previous/Next navigation
  - adminKeys.catalog namespace (all, list(params), genres) in admin.ts
  - createBook, updateBook, deleteBook fetch functions in admin.ts
  - Working /admin/catalog page with paginated table, debounced search, genre filter, and row actions DropdownMenu
  - shadcn dropdown-menu.tsx component scaffolded
affects:
  - 28-book-catalog-crud plan 02 (wires BookForm, ConfirmDialog, StockModal to the catalog page built here)
  - 29-user-management (reuses DataTable and AdminPagination directly)

# Tech tracking
tech-stack:
  added:
    - "@tanstack/react-table ^8.21.3 — headless table logic for DataTable.tsx"
    - "react-hook-form ^7.71.2 — form state for Plan 02 BookForm (installed now to avoid second install)"
    - "@hookform/resolvers ^5.2.2 — bridges react-hook-form with zod schema validation"
    - "shadcn dropdown-menu.tsx — radix-ui DropdownMenu wrapper for row actions"
  patterns:
    - "DataTable<TData> generic component: useReactTable + getCoreRowModel + flexRender + manualPagination: true"
    - "AdminPagination: page/total/size props, totalPages = Math.ceil(total/size), 1-indexed"
    - "adminKeys.catalog.list(params) — object params as last key element for scoped invalidation"
    - "genreMap = new Map<number, string> from genres query for O(1) genre name lookup in table cells"
    - "StockBadge inline component: stock===0 red, stock<=10 amber, else plain number"

key-files:
  created:
    - frontend/src/components/admin/DataTable.tsx
    - frontend/src/components/admin/AdminPagination.tsx
    - frontend/src/components/ui/dropdown-menu.tsx
  modified:
    - frontend/src/lib/admin.ts (catalog namespace + createBook/updateBook/deleteBook)
    - frontend/src/app/admin/catalog/page.tsx (replaced placeholder with full page)

key-decisions:
  - "DataTable<TData> uses generic type parameter from the start — Phase 29 reuses it directly without modification"
  - "catalog page fetches genres separately (useQuery adminKeys.catalog.genres) to build genreMap for O(1) genre name display"
  - "Row action handlers are console.log placeholders in Plan 01 — Plan 02 replaces with BookForm, ConfirmDialog, StockModal"
  - "react-hook-form and @hookform/resolvers installed in Plan 01 despite only being used in Plan 02 — prevents mid-plan install step"
  - "enabled: !!accessToken on booksQuery — query waits for session hydration before firing"

patterns-established:
  - "DataTable: generic <TData> component with ColumnDef<TData, unknown>[] — set pattern for Phase 29"
  - "AdminPagination: reusable prev/next with Showing X-Y of Z text — matches backend 1-indexed page system"
  - "Page state resets to 1 in onChange handler (not useEffect) for search and genre changes"

requirements-completed: [CATL-01, CATL-02]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 28 Plan 01: Book Catalog CRUD - Table Infrastructure Summary

**TanStack Table-backed admin catalog page at /admin/catalog with paginated book table, debounced search, genre filter, and row actions DropdownMenu wired to placeholder handlers**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-01T04:05:29Z
- **Completed:** 2026-03-01T04:09:02Z
- **Tasks:** 2
- **Files modified:** 5 (+ 2 new components)

## Accomplishments
- Installed @tanstack/react-table, react-hook-form, @hookform/resolvers and scaffolded dropdown-menu.tsx
- Extended admin.ts with adminKeys.catalog namespace and createBook/updateBook/deleteBook fetch functions
- Created generic DataTable<TData> component with TanStack Table v8, loading skeleton rows, and empty state
- Created AdminPagination with "Showing X-Y of Z" text and Previous/Next buttons (disabled at boundaries)
- Replaced catalog page placeholder with full paginated table featuring all 6 required columns (Title, Author, Price, Genre, Stock, Actions)
- Next.js production build passes with /admin/catalog as dynamic route

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies, scaffold DropdownMenu, extend admin.ts** - `6622e0f` (feat)
2. **Task 2: Create DataTable, AdminPagination, and full catalog page** - `fb73c61` (feat)

**Plan metadata:** `(pending final docs commit)`

## Files Created/Modified
- `frontend/src/components/admin/DataTable.tsx` - Generic TanStack Table wrapper with loading skeletons and empty state
- `frontend/src/components/admin/AdminPagination.tsx` - Prev/next pagination with page count display
- `frontend/src/components/ui/dropdown-menu.tsx` - shadcn DropdownMenu wrapper (scaffolded via npx shadcn@latest add)
- `frontend/src/lib/admin.ts` - Added adminKeys.catalog namespace + createBook/updateBook/deleteBook
- `frontend/src/app/admin/catalog/page.tsx` - Full catalog page replacing placeholder

## Decisions Made
- DataTable uses `ColumnDef<TData, unknown>[]` (not `ColumnDef<TData>[]`) to satisfy TanStack Table v8 generic constraint
- `enabled: !!accessToken` on books query ensures session hydration before API call fires
- Genre filter uses Select with string value; converted to number on change (`Number(value)`)
- Row action handlers are `console.log` no-ops — Plan 02 replaces with real drawer/dialog state
- react-hook-form and @hookform/resolvers installed now (Plan 01) to avoid a second install mid-Plan 02 execution

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DataTable and AdminPagination are ready for Plan 02 to wire real handlers (BookForm, ConfirmDialog, StockModal)
- adminKeys.catalog is set; Plan 02 uses same keys for mutations and invalidation
- Phase 29 (User Management and Review Moderation) can import DataTable and AdminPagination directly
- No blockers.

---
*Phase: 28-book-catalog-crud*
*Completed: 2026-03-01*
