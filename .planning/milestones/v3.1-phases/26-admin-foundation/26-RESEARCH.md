# Phase 26: Admin Foundation - Research

**Researched:** 2026-02-28
**Domain:** Next.js App Router route restructure, admin layout, CVE-2025-29927 defense-in-depth, shadcn sidebar, TanStack Query key namespacing, admin analytics API integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Sidebar Design**
- Collapsible sidebar: full labels in expanded state, icon-only in collapsed state, with a toggle button
- Flat navigation list with 5 sections at the same level: Overview, Sales, Catalog, Users, Reviews
- Branding at top: "BookStore" app name with "Admin" label/badge subtitle
- "Back to Store" link below branding in sidebar header
- User info (avatar/email + sign out) in sidebar footer; collapses to avatar-only in icon mode
- On mobile: sidebar behaves as a slide-out drawer (consistent with storefront's Sheet-based MobileNav pattern)

**Dashboard Layout**
- 4 cards in a single row: Revenue, Orders, AOV, Low Stock (responsive — stacks on smaller screens)
- Period selector is a segmented button group (Today | This Week | This Month), right-aligned inline with the "Dashboard Overview" page heading
- Top-5 best-sellers mini-table below the card row with columns: Rank, Title, Author, Revenue

**KPI Card Styling**
- Delta indicators use colored text with arrow icons: green "▲ 12.3%" for positive, red "▼ 2.4%" for negative, grey "— 0%" for flat
- Currency formatted as whole dollars with comma separators (e.g., $12,450) — no cents on overview cards
- Low-stock card uses same card shape/size as KPI cards but with amber/warning accent color to distinguish it as a quick-link; shows count + clickable link to Inventory Alerts page

**Route Transition**
- Admin link added to UserMenu dropdown, only visible for admin-role users — not in main Header nav
- Non-admin users hitting /admin are silently redirected to home page ('/') — no toast, no error message (don't reveal route exists)
- Admin layout does NOT show customer Header or Footer — completely separate layout shell

### Claude's Discretion
- Exact sidebar collapse animation and transition timing
- Loading skeleton design for dashboard cards and table
- Error state handling when API calls fail
- Exact spacing, typography scale, and icon choices for sidebar sections
- Responsive breakpoints for card row stacking

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMF-01 | Admin can access a dedicated admin section at `/admin` with a sidebar navigation layout separate from the customer storefront | Route group restructure: `(store)/` for customer pages, `admin/layout.tsx` as independent layout with shadcn Sidebar |
| ADMF-02 | Admin route is protected by role check in both proxy.ts and admin layout Server Component (defense-in-depth against CVE-2025-29927) | CVE-2025-29927: upgrade already covers it at Next.js 16.1.6; defense-in-depth via proxy.ts role check + `auth()` in `admin/layout.tsx` redirect |
| ADMF-03 | Non-admin users are redirected away from `/admin` routes | proxy.ts redirects to `/`; admin layout Server Component also redirects to `/` silently |
| ADMF-04 | Admin sidebar highlights the currently active section | shadcn `SidebarMenuButton` `isActive` prop + `usePathname()` from `next/navigation` |
| DASH-01 | Admin can view KPI cards showing revenue, order count, and AOV for the selected period | `GET /admin/analytics/sales/summary?period=` returns `{ revenue, order_count, aov, delta_percentage }` |
| DASH-02 | Admin can switch period between Today, This Week, and This Month | Client-side React state `period` drives query key; TanStack Query re-fetches on key change |
| DASH-03 | Each KPI card shows a delta badge (green up / red down / grey dash) comparing to the previous period | `delta_percentage` field in `SalesSummaryResponse`; null = grey dash |
| DASH-04 | Admin can see a low-stock count card that links to the inventory alerts section | `GET /admin/analytics/inventory/low-stock?threshold=10` returns `{ total_low_stock }` — display count, link to `/admin/inventory` |
| DASH-05 | Admin can view a top-5 best-selling books mini-table on the overview page | `GET /admin/analytics/sales/top-books?sort_by=revenue&limit=5` returns `{ items: [{ title, author, total_revenue }] }` |
</phase_requirements>

---

## Summary

Phase 26 has two parallel tracks: **infrastructure** (route restructure + admin layout shell) and **data** (admin API layer + dashboard overview page). The infrastructure work is a structural migration: the existing root `app/layout.tsx` must move customer pages into a `(store)/` route group while a new `admin/` segment gets its own layout. The data work establishes the admin fetch layer and TanStack Query namespace that all future admin phases (27-29) depend on.

The key security concern is CVE-2025-29927 (CVSS 9.1), which allowed attackers to bypass Next.js middleware entirely by spoofing the `x-middleware-subrequest` header. The project is already running Next.js 16.1.6 (well past the patched 15.2.3 threshold), so the vulnerability is fixed at the framework level. However, defense-in-depth still requires an independent role check in the `admin/layout.tsx` Server Component — the proxy.ts provides UX-layer redirects while the layout Server Component is the real authorization boundary.

For the sidebar, shadcn's `Sidebar` component is the correct choice. The `--sidebar-*` CSS variables are already defined in `globals.css`, indicating the project was set up with the sidebar in mind. The shadcn sidebar is not yet installed (no `sidebar.tsx` in `components/ui/`), so `npx shadcn@latest add sidebar` is required. For the dashboard, all three analytics endpoints (`/admin/analytics/sales/summary`, `/admin/analytics/sales/top-books`, `/admin/analytics/inventory/low-stock`) are confirmed to exist in the backend with documented response schemas.

**Primary recommendation:** Install shadcn sidebar, restructure routes into `(store)/` group with a Providers-only root layout, build the `admin/layout.tsx` with both role gate and sidebar, then establish `src/lib/admin.ts` + TanStack Query `adminKeys` factory before building the dashboard page.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js App Router | 16.1.6 (installed) | Route groups, Server Components, layouts | Already in use; route groups are native |
| shadcn/ui Sidebar | via `npx shadcn@latest add sidebar` | Collapsible sidebar with icon mode, SidebarProvider state | CSS variables already predefined in globals.css; component composable with project's existing shadcn pattern |
| NextAuth v5 | ^5.0.0-beta.30 (installed) | `auth()` in Server Components for session/role | Already configured; `session.user.role` is available |
| TanStack Query v5 | 5.90.21 (installed) | Data fetching with `adminKeys` namespace | Already in use; query key prefix enables scoped cache invalidation |
| Tailwind v4 + shadcn CSS vars | (installed) | `--sidebar-*` tokens, dark mode, responsive layout | Already configured in globals.css |
| lucide-react | ^0.575.0 (installed) | Sidebar icons (LayoutDashboard, TrendingUp, BookOpen, Users, Star) | Already in use throughout project |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| next-auth/react `useSession` | same | Access `session.user.role` in client sidebar footer | Sidebar footer user info — client component only |
| shadcn `Badge` | (installed) | Delta indicators, "Admin" label in sidebar header | Reuse existing Badge component |
| shadcn `Card`, `CardHeader`, `CardContent` | (installed) | KPI card shells | Reuse existing Card component |
| shadcn `Skeleton` | (installed) | Loading states for KPI cards and mini-table | Reuse existing Skeleton component |
| shadcn `Sheet` | (installed) | Mobile sidebar drawer (used by shadcn Sidebar internally) | shadcn Sidebar uses Sheet for mobile automatically |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| shadcn Sidebar component | Custom CSS sidebar | shadcn Sidebar handles cookie-based state persistence, mobile Sheet, icon collapse, tooltip — building equivalent custom would be significant effort |
| TanStack Query `adminKeys` namespace object | Ad-hoc string keys in each hook | Namespace object enables `queryClient.invalidateQueries({ queryKey: adminKeys.all })` to invalidate all admin cache at once |
| Route group `(store)/` for customer pages | Keep existing flat structure, admin just skips Header/Footer | Route group approach is correct: admin needs a different `<html>/<body>` layout hierarchy; nested layout can't cleanly exclude root layout's Header/Footer |

**Installation:**
```bash
# From frontend/
npx shadcn@latest add sidebar
# This also installs: tooltip, collapsible (peer components used by Sidebar)
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/app/
├── layout.tsx                    # ROOT: html+body+Providers ONLY — no Header/Footer
├── not-found.tsx                 # stays at root
├── (store)/
│   ├── layout.tsx                # customer layout: Header + Footer wrapper
│   ├── page.tsx                  # home page (was app/page.tsx)
│   ├── catalog/                  # (moved from app/catalog/)
│   ├── books/                    # (moved from app/books/)
│   ├── cart/                     # (moved from app/cart/)
│   ├── orders/                   # (moved from app/orders/)
│   ├── wishlist/                 # (moved from app/wishlist/)
│   └── account/                  # (moved from app/account/)
├── (auth)/
│   └── layout.tsx                # (unchanged)
└── admin/
    ├── layout.tsx                # Server Component: auth() role check + SidebarProvider + AppSidebar
    ├── page.tsx                  # redirect to /admin/overview
    └── overview/
        └── page.tsx              # Dashboard overview (KPI cards + period selector + mini-table)

frontend/src/
├── components/
│   ├── admin/
│   │   ├── AppSidebar.tsx        # Client Component: SidebarProvider nav with usePathname
│   │   └── SidebarFooterUser.tsx # Client Component: user info + sign out in sidebar footer
│   └── ui/
│       └── sidebar.tsx           # (added by npx shadcn@latest add sidebar)
└── lib/
    └── admin.ts                  # Server-side fetch functions + adminKeys query key factory
```

### Pattern 1: Route Group Restructure for Multiple Root Layouts

**What:** Move all customer-facing routes into `app/(store)/` route group. The root `app/layout.tsx` becomes Providers-only (html + body + Providers). A `(store)/layout.tsx` wraps children with Header + Footer. The `admin/` segment gets its own layout that never includes the customer Header or Footer.

**Why this approach:** When the admin navigates from `/admin/overview` back to the store (e.g., clicking "Back to Store"), Next.js will trigger a full page reload because the two layouts use different root layouts. This is expected and acceptable — admin-to-store transitions should be treated as cross-application navigation.

**When to use:** Anytime a section needs a fundamentally different chrome (no shared nav, no shared footer, different theme logic).

**Root layout becomes Providers-only:**
```typescript
// app/layout.tsx — AFTER restructure
import type { Metadata } from 'next'
import { Providers } from '@/components/providers'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'Bookstore', template: '%s | Bookstore' },
  description: 'Discover and purchase books from our curated catalog',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

**Store layout wraps with Header + Footer:**
```typescript
// app/(store)/layout.tsx — NEW
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'

export default function StoreLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}
```

### Pattern 2: Admin Layout as Defense-in-Depth Security Boundary (CVE-2025-29927)

**What:** The `admin/layout.tsx` Server Component independently calls `auth()` and checks `session.user.role`. If the user is not an admin, it redirects to `/`. This operates as a real security boundary — even if proxy.ts middleware is somehow bypassed (e.g., via CVE-2025-29927 exploit), the layout Server Component runs server-side and cannot be bypassed by HTTP headers.

**Why:** CVE-2025-29927 (CVSS 9.1, disclosed March 2025) allowed attackers to send `x-middleware-subrequest` header to skip middleware entirely. Next.js 15.2.3+ patches this, and the project is on 16.1.6, but the defense-in-depth pattern remains best practice per the Next.js security postmortem: "Applications are not affected if they perform additional authentication for all Server Rendered Components." The proxy.ts provides UX redirects; the layout provides the real security gate.

**The two-layer pattern:**
```typescript
// src/proxy.ts — Layer 1: UX redirect (fast, edge-compatible)
// Add /admin to protected prefixes AND add admin role check:
const adminPrefixes = ["/admin"]

export const proxy = auth((req) => {
  const { pathname } = req.nextUrl
  const isLoggedIn = !!req.auth
  const userRole = req.auth?.user?.role

  // Existing: protected routes require login
  const isProtected = protectedPrefixes.some((p) => pathname.startsWith(p))
  if (isProtected && !isLoggedIn) {
    const url = new URL("/login", req.nextUrl.origin)
    url.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(url)
  }

  // NEW: admin routes require admin role — silent redirect to /
  const isAdminRoute = adminPrefixes.some((p) => pathname.startsWith(p))
  if (isAdminRoute && userRole !== "admin") {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))
  }

  // ... rest unchanged
})
```

```typescript
// app/admin/layout.tsx — Layer 2: Real security boundary (Server Component)
import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { SidebarProvider } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/admin/AppSidebar'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  // Independent role check — NOT reliant on middleware state
  const session = await auth()
  if (!session?.user || session.user.role !== 'admin') {
    redirect('/')
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </SidebarProvider>
  )
}
```

**Critical:** `auth()` in Server Components reads the NextAuth session cookie directly — it does NOT rely on middleware. This makes it bypass-resistant regardless of proxy.ts state.

### Pattern 3: shadcn Sidebar with Collapsible Icon Mode

**What:** shadcn's `Sidebar` component with `collapsible="icon"` prop. On desktop, clicking `SidebarTrigger` toggles between expanded (labels visible) and icon-only (labels hidden). On mobile, the sidebar renders as a `Sheet` (slide-out drawer) — this is handled automatically by the shadcn Sidebar internals, matching the existing `MobileNav` Sheet pattern.

**Active nav item detection:**
```typescript
// app/components/admin/AppSidebar.tsx — 'use client'
'use client'

import { usePathname } from 'next/navigation'
import {
  Sidebar, SidebarContent, SidebarHeader, SidebarFooter,
  SidebarMenu, SidebarMenuItem, SidebarMenuButton,
} from '@/components/ui/sidebar'
import { LayoutDashboard, TrendingUp, BookOpen, Users, Star, ChevronLeft } from 'lucide-react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'

const navItems = [
  { href: '/admin/overview', label: 'Overview', icon: LayoutDashboard },
  { href: '/admin/sales', label: 'Sales', icon: TrendingUp },
  { href: '/admin/catalog', label: 'Catalog', icon: BookOpen },
  { href: '/admin/users', label: 'Users', icon: Users },
  { href: '/admin/reviews', label: 'Reviews', icon: Star },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        {/* Branding */}
        <div className="flex items-center gap-2 px-2 py-1">
          <span className="font-bold text-lg">BookStore</span>
          <Badge variant="secondary" className="text-xs">Admin</Badge>
        </div>
        {/* Back to Store link */}
        <SidebarMenuButton asChild>
          <Link href="/">
            <ChevronLeft className="h-4 w-4" />
            <span>Back to Store</span>
          </Link>
        </SidebarMenuButton>
      </SidebarHeader>

      <SidebarContent>
        <SidebarMenu>
          {navItems.map((item) => (
            <SidebarMenuItem key={item.href}>
              <SidebarMenuButton
                asChild
                isActive={pathname.startsWith(item.href)}
                tooltip={item.label}
              >
                <Link href={item.href}>
                  <item.icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter>
        <SidebarFooterUser />
      </SidebarFooter>
    </Sidebar>
  )
}
```

**Key detail:** `SidebarMenuButton` with `tooltip` prop shows the label as a tooltip when the sidebar is collapsed to icon-only mode. The `isActive` prop applies the active styling via `data-active` attribute. `usePathname()` is from `next/navigation` — already used in `SearchControls.tsx` and `Pagination.tsx` in this codebase.

**Sidebar footer user info (client component):**
```typescript
// components/admin/SidebarFooterUser.tsx — 'use client'
'use client'

import { useSession, signOut } from 'next-auth/react'
import { SidebarMenuButton, SidebarMenuItem, SidebarMenu, useSidebar } from '@/components/ui/sidebar'
import { LogOut, User } from 'lucide-react'

export function SidebarFooterUser() {
  const { data: session } = useSession()
  const { state } = useSidebar()  // 'expanded' | 'collapsed'
  const email = session?.user?.email ?? ''

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton size="lg" tooltip={email}>
          <User className="h-4 w-4 shrink-0" />
          {state === 'expanded' && (
            <span className="truncate text-sm">{email}</span>
          )}
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton onClick={() => signOut({ callbackUrl: '/' })} tooltip="Sign Out">
          <LogOut className="h-4 w-4" />
          {state === 'expanded' && <span>Sign Out</span>}
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
```

### Pattern 4: Admin Query Key Namespace (TanStack Query)

**What:** A query key factory object `adminKeys` namespaced under `['admin']`. All admin queries use this prefix, enabling bulk cache invalidation and preventing collisions with customer-side query keys.

**Why:** The existing project uses ad-hoc `const REVIEWS_KEY = (bookId) => ['reviews', bookId]` pattern. For admin, a factory object is cleaner because there are multiple endpoints that should be invalidatable as a group. TanStack Query v5 matches on key prefix — `queryClient.invalidateQueries({ queryKey: ['admin'] })` invalidates ALL admin queries at once.

```typescript
// src/lib/admin.ts
import { apiFetch } from '@/lib/api'

// Query key factory — hierarchical prefix enables scoped invalidation
export const adminKeys = {
  all: ['admin'] as const,
  sales: {
    all: ['admin', 'sales'] as const,
    summary: (period: string) => ['admin', 'sales', 'summary', period] as const,
    topBooks: (limit: number) => ['admin', 'sales', 'top-books', limit] as const,
  },
  inventory: {
    all: ['admin', 'inventory'] as const,
    lowStock: (threshold: number) => ['admin', 'inventory', 'low-stock', threshold] as const,
  },
} as const

// Type definitions mirroring backend analytics_schemas.py
export type SalesSummaryResponse = {
  period: string
  revenue: number
  order_count: number
  aov: number
  delta_percentage: number | null
}

export type TopBookEntry = {
  book_id: number
  title: string
  author: string
  total_revenue: number
  units_sold: number
}

export type TopBooksResponse = {
  sort_by: string
  items: TopBookEntry[]
}

export type LowStockResponse = {
  threshold: number
  total_low_stock: number
  items: Array<{
    book_id: number
    title: string
    author: string
    current_stock: number
    threshold: number
  }>
}

// Fetch functions — all require accessToken (admin endpoints enforce require_admin)
export async function fetchSalesSummary(
  accessToken: string,
  period: 'today' | 'week' | 'month'
): Promise<SalesSummaryResponse> {
  return apiFetch<SalesSummaryResponse>(
    `/admin/analytics/sales/summary?period=${period}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}

export async function fetchTopBooks(
  accessToken: string,
  limit: number = 5,
  sort_by: 'revenue' | 'volume' = 'revenue'
): Promise<TopBooksResponse> {
  return apiFetch<TopBooksResponse>(
    `/admin/analytics/sales/top-books?sort_by=${sort_by}&limit=${limit}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}

export async function fetchLowStock(
  accessToken: string,
  threshold: number = 10
): Promise<LowStockResponse> {
  return apiFetch<LowStockResponse>(
    `/admin/analytics/inventory/low-stock?threshold=${threshold}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}
```

### Pattern 5: Dashboard KPI Cards with Period Selector

**What:** Client component that owns `period` state, passes it to TanStack Query hooks. Both the sales summary and top-books queries re-fetch when the period changes because the query key includes the period string.

```typescript
// app/admin/overview/page.tsx — 'use client'
'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { fetchSalesSummary, fetchTopBooks, fetchLowStock, adminKeys } from '@/lib/admin'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type Period = 'today' | 'week' | 'month'

const PERIOD_LABELS: Record<Period, string> = {
  today: 'Today',
  week: 'This Week',
  month: 'This Month',
}

export default function AdminOverviewPage() {
  const [period, setPeriod] = useState<Period>('today')
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''

  const summaryQuery = useQuery({
    queryKey: adminKeys.sales.summary(period),
    queryFn: () => fetchSalesSummary(accessToken, period),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const topBooksQuery = useQuery({
    queryKey: adminKeys.sales.topBooks(5),
    queryFn: () => fetchTopBooks(accessToken, 5, 'revenue'),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  const lowStockQuery = useQuery({
    queryKey: adminKeys.inventory.lowStock(10),
    queryFn: () => fetchLowStock(accessToken, 10),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  // ... render KPI cards, period selector, mini-table
}
```

**Delta badge logic:**
```typescript
function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) {
    return <span className="text-muted-foreground text-sm">— 0%</span>
  }
  if (delta > 0) {
    return <span className="text-green-600 text-sm">▲ {delta.toFixed(1)}%</span>
  }
  return <span className="text-red-600 text-sm">▼ {Math.abs(delta).toFixed(1)}%</span>
}
```

**Currency formatter:**
```typescript
const formatCurrency = (value: number) =>
  `$${Math.round(value).toLocaleString('en-US')}`
// Produces: $12,450 (no cents, comma separator)
```

### Anti-Patterns to Avoid

- **Admin layout relying solely on proxy.ts for security:** proxy.ts can theoretically be bypassed. The admin layout Server Component MUST independently call `auth()` and check `session.user.role`.
- **Using the root layout for Header/Footer then trying to hide them in admin:** Cannot conditionally hide elements injected by a parent layout. The route group + separate layout approach is the correct solution.
- **Single query key for all periods:** Do NOT use `['admin', 'sales', 'summary']` without the period in the key. Different periods must have different cache entries, otherwise switching "Today" → "This Week" returns stale Today data.
- **useSession() in admin layout.tsx Server Component:** `useSession()` is client-only. Use `auth()` from `@/auth` in Server Components. Client components (sidebar footer, dashboard page) use `useSession()`.
- **Not passing `accessToken` to admin fetch functions:** All `/admin/analytics/*` endpoints enforce `require_admin` in FastAPI — they return 403 without a valid Bearer token. The `accessToken` from `session.accessToken` must be passed as `Authorization: Bearer ${accessToken}`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible sidebar with icon mode | Custom CSS + React state sidebar | shadcn `Sidebar` with `collapsible="icon"` | shadcn handles cookie state persistence, mobile Sheet, icon tooltips, CSS variable theming — ~400 lines of tested code |
| Mobile sidebar drawer | Second MobileNav component | shadcn Sidebar built-in mobile Sheet mode | shadcn Sidebar automatically uses Sheet on mobile via `isMobile` detection — no separate MobileNav needed for admin |
| Delta percentage calculation | Frontend formula from two API values | Use `delta_percentage` field directly from API | Backend computes delta correctly; frontend only formats for display |
| Role-based redirect on server | Middleware-only check | `auth()` in Server Component + `redirect()` | Server Component check cannot be bypassed by HTTP header spoofing |
| Query key collision management | Ad-hoc string keys per component | `adminKeys` factory object | Hierarchical keys enable `invalidateQueries({ queryKey: adminKeys.all })` to clear all admin cache on demand |

**Key insight:** The shadcn Sidebar component encapsulates significant complexity (responsive behavior, state persistence, accessibility, theming) that would take significant time to replicate. The CSS variables are already wired in globals.css.

---

## Common Pitfalls

### Pitfall 1: Route Restructure URL Collisions

**What goes wrong:** Moving `app/page.tsx` into `app/(store)/page.tsx` without also moving it out of app root causes a duplicate route error. Next.js does not allow two route groups to resolve to the same URL.

**Why it happens:** Route group folders `(store)` do not change the URL. If both `app/page.tsx` and `app/(store)/page.tsx` exist, they both resolve to `/`.

**How to avoid:** Delete (or move, not copy) `app/page.tsx` before creating `app/(store)/page.tsx`. Move files to `(store)/` by git mv so history is preserved.

**Warning signs:** Build error "Conflicting paths: app/(store)/page.tsx and app/page.tsx both resolve to /"

### Pitfall 2: Full Page Load Between Admin and Store

**What goes wrong:** Developer expects smooth client-side navigation from `/admin/overview` to `/catalog` — instead, the browser does a full page reload.

**Why it happens:** Multiple root layouts cause full page reloads when navigating between them. This is documented Next.js behavior, not a bug.

**How to avoid:** This is expected and correct behavior. The "Back to Store" link in the sidebar should use a regular `<Link href="/">` — the full reload is acceptable and provides a clean context switch.

### Pitfall 3: `auth()` vs `useSession()` Confusion

**What goes wrong:** Trying to call `auth()` in a Client Component, or `useSession()` in a Server Component. Either causes a runtime error.

**Why it happens:** `auth()` is a Next.js server-side function (works in Server Components, Route Handlers, Server Actions). `useSession()` is a React hook (works in Client Components inside `SessionProvider`).

**How to avoid:**
- `admin/layout.tsx` — Server Component → use `auth()` for the role check
- `AppSidebar.tsx` — Client Component → use `useSession()` for the user info in footer
- `DashboardPage.tsx` — Client Component → use `useSession()` for the `accessToken`

### Pitfall 4: `period` State Not Tied to Query Key

**What goes wrong:** Period selector changes local `period` state but the KPI cards don't re-fetch because the query key doesn't include the period.

**Why it happens:** TanStack Query only re-fetches when the query key changes. If the key is static `['admin', 'sales', 'summary']`, switching period does nothing.

**How to avoid:** Always include the period in the query key: `adminKeys.sales.summary(period)` → `['admin', 'sales', 'summary', 'today']`. When period changes, the key changes, triggering a refetch (or a cache hit if that period was previously fetched).

### Pitfall 5: shadcn Sidebar `SidebarProvider` Scope

**What goes wrong:** `useSidebar()` hook throws "useSidebar must be used within a SidebarProvider" when called in a component not wrapped by `SidebarProvider`.

**Why it happens:** `useSidebar()` uses React context. If `AppSidebar` or `SidebarFooterUser` are rendered outside the `SidebarProvider`, the context is missing.

**How to avoid:** `SidebarProvider` wraps the entire admin layout in `admin/layout.tsx`. All child components (including `SidebarFooterUser`) are within the provider boundary. Do NOT put `SidebarProvider` inside the sidebar itself.

### Pitfall 6: Forgetting to Keep `(auth)` Group Working After Restructure

**What goes wrong:** After moving customer pages to `(store)/`, the `(auth)/` group (login/register) stops working because the route matching in proxy.ts still references raw paths that now exist only within route groups.

**Why it happens:** Route groups don't affect URL paths, so `/login` and `/register` continue to work. proxy.ts checks against URL paths, not filesystem paths — the `authOnlyPaths` array checking for `/login` and `/register` remains correct.

**How to avoid:** No change needed to proxy.ts for auth routes. Verify `(auth)/` layout.tsx still exists and hasn't been accidentally moved.

---

## Code Examples

Verified patterns from official sources and project codebase:

### Route Group with Separate Root Layout

```typescript
// app/layout.tsx — Root: html+body+Providers only, no Header/Footer
// Source: Next.js docs on route groups + multiple root layouts
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}

// app/(store)/layout.tsx — Store section: adds Header + Footer
export default function StoreLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}
```

### Admin Layout with Defense-in-Depth Role Check

```typescript
// app/admin/layout.tsx
// Source: CVE-2025-29927 defense-in-depth pattern + NextAuth v5 auth() in Server Components
import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/admin/AppSidebar'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await auth()

  // REAL security boundary — not reliant on middleware state
  if (!session?.user || session.user.role !== 'admin') {
    redirect('/')
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 items-center gap-2 border-b px-4">
          <SidebarTrigger />
        </header>
        <div className="flex-1 overflow-y-auto p-4">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
```

### UserMenu Admin Link (Conditional on Role)

```typescript
// components/layout/UserMenu.tsx — add Admin Dashboard link for admin role
// Source: project pattern — useSession() in client component
if (status === 'authenticated') {
  const role = session?.user?.role
  return (
    <div className="flex items-center gap-2">
      {role === 'admin' && (
        <Link href="/admin">
          <Button variant="ghost" size="sm">Admin</Button>
        </Link>
      )}
      {/* ... existing sign out button */}
    </div>
  )
}
```

### TanStack Query Hook for Dashboard

```typescript
// Follows project pattern from lib/wishlist.ts and lib/reviews.ts
// 'use client'
import { useSession } from 'next-auth/react'
import { useQuery } from '@tanstack/react-query'
import { fetchSalesSummary, adminKeys } from '@/lib/admin'

export function useSalesSummary(period: 'today' | 'week' | 'month') {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''

  return useQuery({
    queryKey: adminKeys.sales.summary(period),
    queryFn: () => fetchSalesSummary(accessToken, period),
    enabled: !!accessToken,
    staleTime: 60_000,
  })
}
```

### Backend API Response Shapes (from analytics_schemas.py)

```typescript
// GET /admin/analytics/sales/summary?period=today|week|month
type SalesSummaryResponse = {
  period: string          // "today" | "week" | "month"
  revenue: number         // float
  order_count: number     // int
  aov: number             // float (0.0 when no orders)
  delta_percentage: number | null  // null when prior period revenue is 0
}

// GET /admin/analytics/sales/top-books?sort_by=revenue&limit=5
type TopBooksResponse = {
  sort_by: string         // "revenue" | "volume"
  items: Array<{
    book_id: number
    title: string
    author: string
    total_revenue: number
    units_sold: number
  }>
}

// GET /admin/analytics/inventory/low-stock?threshold=10
type LowStockResponse = {
  threshold: number
  total_low_stock: number  // Use this for the count card
  items: Array<{
    book_id: number
    title: string
    author: string
    current_stock: number
    threshold: number
  }>
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Middleware-only admin guards | Middleware + Server Component role check | CVE-2025-29927 (March 2025) | Admin layout must call `auth()` independently — middleware alone is insufficient |
| Custom sidebar CSS implementations | shadcn `Sidebar` component | shadcn sidebar released late 2024 | Fully composable, themed, accessible sidebar with cookie state, mobile Sheet, icon mode |
| Single root layout with conditional header visibility | Route groups with multiple root layouts | Next.js App Router (stable) | Clean separation: admin never inherits customer layout chrome |
| Ad-hoc string query keys | Hierarchical query key factory objects | TanStack Query v5 best practice | Enables scoped invalidation with `queryKey: adminKeys.all` |

**Deprecated/outdated:**
- Middleware-only route protection: The CVE-2025-29927 postmortem explicitly states this is insufficient. Always add Server Component verification.
- Custom sidebar components: shadcn sidebar installs and handles all edge cases including mobile, cookie persistence, and theming.

---

## Open Questions

1. **shadcn Sidebar exact peer components installed**
   - What we know: `npx shadcn@latest add sidebar` installs the `sidebar.tsx` component. The sidebar internally uses Tooltip (for icon-mode labels) and Collapsible — these are typically pulled in as peer dependencies by shadcn CLI.
   - What's unclear: Whether the shadcn CLI for this project's version (shadcn ^3.8.5) auto-installs `tooltip.tsx` and `collapsible.tsx` or whether they need separate `npx shadcn@latest add tooltip collapsible` commands.
   - Recommendation: Run `npx shadcn@latest add sidebar` first. If tooltip/collapsible components don't appear in `components/ui/`, run them separately. The sidebar will not render correctly in icon-collapsed mode without tooltips.

2. **`SidebarInset` vs plain `<main>` for content area**
   - What we know: shadcn docs show both `<SidebarInset>` (for `variant="inset"`) and plain `<main>` patterns.
   - What's unclear: Which variant is correct for the project's design (Linear/Vercel-style).
   - Recommendation: Use `<SidebarInset>` — it handles the responsive margin adjustment when sidebar expands/collapses, giving a cleaner layout without manual CSS `margin-left` calculations.

3. **`(store)/` vs `(main)/` naming for route group**
   - What we know: Route group names don't appear in URLs; they're organizational only.
   - What's unclear: User preference for naming.
   - Recommendation: Use `(store)/` as specified in the phase plans. The name conveys intent clearly.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — skipping this section.

---

## Sources

### Primary (HIGH confidence)
- Next.js 16.1.6 installed (`frontend/package.json`) — confirmed version, CVE-2025-29927 patched
- `frontend/src/app/globals.css` — confirmed `--sidebar-*` CSS variables already defined
- `frontend/src/components/ui/` directory listing — confirmed sidebar.tsx NOT installed yet
- `frontend/src/auth.ts` — confirmed `session.user.role` available from JWT, `auth()` export
- `frontend/src/proxy.ts` — confirmed current route protection pattern
- `backend/app/admin/analytics_schemas.py` — confirmed response field names and types
- `backend/app/admin/analytics_router.py` — confirmed endpoint URLs and query parameter names
- Next.js route group docs (https://nextjs.org/docs/app/api-reference/file-conventions/route-groups) — confirmed caveat: full page reload between different root layouts
- shadcn/ui sidebar docs (https://ui.shadcn.com/docs/components/radix/sidebar) — confirmed installation command, SidebarProvider, SidebarMenuButton isActive, useSidebar hook

### Secondary (MEDIUM confidence)
- CVE-2025-29927 analysis (https://projectdiscovery.io/blog/nextjs-middleware-authorization-bypass, https://jfrog.com/blog/cve-2025-29927-next-js-authorization-bypass/) — confirmed vulnerability mechanism, patched in 15.2.3+, defense-in-depth recommendation
- Vercel postmortem (https://vercel.com/blog/postmortem-on-next-js-middleware-bypass) — confirmed "perform additional authentication for all Server Rendered Components" as defense-in-depth
- shadcn sidebar implementation details (https://www.achromatic.dev/blog/shadcn-sidebar) — `group-data-[collapsible=icon]` selector, cookie persistence, tooltip portal caveat

### Tertiary (LOW confidence)
- TanStack Query key factory pattern (search results) — standard community pattern, not in official docs but widely adopted; the `adminKeys` structure is idiomatic for this project

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed from package.json and node_modules; shadcn sidebar install command from official docs
- Architecture: HIGH — route group pattern verified from Next.js docs; auth() pattern verified from existing codebase (orders/page.tsx, account/page.tsx); API schemas from source code
- Security pattern: HIGH — CVE-2025-29927 verified from multiple authoritative sources; defense-in-depth pattern consistent with Vercel postmortem guidance
- Query key factory: MEDIUM — community-established pattern, not prescriptive in TanStack docs, but matches project conventions
- shadcn sidebar component details: MEDIUM — official docs confirm core API; some implementation details (exact peer installs) need runtime verification

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable tech, but shadcn sidebar API evolves — verify if shadcn CLI version changes)
