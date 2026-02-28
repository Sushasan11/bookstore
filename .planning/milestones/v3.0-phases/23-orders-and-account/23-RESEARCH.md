# Phase 23: Orders and Account - Research

**Researched:** 2026-02-28
**Domain:** Next.js 16 App Router — order history list page, account navigation, server-side data fetching
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHOP-07 | User can view order history with date, total, and item summary | `GET /orders` returns `OrderResponse[]` with full items; `list_for_user` orders newest-first; fetchOrders server function follows `fetchOrder` pattern; paginated list with Pagination component pattern from Phase 21 |
| SHOP-08 | User can view individual order detail with full item list and price snapshots | `/orders/[id]` page + `OrderDetail` component already exist from Phase 22; `unit_price` is stored at checkout time as `Decimal` in DB; display pattern established |
</phase_requirements>

---

## Summary

Phase 23 is a primarily **additive** phase with minimal risk. The most important thing to know going in is that two of the three deliverables already exist: the `/orders/[id]` page and `OrderDetail` component were built in Phase 22 (Plan 22-04) for the checkout confirmation flow. Phase 23 simply needs to add the order history list (`/orders` index page) and an account hub page (`/account`), then wire up navigation to both.

The backend is fully ready. `GET /orders` returns `list[OrderResponse]` sorted newest-first with all item details embedded. No backend changes are needed. The frontend `fetchOrder` function in `cart.ts` already shows the exact pattern for server-side order fetching — `fetchOrders` (plural) just needs to call `GET /orders` the same way.

The only architectural decision of note is **pagination approach**: SHOP-07 requires "paginated" order history, but the backend `GET /orders` endpoint returns an unfiltered list (no skip/limit/page params), returning all orders at once. Client-side pagination of the returned array is the correct approach here, keeping backend changes out of scope. For typical users with tens of orders, this is adequate and consistent with the success criteria ("paginated order history list").

**Primary recommendation:** Build in three clean tasks — (1) `fetchOrders` API helper + `/orders` list page with client-side pagination, (2) `/account` hub page with nav cards, (3) human verification of SHOP-07 and SHOP-08.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js App Router | 16.1.6 | Server-component page + client pagination | Already in use; `auth()` pattern established |
| NextAuth.js v5 | beta.30 | `auth()` in server components for `accessToken` | Phase 20 pattern — same as `/orders/[id]` |
| TanStack Query v5 | 5.90.21 | Optional: client-side refetch on focus for account page | Already configured; use only if client interactivity needed |
| shadcn/ui | via radix-ui 1.4.3 | Card, Separator, Skeleton, Badge | Already installed |
| lucide-react | 0.575.0 | Icons (Package, User, History, ChevronRight) | Already installed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | 2.0.7 | Toast for fetch errors | Only if client-side re-fetch needed on account page |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Client-side pagination of fetched list | Backend skip/limit params | Backend change out of scope; list size is small for typical user |
| Server component order list | TanStack Query client fetch | Server component preferred — no auth token on client, cleaner SSR |

**Installation:**

No new packages needed. All dependencies are already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/app/
├── orders/
│   ├── page.tsx                    # NEW: /orders list (server component)
│   ├── loading.tsx                 # NEW: Skeleton for order history
│   ├── _components/
│   │   └── OrderHistoryList.tsx    # NEW: Client component for paginated list
│   └── [id]/                       # EXISTS from Phase 22 — DO NOT MODIFY
│       ├── page.tsx
│       └── _components/
│           └── OrderDetail.tsx
├── account/
│   └── page.tsx                    # NEW: /account hub (server component)
frontend/src/lib/
└── orders.ts                       # NEW: fetchOrders() API helper
```

### Pattern 1: Server Component Order List Page (matches `/orders/[id]` pattern)

**What:** Server component fetches orders using `auth()` + `fetchOrders()`, passes array as prop to client component. No TanStack Query needed.
**When to use:** Order history is read-only, doesn't need optimistic updates. Server rendering is preferred for SEO and initial load performance.

```typescript
// frontend/src/app/orders/page.tsx
import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { fetchOrders } from '@/lib/orders'
import { OrderHistoryList } from './_components/OrderHistoryList'

export const metadata = { title: 'Order History' }

export default async function OrdersPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  const orders = await fetchOrders(session.accessToken)

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Order History</h1>
      <OrderHistoryList orders={orders} />
    </div>
  )
}
```

```typescript
// frontend/src/lib/orders.ts
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

export async function fetchOrders(accessToken: string): Promise<OrderResponse[]> {
  return apiFetch<OrderResponse[]>('/orders', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Pattern 2: Client-Side Pagination of Server-Fetched Data

**What:** Server fetches all orders, passes to client component that handles page slice locally.
**When to use:** Dataset is small (typical user has <100 orders); backend has no pagination params.

```typescript
// frontend/src/app/orders/_components/OrderHistoryList.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

const PAGE_SIZE = 10

interface OrderHistoryListProps {
  orders: OrderResponse[]
}

export function OrderHistoryList({ orders }: OrderHistoryListProps) {
  const [page, setPage] = useState(1)

  if (orders.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">No orders yet.</p>
        <Button asChild className="mt-4">
          <Link href="/catalog">Browse Books</Link>
        </Button>
      </div>
    )
  }

  const totalPages = Math.ceil(orders.length / PAGE_SIZE)
  const pageOrders = orders.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="space-y-4">
      {pageOrders.map((order) => (
        <Link
          key={order.id}
          href={`/orders/${order.id}`}
          className="block rounded-lg border p-4 hover:bg-accent transition-colors"
        >
          <div className="flex justify-between items-start">
            <div>
              <p className="font-medium">Order #{order.id}</p>
              <p className="text-sm text-muted-foreground">
                {new Date(order.created_at).toLocaleDateString(undefined, {
                  year: 'numeric', month: 'long', day: 'numeric',
                })}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {order.items.length} item{order.items.length !== 1 ? 's' : ''}
                {order.items.length > 0 && `: ${order.items[0].book?.title ?? 'Unknown'}${order.items.length > 1 ? `, +${order.items.length - 1} more` : ''}`}
              </p>
            </div>
            <p className="font-semibold">${order.total_price}</p>
          </div>
        </Link>
      ))}
      {/* Pagination controls only if more than one page */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
          <span className="flex items-center text-sm text-muted-foreground px-2">Page {page} of {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      )}
    </div>
  )
}
```

### Pattern 3: Account Hub Page

**What:** Simple server component with nav cards linking to /orders, and placeholders for future /wishlist, /prebook sections (Phase 24).
**When to use:** Central account page needed per roadmap — `/account` is already in `protectedPrefixes` in `proxy.ts`.

```typescript
// frontend/src/app/account/page.tsx
import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Package, Heart, BookMarked } from 'lucide-react'

export const metadata = { title: 'My Account' }

export default async function AccountPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  const email = session.user?.email ?? ''

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">My Account</h1>
      <p className="text-muted-foreground mb-8">{email}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/orders">
          <Card className="p-6 hover:bg-accent transition-colors cursor-pointer">
            <Package className="h-6 w-6 mb-3 text-muted-foreground" />
            <h2 className="font-semibold">Order History</h2>
            <p className="text-sm text-muted-foreground mt-1">View your past orders</p>
          </Card>
        </Link>
        {/* Wishlist and Pre-bookings — Phase 24 */}
      </div>
    </div>
  )
}
```

### Pattern 4: Navigation Wiring

**What:** Add "My Account" link to Header (desktop nav) and MobileNav navLinks array.
**When to use:** Users need discoverability of account features.

```typescript
// Header.tsx — add to <nav> section:
<Link href="/account" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
  Account
</Link>

// MobileNav.tsx — add to navLinks array:
{ href: '/account', label: 'Account' }
```

Note: `UserMenu` currently shows email + Sign Out. Phase 23 could also add an "Account" link inside UserMenu, but that requires converting UserMenu to accept additional links — this can be done minimally.

### Anti-Patterns to Avoid

- **Fetching orders client-side with TanStack Query:** Order history doesn't need live updates or optimistic mutations. Server fetch is simpler and avoids exposing accessToken to client code beyond what's already done in cart.ts.
- **Adding pagination to backend:** `GET /orders` has no skip/limit params. Do not add backend params — out of phase scope. Client-side pagination is sufficient.
- **Modifying `/orders/[id]` page or `OrderDetail` component:** These are complete from Phase 22. Phase 23 only needs to add the `/orders` index page that links to them.
- **Skipping `loading.tsx` on /orders:** The orders fetch can be slow if user has many orders. A loading skeleton prevents layout shift.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Client-side pagination UI | Custom prev/next logic | Simple inline state with useState + array.slice | The catalog Pagination component uses useSearchParams (URL state) — not appropriate here; inline is simpler and avoids URL coupling |
| Order row formatting | Custom date/price formatters | `toLocaleDateString()` + `parseFloat().toFixed(2)` | Already used in OrderDetail — be consistent |
| Route protection | Middleware check in page | Rely on proxy.ts + `auth()` redirect in page | Both already work; double protection is fine, but don't add a third check |

**Key insight:** The `/orders/[id]` detail page is already done. The biggest Phase 23 task is the list page at `/orders` (index). Don't over-engineer the account page — it's a nav hub for now.

---

## Common Pitfalls

### Pitfall 1: `total_price` Formatting on List Page

**What goes wrong:** `order.total_price` comes back as a `Decimal`-serialized string from FastAPI (e.g., `"24.99"`). Rendering `${order.total_price}` directly works but relies on Pydantic serializing Decimal as a numeric string. If it ever comes back as a number, `toFixed(2)` could fail.
**Why it happens:** FastAPI serializes Python `Decimal` to JSON as a numeric or string value depending on config. In this codebase, `OrderDetail` uses `${order.total_price}` directly (no `parseFloat`), which works because the type is `string` in the generated types.
**How to avoid:** Check the generated type for `total_price` — it's typed as `string` in `api.generated.ts` (line ~1275). Use `${order.total_price}` directly, consistent with the existing `OrderDetail` component. Do not add `parseFloat` unless the type changes.
**Warning signs:** If order totals render as `NaN` or malformed, check the Pydantic serialization of `computed_field` Decimal.

### Pitfall 2: Empty Orders Page vs. `/orders` Route Collision

**What goes wrong:** `/orders/page.tsx` (the index) and `/orders/[id]/page.tsx` (the detail) coexist — Next.js App Router handles this correctly, but the `/orders` index page must be at `frontend/src/app/orders/page.tsx`, NOT inside the `[id]` directory.
**Why it happens:** Confusion about Next.js route hierarchy when adding a parent route to an existing dynamic route.
**How to avoid:** Create `frontend/src/app/orders/page.tsx` as a sibling to the existing `[id]/` directory. Verify by running `npm run build` — Next.js will error if routes conflict.

### Pitfall 3: `auth()` in Server Components Returning Empty Session

**What goes wrong:** `auth()` returns a session with `accessToken` when called from server components in Pages (App Router), but NOT when called from client components. If the orders page accidentally has `'use client'`, `auth()` won't work.
**Why it happens:** `auth()` uses Next.js server context (cookies/headers) — only available in server components, route handlers, and middleware.
**How to avoid:** Keep `/orders/page.tsx` and `/account/page.tsx` as server components (no `'use client'` directive). Follow the exact pattern of `/orders/[id]/page.tsx` from Phase 22.

### Pitfall 4: `item.book` Nullable in Order Items

**What goes wrong:** `book: OrderItemBookSummary | null` — a book may have been deleted after the order was placed. The list page needs to handle this gracefully.
**Why it happens:** Books can be soft/hard deleted. The order item keeps `book_id` and `unit_price` as snapshots, but the `book` FK may be null.
**How to avoid:** Use `item.book?.title ?? 'Deleted Book'` (same pattern as `OrderDetail`). Already handled in the existing detail component — carry the pattern to the list summary.

### Pitfall 5: Missing `loading.tsx` Causes CLS on /orders

**What goes wrong:** Without a loading skeleton, the orders page shows blank while the server fetches. This is jarring if the user has many orders or slow backend.
**Why it happens:** App Router shows nothing until the async server component resolves — unless `loading.tsx` is present.
**How to avoid:** Create `frontend/src/app/orders/loading.tsx` with a simple skeleton (3–5 order row placeholders). Mirror the pattern of `frontend/src/app/cart/loading.tsx`.

---

## Code Examples

Verified patterns from existing codebase:

### Fetch Orders (server-side, follows fetchOrder pattern from cart.ts)

```typescript
// frontend/src/lib/orders.ts
// Source: matches pattern in frontend/src/lib/cart.ts fetchOrder()
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type OrderResponse = components['schemas']['OrderResponse']

export async function fetchOrders(accessToken: string): Promise<OrderResponse[]> {
  return apiFetch<OrderResponse[]>('/orders', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Server Page with auth() Guard (follows orders/[id]/page.tsx pattern)

```typescript
// Source: frontend/src/app/orders/[id]/page.tsx
const session = await auth()
if (!session?.accessToken) redirect('/login')

const orders = await fetchOrders(session.accessToken)
// Pass to client component as props
```

### Order Date Formatting (established in OrderDetail.tsx)

```typescript
// Source: frontend/src/app/orders/[id]/_components/OrderDetail.tsx
const orderDate = new Date(order.created_at).toLocaleDateString(undefined, {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})
```

### Item Summary Line (safe null-book handling)

```typescript
// Source: pattern from OrderDetail.tsx — adapts book null-check for list row
const firstTitle = order.items[0]?.book?.title ?? 'Deleted Book'
const summary = order.items.length === 1
  ? firstTitle
  : `${firstTitle} +${order.items.length - 1} more`
```

### Loading Skeleton (mirrors cart/loading.tsx pattern)

```typescript
// frontend/src/app/orders/loading.tsx
import { Skeleton } from '@/components/ui/skeleton'

export default function OrdersLoading() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <Skeleton className="h-8 w-48 mb-6" />
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border p-4">
            <div className="flex justify-between">
              <div className="space-y-2">
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-56" />
              </div>
              <Skeleton className="h-5 w-16" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `getServerSideProps` for auth-gated pages | `auth()` in async server component | Next.js 13+ App Router | No API routes needed for order fetching |
| Client-side `useEffect` data fetching | Server component fetch + prop drilling | Next.js 13+ | Simpler, no loading state in component needed (use loading.tsx) |

**Existing in codebase:**
- `/orders/[id]` page: EXISTS — complete from Phase 22, no changes needed
- `OrderDetail` component: EXISTS — complete from Phase 22, no changes needed
- `fetchOrder` (singular): EXISTS in `cart.ts` — model `fetchOrders` on this
- `/account` prefix: PROTECTED in `proxy.ts` — route already guarded

---

## What Already Exists (Critical for Planning)

This section is the most important output of this research. The planner must know:

| Artifact | Status | Location | Action Required |
|----------|--------|----------|-----------------|
| `/orders/[id]` page | EXISTS — complete | `frontend/src/app/orders/[id]/page.tsx` | None — SHOP-08 is essentially done |
| `OrderDetail` component | EXISTS — complete | `frontend/src/app/orders/[id]/_components/OrderDetail.tsx` | None |
| `fetchOrder(token, id)` | EXISTS | `frontend/src/lib/cart.ts` | Create `fetchOrders(token)` as sibling |
| Route protection `/orders` | EXISTS | `frontend/src/proxy.ts` (line 5) | None — already in `protectedPrefixes` |
| Route protection `/account` | EXISTS | `frontend/src/proxy.ts` (line 5) | None — already in `protectedPrefixes` |
| `/orders` index page | MISSING | `frontend/src/app/orders/page.tsx` | CREATE — core SHOP-07 deliverable |
| `/orders/loading.tsx` | MISSING | `frontend/src/app/orders/loading.tsx` | CREATE — UX quality |
| `/account` page | MISSING | `frontend/src/app/account/page.tsx` | CREATE — account hub |
| Header "Account" nav link | MISSING | `frontend/src/components/layout/Header.tsx` | ADD link |
| MobileNav "Account" link | MISSING | `frontend/src/components/layout/MobileNav.tsx` | ADD to navLinks array |
| `fetchOrders` API helper | MISSING | `frontend/src/lib/orders.ts` | CREATE |

**SHOP-08 insight:** The order detail page already exists. SHOP-08 is verified when a user can navigate from the order history list to an existing `/orders/[id]` page. The Phase 23 work for SHOP-08 is purely the navigation (creating the list page with clickable rows).

---

## Open Questions

1. **Does `/account` warrant its own lib file?**
   - What we know: The account page for Phase 23 is purely a navigation hub — no API calls needed beyond `auth()`.
   - What's unclear: Future phases (24, 25) will add wishlist and pre-booking sections. Should account data fetching start here?
   - Recommendation: Keep Phase 23 account page as a simple server component with no API calls beyond session check. Phase 24 will add actual data fetching for wishlist/pre-bookings.

2. **Should `/orders` index use URL-state pagination or client-side state?**
   - What we know: The catalog Pagination component uses `useSearchParams` for URL-persisted state. The orders list is much smaller (most users have <50 orders).
   - What's unclear: Whether bookmarkable paginated order history is a desired UX.
   - Recommendation: Use simple `useState` client-side pagination — SHOP-07 says "paginated" but not "URL-persisted." Keep it simpler than catalog.

3. **Should `fetchOrders` live in `cart.ts` or a new `orders.ts`?**
   - What we know: `fetchOrder` (singular) lives in `cart.ts` because it was built as part of the cart/checkout flow.
   - What's unclear: Whether to colocate with cart.ts or create a separate `orders.ts`.
   - Recommendation: Create `frontend/src/lib/orders.ts` for `fetchOrders`. This separates concerns: `cart.ts` owns cart mutations + checkout; `orders.ts` owns order history reads. Move `fetchOrder` to `orders.ts` and update the import in `/orders/[id]/page.tsx` — OR keep `fetchOrder` in `cart.ts` and only add `fetchOrders` to `orders.ts`. Either works; the latter requires no file changes in Phase 22's code.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — validation section skipped per instructions (false/absent = skip).

---

## Sources

### Primary (HIGH confidence)

- Codebase: `frontend/src/app/orders/[id]/page.tsx` — established server-component auth pattern
- Codebase: `frontend/src/app/orders/[id]/_components/OrderDetail.tsx` — established OrderResponse rendering patterns
- Codebase: `frontend/src/lib/cart.ts` — `fetchOrder` pattern, `OrderResponse` type usage
- Codebase: `backend/app/orders/router.py` — `GET /orders` returns `list[OrderResponse]`, no pagination params
- Codebase: `backend/app/orders/repository.py` — `list_for_user` orders newest-first
- Codebase: `frontend/src/proxy.ts` — `/account` and `/orders` already in `protectedPrefixes`
- Codebase: `frontend/src/types/api.generated.ts` — `OrderResponse`, `OrderItemResponse` types verified
- Codebase: `frontend/src/app/catalog/_components/Pagination.tsx` — existing pagination pattern
- Codebase: `frontend/src/components/layout/Header.tsx` + `MobileNav.tsx` — nav wiring patterns

### Secondary (MEDIUM confidence)

- None needed — all findings grounded in live codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already installed and in use
- Architecture: HIGH — patterns are established in Phase 22 codebase; Phase 23 follows them directly
- Pitfalls: HIGH — grounded in actual codebase inspection, not speculation

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable stack, no fast-moving dependencies)
