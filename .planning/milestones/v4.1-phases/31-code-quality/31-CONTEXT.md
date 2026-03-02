# Phase 31: Code Quality - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate duplicated admin component implementations, fix TypeScript return types, and make the top-sellers analytics table respect the user's period selection. No new features — purely consolidation and correctness fixes in the admin frontend.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User deferred all decisions to Claude. The following approach will be used:

**DeltaBadge extraction:**
- Extract to `frontend/src/components/admin/DeltaBadge.tsx` as a named export
- Keep identical rendering logic (green ▲ / red ▼ / muted — 0%)
- Remove inline definitions from both `overview/page.tsx` and `sales/page.tsx`

**StockBadge consolidation:**
- Extract to `frontend/src/components/admin/StockBadge.tsx` as a named export
- Accept `threshold` as required parameter (inventory page passes it dynamically, catalog page passes 10)
- No default threshold — make it explicit at call sites for clarity
- Remove inline definitions from both `catalog/page.tsx` and `inventory/page.tsx`

**Period-filtered top sellers (ANLY-01):**
- Pass `period` parameter to `fetchTopBooks()` and include in `adminKeys.sales.topBooks()` query key
- React Query will automatically refetch when period changes
- Standard loading skeleton during refetch — no special animation

**TypeScript fix (TYPE-01):**
- Change `updateBookStock` return type from `Promise<void>` to `Promise<BookResponse>`
- Update `apiFetch<void>` to `apiFetch<BookResponse>` in the implementation
- Ensure `BookResponse` type exists in api.generated.ts or types

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/admin/` — 8 existing shared admin components (AppSidebar, BookForm, ConfirmDialog, DataTable, RevenueChart, StockUpdateModal, etc.)
- `frontend/src/components/ui/badge.tsx` — shadcn Badge used by both StockBadge implementations
- `frontend/src/types/api.generated.ts` — Generated API types including BookResponse

### Established Patterns
- Admin components are flat in `components/admin/` (no sub-folders)
- Inline helper components defined at top of page files (DeltaBadge, StockBadge)
- React Query with `adminKeys` factory for cache key management
- `apiFetch<T>` generic for typed API calls

### Integration Points
- `overview/page.tsx` lines 33-49: DeltaBadge inline definition to remove
- `sales/page.tsx` lines 46-62: DeltaBadge inline definition to remove
- `catalog/page.tsx` lines 49-65: StockBadge inline definition to remove (hardcoded threshold=10)
- `inventory/page.tsx` lines 17-33: StockBadge inline definition to remove (accepts threshold param)
- `sales/page.tsx` line 87: topBooksQuery missing `period` in queryKey and queryFn
- `lib/admin.ts` line 110: `fetchTopBooks` missing `period` parameter
- `lib/admin.ts` line 144: `updateBookStock` returns `Promise<void>` instead of `Promise<BookResponse>`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-code-quality*
*Context gathered: 2026-03-02*
