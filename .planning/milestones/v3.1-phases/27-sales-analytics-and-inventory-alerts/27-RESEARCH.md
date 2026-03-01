# Phase 27: Sales Analytics and Inventory Alerts - Research

**Researched:** 2026-02-28
**Domain:** Recharts bar chart via shadcn chart CLI, TanStack Query, shadcn Dialog/Badge/Input patterns, debounced state
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Revenue Chart Design**
- Side-by-side bar chart comparing current period revenue to prior period
- Time granularity adapts to selected period: today → hourly bars, week → daily bars, month → daily bars
- KPI stat cards (revenue, orders, AOV, delta %) displayed above the chart in a row — same pattern as dashboard overview
- Period selector uses the same today/week/month button toggle pattern from the dashboard overview for consistency
- Install recharts via shadcn chart CLI; wrap chart component with `next/dynamic { ssr: false }` to avoid hydration errors

**Top-Sellers Table**
- Revenue/volume toggle and row limit selector (5, 10, 25) — no specific discussion needed, success criteria is clear
- Follows existing table patterns from dashboard overview and inventory page

**Inventory Threshold & Badges**
- Threshold control: keep preset buttons (5, 10, 20) as quick shortcuts AND add a free-form number input field for custom values
- Table updates via debounced live update (500ms debounce) as admin types — no submit button
- Stock values use shadcn Badge components (pill-shaped labels) instead of inline colored text
- Badge logic: red badge for stock = 0 (out-of-stock), amber badge for stock 1+ below threshold (low stock)

**Stock Update Modal**
- Uses existing Dialog component (already used by CheckoutDialog, ReviewsSection)
- Modal shows: book title as header, current stock value for reference, single number input to set new absolute stock level
- After successful update: modal closes automatically, table refetches to show updated stock, toast notification confirms success
- Backend endpoint already exists: `PATCH /books/{book_id}/stock` with `StockUpdate` schema (admin-only, sets absolute stock quantity, triggers restock alerts)

### Claude's Discretion
- Loading skeleton design for chart
- Exact chart colors and tooltip styling
- Error state handling for chart render failures
- Spacing and typography details

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SALE-01 | Admin can view a revenue comparison bar chart showing current vs previous period | Recharts BarChart with two data series; `next/dynamic { ssr: false }` wrapping; prior revenue derived from `current_revenue / (1 + delta_percentage / 100)` |
| SALE-02 | Admin can view summary stats (revenue, order count, AOV, delta) on the analytics page | Reuse KPI card pattern and `DeltaBadge`/`formatCurrency` helpers from overview page; `fetchSalesSummary` already in `src/lib/admin.ts` |
| SALE-03 | Admin can view a top-sellers table ranked by revenue or volume via a toggle | `fetchTopBooks(accessToken, limit, sort_by)` supports `revenue`/`volume` toggle; `adminKeys.sales.topBooks` cache keyed by limit only — needs sort_by added |
| SALE-04 | Admin can configure the top-sellers table limit (5, 10, or 25 entries) | `fetchTopBooks` `limit` param; backend allows 1-50; three-button toggle pattern same as period selector |
| INVT-01 | Admin can view a low-stock books table sorted by stock ascending with color-coded status badges | `fetchLowStock` returns items pre-sorted by stock ascending; replace inline colored text with shadcn Badge; badge colors added via `className` override on Badge component |
| INVT-02 | Admin can configure the stock threshold via an input field | `useDebounce` hook (already installed, v10.1.0); free-form `<Input type="number">` + preset buttons; debounced value drives `queryKey` |
| INVT-03 | Admin can click "Update Stock" on any row to open the stock update modal | Existing Dialog component; `useMutation` calling `PATCH /books/{book_id}/stock`; `updateBookStock` function to be added to `src/lib/admin.ts`; `useQueryClient` for cache invalidation after success |
</phase_requirements>

---

## Summary

Phase 27 is a frontend-only phase building on the complete foundation from Phase 26. Two pages are being implemented: the Sales Analytics page (replacing a placeholder) and enhancing the existing Inventory Alerts page. All backend endpoints exist and are tested — the work is entirely in React/Next.js/TanStack Query.

The most technically distinct element is the revenue comparison bar chart using Recharts. Recharts is not yet installed — it must be added via `npx shadcn@latest add chart`, which installs `recharts ^2.15.x` plus a `chart.tsx` wrapper component and requires a `"react-is": "^19.0.0"` npm override. Every Recharts component must be wrapped with `next/dynamic({ ssr: false })` because recharts uses browser-only APIs and produces hard-to-debug hydration errors in production Next.js builds. This pattern is already established in Phase 26 and documented in STATE.md.

The key data challenge is that the backend `sales/summary` endpoint returns `current_revenue` and `delta_percentage` but NOT `prior_revenue` explicitly. The frontend must compute `prior_revenue = current_revenue / (1 + delta_percentage / 100)` to populate the second bar in the chart. When `delta_percentage` is `null` (no prior data), the chart should show only the current bar or display a "no prior data" state. The inventory page enhancement is straightforward: swap inline colored text for shadcn Badge components, add a free-form Input field alongside preset buttons with 500ms debounce, and wire an "Update Stock" button per row to open a Dialog modal with a useMutation call.

**Primary recommendation:** Install recharts via `npx shadcn@latest add chart` first (creates `chart.tsx` + updates `package.json` with overrides), then build `RevenueChart.tsx` wrapped in `next/dynamic`, then the Sales page, then enhance the Inventory page.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | ^2.15.x | Bar chart rendering | Installed via shadcn chart CLI; project decision (STATE.md); v2 not v3 — React 19 compat |
| @tanstack/react-query | ^5.90.21 | Data fetching, cache, mutations | Already installed; `adminKeys` factory established in `src/lib/admin.ts` |
| use-debounce | 10.1.0 | Debounce threshold input state | Already installed; `useDebounce` hook used for INVT-02 |
| sonner | ^2.0.7 | Toast notifications | Already installed; used after stock update success |
| next/dynamic | (Next.js built-in 16.1.6) | SSR-disable for recharts | Already used in Phase 26 pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn chart.tsx | installed via CLI | Recharts wrapper with CSS var theming | Wraps BarChart; provides `ChartContainer`, `ChartTooltip`, `ChartTooltipContent` |
| lucide-react | ^0.575.0 | Icons only | Already installed; no new icon dependencies expected |
| radix-ui Dialog | via `dialog.tsx` | Stock update modal | Already installed via Phase 26 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| recharts via shadcn | chart.js / visx | Project already decided recharts via shadcn — no alternative considered |
| useDebounce (value) | useDebouncedCallback | `useDebounce` returns a debounced value, simpler for controlled input → query key; callback variant used when you need to debounce a function call |
| Dialog for stock modal | Sheet (sidebar drawer) | Dialog is correct for small focused forms; already used in CheckoutDialog |

**Installation (recharts only — everything else is already installed):**
```bash
cd frontend
npx shadcn@latest add chart
# This installs recharts ^2.15.x, adds src/components/ui/chart.tsx,
# and adds "overrides": { "react-is": "^19.0.0" } to package.json
npm install  # to apply the override
```

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/admin/sales/page.tsx          # Replace placeholder — Sales Analytics page (SALE-01..04)
├── app/admin/inventory/page.tsx      # Enhance existing — add Badge, Input, Modal (INVT-01..03)
├── components/admin/
│   └── RevenueChart.tsx              # Recharts BarChart, exported as default; imported via next/dynamic
├── components/ui/
│   └── chart.tsx                     # Added by npx shadcn@latest add chart
└── lib/admin.ts                      # Add updateBookStock(); extend adminKeys.sales.topBooks key
```

### Pattern 1: next/dynamic with ssr: false for Recharts

**What:** Recharts uses `window` and `ResizeObserver` internally. Next.js SSR renders on the server where those don't exist. Using `next/dynamic` defers the import to the client.

**When to use:** Any component that imports from `recharts`.

**Example:**
```typescript
// app/admin/sales/page.tsx
import dynamic from 'next/dynamic'
import { Skeleton } from '@/components/ui/skeleton'

const RevenueChart = dynamic(
  () => import('@/components/admin/RevenueChart'),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[300px] w-full rounded-lg" />,
  }
)
```

### Pattern 2: Recharts BarChart with shadcn ChartContainer

**What:** `ChartContainer` from `chart.tsx` provides CSS variable-based colors and responsive sizing. Wrap `BarChart` inside it.

**When to use:** All chart components in this project.

**Example (based on shadcn chart docs pattern):**
```typescript
// components/admin/RevenueChart.tsx
'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'

const chartConfig = {
  current: { label: 'Current', color: 'hsl(var(--chart-1))' },
  prior: { label: 'Prior', color: 'hsl(var(--chart-2))' },
} satisfies ChartConfig

type RevenueChartProps = {
  currentRevenue: number
  priorRevenue: number | null
  period: 'today' | 'week' | 'month'
}

export default function RevenueChart({ currentRevenue, priorRevenue, period }: RevenueChartProps) {
  const data = [
    {
      name: period,
      current: currentRevenue,
      prior: priorRevenue ?? 0,
    },
  ]

  return (
    <ChartContainer config={chartConfig} className="h-[300px] w-full">
      <BarChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={false} />
        <YAxis tickLine={false} axisLine={false} tickFormatter={(v) => `$${v.toLocaleString()}`} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="current" fill="var(--color-current)" radius={4} />
        <Bar dataKey="prior" fill="var(--color-prior)" radius={4} />
      </BarChart>
    </ChartContainer>
  )
}
```

### Pattern 3: Prior Revenue Derivation

**What:** The backend returns `current_revenue` and `delta_percentage` in the same response. `prior_revenue` is NOT returned by the API. The frontend derives it.

**Formula (verified against analytics_service.py):**
```
delta_percentage = (current_revenue - prior_revenue) / prior_revenue * 100
→ prior_revenue = current_revenue / (1 + delta_percentage / 100)
```

**Edge cases:**
- `delta_percentage === null` → prior period had zero revenue → show only current bar, no prior bar (or render prior bar at 0)
- `delta_percentage === 0` → prior revenue equals current revenue → formula: `current / 1.0 = current` ✓
- `current_revenue === 0` → derived prior revenue = 0 regardless (formula: `0 / anything = 0`) ✓

```typescript
// In sales/page.tsx — derive prior revenue from summary response
const priorRevenue =
  summaryData.delta_percentage !== null
    ? summaryData.revenue / (1 + summaryData.delta_percentage / 100)
    : null
```

### Pattern 4: useMutation for Stock Update

**What:** TanStack Query `useMutation` for the `PATCH /books/{book_id}/stock` call. On success: close dialog, invalidate low-stock query, show toast.

**When to use:** Any write operation that should invalidate cached data.

**Example:**
```typescript
// In inventory/page.tsx or a StockUpdateModal component
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { adminKeys } from '@/lib/admin'

const queryClient = useQueryClient()

const stockMutation = useMutation({
  mutationFn: ({ bookId, quantity }: { bookId: number; quantity: number }) =>
    updateBookStock(accessToken, bookId, quantity),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.inventory.all })
    toast.success('Stock updated successfully')
    setModalOpen(false)
  },
  onError: () => {
    toast.error('Failed to update stock')
  },
})
```

### Pattern 5: Debounced Threshold Input

**What:** `useDebounce` from `use-debounce` v10.1.0 wraps the raw input value. The debounced value drives the TanStack Query `queryKey` and `queryFn`. This avoids firing a new request on every keystroke.

**When to use:** Any free-form input that drives a query.

```typescript
import { useState } from 'react'
import { useDebounce } from 'use-debounce'

const [thresholdInput, setThresholdInput] = useState<number>(10)
const [debouncedThreshold] = useDebounce(thresholdInput, 500)

const lowStockQuery = useQuery({
  queryKey: adminKeys.inventory.lowStock(debouncedThreshold),
  queryFn: () => fetchLowStock(accessToken, debouncedThreshold),
  enabled: !!accessToken,
  staleTime: 60_000,
})
```

### Pattern 6: shadcn Badge with Custom Color Classes

**What:** The shadcn `Badge` component only supports pre-defined variants. Red/amber stock badges require `className` override, NOT a new variant.

**When to use:** Whenever Badge color must deviate from defined variants.

```typescript
import { Badge } from '@/components/ui/badge'

function StockBadge({ stock, threshold }: { stock: number; threshold: number }) {
  if (stock === 0) {
    return (
      <Badge className="bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400">
        Out of Stock
      </Badge>
    )
  }
  if (stock < threshold) {
    return (
      <Badge className="bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400">
        Low Stock ({stock})
      </Badge>
    )
  }
  return null // Should not render if the item is in the low-stock list
}
```

### Pattern 7: adminKeys.sales.topBooks Key Fix

**What:** The existing `adminKeys.sales.topBooks` factory in `src/lib/admin.ts` only keys by `limit`, not `sort_by`. Adding a `sort_by` toggle to the Sales page requires updating this key or the cache won't distinguish between revenue-sorted and volume-sorted results.

**Current (BROKEN for toggle):**
```typescript
topBooks: (limit: number) => ['admin', 'sales', 'top-books', limit] as const,
```

**Fixed:**
```typescript
topBooks: (limit: number, sort_by: 'revenue' | 'volume' = 'revenue') =>
  ['admin', 'sales', 'top-books', limit, sort_by] as const,
```

This must be updated in `src/lib/admin.ts`. The existing call from `overview/page.tsx` passes only `limit` — update that call to pass `'revenue'` explicitly for backward compatibility.

### Anti-Patterns to Avoid

- **Importing recharts without next/dynamic:** Causes `window is not defined` errors in production builds — always wrap in `next/dynamic({ ssr: false })`.
- **Using recharts v3 (not v2):** shadcn chart CLI installs `recharts ^2.15.x`. React 19 compat is already resolved via the `react-is` npm override. Do NOT upgrade to v3.
- **Storing debouncedThreshold as state:** `useDebounce` returns a derived value, not a setter. Only `thresholdInput` is state; `debouncedThreshold` is derived from it.
- **Not handling `delta_percentage === null` for chart:** When there is no prior period data, the formula for `prior_revenue` divides by zero. Always guard with a `null` check before computing.
- **Using `queryKey: adminKeys.sales.topBooks(limit)` without sort_by:** Cache will serve stale revenue-sorted data when toggling to volume. Fix the key factory before implementing the toggle.
- **Calling `useMutation` with `queryClient.invalidateQueries` before checking success:** Always run invalidation in `onSuccess`, not in `onSettled`, to avoid invalidating on error.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Responsive bar chart | Custom SVG/Canvas chart | Recharts via shadcn | ResponsiveContainer + accessibility + tooltip handling already solved |
| Debounce logic | setTimeout / clearTimeout in useEffect | `useDebounce` from use-debounce | Already installed; handles React strict mode double-invocation, cleanup, and leading/trailing edge correctly |
| Modal/dialog | Custom portal + focus trap | shadcn Dialog | Radix UI handles a11y, focus trap, scroll lock, animation; already installed |
| Toast notification | Custom notification state | sonner toast() | Already installed and wired in providers; handles stacking, positioning, auto-dismiss |
| Query cache invalidation timing | setTimeout after mutation | `useMutation` onSuccess + `queryClient.invalidateQueries` | TanStack Query handles race conditions between the refetch and the stale cache |

**Key insight:** Every utility needed for this phase is already installed. The only new package is recharts (via shadcn CLI). Hand-rolling any of the above would introduce bugs that the existing libraries have already solved.

---

## Common Pitfalls

### Pitfall 1: Recharts Hydration Errors (Production Only)

**What goes wrong:** Chart renders fine in `next dev` but crashes in `next build && next start` with a hydration mismatch error or `window is not defined`.

**Why it happens:** Recharts uses browser APIs (`window.ResizeObserver`, `document`) at module initialization time. SSR runs on Node.js where these don't exist. Dev mode's lenient hydration hides this.

**How to avoid:** ALWAYS use `next/dynamic(() => import('./RevenueChart'), { ssr: false })` in the page file. Never import `RevenueChart` directly with a static import.

**Warning signs:** Works in dev, crashes in production build. Error message mentions hydration or `window`.

### Pitfall 2: Prior Revenue Derivation Edge Cases

**What goes wrong:** Chart shows `NaN` or `Infinity` for the prior revenue bar.

**Why it happens:** `delta_percentage` can be `null` (no prior revenue) — dividing by `(1 + null/100)` gives `NaN`. Also if somehow `delta_percentage === -100`, the denominator is `0` giving `Infinity`.

**How to avoid:**
```typescript
const priorRevenue =
  summaryData.delta_percentage !== null && summaryData.delta_percentage !== -100
    ? summaryData.revenue / (1 + summaryData.delta_percentage / 100)
    : null
```
Pass `priorRevenue` as a prop to `RevenueChart`; render `prior` bar value as `priorRevenue ?? 0`.

**Warning signs:** Chart bar shows "NaN" or an enormous bar.

### Pitfall 3: Top-Books Cache Miss After Sort Toggle

**What goes wrong:** Toggling between revenue/volume sort shows the wrong data (e.g., still shows revenue-sorted list after switching to volume).

**Why it happens:** `adminKeys.sales.topBooks(limit)` omits `sort_by` from the key — TanStack Query returns the cached result for the same limit regardless of sort order.

**How to avoid:** Update the key factory to include `sort_by` BEFORE implementing the toggle. Update all call sites.

**Warning signs:** Toggle appears to do nothing; network tab shows no new request on toggle.

### Pitfall 4: Preset Buttons Conflict with Debounced Input

**What goes wrong:** Admin clicks preset "10" button but input field still shows old value, or debounce fires after button click with the old input value overwriting the preset.

**Why it happens:** Both preset buttons and the free-form input set `thresholdInput` state. If debounce is still pending when a preset button fires, the debounced value updates after.

**How to avoid:** Preset button click sets `thresholdInput` immediately (same setter). Since `useDebounce` reflects the latest state, a button press will debounce correctly. The 500ms wait applies to the preset click too — this is acceptable. If instant response is needed for presets, call the query directly with the preset value and cancel pending debounce (using `useDebouncedCallback` with `.cancel()`). For this phase, 500ms debounce on presets is acceptable.

**Warning signs:** Threshold input shows stale value after preset button click.

### Pitfall 5: Stock Update Modal State Leak

**What goes wrong:** Modal opens for Book A, admin closes without submitting, then opens for Book B — the form still shows Book A's data.

**Why it happens:** Modal state (selected book, input value) is held in component state and not reset on close.

**How to avoid:** Reset the quantity input state in the Dialog `onOpenChange` handler when `open` becomes `false`. Or key the modal content on `selectedBook.book_id` to force re-mount.

**Warning signs:** Modal shows stale book title or input value from previous open.

---

## Code Examples

Verified patterns from project codebase:

### Existing Pattern: Period Selector Toggle (from overview/page.tsx)
```typescript
// Source: frontend/src/app/admin/overview/page.tsx (lines 92-104)
<div className="flex items-center gap-1 rounded-lg border p-1">
  {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
    <Button
      key={p}
      variant={period === p ? 'default' : 'ghost'}
      size="sm"
      onClick={() => setPeriod(p)}
      className="h-8 text-sm"
    >
      {PERIOD_LABELS[p]}
    </Button>
  ))}
</div>
```
Reuse this pattern for: period selector on Sales page, revenue/volume toggle, limit selector (5/10/25), preset threshold buttons.

### Existing Pattern: Table with Loading/Error/Empty States (from inventory/page.tsx)
```typescript
// Source: frontend/src/app/admin/inventory/page.tsx (lines 96-151)
<tbody>
  {lowStockQuery.isLoading ? (
    Array.from({ length: 5 }).map((_, i) => (
      <tr key={i} className="border-t">
        <td className="py-3 px-4"><Skeleton className="h-4 w-48" /></td>
        ...
      </tr>
    ))
  ) : lowStockQuery.isError ? (
    <tr>
      <td colSpan={4} className="py-6 px-4 text-center text-muted-foreground">
        Failed to load inventory data.{' '}
        <button className="underline hover:no-underline" onClick={() => lowStockQuery.refetch()}>
          Retry
        </button>
      </td>
    </tr>
  ) : !lowStockQuery.data?.items?.length ? (
    <tr>
      <td colSpan={4} className="py-6 px-4 text-center text-muted-foreground">
        No low stock items
      </td>
    </tr>
  ) : (
    lowStockQuery.data.items.map((item) => ( ... ))
  )}
</tbody>
```

### Existing Pattern: KPI Card (from overview/page.tsx)
```typescript
// Source: frontend/src/app/admin/overview/page.tsx (lines 110-144)
<Card>
  <CardHeader className="pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">Revenue</CardTitle>
  </CardHeader>
  <CardContent>
    {summaryQuery.isLoading ? (
      <div className="space-y-2">
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-4 w-16" />
      </div>
    ) : summaryQuery.isError ? (
      <p className="text-sm text-muted-foreground">Failed to load</p>
    ) : (
      <div className="space-y-1">
        <p className="text-2xl font-bold">{formatCurrency(summaryData?.revenue ?? 0)}</p>
        <DeltaBadge delta={delta} />
      </div>
    )}
  </CardContent>
</Card>
```

### New: updateBookStock Fetch Function (to add to src/lib/admin.ts)
```typescript
// Source: backend/app/books/router.py PATCH /books/{book_id}/stock
// StockUpdate schema: { quantity: int (ge=0) }
export async function updateBookStock(
  accessToken: string,
  bookId: number,
  quantity: number
): Promise<void> {
  return apiFetch<void>(
    `/books/${bookId}/stock`,
    {
      method: 'PATCH',
      body: JSON.stringify({ quantity }),
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  )
}
```

Note: `apiFetch` handles 204 No Content as `return undefined as T`, so this correctly returns `void`.

### New: adminKeys.sales.topBooks Fix (src/lib/admin.ts)
```typescript
// Current (line 49 in admin.ts):
topBooks: (limit: number) => ['admin', 'sales', 'top-books', limit] as const,

// Fixed:
topBooks: (limit: number, sort_by: 'revenue' | 'volume' = 'revenue') =>
  ['admin', 'sales', 'top-books', limit, sort_by] as const,

// Update overview/page.tsx call site from:
queryKey: adminKeys.sales.topBooks(5),
// to:
queryKey: adminKeys.sales.topBooks(5, 'revenue'),
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct recharts import in Next.js | `next/dynamic { ssr: false }` wrapping | Next.js 13+ App Router era | Required for App Router — SSR is default, opt-out needed |
| recharts v3 | recharts v2.15.x | shadcn chart CLI pinned to v2 | React 19 compat; v3 has breaking API changes; project uses v2 |
| Custom debounce in useEffect | `use-debounce` library | React Hooks era | Handles cleanup and React Strict Mode double-invocation correctly |
| Inline colored stock text | shadcn Badge component | Phase 27 decision | INVT-01 requires pill-shaped badges per user decision |

**Deprecated/outdated:**
- Recharts v3: Breaking API changes from v2; shadcn CLI installs v2.15.x; do NOT upgrade.
- Class-based colored text for stock status: Replaced by `Badge` component per CONTEXT.md locked decision.

---

## Open Questions

1. **Time granularity in chart (today → hourly, week/month → daily)**
   - What we know: CONTEXT.md says "Time granularity adapts to selected period: today → hourly bars, week → daily bars, month → daily bars"
   - What's unclear: The backend `GET /admin/analytics/sales/summary` returns a SINGLE aggregate (one revenue number per period). It does NOT return hourly or daily breakdown data. There is no timeseries endpoint.
   - Recommendation: The granularity decision may refer to how data WOULD be shown if a timeseries endpoint existed — this is listed as `SALE-05` in Future Requirements ("day-by-day revenue timeseries chart — requires new backend endpoint"). For Phase 27, the chart must be a two-bar comparison (current vs prior period totals) as a single side-by-side view. The label on the X-axis can indicate the period. Flag to user during planning: the granularity feature requires a backend endpoint that doesn't exist and is explicitly deferred to v3.2+.

2. **adminKeys.sales.topBooks cache key mismatch with existing overview page**
   - What we know: The overview page uses `adminKeys.sales.topBooks(5)` (limit=5, no sort_by). The Sales Analytics page needs `adminKeys.sales.topBooks(limit, sort_by)`.
   - What's unclear: Whether to add `sort_by` as an additional key segment (breaking the existing call site) or add a new key factory entry.
   - Recommendation: Update the key factory to add `sort_by` as an optional second parameter with default `'revenue'`. Update the overview page call to `adminKeys.sales.topBooks(5, 'revenue')` — this is a one-line change and the planner should include it as a task in Plan 27-01.

---

## Validation Architecture

> Skipped — `workflow.nyquist_validation` is not present in `.planning/config.json` (field absent, treated as false).

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection — `frontend/src/lib/admin.ts`: confirmed `fetchSalesSummary`, `fetchTopBooks`, `fetchLowStock` signatures and `adminKeys` factory
- Direct code inspection — `frontend/src/app/admin/overview/page.tsx`: confirmed KPI card pattern, `DeltaBadge`, `formatCurrency`, period selector toggle pattern
- Direct code inspection — `frontend/src/app/admin/inventory/page.tsx`: confirmed existing threshold selector, table pattern, no Badge or Input yet
- Direct code inspection — `frontend/src/components/ui/badge.tsx`: confirmed Badge variants and className override approach
- Direct code inspection — `frontend/src/components/ui/dialog.tsx`: confirmed Dialog component API (DialogContent, DialogHeader, DialogTitle, DialogFooter)
- Direct code inspection — `backend/app/admin/analytics_service.py`: confirmed `delta_percentage` formula and that `prior_revenue` is NOT returned by API
- Direct code inspection — `backend/app/admin/analytics_router.py`: confirmed API contract; `sort_by: revenue|volume`, `limit: 1-50`; `threshold: ge=0`
- Direct code inspection — `backend/app/books/router.py`: confirmed `PATCH /books/{book_id}/stock` with `StockUpdate` schema `{ quantity: int (ge=0) }`
- Direct code inspection — `frontend/package.json`: confirmed `use-debounce: ^10.1.0`, `sonner: ^2.0.7`, recharts NOT yet in dependencies
- Direct code inspection — `node_modules/use-debounce`: confirmed `useDebounce(value, delay) => [debouncedValue, controls]` API
- `D:/Python/claude-test/.planning/STATE.md`: confirmed recharts install command (`npx shadcn@latest add chart`), version (`^2.15.x`), `react-is` override requirement, and `next/dynamic { ssr: false }` pattern

### Secondary (MEDIUM confidence)
- STATE.md note: "recharts ^2.15.x (not v3) installed via `npx shadcn@latest add chart`; requires `"react-is": "^19.0.0"` npm override" — this is a project decision record, not verified via live shadcn CLI run, but HIGH confidence given it was written during Phase 26 implementation.

### Tertiary (LOW confidence)
- None. All critical claims are verified from direct codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in node_modules or package.json; recharts install command from STATE.md
- Architecture patterns: HIGH — all patterns derived directly from existing working code in the project
- Pitfalls: HIGH for recharts SSR (documented in STATE.md from Phase 26 experience); HIGH for cache key bug (verified by reading adminKeys factory); MEDIUM for modal state leak (common React pattern pitfall, not observed in code)
- Prior revenue derivation: HIGH — formula verified against analytics_service.py source code

**Research date:** 2026-02-28
**Valid until:** 2026-03-30 (stable stack; recharts v2 and shadcn chart API are stable)
