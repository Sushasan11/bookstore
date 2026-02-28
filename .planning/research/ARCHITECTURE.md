# Architecture Research

**Domain:** BookStore v3.1 — Admin Dashboard Integration with Next.js 15 App Router
**Researched:** 2026-02-28
**Confidence:** HIGH (based on direct codebase inspection + official Next.js App Router docs)

---

## Context: Additive Integration, Not Greenfield

v3.1 adds an admin dashboard to an already-shipped Next.js 15 storefront (v3.0). The FastAPI backend already exposes all required admin endpoints — the frontend's job is to surface them. This document answers: how does the admin dashboard fit into the existing App Router structure without disturbing the customer storefront?

**Existing frontend (v3.0, shipped):**
- `src/app/layout.tsx` — root layout with Header, Footer, Providers
- `src/app/(auth)/` — route group for login/register (centred, no nav)
- `src/app/catalog/`, `books/[id]/`, `cart/`, `orders/`, `wishlist/`, `account/` — customer pages
- `src/proxy.ts` — NextAuth-based route protection (protectedPrefixes array)
- `src/auth.ts` — NextAuth v5 config; `session.user.role` exposes admin role from FastAPI JWT
- `src/lib/api.ts` — `apiFetch<T>` wrapper using Bearer token injection
- `src/components/layout/Header.tsx` — customer nav (Books, Wishlist, Account)

**Backend admin API surface (all existing, all require `is_admin` on JWT):**
- `GET /admin/analytics/sales/summary?period=today|week|month` — KPI data
- `GET /admin/analytics/sales/top-books?sort_by=revenue|volume&limit=N` — top-seller rankings
- `GET /admin/analytics/inventory/low-stock?threshold=N` — low-stock alert
- `GET /admin/reviews?page&per_page&book_id&user_id&rating_min&rating_max&sort_by&sort_dir` — paginated review list
- `DELETE /admin/reviews/bulk` (body: `{review_ids: int[]}`) — bulk soft-delete
- `GET /admin/users?page&per_page&role&is_active` — paginated user list
- `PATCH /admin/users/{id}/deactivate` — deactivate user
- `PATCH /admin/users/{id}/reactivate` — reactivate user
- `POST /books`, `PUT /books/{id}`, `DELETE /books/{id}` — book CRUD (admin-only, in existing books router)
- `PATCH /books/{id}/stock` — stock update (admin-only, in existing books router)
- `POST /genres` — genre creation (admin-only)

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Browser                                    │
│                                                                       │
│  Customer Storefront          Admin Dashboard                         │
│  /catalog, /books, /cart      /admin/*, admin-only                   │
└─────────────┬─────────────────────────┬──────────────────────────────┘
              │                         │
┌─────────────▼─────────────────────────▼──────────────────────────────┐
│                       Next.js 15 App Router                           │
│                                                                       │
│  src/app/                                                             │
│  ├── layout.tsx              ← root HTML shell (Providers only)       │
│  ├── (auth)/                 ← login/register (route group, no nav)   │
│  ├── (store)/                ← customer pages with Header + Footer    │
│  │   ├── layout.tsx          ← Header + Footer                        │
│  │   ├── catalog/            ← public catalog                         │
│  │   ├── books/[id]/         ← book detail                            │
│  │   ├── cart/, orders/,     ← auth-gated customer pages              │
│  │   └── account/, wishlist/ │                                        │
│  └── admin/                  ← admin section (NEW)                    │
│      ├── layout.tsx          ← AdminSidebar + AdminHeader (NEW)       │
│      ├── page.tsx            ← /admin overview/dashboard              │
│      ├── analytics/          ← sales charts, top-sellers              │
│      ├── catalog/            ← book CRUD UI                           │
│      ├── users/              ← user management                        │
│      ├── reviews/            ← review moderation                      │
│      └── inventory/          ← low-stock alerts                       │
│                                                                       │
│  src/proxy.ts  ← add "/admin" to protectedPrefixes + role check      │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ HTTP (REST) + Bearer token
┌─────────────────────────────▼────────────────────────────────────────┐
│                   FastAPI Backend (unchanged)                          │
│  /admin/analytics/*  /admin/reviews/*  /admin/users/*                 │
│  /books/* (POST, PUT, DELETE, PATCH /stock are admin-only)            │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Root layout | `src/app/layout.tsx` | HTML shell, Providers (QueryClient, SessionProvider, ThemeProvider) only — NO nav |
| Store layout | `src/app/(store)/layout.tsx` | Customer Header + Footer wrapper (NEW — extract from root layout) |
| Admin layout | `src/app/admin/layout.tsx` | Admin sidebar nav + admin header bar (NEW) |
| Auth guard | `src/proxy.ts` | Extended to protect `/admin/*` AND verify `session.user.role === "admin"` |
| Admin lib | `src/lib/admin.ts` | API fetch functions for all admin endpoints |
| Admin hooks | `src/app/admin/_hooks/` | TanStack Query hooks for admin data |
| Admin components | `src/app/admin/_components/` | Shared admin UI (DataTable, StatCard, ChartWrapper) |
| Page components | `src/app/admin/*/page.tsx` | Individual admin pages |

---

## Recommended Project Structure

```
frontend/src/
├── app/
│   ├── layout.tsx                    # Root: Providers only, no nav (MODIFIED)
│   ├── (auth)/                       # Existing: login, register
│   ├── (store)/                      # Existing pages moved to route group (MODIFIED)
│   │   ├── layout.tsx                # NEW: Header + Footer (extracted from root)
│   │   ├── page.tsx                  # Home redirect
│   │   ├── catalog/
│   │   ├── books/[id]/
│   │   ├── cart/
│   │   ├── orders/
│   │   ├── wishlist/
│   │   └── account/
│   └── admin/                        # NEW: entire admin section
│       ├── layout.tsx                # Admin shell: sidebar + topbar
│       ├── page.tsx                  # /admin — overview/dashboard
│       ├── analytics/
│       │   └── page.tsx              # /admin/analytics — sales charts
│       ├── catalog/
│       │   ├── page.tsx              # /admin/catalog — book list with CRUD actions
│       │   ├── new/
│       │   │   └── page.tsx          # /admin/catalog/new — add book form
│       │   └── [id]/
│       │       └── page.tsx          # /admin/catalog/[id] — edit book form
│       ├── users/
│       │   └── page.tsx              # /admin/users — user list with deactivate/reactivate
│       ├── reviews/
│       │   └── page.tsx              # /admin/reviews — review moderation with bulk delete
│       └── inventory/
│           └── page.tsx              # /admin/inventory — low-stock alerts
├── components/
│   ├── ui/                           # Existing shadcn/ui components (unchanged)
│   └── layout/
│       ├── Header.tsx                # Existing customer header (unchanged)
│       ├── Footer.tsx                # Existing (unchanged)
│       └── admin/                    # NEW: admin layout components
│           ├── AdminSidebar.tsx
│           ├── AdminHeader.tsx
│           └── AdminBreadcrumb.tsx
├── lib/
│   ├── api.ts                        # Existing apiFetch wrapper (unchanged)
│   ├── admin.ts                      # NEW: admin API fetch functions
│   ├── catalog.ts                    # Existing (unchanged)
│   ├── reviews.ts                    # Existing (unchanged)
│   └── ...                           # Other existing libs
└── proxy.ts                          # MODIFIED: add /admin protection + role check
```

### Structure Rationale

- **`(store)/` route group:** Wrapping customer pages in a route group allows the admin section to have a completely different layout. The root `layout.tsx` drops to providing only `<Providers>` — no Header or Footer. The `(store)/layout.tsx` adds the customer Header and Footer. This is the cleanest App Router pattern for multi-section apps.
- **`admin/` as a flat segment (not a route group):** The `/admin` URL prefix is part of the route. Using `(admin)` would strip the prefix from the URL. Use a plain `admin/` directory so URLs are `/admin`, `/admin/catalog`, etc.
- **`admin/_components/` and `admin/_hooks/`:** The `_` prefix marks these as private folders excluded from routing. Co-locating admin components and hooks next to the pages that use them keeps the admin feature cohesive and avoids polluting `src/components/` with admin-only UI.
- **`src/lib/admin.ts`:** A single module for all admin fetch functions mirrors the pattern of `src/lib/catalog.ts`, `src/lib/reviews.ts`, etc. Centralises admin API calls and makes them easy to find and test.

---

## Architectural Patterns

### Pattern 1: Route Group Layout Extraction

**What:** Move Header + Footer from root `layout.tsx` into a `(store)/layout.tsx` route group layout. Root layout becomes Providers-only.

**When to use:** When different top-level sections of the app require completely different chrome (navigation, sidebars, footers). Here: customer storefront needs top nav + footer; admin needs sidebar; auth pages need neither.

**Trade-offs:** Requires moving existing customer pages into a `(store)/` directory — approximately 10 file moves. No URL changes because route groups are transparent in URLs.

**Example:**
```typescript
// src/app/layout.tsx — MODIFIED (Providers only, no nav)
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}

// src/app/(store)/layout.tsx — NEW (adds customer nav)
export default function StoreLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}

// src/app/admin/layout.tsx — NEW (adds admin sidebar)
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <div className="flex flex-1 flex-col">
        <AdminHeader />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  )
}
```

### Pattern 2: Role-Based Route Protection in proxy.ts

**What:** Extend `proxy.ts` to gate `/admin/*` routes with a two-part check: (1) session must exist, (2) `session.user.role` must equal `"admin"`.

**When to use:** Any route segment that requires not just authentication but a specific user role.

**Trade-offs:** The `role` field comes from the FastAPI JWT payload (`payload.role`) decoded in `src/auth.ts`'s `decodeJwtPayload`. If this field is absent or wrong, admins get redirected to 403. This is already wired in `src/auth.ts` — `session.user.role` is correctly populated.

**Example:**
```typescript
// src/proxy.ts — MODIFIED
import { auth } from "@/auth"
import { NextResponse } from "next/server"

const protectedPrefixes = [
  "/account", "/orders", "/checkout", "/wishlist", "/prebook", "/cart",
  "/admin",  // ADD: admin routes require auth
]
const adminPrefixes = ["/admin"]  // ADD: admin routes also require admin role
const authOnlyPaths = ["/login", "/register"]

export const proxy = auth((req) => {
  const isLoggedIn = !!req.auth
  const { pathname } = req.nextUrl

  const isProtected = protectedPrefixes.some((p) => pathname.startsWith(p))
  if (isProtected && !isLoggedIn) {
    const url = new URL("/login", req.nextUrl.origin)
    url.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(url)
  }

  const isAdminRoute = adminPrefixes.some((p) => pathname.startsWith(p))
  if (isAdminRoute && req.auth?.user?.role !== "admin") {
    // Logged-in but not admin → 403 page or redirect to home
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))
  }

  const isAuthPage = authOnlyPaths.some((p) => pathname === p)
  if (isAuthPage && isLoggedIn) {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))
  }

  return NextResponse.next()
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}
```

**Important:** proxy.ts provides the first layer of protection. Admin Server Components must also call `auth()` and verify role before fetching data — middleware alone is not sufficient for defense in depth (documented pitfall in existing ARCHITECTURE.md).

### Pattern 3: Admin API Lib Module

**What:** Centralise all admin API fetch functions in `src/lib/admin.ts`. Each function accepts an `accessToken` and returns a typed response using `components['schemas']['...']` from the generated types.

**When to use:** For all admin endpoint calls. Mirrors the existing pattern of `src/lib/catalog.ts`, `src/lib/reviews.ts`, etc.

**Trade-offs:** Centralising here makes all admin calls easily mockable and findable, at the cost of a single large-ish file. Alternative (co-locating fetch functions in each page) creates duplication across admin pages that share similar pagination patterns.

**Example:**
```typescript
// src/lib/admin.ts
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

export type SalesSummaryResponse = components['schemas']['SalesSummaryResponse']
export type TopBooksResponse = components['schemas']['TopBooksResponse']
export type LowStockResponse = components['schemas']['LowStockResponse']
export type AdminReviewListResponse = components['schemas']['AdminReviewListResponse']
export type UserListResponse = components['schemas']['UserListResponse']
export type AdminUserResponse = components['schemas']['AdminUserResponse']

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
  sortBy: 'revenue' | 'volume',
  limit = 10
): Promise<TopBooksResponse> {
  return apiFetch<TopBooksResponse>(
    `/admin/analytics/sales/top-books?sort_by=${sortBy}&limit=${limit}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}

export async function fetchLowStock(
  accessToken: string,
  threshold = 10
): Promise<LowStockResponse> {
  return apiFetch<LowStockResponse>(
    `/admin/analytics/inventory/low-stock?threshold=${threshold}`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  )
}

export async function fetchAdminReviews(
  accessToken: string,
  params: {
    page?: number; perPage?: number; bookId?: number; userId?: number;
    ratingMin?: number; ratingMax?: number;
    sortBy?: 'date' | 'rating'; sortDir?: 'asc' | 'desc';
  }
): Promise<AdminReviewListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.perPage) qs.set('per_page', String(params.perPage))
  if (params.bookId) qs.set('book_id', String(params.bookId))
  if (params.userId) qs.set('user_id', String(params.userId))
  if (params.ratingMin) qs.set('rating_min', String(params.ratingMin))
  if (params.ratingMax) qs.set('rating_max', String(params.ratingMax))
  if (params.sortBy) qs.set('sort_by', params.sortBy)
  if (params.sortDir) qs.set('sort_dir', params.sortDir)
  return apiFetch<AdminReviewListResponse>(`/admin/reviews?${qs}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function bulkDeleteReviews(
  accessToken: string,
  reviewIds: number[]
): Promise<{ deleted_count: number }> {
  return apiFetch<{ deleted_count: number }>('/admin/reviews/bulk', {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ review_ids: reviewIds }),
  })
}

export async function fetchAdminUsers(
  accessToken: string,
  params: { page?: number; perPage?: number; role?: string; isActive?: boolean }
): Promise<UserListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.perPage) qs.set('per_page', String(params.perPage))
  if (params.role) qs.set('role', params.role)
  if (params.isActive !== undefined) qs.set('is_active', String(params.isActive))
  return apiFetch<UserListResponse>(`/admin/users?${qs}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function deactivateUser(
  accessToken: string,
  userId: number
): Promise<AdminUserResponse> {
  return apiFetch<AdminUserResponse>(`/admin/users/${userId}/deactivate`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function reactivateUser(
  accessToken: string,
  userId: number
): Promise<AdminUserResponse> {
  return apiFetch<AdminUserResponse>(`/admin/users/${userId}/reactivate`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Pattern 4: Admin Pages Are Client Components with TanStack Query

**What:** Admin dashboard pages use `"use client"` with TanStack Query hooks. Unlike customer catalog pages (Server Components with ISR for SEO), admin pages do not need SEO and benefit from interactive filtering, real-time refresh, and optimistic mutations.

**When to use:** All admin pages. The admin section is not indexed by search engines; every page is auth-gated and user-specific. Client Components with TanStack Query provide better interactive UX (instant filter updates, toast feedback on mutations, loading states without full page refresh).

**Trade-offs:** No server-side rendering for admin pages means a brief loading skeleton on initial visit. This is acceptable — admins expect a dashboard UX, not an SSR page. The alternative (Server Components for admin) would require full page reload on every filter change, which is a poor dashboard experience.

**Example:**
```typescript
// src/app/admin/reviews/page.tsx
'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAdminReviews, bulkDeleteReviews } from '@/lib/admin'
import { toast } from 'sonner'

export default function AdminReviewsPage() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'reviews', page],
    queryFn: () => fetchAdminReviews(accessToken, { page }),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  const bulkDelete = useMutation({
    mutationFn: (ids: number[]) => bulkDeleteReviews(accessToken, ids),
    onSuccess: ({ deleted_count }) => {
      toast.success(`Deleted ${deleted_count} review${deleted_count !== 1 ? 's' : ''}`)
      setSelectedIds([])
      queryClient.invalidateQueries({ queryKey: ['admin', 'reviews'] })
    },
    onError: () => toast.error('Bulk delete failed'),
  })

  // ... render DataTable with checkboxes and Bulk Delete button
}
```

---

## Data Flow

### Admin Analytics Flow

```
Admin navigates to /admin/analytics
  → AdminAnalyticsPage (Client Component)
  → useQuery(['admin', 'analytics', 'summary', period])
    → fetchSalesSummary(accessToken, period)
    → GET /admin/analytics/sales/summary?period=today
    ← { revenue, order_count, aov, delta_percentage }
  → Render KPI cards + period selector
  → User changes period → setSelectedPeriod → new useQuery key → refetch
  → Parallel: useQuery for top-books revenue, useQuery for top-books volume
```

### Book Catalog CRUD Flow

```
Admin clicks "Edit Book"
  → Navigate to /admin/catalog/[id]
  → AdminEditBookPage fetches book via GET /books/{id}
  → Admin submits form
    → useMutation: PUT /books/{id} with form data
    → onSuccess: invalidateQueries(['admin', 'catalog'])
               + invalidateQueries(['books', id])  ← also invalidates customer cache
    → onError: show form-level error toast

Admin clicks "Delete Book"
  → Confirmation dialog
  → useMutation: DELETE /books/{id}
  → onSuccess: invalidateQueries(['admin', 'catalog'])
             + toast.success('Book deleted')
  → onError: toast.error
```

### User Deactivate Flow

```
Admin clicks "Deactivate" on user row
  → Confirmation dialog
  → useMutation: PATCH /admin/users/{id}/deactivate
  → FastAPI immediately revokes all refresh tokens for that user
  → onSuccess: invalidateQueries(['admin', 'users'])
             + toast.success('User deactivated')
  → Deactivated user's next API call returns 403 → they are signed out client-side
    (via existing 403 handler in providers.tsx QueryCache.onError)
```

### Review Bulk Delete Flow

```
Admin selects rows in ReviewsTable (checkbox per row)
  → selectedIds state updated (client-side only)
Admin clicks "Delete Selected" button
  → useMutation: DELETE /admin/reviews/bulk { review_ids: selectedIds }
  → onSuccess: setSelectedIds([])
             + invalidateQueries(['admin', 'reviews'])
             + toast.success(`Deleted N reviews`)
  → Best-effort: backend silently skips already-deleted IDs
```

---

## Admin Layout vs Storefront Layout

The admin layout is deliberately different from the customer storefront layout.

| Concern | Customer Storefront | Admin Dashboard |
|---------|---------------------|-----------------|
| Navigation | Top horizontal header (`Header.tsx`) | Left vertical sidebar (`AdminSidebar.tsx`) |
| Logo/Brand | Centred or left-aligned "Bookstore" | "Admin" or "Bookstore Admin" in sidebar header |
| Nav links | Books, Wishlist, Account, Cart | Overview, Analytics, Catalog, Users, Reviews, Inventory |
| Footer | Full site footer with links | No footer — dashboards don't need footers |
| Max width | `max-w-7xl` content constraint | Full width — sidebar takes fixed width, content fills remainder |
| Background | `bg-background` (theme-aware) | `bg-muted/40` sidebar + `bg-background` content area |
| Auth indicator | Email truncated + "Sign Out" button | Admin badge + email + "Sign Out" |
| Layout file | `(store)/layout.tsx` | `admin/layout.tsx` |

**AdminSidebar.tsx responsibilities:**
- Fixed-width vertical nav (`w-64`)
- Links to all admin sections with active state highlighting
- "Back to Storefront" link at bottom (links to `/catalog`)
- User identity (email, "Admin" role badge)

**AdminHeader.tsx responsibilities:**
- Page title / breadcrumb (e.g., "Users > User Management")
- Optional global actions (e.g., period selector for analytics applies globally)
- Keeps admin context visible without repeating the full sidebar in mobile views

---

## Component Organization

### Admin-Specific Shared Components

These components are used across multiple admin pages and belong in `admin/_components/`:

| Component | Used by | Purpose |
|-----------|---------|---------|
| `DataTable.tsx` | Users, Reviews, Catalog | Paginated table with sortable columns, row selection |
| `StatCard.tsx` | Overview, Analytics | KPI card with value, label, delta percentage badge |
| `PeriodSelector.tsx` | Overview, Analytics | Tabs/buttons for today/week/month period switching |
| `ConfirmDialog.tsx` | Users (deactivate), Catalog (delete), Reviews (bulk delete) | Reusable confirmation modal |
| `AdminPagination.tsx` | Users, Reviews, Catalog | Page-based pagination (reuses logic from customer Pagination.tsx) |

### New Components Required

| Component | Type | Notes |
|-----------|------|-------|
| `AdminSidebar.tsx` | Server Component | Static nav; no client state needed |
| `AdminHeader.tsx` | Server or Client | Breadcrumb can be static; period selector would be client |
| `StatCard.tsx` | Client Component | Shows delta with colour-coded badge (green/red/grey) |
| `RevenueChart.tsx` | Client Component | Requires charting library (see STACK.md) |
| `TopBooksTable.tsx` | Client Component | Simple ranked list, no external library needed |
| `LowStockTable.tsx` | Client Component | Colour-coded stock levels |
| `DataTable.tsx` | Client Component | Checkbox selection for bulk actions |
| `BookForm.tsx` | Client Component | react-hook-form + Zod for add/edit book |

### Modified Components

| Component | Change Required |
|-----------|----------------|
| `src/app/layout.tsx` | Remove `<Header />` and `<Footer />` — move to `(store)/layout.tsx` |
| `src/proxy.ts` | Add `/admin` to `protectedPrefixes`, add role check for `adminPrefixes` |

### Unchanged Components (No Modification)

| Component | Why Unchanged |
|-----------|---------------|
| `Header.tsx` | Customer header — moves to `(store)/layout.tsx` but content unchanged |
| `Footer.tsx` | Same |
| `src/auth.ts` | Already exposes `session.user.role` from FastAPI JWT — no changes needed |
| `src/lib/api.ts` | `apiFetch` wrapper is reused as-is by `src/lib/admin.ts` |
| `src/components/ui/*` | All shadcn components shared between admin and storefront |

---

## Build Order (Phase Dependencies)

Admin pages depend on each other in this order:

```
Phase A: Admin Layout Shell + Route Protection
  - Move customer pages to (store)/ route group
  - Extract Header+Footer from root layout to (store)/layout.tsx
  - Create admin/layout.tsx with AdminSidebar + AdminHeader
  - Extend proxy.ts with /admin protection + role check
  - Create /admin/page.tsx overview stub
  - Create src/lib/admin.ts with all fetch functions
  Prerequisite: v3.0 storefront working (done)
  Risk: route group migration must not break existing customer URLs

Phase B: Dashboard Overview (KPI Cards)
  - /admin/page.tsx — StatCard components, period selector
  - Calls: /admin/analytics/sales/summary, /admin/analytics/inventory/low-stock
  - Introduces: StatCard, PeriodSelector, admin TanStack Query patterns
  Prerequisite: Phase A

Phase C: Sales Analytics
  - /admin/analytics/page.tsx — charts, top-seller tables
  - Calls: /admin/analytics/sales/summary (already in Phase B), /admin/analytics/sales/top-books
  - Introduces: charting library (Recharts), TopBooksTable
  Prerequisite: Phase B (StatCard and PeriodSelector already exist)

Phase D: Book Catalog CRUD
  - /admin/catalog/page.tsx — book list with Edit/Delete actions
  - /admin/catalog/new/page.tsx — book creation form
  - /admin/catalog/[id]/page.tsx — book edit form
  - Calls: GET /books (existing endpoint), POST /books, PUT /books/{id}, DELETE /books/{id}, PATCH /books/{id}/stock
  - Introduces: BookForm (react-hook-form + Zod), ConfirmDialog, DataTable
  Prerequisite: Phase A; BookForm can be built in parallel with Phase B/C

Phase E: User Management
  - /admin/users/page.tsx — user list with deactivate/reactivate
  - Calls: GET /admin/users, PATCH /admin/users/{id}/deactivate, PATCH /admin/users/{id}/reactivate
  - Introduces: nothing new (DataTable already exists from Phase D)
  Prerequisite: Phase D (DataTable)

Phase F: Review Moderation
  - /admin/reviews/page.tsx — review list with filters and bulk delete
  - Calls: GET /admin/reviews, DELETE /admin/reviews/bulk
  - Introduces: row selection in DataTable, bulk delete action bar
  Prerequisite: Phase D (DataTable with selection support)

Phase G: Inventory Alerts
  - /admin/inventory/page.tsx — low-stock book list with threshold control
  - Calls: GET /admin/analytics/inventory/low-stock
  - Introduces: threshold input, colour-coded stock level display
  Prerequisite: Phase A (already has the API call)
  Note: This is the simplest admin page; can be built any time after Phase A
```

**Recommended phase groupings for this milestone:**

| Phase | Contents | Rationale |
|-------|---------|-----------|
| Phase 26 | Admin Layout Shell + Route Protection + Overview | Foundation must be first; overview validates the layout |
| Phase 27 | Sales Analytics + Inventory Alerts | Analytics endpoints together; Inventory is simple and fits here |
| Phase 28 | Book Catalog CRUD | Form-heavy, introduces BookForm and DataTable |
| Phase 29 | User Management + Review Moderation | Both use DataTable with actions; build together to avoid two separate phases for identical patterns |

---

## Integration Points

### Backend Admin Endpoints (no backend changes needed)

All admin endpoints are fully implemented and protected with `require_admin`. The frontend consumes them without any backend modification.

| Admin Feature | Endpoint | Auth Mechanism |
|--------------|---------|---------------|
| Sales summary | `GET /admin/analytics/sales/summary` | Bearer token + `is_admin` check in FastAPI |
| Top books | `GET /admin/analytics/sales/top-books` | Same |
| Low stock | `GET /admin/analytics/inventory/low-stock` | Same |
| Review list | `GET /admin/reviews` | Same |
| Bulk delete reviews | `DELETE /admin/reviews/bulk` | Same |
| User list | `GET /admin/users` | Same |
| Deactivate user | `PATCH /admin/users/{id}/deactivate` | Same |
| Reactivate user | `PATCH /admin/users/{id}/reactivate` | Same |
| Create book | `POST /books` | Bearer token + `is_admin` check |
| Update book | `PUT /books/{id}` | Same |
| Delete book | `DELETE /books/{id}` | Same |
| Update stock | `PATCH /books/{id}/stock` | Same |

### Existing Frontend Integration

| Existing Piece | How Admin Uses It |
|---------------|-----------------|
| `src/auth.ts` | `session.user.role` already decoded from FastAPI JWT — admin check uses this |
| `src/lib/api.ts` | `apiFetch<T>` reused by `src/lib/admin.ts` — no duplication |
| `src/components/ui/*` | All shadcn components (Table, Dialog, Button, Badge, Input, etc.) used in admin UI |
| `src/components/providers.tsx` | QueryClient 403 handler already signs out deactivated users — applies to admin too |
| `react-hook-form` + `zod` | Already installed; BookForm uses these for add/edit book |
| `sonner` (toast) | Already installed; admin mutations use `toast.success` / `toast.error` |

### TanStack Query Cache Key Convention

Admin and customer queries must use separate cache namespaces to prevent cache collisions:

```typescript
// Customer queries (existing)
['books', page, filters]
['reviews', bookId]
['cart']
['orders']

// Admin queries (new) — always prefixed with 'admin'
['admin', 'analytics', 'summary', period]
['admin', 'analytics', 'top-books', sortBy]
['admin', 'analytics', 'inventory', threshold]
['admin', 'reviews', page, filters]
['admin', 'users', page, filters]
['admin', 'catalog', page]  // admin view of book list (may differ from customer view)
```

When an admin mutates a book (edit/delete), invalidate both the admin catalog key AND the customer book key so the customer-facing catalog also reflects the change:

```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['admin', 'catalog'] })
  queryClient.invalidateQueries({ queryKey: ['books'] })  // also bust customer cache
}
```

---

## Anti-Patterns

### Anti-Pattern 1: Protecting Admin Routes Only in Middleware

**What people do:** Add `/admin` to `protectedPrefixes` in proxy.ts and assume that's sufficient.

**Why it's wrong:** Middleware runs the role check on the request before the page loads, but if middleware is bypassed (e.g., direct Server Component fetch), the page renders anyway. Also, middleware cannot block Server Component data fetching that happens inside the page.

**Do this instead:** Double-check in every admin Server Component:
```typescript
// In any admin page.tsx
const session = await auth()
if (!session?.accessToken || session.user.role !== 'admin') redirect('/')
```

### Anti-Pattern 2: Sharing Layout Between Admin and Storefront

**What people do:** Keep the customer Header in root `layout.tsx` and add admin nav as an overlay or conditional render.

**Why it's wrong:** The customer Header is meaningless and visually conflicting in the admin context. Conditional rendering based on URL in layout files is fragile and couples two separate concerns. The App Router route group pattern exists precisely to solve this.

**Do this instead:** Extract the customer Header+Footer into `(store)/layout.tsx`. Create a completely separate `admin/layout.tsx`. Root layout contains only `<Providers>`.

### Anti-Pattern 3: Using SSR/ISR for Admin Pages

**What people do:** Make admin pages Server Components to avoid `"use client"` overhead.

**Why it's wrong:** Admin pages require interactive filtering (period selector for analytics, filter inputs for review/user lists), pagination driven by client state, optimistic mutations, and confirmation dialogs. None of these work naturally in Server Components. The SEO justification for SSR does not apply — admin pages are auth-gated and should not be indexed.

**Do this instead:** Admin pages are Client Components using TanStack Query. This gives interactive filtering (changing state refetches), mutation feedback (toast notifications), and deferred loading states.

### Anti-Pattern 4: Mixing Admin and Customer TanStack Query Cache Keys

**What people do:** Use `['books']` as the cache key for both the admin catalog list and the customer-facing catalog.

**Why it's wrong:** Admin's book list view might include different fields (stock quantity, edit/delete actions) or different pagination than the customer view. A shared cache key means customer cache data could populate an admin view expecting admin-specific fields, causing type errors or stale UI.

**Do this instead:** Prefix all admin query keys with `'admin'`. Invalidate customer keys explicitly when an admin mutation should affect the customer-facing data (e.g., after deleting a book).

### Anti-Pattern 5: Importing from `(store)/` path aliases

**What people do:** Reference `@/app/(store)/...` components from admin pages.

**Why it's wrong:** Route group folder names with parentheses in paths are a Next.js App Router convention — the path is `(store)` on disk but the URL segment does not include it. Importing across route group boundaries works but signals poor separation. Admin-specific components belong in `admin/_components/`.

**Do this instead:** Keep shared UI in `src/components/ui/` and `src/components/layout/`. Keep admin-specific UI in `src/app/admin/_components/`. Do not import from `(store)/_components/` in admin pages.

---

## Scaling Considerations

The admin dashboard is a low-traffic internal tool. Scaling is not a concern at any realistic user count for this bookstore. One note that does matter:

| Scale | Consideration |
|-------|--------------|
| Any | Analytics queries run live SQL aggregates on orders/order_items tables. At high order volume (100k+ orders), these queries slow down. For v3.1 this is acceptable — add materialized views or a caching layer in a future milestone if queries exceed 500ms. |
| Any | Bulk delete of reviews (up to 50 IDs) is a single UPDATE...WHERE IN — O(1) DB round-trip. No scaling concern. |

---

## Sources

- `frontend/src/app/layout.tsx` — existing root layout (direct codebase inspection)
- `frontend/src/proxy.ts` — existing route protection pattern (direct codebase inspection)
- `frontend/src/auth.ts` — `session.user.role` already populated from FastAPI JWT (direct codebase inspection)
- `frontend/src/lib/api.ts` — `apiFetch<T>` wrapper (direct codebase inspection)
- `backend/app/admin/analytics_router.py` — all analytics endpoints (direct codebase inspection)
- `backend/app/admin/router.py` — user management endpoints (direct codebase inspection)
- `backend/app/admin/reviews_router.py` — review moderation endpoints (direct codebase inspection)
- `backend/app/books/router.py` — book CRUD endpoints with admin guard (direct codebase inspection)
- [Next.js App Router — Route Groups](https://nextjs.org/docs/app/building-your-application/routing/route-groups) — `(folder)` transparent URL grouping for separate layouts (HIGH confidence — official docs)
- [Next.js App Router — Layouts](https://nextjs.org/docs/app/building-your-application/routing/layouts-and-templates) — nested layout composition pattern (HIGH confidence — official docs)
- [Next.js App Router — Private Folders (`_folder`)](https://nextjs.org/docs/app/building-your-application/routing/colocation#private-folders) — `_components` excluded from routing (HIGH confidence — official docs)
- [TanStack Query — Query Keys](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys) — namespacing cache keys to avoid collisions (HIGH confidence — official docs)
- [Auth.js — Middleware](https://authjs.dev/getting-started/session-management/protecting) — `auth()` in middleware + Server Components for layered protection (HIGH confidence — official docs)

---

*Architecture research for: BookStore v3.1 — Admin Dashboard Integration*
*Researched: 2026-02-28*
