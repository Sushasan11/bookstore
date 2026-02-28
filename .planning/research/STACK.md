# Stack Research

**Domain:** Admin Dashboard Frontend — Next.js 15 + shadcn/ui additions for v3.1
**Researched:** 2026-02-28
**Confidence:** HIGH (charting, tables, forms all verified against official sources)

> **Scope:** This file covers ONLY the new libraries needed for the v3.1 Admin Dashboard milestone. The existing validated stack (Next.js 15/16, TypeScript, TanStack Query, shadcn/ui, Tailwind CSS v4, NextAuth.js v5, react-hook-form, zod, zustand) is NOT re-researched here — it is locked and shipped in v3.0. See the v3.0 STACK.md in git history for full baseline details.

---

## What v3.1 Needs That v3.0 Doesn't Have

| Gap | Solution | Why New |
|-----|----------|---------|
| Revenue/sales charts | shadcn/ui chart component (Recharts) | No charts in v3.0 storefront |
| Paginated data tables with sort/filter/bulk actions | `@tanstack/react-table` + shadcn Table | No data-grid use case in v3.0 |
| Admin CRUD forms (add/edit books) | Already installed: react-hook-form + zod | Confirmed: package.json already has these |
| Dashboard KPI cards | shadcn/ui Card (already installed) | No new lib needed |

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| recharts | ^2.15.x (via shadcn chart CLI) | Data visualization engine | shadcn/ui's chart component wraps Recharts. Using it via `npx shadcn@latest add chart` installs Recharts as a direct dep and copies the `ChartContainer`/`ChartTooltip` primitives into `src/components/ui/chart.tsx`. You own the components, no abstraction lock-in. |
| @tanstack/react-table | ^8.21.3 | Headless table logic (sort, filter, pagination, row selection) | The shadcn/ui data-table pattern is explicitly built on TanStack Table v8. Provides all table behavior headlessly — renders nothing, you provide the shadcn Table component markup. Same TanStack family as the already-installed TanStack Query. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-hook-form | ^7.71.x (ALREADY INSTALLED) | Admin book CRUD forms | Book add/edit forms with file-like text inputs (title, author, genre, price, stock). Already in package.json — no install needed. |
| zod | ^4.x (ALREADY INSTALLED) | Admin form schema validation | Define book schema once, get TypeScript types + runtime validation. Already in package.json — no install needed. |
| @hookform/resolvers | ^5.2.2 (ALREADY INSTALLED) | RHF-to-Zod bridge | `zodResolver(bookSchema)` in `useForm`. Supports Zod v4. Already in package.json — no install needed. |
| sonner | ^2.x (ALREADY INSTALLED) | Toast notifications for admin actions | "Book saved", "User deactivated", "Reviews deleted (3)". Already installed — no install needed. |
| lucide-react | ^0.575.x (ALREADY INSTALLED) | Icons for admin UI | TrendingUp for revenue, Users for user management, BookOpen for catalog. Already installed. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| shadcn CLI (`npx shadcn@latest add`) | Install chart + table primitives | Use `add chart` and `add data-table` (or `add table` + build manually). Components copied to `src/components/ui/` — you own them. |

---

## Installation

Only two net-new packages are required. Everything else is already in `frontend/package.json`.

```bash
cd frontend

# 1. Add shadcn chart component (copies chart.tsx, installs recharts as dep)
npx shadcn@latest add chart

# 2. Add TanStack Table (headless table logic)
npm install @tanstack/react-table

# 3. Add shadcn table primitive (if not already added — provides the HTML table components)
npx shadcn@latest add table

# React 19 + recharts compatibility override (REQUIRED — see Version Compatibility section)
# Add to frontend/package.json "overrides" field:
# "react-is": "^19.0.0"
```

**Resulting net-new dependencies in package.json:**
```json
{
  "dependencies": {
    "recharts": "^2.15.x",
    "@tanstack/react-table": "^8.21.3"
  },
  "overrides": {
    "react-is": "^19.0.0"
  }
}
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| shadcn/ui charts (Recharts-backed) | Tremor | If you need a full pre-built dashboard UI in hours with minimal customization. Tremor bundles 40+ dashboard components (KPI cards, charts, filters) but weighs ~200KB gzipped vs ~50KB for the shadcn approach. This project already has shadcn/ui — don't add a competing component system. |
| shadcn/ui charts (Recharts-backed) | Recharts directly (no shadcn wrapper) | If you need chart behavior not supported by the shadcn primitives. Since shadcn copies the chart.tsx component into your project, you can always eject and use raw Recharts APIs when needed. |
| shadcn/ui charts (Recharts-backed) | Victory / Nivo | Both are excellent, but have no shadcn integration. Would require custom theming to match the existing Tailwind v4 design tokens. Recharts is the path of least resistance given the existing stack. |
| @tanstack/react-table | AG Grid (Community) | If you need 1000+ row virtual scrolling, Excel-like editing, or server-side Excel export. AG Grid Community is free but 50KB+ and opinionated about styling. The admin tables here (paginated, ~20 rows/page) do not need this. |
| @tanstack/react-table | react-data-grid | Better for spreadsheet-style editable cells. Not the use case here — admin needs sort/filter/bulk-delete, not inline editing. |
| react-hook-form + zod (already installed) | Native form + Server Actions | Next.js 15 Server Actions can handle forms without a form library. RHF is already installed and provides client-side validation UX that Server Actions alone don't give before submission. Keep the existing pattern. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Tremor** | Duplicate component system alongside existing shadcn/ui. Would require maintaining two design systems. Tailwind v4 incompatibilities documented in community issues. | shadcn/ui chart component + custom KPI cards with shadcn Card |
| **Chart.js / react-chartjs-2** | No shadcn integration. Requires manual theming to match Tailwind design tokens. Recharts composes with React JSX — Chart.js uses a canvas imperative API, harder to customize. | Recharts via shadcn chart |
| **@tanstack/react-table v7 (react-table)** | v7 is deprecated. v8 is the current API. Do not use legacy `react-table` package name. | `@tanstack/react-table` v8 |
| **MUI DataGrid / Material UI** | Entire MUI design system conflicts with existing shadcn/ui + Tailwind. Bundle bloat, theme conflicts, React 19 peer-dep warnings documented on MUI GitHub. | @tanstack/react-table with shadcn Table component |
| **Recharts v3 with shadcn/ui** | shadcn's official chart.tsx targets Recharts v2 stable. A PR (#8486) for Recharts v3 is open but not merged. Ship with stable Recharts v2 — the migration to v3 is intentionally minimal when it stabilizes. | Recharts ^2.15.x (the version shadcn CLI installs) |

---

## Stack Patterns by Variant

**For KPI/metric cards (revenue summary, order count, AOV):**
- Use shadcn `Card` + `CardHeader` + `CardContent` (already installed)
- No new library needed — pure layout with Tailwind

**For revenue line/area charts:**
- Use `npx shadcn@latest add chart` → gives `ChartContainer`, `ChartTooltip`
- Compose with Recharts `<AreaChart>`, `<LineChart>`, `<BarChart>` directly
- The `ChartContainer` handles responsive sizing and CSS variable theming

**For top-sellers table (ranked list, revenue/volume columns):**
- Simple: shadcn `Table` component with manual mapping — no TanStack Table needed if no sort/filter
- If sort is required: add `@tanstack/react-table` with `useReactTable` + `getSortedRowModel()`

**For review moderation (paginated, filter by book/user/rating, bulk delete):**
- Full TanStack Table: `useReactTable` with `getPaginationRowModel()`, `getSortedRowModel()`, `getFilteredRowModel()`, `getRowSelectionModel()`
- Row selection → "Delete selected (N)" button triggers bulk delete mutation via TanStack Query `useMutation`

**For user management (paginated, role/active filter, deactivate action):**
- Full TanStack Table: same pattern as review moderation but no bulk selection needed — per-row action buttons

**For low-stock inventory alerts (threshold filter, ordered by stock ASC):**
- Simple shadcn `Table` — server already returns sorted/filtered data; no client-side TanStack Table needed

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| recharts ^2.15.x | React 19.2.3 | Requires `"overrides": { "react-is": "^19.0.0" }` in package.json. Without this override, npm/pnpm will warn about the `react-is` peer dependency conflict. shadcn docs explicitly call this out for React 19 projects. |
| @tanstack/react-table ^8.21.3 | React 19.2.3 | Supported. Note: may not be compatible with the React Compiler (still experimental), but this project does not use the React Compiler. |
| recharts ^2.15.x | Tailwind v4 | Recharts renders SVG — no Tailwind class conflicts. Colors pulled from CSS variables set in `ChartContainer` config, which maps to `@theme` tokens defined in `globals.css`. |
| @tanstack/react-table ^8.21.3 | @tanstack/react-query ^5.90.x | Different packages in the TanStack suite — no version coupling. Query handles server data fetching; Table handles UI rendering of that data. Combine: fetch with `useQuery`, pass `data` to `useReactTable`. |
| react-hook-form ^7.71.x | zod ^4.x | @hookform/resolvers ^5.2.2 bridges the two. Confirmed: resolver v5 auto-detects Zod v3 vs v4 at runtime. Some bundler-specific import issues reported with Zod v4 subpath imports — use `import { z } from 'zod'` (root import), not `'zod/v4'`. |

---

## Integration with Existing Stack

### TanStack Query + TanStack Table Pattern

The two TanStack libraries compose cleanly. Fetch server-paginated data with `useQuery`, pass it to `useReactTable`:

```typescript
// hooks/use-reviews-table.ts
const { data, isLoading } = useQuery({
  queryKey: ["admin", "reviews", filters],
  queryFn: () => fetchAdminReviews(filters),
});

const table = useReactTable({
  data: data?.reviews ?? [],
  columns,
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  onRowSelectionChange: setRowSelection,
  state: { rowSelection },
});
```

Bulk delete: collect `table.getSelectedRowModel().rows`, extract IDs, call `useMutation` → `DELETE /admin/reviews/bulk`.

### shadcn Chart + TanStack Query Pattern

```typescript
// components/admin/revenue-chart.tsx
const { data } = useQuery({
  queryKey: ["admin", "sales", period],
  queryFn: () => fetchSalesSummary(period),
});

// Pass data.daily_revenue to <AreaChart data={...} />
// ChartContainer applies CSS variable colors from shadcn theme
```

### shadcn Table Component vs TanStack Table

shadcn's `Table` component (`npx shadcn@latest add table`) provides the styled HTML `<table>`, `<thead>`, `<tbody>` etc. TanStack Table provides the logic (sorting state, pagination state, row selection). They combine — TanStack drives the state, shadcn Table provides the markup:

```typescript
// TanStack provides: table.getHeaderGroups(), table.getRowModel()
// shadcn provides: <Table>, <TableHeader>, <TableRow>, <TableCell>
// You write: the loop that maps TanStack model → shadcn components
```

---

## Sources

- [shadcn/ui Chart docs](https://ui.shadcn.com/docs/components/radix/chart) — HIGH confidence (official)
- [shadcn/ui React 19 compatibility](https://ui.shadcn.com/docs/react-19) — HIGH confidence (documents recharts react-is override requirement)
- [recharts npm latest (2.15.x / 3.x)](https://www.npmjs.com/package/recharts) — HIGH confidence
- [recharts 3.0 migration guide](https://github.com/recharts/recharts/wiki/3.0-migration-guide) — HIGH confidence (confirmed v3 exists but shadcn/ui not yet updated to use it)
- [shadcn/ui PR #8486 — recharts v3 update](https://github.com/shadcn-ui/ui/pull/8486) — MEDIUM confidence (WIP, not merged as of research date)
- [TanStack Table v8 docs](https://tanstack.com/table/v8/docs/installation) — HIGH confidence (official)
- [@tanstack/react-table npm 8.21.3](https://www.npmjs.com/package/@tanstack/react-table) — HIGH confidence
- [shadcn/ui data-table docs](https://ui.shadcn.com/docs/components/radix/data-table) — HIGH confidence (official pattern: TanStack Table + shadcn Table)
- [react-hook-form v7.71.x npm](https://www.npmjs.com/package/react-hook-form) — HIGH confidence
- [@hookform/resolvers v5.2.2 npm](https://www.npmjs.com/package/@hookform/resolvers) — HIGH confidence (Zod v4 support confirmed)
- [Zod v4 stable release notes](https://zod.dev/v4) — HIGH confidence
- [shadcn/ui forms docs](https://ui.shadcn.com/docs/forms/react-hook-form) — HIGH confidence (official)

---

*Stack research for: BookStore v3.1 Admin Dashboard (frontend additions)*
*Researched: 2026-02-28*
