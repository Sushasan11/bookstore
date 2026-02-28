# Phase 24: Wishlist and Pre-booking - Research

**Researched:** 2026-02-28
**Domain:** TanStack Query optimistic mutations, React client components, Next.js App Router page patterns
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Heart icon appears on **both** BookCard (catalog grid) and book detail page (ActionButtons area)
- Toggle state: **filled red heart** when wishlisted, **outline heart** when not — classic pattern (Amazon, Airbnb)
- No animation on toggle — simple state swap
- After toggle: **toast notification** ("Added to wishlist" / "Removed from wishlist") — consistent with existing cart toast pattern
- Optimistic update: heart fills/unfills immediately, rolls back with error toast on failure
- Unauthenticated user tapping heart: **toast error + redirect to /login** — same pattern as unauthenticated add-to-cart (no auto-wishlist after login)

### Claude's Discretion

- Wishlist page layout (grid vs list, sorting, empty state design)
- Pre-book button design and placement (replacing "Add to Cart" when out of stock)
- Pre-book confirmation flow (inline vs dialog)
- Pre-bookings list layout on account page
- Pre-booking cancellation interaction
- Heart icon positioning on BookCard (corner placement, z-index relative to cart icon)
- What happens when a wishlisted book's stock status changes

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WISH-01 | User can add a book to their wishlist from catalog or detail page | Wishlist POST /wishlist API exists; BookCard and ActionButtons are already 'use client'; useWishlist hook mirrors useCart pattern |
| WISH-02 | User can remove a book from their wishlist | Wishlist DELETE /wishlist/{book_id} API exists; removal integrated in same toggle mutation |
| WISH-03 | User can view their wishlist with book details and current price/stock | GET /wishlist returns WishlistResponse with embedded book data including stock_quantity and price; new /wishlist page needed |
| WISH-04 | Wishlist toggle uses optimistic update (instant heart icon feedback) | TanStack Query onMutate/onError rollback pattern identical to cart; WISHLIST_KEY cache entry stores Set of book IDs |
| PREB-01 | User sees "Pre-book" button instead of "Add to Cart" when a book is out of stock | ActionButtons already receives inStock prop; button swap is conditional render; Pre-book button replaces disabled "Out of Stock" state |
| PREB-02 | User can pre-book an out-of-stock book | POST /prebooks API exists; 409 PREBOOK_BOOK_IN_STOCK and 409 PREBOOK_DUPLICATE error codes documented |
| PREB-03 | User can view active pre-bookings on their account page | GET /prebooks returns PreBookListResponse; display inline on /account page or as linked sub-page |
| PREB-04 | User can cancel a pre-booking | DELETE /prebooks/{prebook_id} soft-cancels (sets status=CANCELLED); TanStack Query mutation with optimistic removal |
</phase_requirements>

---

## Summary

All backend APIs for this phase are fully implemented and already reflected in the auto-generated TypeScript types (`api.generated.ts`). The frontend work is purely additive: new hook files, new pages, and modifications to two existing components (BookCard and ActionButtons). No backend changes are needed.

The dominant technical pattern is the **TanStack Query optimistic mutation** — already established by the cart feature (`useCart` in `cart.ts`). The wishlist toggle follows the same `onMutate` / `onError` rollback / `onSettled` invalidate lifecycle. The unique challenge is that the toggle state needs to be known by two separate components (BookCard in the grid, ActionButtons on the detail page) simultaneously; this requires a shared cache key for the wishlist set, analogous to `CART_KEY`.

The pre-booking feature is simpler than wishlist: no optimistic UI is required (the "Pre-book" button is a one-shot action, not a persistent toggle), and the pre-bookings list on the account page is a straightforward server-fetched list with client-side cancel mutations, mirroring the order history pattern.

**Primary recommendation:** Build a `useWishlist` hook in `src/lib/wishlist.ts` that owns the wishlist cache, expose `wishlisted` as a `Set<number>` derived from the cache, and consume it in both BookCard and ActionButtons. Pre-booking gets a separate `usePrebook` hook in `src/lib/prebook.ts`. Pages follow the established server-fetch + error-boundary pattern from `/orders`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TanStack Query | v5 (already installed) | Wishlist and prebook server state, optimistic mutations | Already project standard for all cart/order mutations |
| next-auth/react | v5 (already installed) | `useSession()` for accessToken in client hooks | Already used in BookCard, ActionButtons, useCart |
| sonner | (already installed) | Toast notifications on toggle/prebook/cancel | Already used for cart toasts — consistency required |
| lucide-react | (already installed) | `Heart`, `HeartOff` icons for wishlist toggle | `Heart` already imported in ActionButtons (currently disabled) |
| shadcn/ui | (already installed) | Button, Card, Badge components | Project UI standard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openapi-typescript generated types | (already generated) | `components['schemas']['WishlistItemResponse']`, `PreBookResponse`, etc. | Always — types are already in `api.generated.ts`, no manual type definition needed |
| next/navigation `useRouter` | Next.js 15 | Redirect to /login for unauthenticated toggle | Already used in BookCard and ActionButtons |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Set<number> wishlist cache | Full WishlistResponse cache | Full cache is more data but enables the wishlist page to reuse the same cache; both are valid — see Architecture section |
| Inline pre-bookings on /account | Separate /prebooks page | Inline is simpler; a separate page adds nav complexity without benefit at this scale |

**Installation:** No new packages needed. All dependencies already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── lib/
│   ├── wishlist.ts          # useWishlist hook + API functions (new)
│   └── prebook.ts           # usePrebook hook + API functions (new)
├── app/
│   ├── wishlist/
│   │   └── page.tsx         # /wishlist page (new, server component)
│   ├── account/
│   │   └── page.tsx         # MODIFIED: add pre-bookings section and wishlist link
│   ├── catalog/_components/
│   │   └── BookCard.tsx     # MODIFIED: add heart icon + useWishlist
│   └── books/[id]/_components/
│       └── ActionButtons.tsx # MODIFIED: wire heart + pre-book button
```

### Pattern 1: Wishlist Toggle with Shared Cache Key

**What:** A single `WISHLIST_KEY` cache entry holds the full `WishlistResponse` (matching the GET /wishlist shape). Both BookCard and ActionButtons read `wishlisted` as a derived `Set<number>` from this cache. Toggling calls add or remove depending on current state.

**When to use:** Whenever the same boolean state must be shown across multiple components on different pages (catalog grid and book detail).

**Example:**
```typescript
// Source: mirrors useCart pattern from src/lib/cart.ts
'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type WishlistResponse = components['schemas']['WishlistResponse']
type WishlistItemResponse = components['schemas']['WishlistItemResponse']

export const WISHLIST_KEY = ['wishlist'] as const

export function useWishlist() {
  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()
  const router = useRouter()

  const wishlistQuery = useQuery({
    queryKey: WISHLIST_KEY,
    queryFn: () => apiFetch<WishlistResponse>('/wishlist', {
      headers: { Authorization: `Bearer ${accessToken}` },
    }),
    enabled: !!accessToken,
    staleTime: 60_000,
  })

  // Derived set of book IDs — O(1) lookup for heart icon state
  const wishlistedIds = new Set(
    wishlistQuery.data?.items.map((item) => item.book_id) ?? []
  )

  const toggleWishlist = useMutation({
    mutationFn: ({ bookId, isWishlisted }: { bookId: number; isWishlisted: boolean }) =>
      isWishlisted
        ? apiFetch<void>(`/wishlist/${bookId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${accessToken}` },
          })
        : apiFetch<WishlistItemResponse>('/wishlist', {
            method: 'POST',
            headers: { Authorization: `Bearer ${accessToken}` },
            body: JSON.stringify({ book_id: bookId }),
          }),
    onMutate: async ({ bookId, isWishlisted }) => {
      await queryClient.cancelQueries({ queryKey: WISHLIST_KEY })
      const previous = queryClient.getQueryData<WishlistResponse>(WISHLIST_KEY)
      // Optimistic update
      if (previous) {
        const updatedItems = isWishlisted
          ? previous.items.filter((i) => i.book_id !== bookId)
          : [...previous.items, { id: -1, book_id: bookId, added_at: new Date().toISOString(), book: {} as WishlistItemResponse['book'] }]
        queryClient.setQueryData<WishlistResponse>(WISHLIST_KEY, { items: updatedItems })
      }
      return { previous }
    },
    onError: (_err, { isWishlisted }, context) => {
      if (context?.previous) {
        queryClient.setQueryData(WISHLIST_KEY, context.previous)
      }
      toast.error(isWishlisted ? 'Failed to remove from wishlist' : 'Failed to add to wishlist')
    },
    onSuccess: (_data, { isWishlisted }) => {
      toast.success(isWishlisted ? 'Removed from wishlist' : 'Added to wishlist')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: WISHLIST_KEY })
    },
  })

  const handleToggle = (bookId: number) => {
    if (!session?.accessToken) {
      toast.error('Please sign in to save books to your wishlist')
      router.push('/login')
      return
    }
    toggleWishlist.mutate({ bookId, isWishlisted: wishlistedIds.has(bookId) })
  }

  return { wishlistQuery, wishlistedIds, handleToggle, isPending: toggleWishlist.isPending }
}
```

### Pattern 2: Heart Icon Integration in BookCard

**What:** Heart button sits in the top-left corner of the card cover area (cart icon is top-right). Uses `useWishlist()` hook — `wishlistedIds.has(book.id)` drives filled vs. outline state.

**When to use:** Any card component that shows both add-to-cart and wishlist actions.

**Example:**
```typescript
// BookCard.tsx — relevant additions
import { Heart } from 'lucide-react'
import { useWishlist } from '@/lib/wishlist'

export function BookCard({ book }: { book: BookResponse }) {
  const { wishlistedIds, handleToggle, isPending } = useWishlist()
  const isWishlisted = wishlistedIds.has(book.id)

  const handleHeartClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    handleToggle(book.id)
  }

  return (
    <div className="group relative ...">
      {/* Heart — top-left, mirrors cart icon at top-right */}
      <Button
        variant="secondary"
        size="icon"
        className="absolute top-2 left-2 h-8 w-8 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity shadow-sm"
        onClick={handleHeartClick}
        disabled={isPending}
        aria-label={isWishlisted ? `Remove ${book.title} from wishlist` : `Add ${book.title} to wishlist`}
      >
        <Heart className={isWishlisted ? 'fill-red-500 text-red-500' : ''} />
      </Button>
      {/* existing cart icon stays top-right */}
    </div>
  )
}
```

### Pattern 3: ActionButtons — Pre-book Button Replaces Disabled "Out of Stock"

**What:** When `inStock` is false, render a "Pre-book" button using `usePrebook` hook instead of the disabled "Out of Stock" button. The "Add to Wishlist" heart becomes a live toggle.

**When to use:** Book detail page ActionButtons when stock_quantity === 0.

**Example:**
```typescript
// ActionButtons.tsx — restructured conditional
export function ActionButtons({ bookId, inStock }: ActionButtonsProps) {
  const { wishlistedIds, handleToggle } = useWishlist()
  const { handlePrebook, isPending: isPrebooked } = usePrebook()
  const isWishlisted = wishlistedIds.has(bookId)

  return (
    <div className="mt-6">
      <div className="flex flex-wrap gap-4">
        {inStock ? (
          <Button size="lg" onClick={handleAddToCart} disabled={addItem.isPending}>
            <ShoppingCart /> {addItem.isPending ? 'Adding...' : 'Add to Cart'}
          </Button>
        ) : (
          <Button size="lg" variant="outline" onClick={() => handlePrebook(bookId)} disabled={isPrebooked}>
            Pre-book
          </Button>
        )}
        <Button
          size="lg"
          variant="outline"
          onClick={() => handleToggle(bookId)}
        >
          <Heart className={isWishlisted ? 'fill-red-500 text-red-500' : ''} />
          {isWishlisted ? 'Wishlisted' : 'Add to Wishlist'}
        </Button>
      </div>
    </div>
  )
}
```

### Pattern 4: Wishlist Page — Server Fetch then Client List

**What:** `/wishlist/page.tsx` is a server component that fetches the wishlist via `auth()` + `apiFetch`. Renders a client list component with remove capability. Mirrors `/orders/page.tsx` exactly.

**When to use:** All authenticated data pages in this project.

**Example:**
```typescript
// app/wishlist/page.tsx
import { auth } from '@/auth'
import { redirect } from 'next/navigation'
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

export default async function WishlistPage() {
  const session = await auth()
  if (!session?.accessToken) redirect('/login')

  let data: components['schemas']['WishlistResponse'] = { items: [] }
  try {
    data = await apiFetch('/wishlist', {
      headers: { Authorization: `Bearer ${session.accessToken}` },
    })
  } catch {
    // Show empty state on error
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">My Wishlist</h1>
      <WishlistList items={data.items} />
    </div>
  )
}
```

### Pattern 5: Pre-bookings Inline on Account Page

**What:** The `/account` page already has a placeholder comment `{/* Wishlist and Pre-bookings — Phase 24 */}`. Add two new Card links: one to `/wishlist`, one that reveals an inline pre-bookings list fetched server-side. Pre-bookings are a bounded user-owned list — no pagination needed at this scale.

**When to use:** Account hub pattern (same as Phase 23 decision for client-side pagination on bounded lists).

### Anti-Patterns to Avoid

- **Fetching wishlist per-component:** Both BookCard and ActionButtons call `useWishlist()` but share `WISHLIST_KEY` — TanStack Query deduplicates the network request automatically. Never fetch per-component with separate keys.
- **Storing wishlist state in Zustand:** The wishlist is server-owned mutable state — TanStack Query is the right tool. Zustand is only used for UI-only display state (cart badge in this project).
- **Optimistic update with fabricated book data:** The `onMutate` optimistic item has a stub `book` object with empty fields. The `onSettled` invalidation refetches the real data immediately after. Displaying wishlist items from the optimistic cache before the refetch would show broken book info — the optimistic update is only for the `book_id` membership check (heart fill state), not for rendering wishlist item rows.
- **Using `book_id` param vs `prebook_id` param:** Wishlist DELETE uses `/wishlist/{book_id}` (book ID, not wishlist item ID). Pre-booking DELETE uses `/prebooks/{prebook_id}` (the pre-booking record ID). Mixing these up is a common mistake.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Optimistic toggle rollback | Custom state machine | TanStack Query `onMutate`/`onError` context | Already proven in `useCart`; handles race conditions, concurrent mutations, query cancellation |
| Toast notifications | Custom notification system | `sonner` (already installed) | Project standard; `toast.success` / `toast.error` pattern already used in cart |
| Unauthenticated redirect | Custom auth check component | Inline `if (!session?.accessToken)` + `toast.error` + `router.push('/login')` | Established pattern in BookCard and ActionButtons |
| Heart icon | Custom SVG | `lucide-react` `Heart` — `fill-red-500 text-red-500` CSS for filled state | `Heart` already imported in ActionButtons |

**Key insight:** This phase is almost entirely a composition of already-proven patterns. The only new judgment calls are UI layout decisions (Claude's discretion items in CONTEXT.md).

---

## Common Pitfalls

### Pitfall 1: Heart Icon Z-index Conflict with Cart Icon on BookCard

**What goes wrong:** Both the cart icon (top-right) and heart icon (top-left) are `absolute`-positioned over the cover image. If z-index is not explicit, one can obscure the other or the Link element beneath.

**Why it happens:** The card's `relative` parent and `absolute` children are in the same stacking context. The Link wraps the entire card and is a clickable area.

**How to avoid:** Both icon buttons use `e.preventDefault()` + `e.stopPropagation()` to prevent the Link navigation from firing. The existing cart icon already does this correctly. Mirror the same approach for the heart icon.

**Warning signs:** Clicking the heart navigates to the book detail page instead of toggling — stopPropagation was missed.

### Pitfall 2: Wishlist Cache Not Populated Before First Toggle

**What goes wrong:** On a fresh page load of the catalog, `wishlistQuery.data` is undefined until the first fetch completes. `wishlistedIds` will be an empty Set, so hearts show as un-filled even for wishlisted books until the fetch resolves.

**Why it happens:** `useQuery` starts as `isLoading: true`; the Set is derived from `wishlistQuery.data?.items ?? []` which is empty during loading.

**How to avoid:** This is acceptable behavior — hearts render in the un-filled state during the brief loading period, then correctly fill once data arrives. No special handling needed. Do NOT show a loading spinner on every heart icon; that degrades UX on the catalog grid.

**Warning signs:** If the brief flash bothers the user, consider `initialData` seeded from server props — but this is over-engineering for this phase.

### Pitfall 3: Pre-book Button Visible on In-Stock Books

**What goes wrong:** If the `inStock` condition check is wrong or the prop name is misread, the Pre-book button appears on books that have stock.

**Why it happens:** The `in_stock` boolean field on `BookResponse` and `stock_quantity > 0` are two separate things — the book detail page passes `book.in_stock` as the `inStock` prop. The backend sets `in_stock` as a computed field. Ensure `inStock={book.in_stock}` is the source, not a manual `stock_quantity > 0` check.

**Warning signs:** Backend returns `409 PREBOOK_BOOK_IN_STOCK` when the user tries to pre-book — means the button appeared incorrectly.

### Pitfall 4: 409 PREBOOK_DUPLICATE Not Handled Gracefully

**What goes wrong:** A user tries to pre-book a book they already pre-booked. The API returns `409 PREBOOK_DUPLICATE`. If unhandled, this shows a generic error toast.

**Why it happens:** Missing `ApiError` status check in `onError`.

**How to avoid:** In `usePrebook` hook's `onError`, check `err instanceof ApiError && err.status === 409` — show "You already have an active pre-booking for this book" toast. Optionally disable the Pre-book button if the user already has an active prebook (requires fetching prebooks on the detail page, which is an over-fetch — a simple error toast is sufficient).

### Pitfall 5: Wishlist Page Cache Mismatch (Server Fetch vs Client Hook)

**What goes wrong:** The `/wishlist/page.tsx` server component fetches data directly via `apiFetch` (outside TanStack Query). The `useWishlist` hook also fetches via TanStack Query. These are separate requests — removing an item on the wishlist page via client mutation correctly updates the TanStack Query cache, but the server-rendered initial data is stale.

**Why it happens:** Server-side fetch and client-side TanStack Query cache are independent.

**How to avoid:** The wishlist page should pass the server-fetched data as `initialData` to TanStack Query (same pattern as how `useCart` works — the page doesn't pre-fetch; useCart fetches on mount). Alternatively, make WishlistList a pure client component that reads from `useWishlist()` hook directly, fetching on mount. The simpler approach used in orders (pass data as prop to client list component) works fine if the list component calls a mutation and then `queryClient.invalidateQueries` — the page will revalidate. **Recommended:** WishlistList is a client component that receives initial items as prop but uses TanStack mutation for remove — same as `OrderHistoryList` but with mutations.

### Pitfall 6: Pre-booking cancellation uses prebook `id`, not `book_id`

**What goes wrong:** Developer passes `book_id` to the cancel mutation instead of the pre-booking record `id`.

**Why it happens:** The DELETE endpoint is `/prebooks/{prebook_id}` — it uses the pre-booking row ID, not the book's ID.

**How to avoid:** `PreBookResponse` has both `id` (pre-booking row ID) and `book_id`. Always use `prebook.id` for cancellation. See `prebooks/router.py` line 49.

---

## Code Examples

### Wishlist API Functions

```typescript
// Source: mirrors cart.ts pattern, verified against backend/app/wishlist/router.py
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type WishlistResponse = components['schemas']['WishlistResponse']
type WishlistItemResponse = components['schemas']['WishlistItemResponse']

export async function fetchWishlist(accessToken: string): Promise<WishlistResponse> {
  return apiFetch<WishlistResponse>('/wishlist', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function addToWishlist(accessToken: string, bookId: number): Promise<WishlistItemResponse> {
  return apiFetch<WishlistItemResponse>('/wishlist', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ book_id: bookId }),
  })
}

export async function removeFromWishlist(accessToken: string, bookId: number): Promise<void> {
  return apiFetch<void>(`/wishlist/${bookId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Pre-booking API Functions

```typescript
// Source: verified against backend/app/prebooks/router.py
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type PreBookResponse = components['schemas']['PreBookResponse']
type PreBookListResponse = components['schemas']['PreBookListResponse']

export async function fetchPrebooks(accessToken: string): Promise<PreBookListResponse> {
  return apiFetch<PreBookListResponse>('/prebooks', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function createPrebook(accessToken: string, bookId: number): Promise<PreBookResponse> {
  return apiFetch<PreBookResponse>('/prebooks', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ book_id: bookId }),
  })
}

export async function cancelPrebook(accessToken: string, prebookId: number): Promise<void> {
  return apiFetch<void>(`/prebooks/${prebookId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Heart Icon — Filled vs Outline (lucide-react)

```typescript
// Source: lucide-react Heart icon, CSS fill pattern
import { Heart } from 'lucide-react'

// Filled (wishlisted):
<Heart className="fill-red-500 text-red-500 h-4 w-4" />

// Outline (not wishlisted):
<Heart className="h-4 w-4" />
```

### BookSummary Type Reference (wishlist items)

```typescript
// Source: api.generated.ts — app__wishlist__schemas__BookSummary
// Wishlist item's embedded book has:
{
  id: number
  title: string
  author: string
  price: string        // decimal string e.g. "12.99"
  stock_quantity: number  // non-zero means back in stock
  cover_image_url: string | null
}
```

### PreBookResponse Type Reference

```typescript
// Source: api.generated.ts — PreBookResponse
{
  id: number            // pre-booking row ID — use THIS for cancellation
  book_id: number
  book_title: string
  book_author: string
  status: string        // "waiting" | "notified" | "cancelled"
  created_at: string
  notified_at: string | null
  cancelled_at: string | null
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ActionButtons has disabled Heart placeholder | ActionButtons gets live useWishlist hook | Phase 24 | Heart button becomes functional |
| ActionButtons shows disabled "Out of Stock" text | ActionButtons shows "Pre-book" button when !inStock | Phase 24 | User can reserve out-of-stock titles |
| /account page has placeholder comment for Phase 24 | /account shows wishlist link card + pre-bookings section | Phase 24 | Account hub gains two new sections |

**Already in place (do not rebuild):**
- `Heart` icon: already imported in `ActionButtons.tsx` (line 2) — currently renders as a disabled placeholder
- Unauthenticated redirect: `toast.error + router.push('/login')` pattern is in BookCard (line 44-47) and ActionButtons (line 22-25)
- `apiFetch` + `ApiError`: handles 204 No Content (wishlist DELETE returns 204) transparently at line 39 of `api.ts`

---

## Open Questions

1. **Should pre-bookings be inline on /account or a separate /prebooks page?**
   - What we know: Account page already has a grid of Card links (`/orders`). Pre-bookings could be a third card link, or the list could be rendered inline below the cards.
   - What's unclear: Number of pre-bookings a user realistically has (likely small — few books stay out of stock permanently).
   - Recommendation (Claude's Discretion): Render pre-bookings inline on `/account` below the existing cards (like a section with a heading), not as a separate page. This keeps the account hub self-contained. Mark as Claude's discretion.

2. **Wishlist page layout: grid or list?**
   - What we know: Wishlist items include `cover_image_url` and price/stock status — enough data for a grid similar to catalog, or a list similar to cart items.
   - Recommendation (Claude's Discretion): Use a simple list layout (like cart items) rather than a grid — wishlist is a personal saved list, not a browsing surface. Each row: cover thumbnail, title, author, price, stock badge, remove button.

3. **Should useWishlist query be enabled for unauthenticated users?**
   - What we know: `enabled: !!accessToken` — same as `useCart`. Hearts show as un-filled (no query fired) for logged-out users. Clicking a heart triggers the auth redirect.
   - Recommendation: Yes, gate behind `enabled: !!accessToken`. No wishlist fetch for unauthenticated sessions.

---

## Sources

### Primary (HIGH confidence)

- `backend/app/wishlist/router.py` — exact API routes, request/response shapes, error codes (409 WISHLIST_ITEM_DUPLICATE, 404 WISHLIST_ITEM_NOT_FOUND)
- `backend/app/prebooks/router.py` — exact API routes, error codes (409 PREBOOK_BOOK_IN_STOCK, 409 PREBOOK_DUPLICATE, 409 PREBOOK_ALREADY_CANCELLED, 404 PREBOOK_NOT_FOUND)
- `backend/app/wishlist/schemas.py` — WishlistAdd, WishlistItemResponse, WishlistResponse, BookSummary
- `backend/app/prebooks/schemas.py` — PreBookCreate, PreBookResponse, PreBookListResponse
- `frontend/src/types/api.generated.ts` — all TypeScript types for wishlist and prebooks, already generated
- `frontend/src/lib/cart.ts` — useCart optimistic mutation pattern (direct source for useWishlist architecture)
- `frontend/src/app/catalog/_components/BookCard.tsx` — current component structure, cart icon placement, existing auth pattern
- `frontend/src/app/books/[id]/_components/ActionButtons.tsx` — existing Heart placeholder, inStock prop usage
- `frontend/src/app/account/page.tsx` — Phase 24 placeholder comment confirmed at line 29
- `frontend/src/app/orders/page.tsx` — server-fetch + client list page pattern
- `frontend/src/lib/api.ts` — apiFetch handles 204 No Content, ApiError class

### Secondary (MEDIUM confidence)

- `backend/app/prebooks/models.py` — PreBookStatus enum: WAITING/NOTIFIED/CANCELLED — status field in response is one of these string values
- `backend/app/wishlist/models.py` — UniqueConstraint on (user_id, book_id) confirms one entry per user-book pair

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and used in project; no new dependencies
- Architecture: HIGH — patterns directly verified from existing cart.ts, orders pattern; API shapes verified from backend source + generated types
- Pitfalls: HIGH — derived from reading actual component code and backend error codes; not speculative

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable — no fast-moving dependencies involved)
