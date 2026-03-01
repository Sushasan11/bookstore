---
phase: 26-admin-foundation
plan: 02
subsystem: ui
tags: [next.js, tanstack-query, shadcn, admin, dashboard, kpi, analytics]

# Dependency graph
requires:
  - "26-01 (admin layout shell, SidebarProvider, defense-in-depth auth)"
provides:
  - "frontend/src/lib/admin.ts: adminKeys query key factory, 3 fetch functions, 4 TypeScript types"
  - "/admin/overview page with 4 KPI cards, period selector, delta badges, low-stock amber card"
  - "Top-5 best-sellers mini-table with rank, title, author, revenue"
  - "Reusable admin fetch layer for phases 27-29 to import"
affects:
  - "27-sales-analytics (imports adminKeys, fetchSalesSummary, fetchTopBooks)"
  - "28-book-catalog-crud (imports adminKeys for catalog mutations/invalidation)"
  - "29-user-management-review-moderation (imports adminKeys for user/review queries)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "adminKeys hierarchical query key factory: ['admin', 'sales', 'summary', period] enables scoped invalidation"
    - "DeltaBadge inline helper component: null/0 -> grey dash, positive -> green triangle, negative -> red triangle"
    - "Period selector: segmented button group with useState driving TanStack Query key change for automatic refetch"
    - "Low-stock card: amber accent with border-amber-500/50 bg-amber-500/5 and Link to /admin/inventory"

key-files:
  created:
    - "frontend/src/lib/admin.ts"
    - "frontend/src/app/admin/overview/page.tsx"
  modified: []

key-decisions:
  - "No table UI component installed — used clean HTML <table> with Tailwind classes (table.tsx not present, not needed for this simple use case)"
  - "Period selector uses Button variant='ghost' for inactive and variant='default' for active (matches plan spec)"
  - "All three queries share the same accessToken from useSession — no per-query session fetching"
  - "Loading skeletons sized to match value + delta layout for minimal layout shift on data load"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-05]

# Metrics
duration: ~3min
completed: 2026-02-28
---

# Phase 26 Plan 02: Admin Data Layer and Dashboard Overview Summary

**Admin fetch layer (`src/lib/admin.ts`) with TanStack Query key factory and dashboard overview page showing live KPI cards, period selector, delta badges, low-stock amber card, and top-5 best-sellers mini-table**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-28T14:15:51Z
- **Completed:** 2026-02-28T14:18:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `src/lib/admin.ts` with all 4 TypeScript types, `adminKeys` hierarchical query key factory, and 3 fetch functions (fetchSalesSummary, fetchTopBooks, fetchLowStock) each passing `Authorization: Bearer ${accessToken}`
- Created `/admin/overview` dashboard page as a `'use client'` component with 3 TanStack Query hooks, period state driving query key changes
- Built 4 KPI cards: Revenue ($X,XXX format), Orders (count), AOV (currency), Low Stock (amber accent with inventory link)
- Added `DeltaBadge` inline helper: green ▲ for positive, red ▼ for negative, grey — for zero/null
- Added loading skeleton states and error states with retry buttons for all queries
- Added top-5 best-sellers table with Rank, Title, Author, Revenue columns and loading/empty/error states
- Next.js build passes cleanly (`/admin/overview` renders as `ƒ Dynamic` server-rendered route)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create admin fetch layer with types and query key factory** — `7381926` (feat)
2. **Task 2: Build dashboard overview page with KPI cards, period selector, and mini-table** — `a51ceba` (feat)

## Files Created/Modified

- `frontend/src/lib/admin.ts` — TypeScript types (SalesSummaryResponse, TopBookEntry, TopBooksResponse, LowStockResponse), adminKeys factory, fetchSalesSummary/fetchTopBooks/fetchLowStock functions
- `frontend/src/app/admin/overview/page.tsx` — Client component: period state, 3 useQuery hooks, 4 KPI cards with skeletons/errors, DeltaBadge helper, best-sellers mini-table

## Decisions Made

- **No shadcn Table component needed:** `components/ui/table.tsx` was not present. Used a clean HTML `<table>` with Tailwind classes — appropriate for a simple 5-row read-only display.
- **Period selector uses Button component:** Used `variant="ghost"` for inactive and `variant="default"` for active state, wrapped in a rounded border container to form a segmented group appearance.
- **Low-stock card amber styling:** Used `border-amber-500/50 bg-amber-500/5` on the Card and `text-amber-600 dark:text-amber-400` on the value and link for consistent amber accent.

## Deviations from Plan

None — plan executed exactly as written. All must_haves satisfied:
- 4 KPI cards (Revenue, Orders, AOV, Low Stock) rendered in responsive grid
- Period selector toggles between Today/This Week/This Month
- Delta badge: green ▲ positive, red ▼ negative, grey — zero/null
- Currency formatted as whole dollars with comma separators
- Low-stock card with amber accent and link to /admin/inventory
- Top-5 best-sellers mini-table with Rank, Title, Author, Revenue

## User Setup Required

None.

## Next Phase Readiness

- `src/lib/admin.ts` is ready for import in phases 27-29 — provides all types, fetch functions, and query keys needed for sales analytics, catalog CRUD, and user management pages
- `/admin/overview` is live and protected by admin layout auth gate from Plan 01
- Period selector pattern established can be reused in Phase 27 sales analytics page

---

## Self-Check: PASSED

- `frontend/src/lib/admin.ts` — FOUND
- `frontend/src/app/admin/overview/page.tsx` — FOUND
- Commit `7381926` — FOUND (feat(26-02): create admin fetch layer with types and query key factory)
- Commit `a51ceba` — FOUND (feat(26-02): build dashboard overview page with KPI cards, period selector, and mini-table)
- Next.js build: PASSED (13/13 static pages generated, /admin/overview in route table)
- TypeScript: PASSED (npx tsc --noEmit with no errors)

---
*Phase: 26-admin-foundation*
*Completed: 2026-02-28*
