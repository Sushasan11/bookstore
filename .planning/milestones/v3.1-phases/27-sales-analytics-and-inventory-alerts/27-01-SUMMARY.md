---
phase: 27-sales-analytics-and-inventory-alerts
plan: "01"
subsystem: admin-sales-analytics
tags: [recharts, tanstack-query, next-dynamic, admin, sales]
dependency_graph:
  requires:
    - 26-admin-foundation (adminKeys, fetchSalesSummary, fetchTopBooks, useSession pattern)
  provides:
    - RevenueChart.tsx (two-bar Recharts comparison chart wrapped in ChartContainer)
    - Sales Analytics page at /admin/sales (full replacement of placeholder)
    - Updated adminKeys.sales.topBooks with sort_by cache key parameter
  affects:
    - frontend/src/app/admin/overview/page.tsx (topBooks call site updated)
    - frontend/src/lib/admin.ts (adminKeys factory extended)
tech_stack:
  added:
    - recharts ^2.15.4 (installed via shadcn chart CLI)
    - frontend/src/components/ui/chart.tsx (ChartContainer, ChartTooltip, ChartTooltipContent, ChartConfig)
  patterns:
    - next/dynamic with ssr: false for recharts components (prevents SSR hydration errors)
    - prior revenue derived from delta_percentage: revenue / (1 + delta/100) with null and -100 guards
    - adminKeys hierarchical factory extended with sort_by parameter for correct TanStack Query cache keying
key_files:
  created:
    - frontend/src/components/admin/RevenueChart.tsx
    - frontend/src/components/ui/chart.tsx
  modified:
    - frontend/src/app/admin/sales/page.tsx
    - frontend/src/lib/admin.ts
    - frontend/src/app/admin/overview/page.tsx
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "RevenueChart uses ChartContainer from shadcn chart.tsx for consistent styling and CSS variable color tokens"
  - "Prior revenue derived via formula rather than separate API call: priorRevenue = currentRevenue / (1 + delta/100)"
  - "Top-sellers table uses dynamic column header (Revenue vs Units Sold) based on sortBy state rather than showing both columns"
  - "Period card (4th KPI) shows selected period label as informational context rather than a delta-bearing metric"
requirements-completed: [SALE-01, SALE-02, SALE-03, SALE-04]
metrics:
  duration: "~5 minutes"
  completed: "2026-02-28"
  tasks_completed: 2
  files_created: 2
  files_modified: 5
---

# Phase 27 Plan 01: Sales Analytics Page Summary

**One-liner:** Two-bar Recharts revenue comparison chart with shadcn ChartContainer, KPI cards, and interactive top-sellers table with revenue/volume toggle and configurable row limit at /admin/sales.

## What Was Built

### Task 1: Install recharts, create RevenueChart, fix adminKeys

- Installed recharts ^2.15.4 via `npx shadcn@latest add chart --yes`, which created `src/components/ui/chart.tsx` with `ChartContainer`, `ChartTooltip`, `ChartTooltipContent`, and `ChartConfig`
- Fixed `adminKeys.sales.topBooks` in `src/lib/admin.ts` to accept `(limit, sort_by)` — this ensures TanStack Query creates separate cache entries for revenue-sorted vs volume-sorted results, preventing stale data on toggle
- Updated `overview/page.tsx` call site from `topBooks(5)` to `topBooks(5, 'revenue')` for backward compatibility
- Created `RevenueChart.tsx` as a `'use client'` component with `BarChart` and two `Bar` elements (current period + prior period) wrapped in `ChartContainer`. Shows "No prior period data available" note when `priorRevenue` is `null`

### Task 2: Build Sales Analytics page

- Replaced placeholder `/admin/sales` page with full Sales Analytics page
- `RevenueChart` imported via `next/dynamic({ ssr: false })` with `Skeleton` loading fallback — recharts cannot run server-side
- Period selector (Today / This Week / This Month) drives both KPI queries and chart data
- Four KPI cards: Revenue (with `DeltaBadge`), Orders (with `DeltaBadge`), Avg. Order Value (with `DeltaBadge`), Period context
- Prior revenue derivation: `priorRevenue = currentRevenue / (1 + delta/100)` with guards for `delta === null` and `delta === -100`
- Top-sellers table with Revenue/Volume sort toggle and 5/10/25 limit selector
- Column header dynamically switches between "Revenue" and "Units Sold" based on `sortBy` state
- Full loading skeletons (count = current limit value), error states with Retry buttons, empty state

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `npx tsc --noEmit`: PASS — no TypeScript errors
- `npm run build`: PASS — production build succeeds, `/admin/sales` listed as dynamic route
- All 15 automated checks on sales/page.tsx: PASS

## Self-Check

- `frontend/src/components/admin/RevenueChart.tsx`: FOUND
- `frontend/src/components/ui/chart.tsx`: FOUND
- `frontend/src/app/admin/sales/page.tsx`: FOUND (394 lines, replacing 13-line placeholder)
- Task 1 commit 76227c9: FOUND
- Task 2 commit 6bff99b: FOUND

## Self-Check: PASSED
