# Phase 26: Admin Foundation - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a protected `/admin` section with its own sidebar layout (separate from the customer storefront), route protection enforced at both proxy.ts and layout Server Component levels, and a dashboard overview page showing KPI metrics (revenue, order count, AOV) with period comparison and a low-stock quick-link card plus a top-5 best-sellers mini-table.

</domain>

<decisions>
## Implementation Decisions

### Sidebar Design
- Collapsible sidebar: full labels in expanded state, icon-only in collapsed state, with a toggle button
- Flat navigation list with 5 sections at the same level: Overview, Sales, Catalog, Users, Reviews
- Branding at top: "BookStore" app name with "Admin" label/badge subtitle
- "Back to Store" link below branding in sidebar header
- User info (avatar/email + sign out) in sidebar footer; collapses to avatar-only in icon mode
- On mobile: sidebar behaves as a slide-out drawer (consistent with storefront's Sheet-based MobileNav pattern)

### Dashboard Layout
- 4 cards in a single row: Revenue, Orders, AOV, Low Stock (responsive — stacks on smaller screens)
- Period selector is a segmented button group (Today | This Week | This Month), right-aligned inline with the "Dashboard Overview" page heading
- Top-5 best-sellers mini-table below the card row with columns: Rank, Title, Author, Revenue

### KPI Card Styling
- Delta indicators use colored text with arrow icons: green "▲ 12.3%" for positive, red "▼ 2.4%" for negative, grey "— 0%" for flat
- Currency formatted as whole dollars with comma separators (e.g., $12,450) — no cents on overview cards
- Low-stock card uses same card shape/size as KPI cards but with amber/warning accent color to distinguish it as a quick-link; shows count + clickable link to Inventory Alerts page

### Route Transition
- Admin link added to UserMenu dropdown, only visible for admin-role users — not in main Header nav
- Non-admin users hitting /admin are silently redirected to home page ('/') — no toast, no error message (don't reveal route exists)
- Admin layout does NOT show customer Header or Footer — completely separate layout shell

### Claude's Discretion
- Exact sidebar collapse animation and transition timing
- Loading skeleton design for dashboard cards and table
- Error state handling when API calls fail
- Exact spacing, typography scale, and icon choices for sidebar sections
- Responsive breakpoints for card row stacking

</decisions>

<specifics>
## Specific Ideas

- Sidebar pattern should feel like Linear or Vercel dashboards — clean, collapsible, icon mode
- Period selector modeled after Stripe/Shopify segmented controls
- Low-stock card should clearly read as "action item" rather than pure metric — amber color + link affordance

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Card` component (`components/ui/card.tsx`): Has CardHeader, CardFooter, CardTitle, CardDescription variants — use for KPI cards
- `Badge` component (`components/ui/badge.tsx`): Use for delta indicators and sidebar "Admin" label
- `Sheet` component (`components/ui/sheet.tsx`): Already used for MobileNav — reuse pattern for mobile admin sidebar
- `Skeleton` component (`components/ui/skeleton.tsx`): Use for loading states
- `Button` component with `ghost`/`outline` variants: Use for sidebar nav items and period selector
- `Sonner` toast system: Already configured in Providers

### Established Patterns
- **Auth**: NextAuth v5 with JWT containing `role` field; session provides `accessToken` and `user.role`
- **Data fetching**: `apiFetch<T>()` utility in `lib/api.ts` + TanStack Query hooks with query key constants
- **Route protection**: `proxy.ts` checks `protectedPrefixes` and redirects unauthenticated users; need to add `/admin` prefix
- **Route groups**: `(auth)` group already exists for login/register pages — use same pattern for `(store)` and `admin`
- **Styling**: Tailwind v4 + shadcn/ui + CSS variables for theming; dark mode via next-themes
- **CSS variables**: `globals.css` already has `--sidebar-*` CSS variables predefined for sidebar component

### Integration Points
- `proxy.ts`: Add `/admin` to protected prefixes + role check for admin-only access
- `app/layout.tsx`: Restructure into `(store)/layout.tsx` for customer pages, `admin/layout.tsx` for admin pages
- `UserMenu.tsx`: Add conditional "Admin Dashboard" link for admin-role users
- Backend admin endpoints: `GET /admin/analytics/sales/summary?period=`, `GET /admin/analytics/sales/top-books?limit=5`, `GET /admin/analytics/inventory/low-stock`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-admin-foundation*
*Context gathered: 2026-02-28*
