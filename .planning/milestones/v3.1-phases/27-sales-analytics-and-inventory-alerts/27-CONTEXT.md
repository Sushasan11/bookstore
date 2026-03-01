# Phase 27: Sales Analytics and Inventory Alerts - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin can analyze sales performance through a revenue comparison chart and top-sellers rankings, and identify low-stock books via a configurable threshold view with stock update actions. This phase builds on the placeholder sales page and enhances the existing inventory page.

</domain>

<decisions>
## Implementation Decisions

### Revenue Chart Design
- Side-by-side bar chart comparing current period revenue to prior period
- Time granularity adapts to selected period: today → hourly bars, week → daily bars, month → daily bars
- KPI stat cards (revenue, orders, AOV, delta %) displayed above the chart in a row — same pattern as dashboard overview
- Period selector uses the same today/week/month button toggle pattern from the dashboard overview for consistency
- Install recharts via shadcn chart CLI; wrap chart component with `next/dynamic { ssr: false }` to avoid hydration errors

### Top-Sellers Table
- Revenue/volume toggle and row limit selector (5, 10, 25) — no specific discussion needed, success criteria is clear
- Follows existing table patterns from dashboard overview and inventory page

### Inventory Threshold & Badges
- Threshold control: keep preset buttons (5, 10, 20) as quick shortcuts AND add a free-form number input field for custom values
- Table updates via debounced live update (500ms debounce) as admin types — no submit button
- Stock values use shadcn Badge components (pill-shaped labels) instead of inline colored text
- Badge logic: red badge for stock = 0 (out-of-stock), amber badge for stock 1+ below threshold (low stock)

### Stock Update Modal
- Uses existing Dialog component (already used by CheckoutDialog, ReviewsSection)
- Modal shows: book title as header, current stock value for reference, single number input to set new absolute stock level
- After successful update: modal closes automatically, table refetches to show updated stock, toast notification confirms success
- Backend endpoint already exists: `PATCH /books/{book_id}/stock` with `StockUpdate` schema (admin-only, sets absolute stock quantity, triggers restock alerts)

### Claude's Discretion
- Loading skeleton design for chart
- Exact chart colors and tooltip styling
- Error state handling for chart render failures
- Spacing and typography details

</decisions>

<specifics>
## Specific Ideas

- Dashboard overview already has KPI cards and a mini Top 5 table — the Sales Analytics page should feel like a deeper dive into the same data, not a duplicate
- The existing inventory page is functional but needs Badge components and the free-form input field added alongside the preset buttons

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Card`, `CardContent`, `CardHeader`, `CardTitle`: Used throughout admin pages for KPI cards and content sections
- `Badge` component (`frontend/src/components/ui/badge.tsx`): Available for stock status badges
- `Dialog` component (`frontend/src/components/ui/dialog.tsx`): Used by CheckoutDialog — reuse for stock update modal
- `Input` component (`frontend/src/components/ui/input.tsx`): Available for threshold free-form input
- `Button` with variant toggle pattern: Used in dashboard overview period selector and inventory threshold selector
- `Skeleton` component: Used for loading states across all admin pages
- `DeltaBadge` helper in overview page: Shows ▲/▼ percentage changes with green/red coloring
- `formatCurrency` helper in overview page: Formats dollar amounts

### Established Patterns
- TanStack Query with `adminKeys` factory for cache management (`src/lib/admin.ts`)
- `useSession()` + `accessToken` pattern for authenticated admin API calls
- `next/dynamic { ssr: false }` pattern established in Phase 26 for SSR-disable
- Admin pages use `space-y-6` layout with flex header rows for title + controls
- Table pattern: `rounded-lg border` wrapper, `bg-muted/50` header, `hover:bg-muted/30` rows

### Integration Points
- Sales page (`frontend/src/app/admin/sales/page.tsx`): Currently placeholder — will be replaced entirely
- Inventory page (`frontend/src/app/admin/inventory/page.tsx`): Existing functional page — will be enhanced with Badge components, free-form input, and Update Stock button/modal
- `src/lib/admin.ts`: Already has `fetchSalesSummary`, `fetchTopBooks`, `fetchLowStock` — may need a new `updateBookStock` function wrapping `PATCH /books/{book_id}/stock`
- Backend `PATCH /books/{book_id}/stock` endpoint exists in `backend/app/books/router.py` — no backend changes needed
- Sonner toast (`frontend/src/components/ui/sonner.tsx`): Available for success/error notifications

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-sales-analytics-and-inventory-alerts*
*Context gathered: 2026-02-28*
