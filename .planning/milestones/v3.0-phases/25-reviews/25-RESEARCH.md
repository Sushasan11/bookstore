# Phase 25: Reviews - Research

**Researched:** 2026-02-28
**Domain:** Frontend review UI — displaying reviews, star rating selector, write/edit/delete forms on book detail page
**Confidence:** HIGH

---

## Summary

Phase 25 is exclusively a **frontend-only phase**. The backend is fully implemented and production-ready: the `reviews` module (model, repository, service, router, schemas) is complete, all five endpoints are registered in `main.py`, and the Alembic migration (`g2h3i4j5k6l7`) is applied. The generated API types (`api.generated.ts`) already include `ReviewResponse`, `ReviewListResponse`, `ReviewCreate`, `ReviewUpdate`, `ReviewAuthorSummary`, and `ReviewBookSummary` — no type regeneration is needed.

The work is entirely in `frontend/src/app/books/[id]/`: adding a `ReviewsSection` below the book description and an interactive `ReviewForm` for write/edit/delete. The `RatingDisplay` component (which renders aggregate star rating in the hero) already has a `TODO: Phase 25` note referencing the reviews section scroll target. The book detail page (`/books/[id]/page.tsx`) is a Next.js ISR server component that needs to be extended by adding a data fetch for the book's reviews at build time, and a client-side `useReviews` hook for mutations.

The one non-trivial decision is the **interactive star rating selector**. shadcn/ui has no built-in star component. The project's existing `RatingDisplay` uses plain Unicode `★` spans with Tailwind — a small custom 5-button star selector following the same pattern is the right call. It avoids adding a new dependency for a ~30-line component and matches the existing project aesthetic.

**Primary recommendation:** Build `ReviewsSection` (server-rendered list) + `ReviewForm` (client component) + `StarSelector` (small custom widget) + `useReviews` hook in `frontend/src/lib/reviews.ts`. No backend changes required.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REVW-01 | User can see reviews and ratings on the book detail page | `GET /books/{book_id}/reviews` returns `ReviewListResponse`; fetch in page.tsx server component; render `ReviewsSection` |
| REVW-02 | User who purchased a book can leave a 1-5 star rating with optional text review | `POST /books/{book_id}/reviews` with `ReviewCreate`; backend enforces purchase gate (403 NOT_PURCHASED); frontend shows form only when `session` exists; custom `StarSelector` for interactive rating |
| REVW-03 | User can edit their own review | `PATCH /reviews/{review_id}` with `ReviewUpdate`; detect user's own review by `review.user_id === session.userId`; pre-populate form fields |
| REVW-04 | User can delete their own review | `DELETE /reviews/{review_id}` returns 204; requires confirmation prompt — use shadcn `Dialog` (already installed) |
| REVW-05 | User sees "already reviewed" state with edit option if they've already reviewed | Query `GET /books/{book_id}/reviews` and detect user's own review in list; or rely on 409 `DUPLICATE_REVIEW` response which includes `existing_review_id` |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TanStack Query v5 | `^5.90.21` (installed) | Server state for review list and mutations | Already project standard; consistent with cart/wishlist/prebook hooks |
| Next.js 16 App Router | `16.1.6` (installed) | ISR server component for initial review fetch; client components for form | Already project foundation |
| next-auth v5 | `^5.0.0-beta.30` (installed) | `useSession()` in client components to get `accessToken` and `userId` | Project auth standard |
| sonner | `^2.0.7` (installed) | Toast notifications for success/error states | Project notification standard |
| lucide-react | `^0.575.0` (installed) | Star icon if needed; Trash2, Pencil icons for actions | Project icon library |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn `Dialog` | installed | Delete confirmation prompt | REVW-04 requires confirmation before delete |
| shadcn `Textarea` | NOT installed | Optional text review input | Must install with `npx shadcn add textarea` |
| shadcn `Skeleton` | installed | Loading state while reviews fetch | Use in `ReviewsSection` loading state |

**Installation needed:**
```bash
cd frontend && npx shadcn add textarea
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom StarSelector | `react-rating`, `react-stars`, `@smastrom/react-rating` | Third-party libs add bundle weight and require their own styling integration; 30-line custom component is simpler |
| Custom StarSelector | Lucide `Star` icons as buttons | Could work; plain Unicode `★` matches existing `RatingDisplay` visual style exactly |
| Textarea (shadcn) | Plain `<textarea>` with Tailwind | shadcn Textarea has consistent focus ring + dark mode tokens already wired |

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── lib/
│   └── reviews.ts              # useReviews hook + API functions (NEW)
├── app/books/[id]/
│   ├── page.tsx                # EXTEND: add initial review fetch, pass to ReviewsSection
│   └── _components/
│       ├── ReviewsSection.tsx  # NEW: server-rendered list + client form
│       ├── ReviewCard.tsx      # NEW: single review display (author, stars, text, date)
│       ├── ReviewForm.tsx      # NEW: 'use client' — write/edit form with StarSelector
│       ├── StarSelector.tsx    # NEW: interactive 1-5 star picker
│       └── RatingDisplay.tsx   # MODIFY: resolve TODO — add #reviews scroll anchor link
```

### Pattern 1: Reviews Data Layer (lib/reviews.ts)

**What:** Mirror of `lib/wishlist.ts` and `lib/prebook.ts` — API fetch functions + a `useReviews` hook using TanStack Query.
**When to use:** All review mutations (create, update, delete) and fetching current user's review.

```typescript
// lib/reviews.ts — follows established project hook pattern
'use client'

import { useSession } from 'next-auth/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/api'
import type { components } from '@/types/api.generated'

type ReviewResponse = components['schemas']['ReviewResponse']
type ReviewListResponse = components['schemas']['ReviewListResponse']
type ReviewCreate = components['schemas']['ReviewCreate']
type ReviewUpdate = components['schemas']['ReviewUpdate']

export const REVIEWS_KEY = (bookId: number) => ['reviews', bookId] as const

export async function fetchReviews(bookId: number): Promise<ReviewListResponse> {
  return apiFetch<ReviewListResponse>(`/books/${bookId}/reviews?size=50`)
}

export async function createReview(
  accessToken: string,
  bookId: number,
  body: ReviewCreate
): Promise<ReviewResponse> {
  return apiFetch<ReviewResponse>(`/books/${bookId}/reviews`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(body),
  })
}

export async function updateReview(
  accessToken: string,
  reviewId: number,
  body: ReviewUpdate
): Promise<ReviewResponse> {
  return apiFetch<ReviewResponse>(`/reviews/${reviewId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(body),
  })
}

export async function deleteReview(
  accessToken: string,
  reviewId: number
): Promise<void> {
  return apiFetch<void>(`/reviews/${reviewId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Pattern 2: ReviewsSection — Server-Seeded + Client Cache Takeover

**What:** The book detail page server component fetches initial reviews server-side and passes them as props. `ReviewsSection` uses TanStack Query with `initialData` so the list is immediately visible (SSR), then stays live after client-side mutations invalidate the cache.
**When to use:** Same pattern as `WishlistList` — SSR items render immediately, TanStack Query takes over.

```typescript
// In page.tsx — extend existing server component
import { fetchReviews } from '@/lib/reviews'

// Inside BookDetailPage:
let initialReviews: ReviewListResponse = { items: [], total: 0, page: 1, size: 50 }
try {
  initialReviews = await fetchReviews(book.id)
} catch {
  // show empty state, don't crash page
}

// Pass to ReviewsSection (rendered below description)
<ReviewsSection bookId={book.id} initialReviews={initialReviews} />
```

```typescript
// ReviewsSection.tsx
'use client'
import { useQuery } from '@tanstack/react-query'
import { fetchReviews, REVIEWS_KEY } from '@/lib/reviews'

export function ReviewsSection({ bookId, initialReviews }) {
  const { data } = useQuery({
    queryKey: REVIEWS_KEY(bookId),
    queryFn: () => fetchReviews(bookId),
    initialData: initialReviews,
    staleTime: 30_000,
  })
  // ...render ReviewCard list + ReviewForm
}
```

### Pattern 3: Detecting the Current User's Own Review

**What:** After fetching reviews, find the current user's review by matching `review.user_id` against the session user ID. The JWT `sub` claim holds the user ID as a string.
**When to use:** Drives the "already reviewed" state (REVW-05) and enables edit mode.

```typescript
// From session — NextAuth v5 decodes JWT sub via jose decodeJwt (Phase 20 decision)
// session.userId is available via auth() on server, useSession() on client
// In client component:
const { data: session } = useSession()
const userId = session ? Number((session as any).userId) : null

const myReview = data?.items.find(r => r.user_id === userId) ?? null
```

**Note:** Check the session type definition in `frontend/src/auth.ts` or NextAuth types to confirm the exact field name for user ID (`userId` vs parsing `accessToken`).

### Pattern 4: Interactive StarSelector

**What:** Five clickable star buttons (keyboard accessible) that set a rating from 1-5. Renders filled/empty state based on hover + selected value.
**When to use:** Inside `ReviewForm` for both create and edit flows.

```typescript
// StarSelector.tsx — pure controlled component, ~40 lines
interface StarSelectorProps {
  value: number          // 1-5, 0 = unset
  onChange: (rating: number) => void
  disabled?: boolean
}

export function StarSelector({ value, onChange, disabled }: StarSelectorProps) {
  const [hovered, setHovered] = useState(0)
  const display = hovered || value

  return (
    <div className="flex gap-1" role="group" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          aria-label={`${star} star${star !== 1 ? 's' : ''}`}
          className={`text-2xl transition-colors ${
            star <= display ? 'text-yellow-500' : 'text-muted-foreground'
          }`}
        >
          ★
        </button>
      ))}
    </div>
  )
}
```

### Pattern 5: 409 DUPLICATE_REVIEW Handling

**What:** When `POST /books/{book_id}/reviews` returns 409, the response body includes `existing_review_id`. Use this to switch the form into edit mode rather than showing a bare error.
**When to use:** In `createReview` mutation's `onError` handler.

```typescript
onError: (err) => {
  if (err instanceof ApiError && err.status === 409) {
    const body = err.data as { code: string; existing_review_id?: number }
    if (body.code === 'DUPLICATE_REVIEW' && body.existing_review_id) {
      // Switch to edit mode — invalidate query to load existing review
      queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
      toast.info('You already reviewed this book — editing your existing review')
    }
  }
}
```

### Pattern 6: Delete Confirmation with shadcn Dialog

**What:** Use the installed `Dialog` component (same as `CheckoutDialog` in Phase 22) for delete confirmation instead of `window.confirm`.
**When to use:** REVW-04 — user clicks delete, Dialog opens, confirms, mutation fires.

```typescript
// Pattern from CheckoutDialog.tsx — Dialog is a pure controlled component
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

<Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete Review</DialogTitle>
      <DialogDescription>
        Are you sure you want to delete your review? This cannot be undone.
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
        Cancel
      </Button>
      <Button
        variant="destructive"
        disabled={deleteMutation.isPending}
        onClick={() => deleteMutation.mutate({ reviewId: myReview.id })}
      >
        Delete
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Anti-Patterns to Avoid

- **Calling `/books/{book_id}/reviews` with default page size (20)**: Use `size=50` to get all reviews for the detail page — book reviews are bounded and rarely exceed 50 in this app. Avoids pagination complexity.
- **Checking purchase eligibility client-side**: Do NOT pre-fetch orders to decide whether to show the form. Always show the form to authenticated users; let the backend return 403 NOT_PURCHASED if they haven't purchased. Surface this as a toast message.
- **Using `window.confirm` for delete**: The project uses shadcn `Dialog` for confirmations (established in CheckoutDialog pattern). Stay consistent.
- **Creating a separate route for reviews**: Keep everything on the book detail page per the phase goal. No `/books/[id]/reviews` sub-route.
- **ISR invalidation on review submit**: The `revalidate = 3600` on page.tsx only affects the SSR shell. Client-side TanStack Query cache invalidation (`queryClient.invalidateQueries`) handles live updates after mutations — no need for `revalidatePath` or `router.refresh()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom alert divs | `sonner` (installed) | Already project standard — use `toast.success/error/info` |
| Delete confirmation modal | Custom overlay | shadcn `Dialog` (installed) | Established pattern in CheckoutDialog; accessible, keyboard dismissible |
| Text area for review body | `<input>` | shadcn `Textarea` (install) | Consistent focus ring, dark mode, and resize behavior |
| API typing | Inline fetch with `as any` | `components['schemas']['ReviewResponse']` from `api.generated.ts` | Already generated — zero-cost typed access |
| Error state display | Custom error boundary | Try/catch returning empty state + `toast.error` | Established pattern in `account/page.tsx` and `cart.ts` |

**Key insight:** The backend is the hard part, and it's already done. This phase is purely about wiring up well-understood client patterns the project has already established.

---

## Common Pitfalls

### Pitfall 1: Session userId Access in Client Components

**What goes wrong:** `useSession()` in Next.js with NextAuth v5 returns a `session` object; the `sub` JWT claim (the FastAPI user ID) may not be directly on `session.user.id` without custom session typing.
**Why it happens:** NextAuth v5 with a custom JWT bridge (Phase 20 decision) stores the FastAPI user ID in the JWT `sub` claim. The session callback in `auth.config.ts` must propagate this to the session object. The shape depends on the Phase 20 session callback implementation.
**How to avoid:** Before writing review ownership detection, check `frontend/src/auth.ts` or `frontend/src/auth.config.ts` for how `sub` is surfaced in the session. The `jose decodeJwt` call in the Phase 20 jwt callback extracts `sub` and returns it — verify what key name is used on the client session object.
**Warning signs:** `userId` comes through as `undefined` — add a quick `console.log(session)` in the component during development.

### Pitfall 2: ISR Page Not Refreshing After Review Submit

**What goes wrong:** After submitting a review, the review count in `BookDetailHero` (avg_rating, review_count) stays stale because it was SSR'd.
**Why it happens:** The book detail page has `revalidate = 3600`. The `avg_rating` and `review_count` shown in `BookDetailHero` come from the ISR-cached book data, not from the reviews query.
**How to avoid:** Accept that `avg_rating`/`review_count` in the hero may be up to 1 hour stale. The `ReviewsSection` itself will show live data via TanStack Query. This is an acceptable trade-off documented in CATL-07. Do not add `router.refresh()` after mutations — it would trigger a full page re-render and is slow.
**Warning signs:** If exact count accuracy matters, the planner can add a client-side derived count from the reviews list, but this is out of scope per current requirements.

### Pitfall 3: ReviewForm Must Not Render for Unauthenticated Users

**What goes wrong:** Showing the "Write a Review" form to unauthenticated users leads to a confusing experience when submit fails with 401.
**Why it happens:** The form is a client component; session state is async.
**How to avoid:** Check `session?.accessToken` before rendering the form. If unauthenticated, render a "Sign in to write a review" prompt instead. Unauthenticated users can still see the review list (GET is public).

### Pitfall 4: `ReviewUpdate` PATCH Semantics — Partial Update

**What goes wrong:** Sending `{ rating: 4, text: null }` to PATCH clears the review text unintentionally if user only changed the rating.
**Why it happens:** The backend uses `model_fields_set` to distinguish "user omitted" from "user sent null". If the frontend serializes the full form state (including `text: null`), the text gets cleared.
**How to avoid:** In the update mutation, only include fields that the user actually changed. Build the PATCH body selectively:
```typescript
const body: ReviewUpdate = {}
if (rating !== originalRating) body.rating = rating
if (text !== originalText) body.text = text
// Do NOT send text: null unless user explicitly cleared it
```

### Pitfall 5: `Textarea` shadcn Component Not Installed

**What goes wrong:** `import { Textarea } from '@/components/ui/textarea'` throws a module-not-found error.
**Why it happens:** Only 11 shadcn components are installed. `Textarea` is not one of them.
**How to avoid:** The plan's Wave 0 must include `cd frontend && npx shadcn add textarea` before any work referencing `Textarea`.
**Warning signs:** TypeScript will immediately flag the missing module import.

### Pitfall 6: Star Rating Selector Accessibility

**What goes wrong:** Clicking a star doesn't work with keyboard navigation; screen reader can't announce the selected rating.
**Why it happens:** Plain `<span onClick>` elements are not keyboard-focusable.
**How to avoid:** Use `<button type="button">` for each star (not div or span) with `aria-label`. The `type="button"` prevents form submission on click.

---

## Code Examples

Verified patterns from project codebase:

### Fetching reviews server-side in page.tsx

```typescript
// Source: existing pattern from /wishlist page.tsx + prebook fetch in account/page.tsx
import { fetchReviews } from '@/lib/reviews'

// In BookDetailPage server component:
let initialReviews = { items: [], total: 0, page: 1, size: 50 }
try {
  initialReviews = await fetchReviews(book.id)
} catch {
  // empty state — don't crash the page
}
```

### TanStack Query mutation with cache invalidation (project pattern)

```typescript
// Source: lib/wishlist.ts onSettled pattern, lib/prebook.ts onSuccess pattern
const createMutation = useMutation({
  mutationFn: (body: ReviewCreate) => createReview(accessToken, bookId, body),
  onSuccess: () => {
    toast.success('Review submitted!')
    queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
  },
  onError: (err) => {
    if (err instanceof ApiError && err.status === 403) {
      toast.error('You must purchase this book before reviewing it')
    } else if (err instanceof ApiError && err.status === 409) {
      const body = err.data as { code: string; existing_review_id?: number }
      if (body.code === 'DUPLICATE_REVIEW') {
        queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
        toast.info('Showing your existing review — you can edit it below')
      }
    } else {
      toast.error('Failed to submit review')
    }
  },
})
```

### Delete mutation with 204 handling

```typescript
// Source: lib/wishlist.ts removeFromWishlist pattern + lib/api.ts 204 handling
const deleteMutation = useMutation({
  mutationFn: ({ reviewId }: { reviewId: number }) =>
    deleteReview(accessToken, reviewId),
  onSuccess: () => {
    toast.success('Review deleted')
    setDeleteDialogOpen(false)
    queryClient.invalidateQueries({ queryKey: REVIEWS_KEY(bookId) })
  },
  onError: () => {
    toast.error('Failed to delete review')
  },
})
```

### Rendering a date in a review card

```typescript
// Source: formatPublishDate pattern from BookDetailHero.tsx
function formatReviewDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric',
    })
  } catch {
    return dateStr
  }
}
```

### Auth-gated form (project pattern)

```typescript
// Source: ActionButtons.tsx handleAddToCart / handlePrebook pattern
if (!session?.accessToken) {
  toast.error('Please sign in to write a review')
  router.push('/login')
  return
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `window.confirm()` for delete | shadcn `Dialog` component | Phase 22 (CheckoutDialog) | Accessible, styleable, consistent with design system |
| Separate page for reviews | Section on detail page | This phase | Simpler UX, no new route needed |
| Custom star rating library | Small custom component | This phase | Zero dependency cost, matches existing `RatingDisplay` aesthetic |

**Deprecated/outdated:**
- External star rating libraries (`react-rating`, `react-stars`): Not needed — custom widget is 30-40 lines and matches the existing project's `★` Unicode character approach in `RatingDisplay.tsx`.

---

## Open Questions

1. **Session userId field name for ownership detection**
   - What we know: NextAuth v5 with FastAPI JWT bridge (Phase 20). The `jose decodeJwt` call in the jwt callback extracts `sub` (FastAPI user ID). The session callback propagates this.
   - What's unclear: The exact field name on the client-side session object (`session.userId`? `session.user.id`? decoded from `session.accessToken`?). Need to check `frontend/src/auth.ts`.
   - Recommendation: Read `auth.ts` at the start of Wave 1 implementation. If the field is not cleanly surfaced, decode it from `session.accessToken` using `jose` (already installed) — same approach used in the jwt callback.

2. **RatingDisplay.tsx scroll anchor**
   - What we know: The component has a `TODO: Phase 25 — link to reviews section` comment.
   - What's unclear: The `RatingDisplay` is currently in `BookDetailHero` (a server component); adding an anchor link means updating the TODO comment but not adding client-side logic.
   - Recommendation: Change `cursor-pointer` div to an `<a href="#reviews">` anchor tag pointing to the reviews section ID. Pure HTML — no client boundary needed.

3. **Review list pagination for books with many reviews**
   - What we know: Backend supports pagination; `size` param max is 100. Fetching `size=50` covers most books.
   - What's unclear: Requirements do not mention pagination for the reviews list on the detail page.
   - Recommendation: Fetch `size=50` (no pagination UI). This satisfies REVW-01 without added complexity. Pagination can be deferred to v3.1.

---

## Sources

### Primary (HIGH confidence)

- `backend/app/reviews/router.py` — All 5 REST endpoints confirmed: POST /books/{book_id}/reviews, GET /books/{book_id}/reviews, GET /reviews/{review_id}, PATCH /reviews/{review_id}, DELETE /reviews/{review_id}
- `backend/app/reviews/schemas.py` — ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse shapes
- `backend/app/reviews/service.py` — Business logic: purchase gate, ownership check, duplicate detection, 409 DuplicateReviewError with `existing_review_id`
- `backend/app/core/exceptions.py` — DuplicateReviewError handler: 409 with `{ code: "DUPLICATE_REVIEW", existing_review_id: int }`
- `frontend/src/types/api.generated.ts` (lines 1340-1434) — All review TypeScript types confirmed generated
- `backend/app/main.py` — `reviews_router` confirmed registered at line 101
- `backend/alembic/versions/g2h3i4j5k6l7_create_reviews.py` — Migration confirmed applied
- `frontend/src/app/books/[id]/page.tsx` — Current server component structure; `revalidate = 3600` ISR
- `frontend/src/app/books/[id]/_components/RatingDisplay.tsx` — TODO comment at line 41; existing `★` Unicode pattern
- `frontend/src/lib/wishlist.ts` — Canonical hook pattern: useQuery + useMutation + toast + invalidate
- `frontend/src/lib/prebook.ts` — 409 error handling pattern for structured error codes
- `frontend/src/app/cart/_components/CheckoutDialog.tsx` — Confirmed Dialog usage pattern for delete confirmation
- `frontend/package.json` — Installed deps: TanStack Query v5.90, lucide-react 0.575, sonner 2.0, shadcn 3.8
- `frontend/src/components/ui/` — 11 installed components confirmed; `textarea` NOT installed

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` Blockers section: "Star rating selector not in shadcn/ui — evaluate community extensions vs. small custom component before phase starts" → Research conclusion: custom component wins (30 lines, matches existing aesthetic, zero dependency)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed; no new dependencies needed except `npx shadcn add textarea`
- Architecture: HIGH — patterns verified from 4+ existing hooks and component files in the codebase
- Pitfalls: HIGH — most derived from reading actual code; session userId question is the one genuine unknown
- Backend readiness: HIGH — all endpoints, schemas, migration, and router registration confirmed in source

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable stack — 30-day window)
