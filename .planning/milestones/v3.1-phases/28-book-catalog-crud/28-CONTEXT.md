# Phase 28: Book Catalog CRUD - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin can manage the entire book catalog from a paginated, searchable table — adding, editing, deleting books and updating stock quantities — with changes reflected immediately in the customer storefront. Backend CRUD endpoints already exist (POST/PUT/DELETE /books, PATCH /books/{id}/stock, GET /books with pagination/search/filter). This phase builds the admin frontend.

</domain>

<decisions>
## Implementation Decisions

### Catalog Table Design
- Standard row density — consistent with the inventory page table pattern
- Essential 6 columns: Title, Author, Price, Genre, Stock, Actions
- Row actions via three-dot (⋮) dropdown menu with Edit, Delete, Update Stock options
- 20 items per page (matches backend default `size=20`)
- Debounced text search and genre filter per success criteria
- This will be the first DataTable component — sets the pattern for future admin tables

### Add/Edit Book Form
- Side drawer using existing `sheet.tsx` component
- Single `BookForm` component serving both Add and Edit modes (title changes contextually)
- Edit mode pre-populates all fields from the selected book
- Inline validation errors displayed under each field (red text)
- 8 fields: title (required), author (required), price (required), isbn, genre_id, description, cover_image_url, publish_date

### Delete Flow
- Standard AlertDialog (using existing `dialog.tsx` / shadcn AlertDialog)
- Shows book title only: "Are you sure you want to delete 'Book Title'?"
- Warning text: "This action cannot be undone"
- Red-styled Delete button
- Success toast on completion: "Book deleted successfully" (matches inventory page toast pattern)

### Stock Update
- Reuse inventory page's stock update modal as a shared component (extract from inventory page)
- Special toast when restocking from zero: "Stock updated — pre-booking notifications sent to N users"
- Cross-cache invalidation: mutations invalidate both admin catalog queries AND customer-facing book queries for immediate consistency

### Claude's Discretion
- Form field grouping/layout within the side drawer
- Post-delete table behavior (refetch vs optimistic removal)
- "Add Book" button placement (page header vs above table)
- Loading skeleton design for table
- Empty state design when no books match search/filter
- Exact spacing and typography choices

</decisions>

<specifics>
## Specific Ideas

- Inventory page (`/admin/inventory`) has an established pattern for stock update modals, StockBadge component, debounced inputs, and toast notifications — reuse these patterns for consistency
- Dropdown menu (⋮) for row actions keeps the table clean with multiple actions per row
- Side drawer for forms keeps table context partially visible while editing

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sheet.tsx`: Side drawer component — use for BookForm
- `dialog.tsx`: AlertDialog — use for delete confirmation
- `badge.tsx`: StockBadge pattern from inventory page — reuse for stock column
- `sonner.tsx` + `toast`: Toast notifications — consistent success/error feedback
- `select.tsx`, `input.tsx`, `label.tsx`, `textarea.tsx`: Form primitives
- `skeleton.tsx`: Loading skeletons for table rows
- `admin.ts`: `adminKeys` query key factory, `updateBookStock` function
- `catalog.ts`: `fetchBooks`, `fetchBook`, `fetchGenres` — customer-facing fetch layer

### Established Patterns
- `useQuery` + `useMutation` from TanStack Query — used throughout admin pages
- `useDebounce` from `use-debounce` — used in inventory page for threshold input
- `useSession` from `next-auth/react` — all admin pages use `session.accessToken`
- Query key factory pattern via `adminKeys` — extend with `catalog` namespace
- Mutation pattern: `onSuccess` invalidates queries + shows toast, `onError` shows error toast

### Integration Points
- `frontend/src/app/admin/catalog/page.tsx`: Currently a placeholder — replace with full CRUD page
- Backend endpoints: POST/PUT/DELETE `/books`, PATCH `/books/{id}/stock`, GET `/books`, GET `/genres`
- `admin.ts`: Extend with catalog fetch functions (createBook, updateBook, deleteBook) and `adminKeys.catalog` namespace
- Customer cache: Invalidate customer book queries on admin mutations for storefront consistency
- Inventory page: Extract stock update modal into shared component for reuse

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 28-book-catalog-crud*
*Context gathered: 2026-03-01*
