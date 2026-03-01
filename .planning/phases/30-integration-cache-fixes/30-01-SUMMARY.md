---
phase: 30-integration-cache-fixes
plan: 01
subsystem: api
tags: [nextjs, cache, revalidation, admin, security, tanstack-query]

# Dependency graph
requires:
  - phase: 29-user-management-and-review-moderation
    provides: admin mutations (catalog CRUD, stock update, review delete) that needed revalidation wiring
  - phase: 28-book-catalog-crud
    provides: catalog/page.tsx and StockUpdateModal.tsx mutation patterns
provides:
  - POST /api/revalidate Route Handler with admin auth guard (403 for non-admin)
  - triggerRevalidation() fire-and-forget helper in src/lib/revalidate.ts
  - All 6 admin mutations wired to trigger Next.js fetch cache revalidation on success
  - Verified middleware defense-in-depth: Layer 1 (middleware.ts) + Layer 2 (admin/layout.tsx)
affects: [storefront catalog page, book detail pages, ISR, admin mutations]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Admin mutations call triggerRevalidation() fire-and-forget from onSuccess — never await to unblock admin UX"
    - "Route Handler POST /api/revalidate checks admin role via auth() before calling revalidatePath"
    - "RevalidationPath union type: string for simple paths, {path, type} for dynamic route pattern revalidation"
    - "revalidatePath('/books/[id]', 'page') revalidates ALL matching dynamic route pages — use for bulk ops where specific IDs unknown"
    - "ISR revalidate=3600 on book detail page remains as belt-and-suspenders fallback if on-demand revalidation fails"

key-files:
  created:
    - frontend/src/app/api/revalidate/route.ts
    - frontend/src/lib/revalidate.ts
  modified:
    - frontend/src/app/admin/catalog/page.tsx
    - frontend/src/components/admin/StockUpdateModal.tsx
    - frontend/src/app/admin/reviews/page.tsx

key-decisions:
  - "Path-based revalidation (revalidatePath) chosen over tag-based (revalidateTag) — no need to retrofit next: {tags} across existing fetch calls"
  - "Separate revalidate.ts helper file (not inline) — single import point for all admin mutation pages, DRY"
  - "triggerRevalidation is fire-and-forget (no await) — admin UX not blocked by revalidation latency"
  - "Revalidation Route Handler requires admin auth via auth() — prevents unauthorized cache busting"
  - "createMutation revalidates /catalog only (no book detail page exists yet for new book)"
  - "updateMutation revalidates /catalog + /books/${id} (specific page via editingBook.id)"
  - "deleteMutation revalidates /catalog only (detail page 404s naturally after ISR miss)"
  - "stockMutation revalidates /books/${book_id} — stock/availability shown on detail page"
  - "singleDeleteMutation revalidates /books/${deleteTarget.book.book_id} — affects avg_rating and review_count on detail"
  - "bulkDeleteMutation uses {path: '/books/[id]', type: 'page'} — revalidates ALL book detail pages since selectedIds are review IDs not book IDs"
  - "middleware.ts verified as Layer 1 (no changes) — uses auth() wrapper, adminPrefixes=['/admin'], redirects non-admin to /"
  - "admin/layout.tsx verified as Layer 2 (no changes) — independent auth() + role check, defense-in-depth against CVE-2025-29927"

patterns-established:
  - "Admin mutation revalidation: import triggerRevalidation from @/lib/revalidate, call fire-and-forget in onSuccess after queryClient.invalidateQueries"
  - "Dynamic route bulk revalidation: {path: '/route/[param]', type: 'page'} pattern revalidates all matched pages"

requirements-completed: [ADMF-02, ADMF-03, CATL-03, CATL-04, CATL-05, CATL-06]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 30 Plan 01: Integration and Cache Fixes Summary

**Admin mutation cache propagation fixed via POST /api/revalidate Route Handler with admin guard, fire-and-forget triggerRevalidation helper, and middleware defense-in-depth verified (Layer 1 middleware.ts + Layer 2 admin/layout.tsx)**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-01T11:17:52Z
- **Completed:** 2026-03-01T11:21:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Created admin-guarded `POST /api/revalidate` Route Handler that calls `revalidatePath` for each entry in the request body — supports string paths and `{path, type}` objects for dynamic route pattern revalidation
- Created `triggerRevalidation()` fire-and-forget helper in `src/lib/revalidate.ts` as single import point for all admin mutation pages
- Wired all 6 admin mutations (3 catalog CRUD, 1 stock update, 2 review delete) to call `triggerRevalidation` in their `onSuccess` callbacks — customer-facing RSC storefront now reflects admin changes without full page reload
- Verified middleware defense-in-depth: `middleware.ts` (Layer 1) and `admin/layout.tsx` (Layer 2) both perform independent admin role checks, satisfying CVE-2025-29927 requirements ADMF-02 and ADMF-03

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify middleware defense-in-depth and create revalidation Route Handler** - `561f8c2` (feat)
2. **Task 2: Wire triggerRevalidation into all admin mutation onSuccess callbacks** - `4003457` (feat)

## Files Created/Modified
- `frontend/src/app/api/revalidate/route.ts` - Admin-guarded POST Route Handler; calls revalidatePath for each typed path entry; returns 403 for non-admin
- `frontend/src/lib/revalidate.ts` - RevalidationPath union type + triggerRevalidation() fire-and-forget fetch helper with dev-mode error logging
- `frontend/src/app/admin/catalog/page.tsx` - Added triggerRevalidation import; wired create/update/delete mutations
- `frontend/src/components/admin/StockUpdateModal.tsx` - Added triggerRevalidation import; wired stockMutation onSuccess
- `frontend/src/app/admin/reviews/page.tsx` - Added triggerRevalidation import; wired singleDelete and bulkDelete mutations

## Decisions Made
- Path-based revalidation (revalidatePath) vs tag-based: chose path-based to avoid retrofitting `next: { tags }` across all existing fetch calls in catalog.ts/reviews.ts
- Separate `revalidate.ts` helper file as single DRY import point rather than inlining fetch calls
- Bulk review delete uses `{path: '/books/[id]', type: 'page'}` — since selectedIds are review IDs (not book IDs), we can't enumerate specific book IDs; the `'page'` type revalidates all pages matching the dynamic segment
- create mutation only revalidates `/catalog` (not a specific book detail) — no book detail page exists yet for a newly created book
- delete mutation only revalidates `/catalog` — deleted book's detail page will 404 naturally after ISR miss

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Cache propagation gap closed: admin mutations now trigger on-demand Next.js fetch cache revalidation
- v3.1 audit items ADMF-02, ADMF-03, CATL-03, CATL-04, CATL-05, CATL-06 satisfied
- storefront catalog and book detail pages will reflect admin changes within seconds of mutation success
- ISR revalidate=3600 on book detail page remains as safety net

---
*Phase: 30-integration-cache-fixes*
*Completed: 2026-03-01*
