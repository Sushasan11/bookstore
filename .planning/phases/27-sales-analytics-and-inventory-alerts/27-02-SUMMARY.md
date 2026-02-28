---
phase: 27-sales-analytics-and-inventory-alerts
plan: "02"
subsystem: ui
tags: [react, tanstack-query, shadcn, debounce, inventory]

# Dependency graph
requires:
  - phase: 27-01
    provides: adminKeys.inventory.lowStock, fetchLowStock, LowStockResponse — built in Plan 01

provides:
  - updateBookStock function in admin.ts (PATCH /books/{book_id}/stock)
  - Enhanced Inventory Alerts page with Badge pills, debounced threshold input, and stock update modal

affects:
  - 28-book-catalog-crud
  - 29-user-management-review-moderation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - useDebounce from use-debounce (already installed) for 500ms query key debouncing on threshold changes
    - Badge className override (bg-red-100, bg-amber-100) — no new variants, per RESEARCH.md Pattern 6
    - useMutation with queryClient.invalidateQueries on adminKeys.inventory.all for scoped cache bust
    - Modal state resets in onOpenChange to prevent stale data between different book selections

key-files:
  created: []
  modified:
    - frontend/src/lib/admin.ts
    - frontend/src/app/admin/inventory/page.tsx

key-decisions:
  - "Badge className override used for red/amber stock status pills — no new shadcn variants added"
  - "thresholdInput (raw) vs debouncedThreshold (query key) separation ensures 500ms debounce applies to both preset clicks and manual typing"
  - "Modal state (selectedBook, newQuantity) reset on onOpenChange to prevent stale data when switching between books"

patterns-established:
  - "StockBadge inline helper component: stock===0 -> red Out of Stock badge, stock<=threshold -> amber Low Stock (N) badge"
  - "Preset buttons + free-form Input share the same thresholdInput state; debounce applied uniformly to both"

requirements-completed: [INVT-01, INVT-02, INVT-03]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 27 Plan 02: Sales Analytics and Inventory Alerts (Inventory Enhancements) Summary

**Inventory Alerts page enhanced with shadcn Badge pills for stock status, debounced free-form threshold input alongside preset buttons, and a Dialog modal with useMutation for in-place stock updates**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T17:17:12Z
- **Completed:** 2026-02-28T17:19:05Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `updateBookStock` to `admin.ts` — wraps PATCH /books/{book_id}/stock with standard admin auth pattern
- `StockBadge` helper component with red pill for out-of-stock and amber pill with count for low stock
- Free-form threshold `<Input type="number">` with 500ms `useDebounce` drives query key and queryFn, while preset buttons (5, 10, 20) remain as quick shortcuts
- "Update Stock" `<Button variant="outline" size="sm">` on each table row opens a `<Dialog>` modal showing book title, current stock, and a quantity input
- `useMutation` calls `updateBookStock`, invalidates `adminKeys.inventory.all` on success (covers all threshold cache variants), shows sonner toast, closes modal

## Task Commits

Each task was committed atomically:

1. **Task 1: Add updateBookStock function to admin.ts** - `ffa8229` (feat)
2. **Task 2: Enhance Inventory Alerts page** - `1ee6830` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/lib/admin.ts` - Added `updateBookStock(accessToken, bookId, quantity)` function exporting via PATCH /books/{bookId}/stock
- `frontend/src/app/admin/inventory/page.tsx` - Full enhancement: StockBadge, debounced Input, preset buttons, 5-column table, Dialog modal, useMutation

## Decisions Made

- Badge className override (bg-red-100, bg-amber-100) used for stock status pills — no new shadcn badge variants needed, follows RESEARCH.md Pattern 6
- `thresholdInput` (raw state) vs `debouncedThreshold` (query key) separation — debounce applies uniformly to both preset button clicks and manual typing
- Modal `onOpenChange` resets both `selectedBook` and `newQuantity` to prevent stale data when opening modal for a different book

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 27 complete: Sales Analytics page and Inventory Alerts page both fully built
- Phase 28 (Book Catalog CRUD) can begin — no blockers

## Self-Check: PASSED

- `frontend/src/lib/admin.ts` — FOUND
- `frontend/src/app/admin/inventory/page.tsx` — FOUND
- Commit `ffa8229` (Task 1) — FOUND
- Commit `1ee6830` (Task 2) — FOUND

---
*Phase: 27-sales-analytics-and-inventory-alerts*
*Completed: 2026-02-28*
