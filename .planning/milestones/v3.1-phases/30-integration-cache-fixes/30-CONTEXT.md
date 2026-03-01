# Phase 30: Integration and Cache Fixes - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Close two specific gaps from the v3.1 milestone audit: (1) verify middleware-layer admin protection satisfies defense-in-depth, and (2) fix admin mutation cache invalidation so changes propagate to the customer RSC storefront without requiring a full page reload or manual cache bust.

</domain>

<decisions>
## Implementation Decisions

### Cache invalidation trigger
- Add a Next.js Route Handler (e.g. `POST /api/revalidate`) that calls `revalidatePath`
- Admin mutations call it fire-and-forget from `onSuccess` callbacks — do NOT await the response or block the admin UX
- Route handler must verify admin role via `auth()` before revalidating (prevent unauthorized cache busting)
- Minimal change to existing architecture — admin mutations stay as client-side `useMutation` calls, no conversion to Server Actions

### Revalidation approach
- Use path-based revalidation (`revalidatePath`), not tag-based (`revalidateTag`)
- No need to retrofit `{ next: { tags: [...] } }` across existing fetch calls in `catalog.ts`/`reviews.ts`

### Revalidation scope
- Revalidate `/catalog` (server component listing page) and `/books/[id]` (ISR detail page) only
- Homepage is a client component with no book data — does not need revalidation
- Keep existing `revalidate = 3600` ISR on book detail page as safety net alongside on-demand revalidation (belt and suspenders)

### Mutation coverage
- Claude to analyze which mutations actually affect storefront-visible data and wire revalidation accordingly
- At minimum: catalog CRUD (add/edit/delete book) and stock updates affect what customers see
- Review deletion affects book detail page (avg_rating, review_count displayed via RSC)
- User management (deactivate/reactivate) does not affect storefront book pages

### Middleware verification
- `middleware.ts` already exists with full admin route protection using `auth()` — checks role and redirects non-admins before Server Components run
- No separate `proxy.ts` file exists — the defense-in-depth intent is already satisfied by the current middleware
- Verify the existing middleware meets the success criteria rather than creating a redundant proxy.ts
- Keep BOTH middleware (Layer 1) and admin `layout.tsx` role check (Layer 2) — true defense-in-depth against CVE-2025-29927 middleware bypass

### Claude's Discretion
- Exact revalidation granularity per mutation type (revalidate both /catalog + /books/[id] for all mutations, or smart per-mutation paths)
- Whether to pass specific book IDs to revalidate individual `/books/[id]` pages or revalidate a broader path
- Error handling if the revalidation API call fails (silent failure acceptable given ISR safety net)
- Whether middleware needs any adjustments or just a verification pass

</decisions>

<specifics>
## Specific Ideas

- Fire-and-forget pattern for revalidation calls — admin sees instant success toast, storefront updates within seconds in background
- The revalidation API route should be admin-only (auth check) to prevent unauthorized cache busting
- Existing 1-hour ISR on book detail is the fallback if on-demand revalidation fails for any reason

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `auth()` from `@/auth`: Used in both middleware.ts and admin layout.tsx for role checks — reuse in the revalidation route handler
- `adminKeys` query key factory in `lib/admin.ts`: Hierarchical prefix enables scoped TanStack Query cache invalidation (already wired in mutations)
- `apiFetch` in `lib/api.ts`: Standard fetch wrapper, but revalidation route is internal Next.js — may use plain fetch

### Established Patterns
- Admin mutations use TanStack Query `useMutation` with `onSuccess` callbacks that invalidate query caches — revalidation call fits naturally into these callbacks
- Storefront catalog page (`(store)/catalog/page.tsx`) is a Server Component with direct `await fetchBooks()` — no TanStack Query, relies on Next.js fetch cache
- Book detail page (`(store)/books/[id]/page.tsx`) uses `React.cache` for request dedup and `export const revalidate = 3600` for ISR
- No `revalidatePath` or `revalidateTag` calls exist anywhere in the codebase today

### Integration Points
- `frontend/src/app/admin/catalog/page.tsx`: createMutation, updateMutation, deleteMutation onSuccess callbacks — add revalidation call here
- `frontend/src/components/admin/StockUpdateModal.tsx`: stock update mutation onSuccess — add revalidation call here
- `frontend/src/app/admin/reviews/page.tsx`: review delete mutations onSuccess — add revalidation call if review deletion affects storefront
- `frontend/src/middleware.ts`: Existing middleware to verify meets defense-in-depth criteria
- `frontend/src/app/admin/layout.tsx`: Layer 2 defense-in-depth check (keep as-is)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-integration-cache-fixes*
*Context gathered: 2026-03-01*
