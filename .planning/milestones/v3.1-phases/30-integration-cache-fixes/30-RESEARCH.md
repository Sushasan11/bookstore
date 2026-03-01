# Phase 30: Integration and Cache Fixes - Research

**Researched:** 2026-03-01
**Domain:** Next.js middleware verification + Next.js on-demand cache revalidation via Route Handler
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Cache invalidation trigger:** Add a Next.js Route Handler (`POST /api/revalidate`) that calls `revalidatePath`. Admin mutations call it fire-and-forget from `onSuccess` callbacks — do NOT await the response or block the admin UX.
- **Route handler auth:** Must verify admin role via `auth()` before revalidating — prevents unauthorized cache busting.
- **Minimal architecture change:** Admin mutations stay as client-side `useMutation` calls. No conversion to Server Actions.
- **Revalidation approach:** Path-based (`revalidatePath`), NOT tag-based (`revalidateTag`). No retrofitting `{ next: { tags: [...] } }` on existing fetch calls.
- **Revalidation scope:** Revalidate `/catalog` and `/books/[id]` only. Homepage is a client component with no book data — does NOT need revalidation.
- **ISR safety net:** Keep existing `export const revalidate = 3600` on book detail page alongside on-demand revalidation (belt and suspenders).
- **Mutation coverage:** Catalog CRUD (add/edit/delete book) and stock updates affect storefront. Review deletion affects book detail page (avg_rating, review_count). User management does NOT affect storefront book pages.
- **Middleware verification:** `middleware.ts` already exists with full admin route protection using `auth()`. No separate `proxy.ts` file exists. The defense-in-depth intent is already satisfied. Verify existing middleware meets success criteria rather than creating a redundant proxy.ts. Keep BOTH middleware (Layer 1) and admin `layout.tsx` role check (Layer 2).

### Claude's Discretion

- Exact revalidation granularity per mutation type (revalidate both `/catalog` + `/books/[id]` for all mutations, or smart per-mutation paths)
- Whether to pass specific book IDs to revalidate individual `/books/[id]` pages or revalidate a broader path
- Error handling if the revalidation API call fails (silent failure acceptable given ISR safety net)
- Whether middleware needs any adjustments or just a verification pass

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMF-02 | Admin route is protected by role check in both proxy.ts and admin layout Server Component (defense-in-depth against CVE-2025-29927) | middleware.ts already implements Layer 1 with `auth()` role check; admin/layout.tsx implements Layer 2 — both active, verified in code |
| ADMF-03 | Non-admin users are redirected away from `/admin` routes | middleware.ts redirects unauthenticated users and non-admin roles to `/` before Server Components run |
| CATL-03 | Admin can add a new book via form — change propagates to customer storefront | `createMutation.onSuccess` → fire-and-forget `POST /api/revalidate` → `revalidatePath('/catalog')` and `revalidatePath('/books/[id]', 'page')` |
| CATL-04 | Admin can edit an existing book — change propagates to customer storefront | `updateMutation.onSuccess` → same revalidation pattern; book detail page benefits from specific bookId revalidation |
| CATL-05 | Admin can delete a book — change propagates to customer storefront | `deleteMutation.onSuccess` → `revalidatePath('/catalog')` at minimum; deleted book detail becomes 404 on next visit |
| CATL-06 | Admin can update stock — change propagates to customer storefront | `StockUpdateModal.stockMutation.onSuccess` → revalidate `/books/[bookId]` specifically (stock availability visible on detail page) |
</phase_requirements>

---

## Summary

Phase 30 closes two integration gaps found by the v3.1 milestone audit: (1) verify that the existing `middleware.ts` satisfies the Layer 1 defense-in-depth requirement (ADMF-02, ADMF-03), and (2) fix the cache propagation break where admin mutations invalidate TanStack Query's client cache but have no effect on the Next.js fetch cache used by the RSC storefront.

The middleware verification is lightweight: `frontend/src/middleware.ts` already exists, uses the NextAuth `auth()` wrapper, checks `req.auth?.user?.role !== 'admin'` for `/admin` routes, and redirects non-admins to `/` before any Server Component executes. There is no separate `proxy.ts` that needs wiring — the audit's description of the gap was based on a prior planned architecture that was superseded. The actual implementation already satisfies ADMF-02 and ADMF-03. This sub-task is a verification + documentation pass, not a code change.

The cache propagation fix is the substantive work. The storefront catalog page (`(store)/catalog/page.tsx`) is a pure async Server Component — it calls `fetchBooks()` directly via `apiFetch`, which uses the native `fetch()` that Next.js caches. The book detail page (`(store)/books/[id]/page.tsx`) uses `React.cache` for request dedup and `export const revalidate = 3600` for ISR. Both pages are untouched by `queryClient.invalidateQueries()` calls in the admin client components — TanStack Query's cache is entirely separate from the Next.js fetch cache. The fix requires a new internal Route Handler at `POST /api/revalidate` that calls `revalidatePath()` server-side, which purges the Next.js data cache and causes those RSC pages to re-fetch on the next request.

**Primary recommendation:** Create `POST /api/revalidate` with admin auth guard, call it fire-and-forget from `onSuccess` callbacks in the catalog mutations and StockUpdateModal. The middleware verification task is code-review only — the implementation is already correct.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `next` (built-in) | 16.1.6 | `revalidatePath`, `revalidateTag` server functions | Only Next.js can purge Next.js fetch cache — no alternative |
| `next-auth` v5 | ^5.0.0-beta.30 | `auth()` in Route Handler for admin gate | Same auth pattern used throughout codebase |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `next/server` (built-in) | 16.1.6 | `NextResponse.json()` in Route Handler | Standard response pattern for API routes |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Path-based `revalidatePath` | Tag-based `revalidateTag` | Tags require retrofitting all `fetch()` calls with `{ next: { tags: [...] } }` — decided against in CONTEXT.md |
| Route Handler fire-and-forget | Server Actions | Server Actions require converting mutations from `useMutation` — decided against in CONTEXT.md |

**Installation:** No new packages required. `revalidatePath` is a Next.js built-in.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── app/
│   ├── api/
│   │   ├── auth/[...nextauth]/   # existing
│   │   └── revalidate/           # NEW: POST /api/revalidate
│   │       └── route.ts
│   ├── admin/
│   │   └── catalog/page.tsx      # add revalidation calls to onSuccess
│   └── components/admin/
│       └── StockUpdateModal.tsx  # add revalidation call to onSuccess
└── middleware.ts                 # existing — verify only
```

### Pattern 1: On-Demand Revalidation Route Handler

**What:** A `POST /api/revalidate` Route Handler that accepts a JSON body with paths to revalidate, verifies admin role via `auth()`, then calls `revalidatePath()` for each path.

**When to use:** Any time a server-side Next.js data cache purge is needed from a client component mutation.

```typescript
// frontend/src/app/api/revalidate/route.ts
// Source: Next.js docs — revalidatePath API reference (nextjs.org/docs/app/api-reference/functions/revalidatePath)
import { revalidatePath } from 'next/cache'
import { auth } from '@/auth'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const session = await auth()

  // Admin guard — prevent unauthorized cache busting
  if (!session?.user || session.user.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const body = await request.json()
  const paths: string[] = body.paths ?? []

  for (const path of paths) {
    revalidatePath(path)
  }

  return NextResponse.json({ revalidated: true, paths })
}
```

### Pattern 2: Fire-and-Forget Call in onSuccess

**What:** Call `fetch('/api/revalidate', ...)` in the mutation `onSuccess` callback without `await` — admin sees the success toast immediately, storefront updates in the background.

**When to use:** All admin mutations that affect storefront-visible data.

```typescript
// In catalog/page.tsx — createMutation.onSuccess, updateMutation.onSuccess, deleteMutation.onSuccess
// In StockUpdateModal.tsx — stockMutation.onSuccess
// In reviews/page.tsx — singleDeleteMutation.onSuccess, bulkDeleteMutation.onSuccess

function triggerRevalidation(paths: string[]) {
  // Fire-and-forget: do NOT await — admin UX must not block on this
  fetch('/api/revalidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  }).catch(() => {
    // Silent failure: ISR safety net (revalidate = 3600) handles recovery
  })
}

// Usage in onSuccess:
onSuccess: (data) => {
  queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
  queryClient.invalidateQueries({ queryKey: ['books'] })
  triggerRevalidation(['/catalog', '/books/' + bookId])
  toast.success('Book updated successfully')
}
```

### Pattern 3: Middleware Verification (no code change expected)

**What:** The existing `middleware.ts` uses the NextAuth v5 `auth()` wrapper pattern, which runs in the Edge runtime. The `matcher` config skips static assets. It checks `req.auth?.user?.role !== 'admin'` for `/admin` routes and redirects to `/`.

**Verification checklist:**
- `export const middleware = auth((req) => { ... })` — confirms Edge-compatible auth wrapper
- `matcher` includes `/admin` routes — confirmed by `"/((?!api|_next/static|_next/image|favicon.ico).*)"` which matches all paths including `/admin`
- Unauthenticated admin request: redirects to `/` (not login — prevents revealing route existence)
- Non-admin authenticated request: redirects to `/`
- This is exactly what ADMF-02 and ADMF-03 require

### Anti-Patterns to Avoid

- **Awaiting revalidation in onSuccess:** Blocks admin toast until revalidation completes over the network — defeats UX goal.
- **No admin auth check on the Route Handler:** Any browser can call `POST /api/revalidate` and bust the cache for every page — a DoS vector.
- **Using `revalidatePath('/')` (root path type):** Revalidates everything — too broad. Use specific paths.
- **Converting mutations to Server Actions:** Changes client mutation architecture across multiple pages — decided against in CONTEXT.md.
- **Using `revalidateTag` without retrofitting fetch calls:** `revalidateTag('books')` only works if the fetch calls that built the cache used `{ next: { tags: ['books'] } }`. The current `apiFetch` in `catalog.ts` does not pass tags — tags would silently no-op.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Purging Next.js data cache | Custom cache map, in-memory TTL | `revalidatePath()` from `next/cache` | Next.js owns its internal fetch cache — only `revalidatePath`/`revalidateTag` can purge it correctly across all segments |
| Admin auth in Route Handler | Manual JWT parsing, cookie reads | `auth()` from `@/auth` | Same session strategy (JWT httpOnly cookie) used everywhere — `auth()` is the established pattern |

**Key insight:** The Next.js data cache and TanStack Query's cache are completely separate systems. Invalidating one has zero effect on the other.

---

## Common Pitfalls

### Pitfall 1: `revalidatePath` path must match the route, not the filesystem

**What goes wrong:** Calling `revalidatePath('/books/[id]')` with the bracket syntax does NOT revalidate individual book pages. It revalidates the layout segment definition, not all instances.

**Why it happens:** `revalidatePath` interprets strings literally unless you pass the `type` parameter.

**How to avoid:** To revalidate a specific book page, call `revalidatePath('/books/42')` with the actual ID. To revalidate ALL book detail pages, call `revalidatePath('/books/[id]', 'page')` — the `'page'` type parameter instructs Next.js to revalidate all pages matching that segment pattern.

**Warning signs:** Storefront book detail page still shows stale data after admin edit, even after calling `revalidatePath`.

**Reference:** Next.js 15 revalidatePath API — `type` parameter controls segment vs all-instances behavior.

```typescript
// Revalidate specific book page (preferred for edit/delete/stock):
revalidatePath(`/books/${bookId}`)

// Revalidate ALL book detail pages (blunter, sufficient for adds):
revalidatePath('/books/[id]', 'page')

// Revalidate catalog listing:
revalidatePath('/catalog')
```

### Pitfall 2: Route Handler `auth()` returns null in development if cookies differ

**What goes wrong:** `auth()` returns `null` in the Route Handler even when the admin is logged in, causing 403 responses for all revalidation calls.

**Why it happens:** In Next.js development, if the Route Handler runs on a different port or the cookie domain mismatch. Also, `auth()` in a Route Handler requires the full `Request` context — not an issue with the standard App Router pattern but worth verifying.

**How to avoid:** Test the Route Handler with the actual admin session. The `auth()` call in Route Handlers (App Router) works identically to Server Components — no special handling needed. Confirm the session cookie is being forwarded.

**Warning signs:** Revalidation calls return 403 even when logged in as admin.

### Pitfall 3: Fire-and-forget swallows actual errors in development

**What goes wrong:** The `.catch(() => {})` that silences errors also hides Route Handler bugs during development.

**Why it happens:** Intentional for production, but makes debugging hard.

**How to avoid:** In the `triggerRevalidation` helper, log errors in development:

```typescript
function triggerRevalidation(paths: string[]) {
  fetch('/api/revalidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  }).catch((err) => {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[revalidate] failed:', err)
    }
  })
}
```

### Pitfall 4: Storefront catalog page has no explicit cache directive — may be dynamic

**What goes wrong:** The `(store)/catalog/page.tsx` uses `searchParams` (a dynamic function), which causes Next.js to opt the page into **dynamic rendering** (no caching at all). `revalidatePath('/catalog')` would be a no-op because there is nothing cached to purge.

**Why it happens:** Next.js 14/15 makes pages dynamic when they access `searchParams`, `cookies()`, or `headers()`. Dynamic pages are rendered on each request — they cannot be cached or revalidated by `revalidatePath`.

**How to verify:** Check if `(store)/catalog/page.tsx` is actually cached. Since it accesses `searchParams: Promise<{...}>`, it IS dynamic. This means the catalog page always fetches fresh data — `revalidatePath('/catalog')` may be unnecessary for the catalog listing page.

**Impact:** The cache propagation gap may only affect the book detail page (which uses ISR). The catalog listing is already "live." Plan should confirm this understanding and decide whether to revalidate catalog at all.

**Warning signs:** None — this is actually a good outcome. The catalog is already fresh on every request.

### Pitfall 5: `revalidatePath` in Route Handlers requires Next.js 14+

**What goes wrong:** `revalidatePath` called from a Route Handler throws or does nothing.

**Why it happens:** `revalidatePath` originally only worked in Server Actions. As of Next.js 14, it also works in Route Handlers.

**How to avoid:** This project uses Next.js 16.1.6 — no issue. Confidence: HIGH.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Complete Route Handler

```typescript
// frontend/src/app/api/revalidate/route.ts
// Pattern: admin-guarded on-demand revalidation
import { revalidatePath } from 'next/cache'
import { auth } from '@/auth'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const session = await auth()

  if (!session?.user || session.user.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
  }

  const body = await request.json().catch(() => ({}))
  const paths: string[] = Array.isArray(body.paths) ? body.paths : []

  for (const path of paths) {
    revalidatePath(path)
  }

  return NextResponse.json({ revalidated: true, paths })
}
```

### Reusable Helper (no new file — inline or small util)

```typescript
// Can live in the component or be extracted to src/lib/revalidate.ts
// Decision per Claude's Discretion: recommend inline in each mutation file for visibility

function triggerRevalidation(paths: string[]) {
  fetch('/api/revalidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  }).catch((err) => {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[revalidate] failed:', err)
    }
  })
}
```

### Mutation Coverage Matrix

| Mutation | Location | Paths to Revalidate | Rationale |
|----------|----------|---------------------|-----------|
| Create book | `catalog/page.tsx` `createMutation.onSuccess` | `['/catalog']` | New book appears in listing; book detail doesn't exist yet |
| Update book | `catalog/page.tsx` `updateMutation.onSuccess` | `['/catalog', '/books/${bookId}']` | Listing may show title/author; detail page shows full data |
| Delete book | `catalog/page.tsx` `deleteMutation.onSuccess` | `['/catalog']` | Listing must remove book; deleted detail page serves 404 naturally on ISR miss |
| Stock update | `StockUpdateModal.tsx` `stockMutation.onSuccess` | `['/books/${bookId}']` | Stock/availability shown on detail page; catalog shows badge but is dynamic (always fresh) |
| Single review delete | `reviews/page.tsx` `singleDeleteMutation.onSuccess` | `['/books/${reviewBookId}']` | Detail page shows `avg_rating` and `review_count` from RSC fetch — needs purge |
| Bulk review delete | `reviews/page.tsx` `bulkDeleteMutation.onSuccess` | `['/books/[id]', 'page']` | Multiple books affected; revalidate all book detail pages |

**Note on catalog page:** `(store)/catalog/page.tsx` accesses `searchParams` (dynamic function), which opts it into dynamic rendering. It is NOT cached by Next.js — it fetches fresh data on every request. `revalidatePath('/catalog')` is harmless but effectively a no-op for this page. Including it is fine for future-proofing if the catalog page ever gains ISR.

**Note on review mutations and book ID availability:** The review delete mutations in `reviews/page.tsx` have access to `deleteTarget` (single) and `selectedIds` (bulk). The `deleteTarget` object has `deleteTarget.book.title` but not `book_id` directly — need to verify the `AdminReviewEntry` type has `book.id` or similar. Bulk delete doesn't know which books were affected by IDs — fallback to `revalidatePath('/books/[id]', 'page')` for bulk.

### Existing Middleware (verified, no changes needed)

```typescript
// frontend/src/middleware.ts — current implementation satisfies ADMF-02, ADMF-03
export const middleware = auth((req) => {
  // ...
  const isAdminRoute = adminPrefixes.some((p) => pathname.startsWith(p))
  if (isAdminRoute && !isLoggedIn) {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))  // Layer 1
  }
  if (isAdminRoute && req.auth?.user?.role !== "admin") {
    return NextResponse.redirect(new URL("/", req.nextUrl.origin))  // Layer 1
  }
  // ...
})

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
  // Matches /admin/* routes — Layer 1 edge redirect is active
}
```

```typescript
// frontend/src/app/admin/layout.tsx — current implementation is Layer 2
const session = await auth()
if (!session?.user || session.user.role !== 'admin') {
  redirect('/')  // Layer 2 — independent Server Component check (CVE-2025-29927 defense)
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `router.refresh()` (client) | `revalidatePath()` (server, Route Handler) | Next.js 13+ App Router | `router.refresh()` only triggers a re-render of the current client view — does NOT purge the Next.js fetch cache for other users/routes |
| `revalidatePath` in Server Actions only | `revalidatePath` in Route Handlers | Next.js 14 | Route Handlers can now trigger cache purges, enabling the fire-and-forget pattern from client mutations |
| Middleware via `_middleware.ts` | `middleware.ts` in `src/` | Next.js 13 | File-based middleware; `config.matcher` controls which routes it intercepts |

**Deprecated/outdated:**
- `pages/_middleware.ts`: Replaced by `src/middleware.ts` in Next.js 13 App Router — not relevant here.
- `res.revalidate()` (Pages Router): Only for Pages Router ISR — not applicable in App Router.

---

## Open Questions

1. **Does `AdminReviewEntry` expose `book.id`?**
   - What we know: `deleteTarget` in reviews page has type `AdminReviewEntry`. The column renders `row.original.book.title` — so `book` is an object.
   - What's unclear: Whether `book.id` (the numeric book ID) is present on the type, which is needed to call `revalidatePath('/books/${bookId}')` for single review delete.
   - Recommendation: Check `types/api.generated.ts` or the `AdminReviewEntry` schema. If `book.id` is present, use specific path revalidation. If not, fall back to `revalidatePath('/books/[id]', 'page')`.

2. **Is the catalog listing page actually cached?**
   - What we know: `(store)/catalog/page.tsx` accesses `searchParams` — a dynamic function that opts the page out of Next.js data caching.
   - What's unclear: Whether Next.js 16 has changed this behavior (unlikely — dynamic function = dynamic page is a fundamental App Router invariant).
   - Recommendation: Include `revalidatePath('/catalog')` in create/update/delete mutations anyway (harmless, future-proof). Do not over-engineer.

3. **Bulk delete review: which book pages to revalidate?**
   - What we know: `selectedIds` contains review IDs, not book IDs. The bulk delete mutation doesn't know which books are affected.
   - What's unclear: Whether fetching book IDs for selected reviews before deletion is worth the complexity.
   - Recommendation: Use `revalidatePath('/books/[id]', 'page')` for bulk delete — revalidates all book detail pages. This is a coarser but simpler and correct approach given the low frequency of bulk deletions.

---

## Sources

### Primary (HIGH confidence)

- Next.js 16 docs — `revalidatePath` API reference: https://nextjs.org/docs/app/api-reference/functions/revalidatePath
- Next.js 16 docs — Route Handlers: https://nextjs.org/docs/app/building-your-application/routing/route-handlers
- Next.js 16 docs — Caching and Revalidating: https://nextjs.org/docs/app/building-your-application/caching
- Codebase — `frontend/src/middleware.ts` (verified: full admin protection with auth() wrapper active)
- Codebase — `frontend/src/app/admin/layout.tsx` (verified: Layer 2 defense-in-depth active)
- Codebase — `frontend/src/app/admin/catalog/page.tsx` (verified: mutation onSuccess callbacks are the injection points)
- Codebase — `frontend/src/components/admin/StockUpdateModal.tsx` (verified: self-contained mutation with onSuccess)
- Codebase — `frontend/src/app/admin/reviews/page.tsx` (verified: single + bulk delete mutations)
- Codebase — `frontend/src/app/(store)/catalog/page.tsx` (verified: dynamic page via searchParams — not ISR-cached)
- Codebase — `frontend/src/app/(store)/books/[id]/page.tsx` (verified: ISR with `export const revalidate = 3600` + React.cache)

### Secondary (MEDIUM confidence)

- v3.1 audit finding: `['books']` TanStack Query invalidation is no-op on customer RSC storefront — verified by code analysis (separate cache systems)
- CVE-2025-29927 Next.js middleware bypass — documented as motivation for Layer 2 Server Component check

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `revalidatePath` is a stable Next.js built-in; no external packages required; verified against codebase versions
- Architecture: HIGH — Route Handler pattern is well-established; fire-and-forget pattern is low-risk with ISR fallback; all injection points identified from codebase
- Pitfalls: HIGH — dynamic page behavior (catalog uses searchParams) is a concrete finding from code inspection; `revalidatePath` type parameter behavior is documented; auth() pattern is established in codebase

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (Next.js cache APIs are stable; no fast-moving ecosystem concerns)
