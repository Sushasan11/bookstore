# Project Research Summary

**Project:** BookStore v3.1 — Admin Dashboard Frontend
**Domain:** E-commerce admin dashboard added to an existing Next.js 15 + FastAPI bookstore application
**Researched:** 2026-02-28
**Confidence:** HIGH

## Executive Summary

The v3.1 milestone is a frontend-only admin dashboard that surfaces an already-complete FastAPI backend. All six admin sections (Overview, Sales Analytics, Book Catalog CRUD, User Management, Review Moderation, Inventory Alerts) have fully-implemented, tested backend endpoints — the implementation risk is entirely in the frontend. Because the dashboard is additive to a shipped v3.0 storefront, the dominant architectural challenge is cleanly separating the admin layout from the customer storefront without breaking existing customer URLs. The correct pattern is to extract the customer Header/Footer into a `(store)/` App Router route group, leaving the root layout as a Providers-only shell and placing the new `admin/` section at the same level with its own sidebar layout. This is a one-time restructure that must happen in the first phase before any admin feature page is built.

The recommended frontend additions are minimal: two net-new packages (Recharts via the shadcn chart CLI, and `@tanstack/react-table`) on top of libraries already installed in v3.0 (react-hook-form, zod, TanStack Query, sonner, shadcn/ui). Admin pages should be Client Components using TanStack Query — not Server Components — because interactive filtering, optimistic mutations, and toast feedback require client state, and admin pages are auth-gated so SEO is irrelevant. The backend already supports pagination, filtering, and sorting on all admin endpoints, meaning the frontend can implement server-driven tables throughout without loading unbounded result sets into the browser.

The two non-negotiable risks are security and chart hydration. CVE-2025-29927 (CVSS 9.1) allows Next.js middleware bypass in versions below 15.2.3, so role checks must be independently verified in every admin layout Server Component — not only in `proxy.ts`. Recharts (the engine under shadcn charts) triggers hydration errors in Next.js 15 production builds when server-pre-rendered; every chart component must be wrapped with `next/dynamic` and `{ ssr: false }`. Both must be resolved in Phase 26 (the first phase) before any feature pages are built.

---

## Key Findings

### Recommended Stack

The v3.0 stack (Next.js 15, TypeScript, TanStack Query, shadcn/ui, Tailwind CSS v4, NextAuth.js v5, react-hook-form, zod, zustand, sonner, lucide-react) is locked and unchanged. The v3.1 admin dashboard requires exactly two net-new runtime dependencies:

- **recharts ^2.15.x** (installed via `npx shadcn@latest add chart`) — the charting engine under shadcn's `ChartContainer` and `ChartTooltip` primitives. Must use ^2.15.x, not v3, because shadcn's chart.tsx targets the v2 stable API. Requires a `"react-is": "^19.0.0"` npm override for React 19 compatibility.
- **@tanstack/react-table ^8.21.3** — headless table logic (sort, filter, pagination, row selection) composable with the existing shadcn `Table` component. Same TanStack family as the already-installed TanStack Query; no version coupling between them.

Everything else needed for admin forms (react-hook-form, zod, @hookform/resolvers), notifications (sonner), and icons (lucide-react) is already installed. Tremor, MUI DataGrid, Chart.js, AG Grid, and Recharts v3 are explicitly ruled out: they either conflict with the existing shadcn/ui system, introduce unnecessary bundle weight, or lack stable integration with the current stack.

**Core technologies for v3.1:**
- **recharts ^2.15.x**: Data visualization via shadcn chart primitives — requires react-is override; avoid v3 until shadcn PR #8486 merges
- **@tanstack/react-table ^8.21.3**: Headless table behavior for sort, filter, pagination, and row selection; pairs with shadcn Table component for markup
- **react-hook-form + zod (already installed)**: Admin book CRUD forms with Zod v4 schema validation; no install needed
- **TanStack Query (already installed)**: Server data fetching, mutation feedback, cache invalidation; all admin pages are Client Components using `useQuery` and `useMutation`
- **shadcn/ui + Tailwind CSS v4 (already installed)**: All admin UI primitives — Card, Table, Dialog, Badge, Input, Skeleton, AlertDialog — shared between storefront and admin

### Expected Features

All features map directly to backend endpoints that are already built and tested. The frontend must expose six distinct admin sections with no backend changes required.

**Must have (table stakes — all P1 for v3.1):**
- Dashboard overview: KPI cards (revenue, order count, AOV) with delta badges and period selector (Today/This Week/This Month)
- Low-stock count badge on overview linking to Inventory section
- Revenue comparison bar chart (current vs prior period — two bars, NOT a timeseries; backend only provides period totals)
- Top-sellers table with revenue/volume toggle and configurable row limit (5/10/25)
- Paginated catalog table with debounced search, genre filter, and Add/Edit/Delete/Update Stock actions
- Book add/edit form with full field set (title, author, price, ISBN, genre, description, cover URL, publish date)
- Delete book with confirmation dialog ("this action cannot be undone")
- Stock update modal with pre-booking notification awareness (toast: "Pre-booking notification emails will be sent" if stock was 0)
- Paginated user table with role and active-status filters, deactivate/reactivate per row (deactivate disabled for admin-role users)
- Paginated review moderation table with filter bar (book ID, user ID, rating range, sort), single-review delete, and bulk delete with checkbox selection
- Inventory alerts table: configurable threshold input, stock-level color coding (red for out-of-stock, amber for low), Update Stock link per row
- Admin sidebar navigation with active route highlighting and "Back to Storefront" link
- Admin route guard: role check in middleware AND in admin/layout.tsx Server Component

**Should have (differentiators — P2, ship if time allows in v3.1):**
- Top-5 sellers mini-table on Overview page (high informational value, reuses existing endpoint with limit=5)
- Revenue/volume toggle on top-sellers (already described above — confirmed P1 in FEATURES.md prioritization matrix)
- Sticky sidebar with active route highlighting (minimal cost, significantly improves orientation)

**Defer to v3.2:**
- Day-by-day revenue timeseries chart — requires a new backend endpoint (`GET /admin/analytics/sales/timeseries`) not present in v3.1
- Review text expand/collapse — quality-of-life improvement, not a blocker
- Inline stock editing directly from the Inventory Alerts table

**Defer to v4+:**
- Sales forecasting — requires ML infrastructure
- CSV export of analytics data — data volume does not justify at current scale
- Bulk stock import via CSV — requires new backend endpoint
- Admin user role management UI — requires new backend endpoint

**Critical scope constraint:** The revenue chart must be a two-bar comparison (current period vs prior period), not a continuous timeseries. The backend `GET /admin/analytics/sales/summary` returns period totals and a `delta_percentage` — it does not expose day-by-day data. A timeseries chart would require a new backend endpoint and is explicitly deferred to v3.2.

### Architecture Approach

The admin dashboard integrates into the existing App Router structure via a route group restructure and one new section. The root `layout.tsx` is stripped to Providers-only (no Header/Footer). Existing customer pages move into a `(store)/` route group with its own `layout.tsx` that adds the customer Header and Footer — approximately 10 file moves with no URL changes (route groups are transparent in URLs). The new `admin/` section sits alongside `(store)/` with its own `layout.tsx` providing AdminSidebar and AdminHeader. This is the only correct App Router pattern for multi-section apps with completely different chrome in each section.

Admin data fetching uses Client Components throughout with TanStack Query hooks that call a new `src/lib/admin.ts` module mirroring the existing `src/lib/catalog.ts` pattern. All admin query keys are prefixed with `"admin"` to prevent cache collisions with the customer-facing `["books"]` and `["reviews"]` caches. When an admin mutates a book, both the admin catalog key and the customer books key are invalidated so the customer storefront reflects the change immediately.

**Major components:**
1. **`admin/layout.tsx` (Server Component)**: Admin shell with independent role verification (`auth()` + redirect), AdminSidebar, AdminHeader — the real security boundary, not middleware
2. **`src/lib/admin.ts`**: All admin API fetch functions using the existing `apiFetch` wrapper with Bearer token injection; mirrors `src/lib/catalog.ts` structure
3. **`admin/_components/DataTable.tsx`**: Reusable TanStack Table + shadcn Table integration with pagination, sortable columns, and row selection; built in Phase 28, reused in Phase 29
4. **`admin/_components/StatCard.tsx`**: KPI card with current value, label, and delta percentage badge (green up-arrow / red down-arrow / grey dash)
5. **`admin/_components/RevenueChart.tsx`**: shadcn BarChart wrapped in `next/dynamic` with `{ ssr: false }` — the mandatory pattern for all Recharts components
6. **`src/proxy.ts` (modified)**: Adds `/admin` to `protectedPrefixes` plus a separate `adminPrefixes` role check for UX-level redirect (not the primary security boundary)

### Critical Pitfalls

1. **Chart SSR hydration errors (CRITICAL)** — Recharts accesses `window` at import time, causing "Hydration failed" errors in Next.js 15 production builds (works in dev, breaks in prod — deceptive failure mode). Every component that renders Recharts must be wrapped in `next/dynamic({ ssr: false, loading: () => <Skeleton /> })`. Establish this pattern in Phase 26 before any chart component is written.

2. **Middleware-only admin gate is bypassable (CRITICAL — CVE-2025-29927, CVSS 9.1)** — Sending `x-middleware-subrequest` header bypasses Next.js middleware in versions below 15.2.3. Defense requires two independent layers: (1) upgrade to Next.js 15.2.3+, and (2) verify `session.user.role === "admin"` inside `admin/layout.tsx` as a Server Component using `auth()`. The middleware check in `proxy.ts` is a UX redirect; the layout check is the real security boundary.

3. **Customer layout bleeding into admin (HIGH)** — Root `layout.tsx` applies to all routes; nested layouts are additive, not overriding. The customer Header/Footer must move to `(store)/layout.tsx` before any admin page is built. Doing this restructure later forces re-touching every existing storefront route to move it into the route group.

4. **Stale data after CRUD mutations (MEDIUM)** — TanStack Query does not auto-invalidate after mutations. Every `useMutation` must include `onSuccess: () => queryClient.invalidateQueries(...)` with the correct namespaced key array. Establish shared `QUERY_KEYS` constants in Phase 28 (first CRUD phase) so all subsequent phases copy the same pattern.

5. **Recharts `ResponsiveContainer` renders at zero height (MEDIUM)** — `height="100%"` fails when the parent has no explicit height in a flex/grid context. Always set an explicit `h-*` class or pixel value on the parent div, or pass `height={256}` directly to `ResponsiveContainer`. Address as an explicit checklist item in Phase 27 (Sales Analytics).

---

## Implications for Roadmap

Based on combined research, the admin dashboard decomposes into four implementation phases ordered by dependency. The ARCHITECTURE.md build order (Phases A through G) has been consolidated into four milestones that group work by shared patterns and shared risk.

### Phase 26: Admin Foundation — Layout, Route Protection, and Overview

**Rationale:** Three critical prerequisites must be resolved before any feature page is built: (1) route group restructuring to prevent customer chrome from bleeding into admin, (2) CVE-2025-29927 defense-in-depth with layout-level role check, and (3) the `next/dynamic` SSR-disable pattern for charts must be documented and proven before charts are added in Phase 27. Bundling these with the Overview page validates the entire foundation end-to-end before moving on.

**Delivers:** Working admin shell (sidebar, header, route protection), KPI cards with period selector and delta badges, low-stock count card, `src/lib/admin.ts` with all fetch functions, TanStack Query admin key namespace established (`["admin", ...]` prefix), `next/dynamic` chart wrapper pattern documented.

**Features from FEATURES.md:** KPI summary cards, period selector, delta badges, low-stock count card on overview, admin sidebar navigation, admin route guard.

**Avoids:** CVE-2025-29927 middleware bypass (layout-level `auth()` check), customer layout bleed (route group restructure), chart hydration errors (establishes `ssr: false` pattern before first chart), admin cache key collision (establishes key namespace convention).

**Research flag:** No additional research needed. Route groups and nested layouts are official Next.js App Router docs. Auth.js RBAC patterns are documented. Direct codebase inspection of `proxy.ts` and `auth.ts` in ARCHITECTURE.md confirms the exact integration points.

### Phase 27: Sales Analytics and Inventory Alerts

**Rationale:** Both sections are read-only (no mutations) and data-light — they build on analytics API calls already established in Phase 26. Sales Analytics introduces the only net-new library (Recharts via shadcn charts) and validates the chart SSR pattern under real data. Inventory Alerts is the simplest admin page (server returns pre-sorted data; no TanStack Table needed) and is a natural pairing since both sections share the analytics endpoint prefix. Grouping them avoids a separate minimal phase for Inventory.

**Delivers:** Revenue comparison bar chart (two-period BarChart using shadcn ChartContainer + Recharts BarChart), top-sellers table with revenue/volume toggle, Inventory Alerts table with configurable threshold input and color-coded stock badges (red for out-of-stock, amber for low).

**Uses from STACK.md:** `recharts ^2.15.x` via `npx shadcn@latest add chart`, `ChartContainer`, `ChartTooltip`. Simple shadcn `Table` for inventory — no TanStack Table needed since server pre-sorts the data.

**Avoids:** Zero-height `ResponsiveContainer` trap (explicit parent height is a plan checklist item), building a timeseries chart when the backend only provides period totals (chart is two bars: current vs prior period).

**Research flag:** No additional research needed. shadcn/ui chart docs are official. The two-bar comparison chart is a straightforward BarChart configuration with two data series.

### Phase 28: Book Catalog CRUD

**Rationale:** Catalog management introduces the two most complex admin patterns: full TanStack Table (sort, filter, pagination) and form-based CRUD (react-hook-form + zod for add/edit). Building this before User Management and Review Moderation means `DataTable.tsx`, `BookForm.tsx`, and `ConfirmDialog.tsx` are established as shared components that Phase 29 simply reuses. The stock update mutation also establishes and validates the cache invalidation pattern (`QUERY_KEYS` constants + `invalidateQueries` on success) that all subsequent mutation-heavy pages copy.

**Delivers:** Paginated catalog table with debounced search and genre filter, add book form (modal or dedicated page), edit book form (pre-populated), delete with confirmation dialog, stock update modal with pre-booking notification toast, cross-cache invalidation (admin catalog key + customer books key on any book mutation).

**Implements from ARCHITECTURE.md:** `DataTable.tsx` (TanStack Table + shadcn Table integration), `BookForm.tsx` (react-hook-form + zodResolver), `ConfirmDialog.tsx` (shadcn AlertDialog), `AdminPagination.tsx`, `QUERY_KEYS` constants module.

**Avoids:** Stale data after mutations (invalidates both `["admin", "catalog"]` and `["books"]` on book changes), unbounded table data load (server-side pagination from day one — `?page=N&per_page=20` on every catalog fetch).

**Research flag:** No additional research needed. react-hook-form + zod patterns are well-documented in official docs and already used in v3.0 storefront. TanStack Table v8 has official shadcn data-table docs and the `sadmann7/tablecn` reference implementation (3k+ stars).

### Phase 29: User Management and Review Moderation

**Rationale:** Both sections are table-heavy with per-row and bulk actions. With `DataTable.tsx` already built in Phase 28, both pages are primarily configuration of an established component (different columns, different filter params, different action buttons). Review Moderation adds one new capability beyond User Management: multi-row selection and bulk delete. Grouping them avoids two separate phases for nearly identical patterns. Their backend endpoints (user deactivate/reactivate, review bulk delete) are simpler than book CRUD.

**Delivers:** Paginated user table with role/status filters, deactivate/reactivate with confirmation dialogs (deactivate button disabled for admin-role targets), status badges; paginated review table with full filter bar (book ID, user ID, rating range, sort direction), single-review delete, bulk delete with checkbox selection and confirmation modal ("Delete N reviews? This cannot be undone"), selection state reset after bulk delete.

**Avoids:** Bulk delete without confirmation (AlertDialog required before `DELETE /admin/reviews/bulk`), selection checkboxes remaining checked after deletion (clear `selectedIds` in `onSuccess`), double-click mutations (action buttons disabled via `mutation.isPending`), role check bypassed on deactivate (backend returns 403 for admin targets; frontend also disables the button client-side).

**Research flag:** No additional research needed. Both sections follow the DataTable pattern established in Phase 28. The bulk delete flow is a standard TanStack Query `useMutation` with selection state management.

### Phase Ordering Rationale

- Phase 26 must precede all others: route group restructuring cannot be deferred — doing it after Phase 27 or 28 would require moving all admin feature pages into a different directory mid-build.
- Phase 27 can proceed in parallel with early Phase 28 work (BookForm development is independent of the chart library), but the analytics page itself requires the chart SSR pattern proven in Phase 26 first.
- Phase 28 must precede Phase 29: `DataTable.tsx` built in Phase 28 is directly consumed by Phase 29 user and review pages; building Phase 29 first would require duplicating or stubbing the component.
- Phase 29 is last: it has no downstream consumers and introduces no new component patterns beyond Phase 28.

### Research Flags

All four phases follow fully documented patterns. No `/gsd:research-phase` step is needed during planning.

- **Phase 26:** Route groups, NextAuth role checks, proxy.ts extension — all covered by official Next.js and Auth.js docs. Direct codebase inspection in ARCHITECTURE.md confirms exact integration points.
- **Phase 27:** shadcn chart components and Recharts BarChart — fully documented in official shadcn/ui chart docs. Two-bar comparison is a simple configuration.
- **Phase 28:** react-hook-form + zod + TanStack Table — all documented in official sources. `sadmann7/tablecn` provides a concrete reference implementation.
- **Phase 29:** Composition of Phase 28 patterns — no new libraries or patterns introduced.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Two net-new packages verified against official docs and npm. Version constraints (recharts ^2.15.x, react-is override) confirmed via shadcn/ui React 19 compatibility docs. Recharts v3 vs v2 decision confirmed via shadcn PR #8486 status. |
| Features | HIGH | All backend endpoints confirmed to exist via direct codebase inspection. Feature set derived from official Shopify admin UX guidelines, IBM Carbon Design System badge patterns, and direct API inspection. Anti-features are justified by documented backend constraints, not assumptions. |
| Architecture | HIGH | Based on direct codebase inspection of `proxy.ts`, `auth.ts`, `layout.tsx`, and existing lib modules. Route group pattern is official Next.js App Router documentation. Component boundaries and data flow confirmed by working v3.0 codebase. |
| Pitfalls | HIGH | CVE-2025-29927 sourced from NVD (CVSS 9.1) and ProjectDiscovery technical analysis. Chart SSR hydration issue sourced from shadcn/ui issue tracker (#5661) and Recharts GitHub (#2918). TanStack Query mutation/invalidation patterns are official documentation. |

**Overall confidence:** HIGH

### Gaps to Address

- **Revenue chart data shape validation:** The backend returns `delta_percentage` and current-period revenue, but not the prior-period revenue as a raw value. The prior period must be computed as `current_revenue / (1 + delta_percentage / 100)`. Validate this formula against a live API response before implementing `RevenueChart.tsx`. When `delta_percentage` is null (no prior period data), render only the current period bar.

- **Next.js version verification:** PITFALLS.md flags CVE-2025-29927 requiring Next.js 15.2.3+. Verify the current `frontend/package.json` version before Phase 26 starts. If below 15.2.3, include the version upgrade as the first task in Phase 26.

- **`(store)/` route group migration scope:** Approximately 10 file moves are required to place customer pages inside the `(store)/` directory. During Phase 26 planning, enumerate the exact files to move and identify any import paths or path aliases that reference the old locations to ensure a clean, single-commit migration.

- **Recharts v3 future migration:** shadcn/ui PR #8486 for Recharts v3 support is open but unmerged as of research date. Ship with recharts ^2.15.x. Add a note to the v3.2 backlog to evaluate migration once the PR merges.

---

## Sources

### Primary (HIGH confidence)

- [shadcn/ui Chart docs](https://ui.shadcn.com/charts) — chart component API, Recharts integration, 53 pre-built chart components
- [shadcn/ui React 19 compatibility](https://ui.shadcn.com/docs/react-19) — react-is override requirement for Recharts + React 19
- [TanStack Table v8 docs](https://tanstack.com/table/v8/docs/installation) — headless table API, sort/filter/pagination/selection models
- [shadcn/ui Data Table docs](https://ui.shadcn.com/docs/components/data-table) — TanStack Table + shadcn Table integration pattern
- [sadmann7/tablecn GitHub (3k+ stars)](https://github.com/sadmann7/tablecn) — reference implementation for shadcn DataTable with server-side operations
- [CVE-2025-29927 NVD](https://nvd.nist.gov/vuln/detail/CVE-2025-29927) — CVSS 9.1 middleware bypass affecting Next.js <15.2.3
- [ProjectDiscovery CVE-2025-29927 analysis](https://projectdiscovery.io/blog/nextjs-middleware-authorization-bypass) — x-middleware-subrequest header exploit mechanism
- [Next.js App Router — Route Groups](https://nextjs.org/docs/app/building-your-application/routing/route-groups) — `(folder)` transparent URL grouping for separate layouts
- [Next.js App Router — Layouts](https://nextjs.org/docs/app/building-your-application/routing/layouts-and-templates) — nested layout composition
- [Next.js App Router — Private Folders](https://nextjs.org/docs/app/building-your-application/routing/colocation#private-folders) — `_components` excluded from routing
- [Auth.js RBAC Guide](https://authjs.dev/guides/role-based-access-control) — session role checks in middleware and Server Components
- [Auth.js — Middleware](https://authjs.dev/getting-started/session-management/protecting) — `auth()` in middleware + Server Components for layered protection
- [TanStack Query — Query Invalidation](https://tanstack.com/query/v4/docs/react/guides/query-invalidation) — cache invalidation after mutations
- [TanStack Query — Query Keys](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys) — namespacing to avoid cache collisions
- Direct codebase inspection: `frontend/src/proxy.ts`, `frontend/src/auth.ts`, `frontend/src/app/layout.tsx`, `frontend/src/lib/api.ts`, `backend/app/admin/` routers — source of truth for integration points

### Secondary (MEDIUM confidence)

- [shadcn/ui issue #5661](https://github.com/shadcn-ui/ui/issues/5661) — Chart hydration regression in Next.js 15 + React 19; dynamic import fix
- [recharts/recharts issue #2918](https://github.com/recharts/recharts/issues/2918) — ResponsiveContainer SSR pattern
- [shadcn/ui PR #8486](https://github.com/shadcn-ui/ui/pull/8486) — Recharts v3 update (unmerged as of research date; reason for staying on v2)
- [Shopify Admin UI guidelines](https://shopify.dev/docs/apps/design-guidelines/overview) — authoritative e-commerce admin UX conventions
- [IBM Carbon Design System — Status Indicator Pattern](https://carbondesignsystem.com/patterns/status-indicator-pattern/) — badge design in admin tables
- [10 Best E-commerce Dashboard Examples — Rows.com](https://rows.com/blog/post/ecommerce-dashboard) — KPI card and period-selector patterns
- [Databox — Must-Have Ecommerce Dashboard Examples](https://databox.com/dashboard-examples/ecommerce) — operational metric patterns (slight promotional bias)
- [freeCodeCamp — Build an Admin Dashboard with shadcn/ui](https://www.freecodecamp.org/news/build-an-admin-dashboard-with-shadcnui-and-tanstack-start/) — concrete implementation patterns

### Tertiary (LOW confidence — used for UX conventions only)

- [Admin Dashboard UI/UX Best Practices 2025 — Medium](https://medium.com/@CarlosSmith24/admin-dashboard-ui-ux-best-practices-for-2025-8bdc6090c57d) — badge and table UX patterns (community publication, not validated against authoritative sources)
- [The Right Way to Design Table Status Badges — UX Movement](https://uxmovement.substack.com/p/why-youre-designing-table-status) — badge differentiation principles

---

*Research completed: 2026-02-28*
*Ready for roadmap: yes*
