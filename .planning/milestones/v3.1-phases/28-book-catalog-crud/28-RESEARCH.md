# Phase 28: Book Catalog CRUD - Research

**Researched:** 2026-03-01
**Domain:** Admin CRUD interface — paginated table, side drawer form, confirmation dialogs, cross-cache invalidation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Catalog Table Design**
- Standard row density — consistent with the inventory page table pattern
- Essential 6 columns: Title, Author, Price, Genre, Stock, Actions
- Row actions via three-dot (⋮) dropdown menu with Edit, Delete, Update Stock options
- 20 items per page (matches backend default `size=20`)
- Debounced text search and genre filter per success criteria
- This will be the first DataTable component — sets the pattern for future admin tables

**Add/Edit Book Form**
- Side drawer using existing `sheet.tsx` component
- Single `BookForm` component serving both Add and Edit modes (title changes contextually)
- Edit mode pre-populates all fields from the selected book
- Inline validation errors displayed under each field (red text)
- 8 fields: title (required), author (required), price (required), isbn, genre_id, description, cover_image_url, publish_date

**Delete Flow**
- Standard AlertDialog (using existing `dialog.tsx` / shadcn AlertDialog)
- Shows book title only: "Are you sure you want to delete 'Book Title'?"
- Warning text: "This action cannot be undone"
- Red-styled Delete button
- Success toast on completion: "Book deleted successfully" (matches inventory page toast pattern)

**Stock Update**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CATL-01 | Admin can view a paginated catalog table showing title, author, price, genre, stock, and actions | `fetchBooks` from `catalog.ts` with page/size params; `BookListResponse` type from generated API types; HTML table pattern from inventory page |
| CATL-02 | Admin can search books with debounced text input and filter by genre | `useDebounce` from `use-debounce` (already installed); genre filter with shadcn `Select`; `fetchGenres` from `catalog.ts` for genre list |
| CATL-03 | Admin can add a new book via a form with full field validation (title, author, price, ISBN, genre, description, cover URL, publish date) | `react-hook-form` + `@hookform/resolvers` + `zod` (zod already installed, react-hook-form needs install); `BookCreate` schema from generated types; shadcn `Sheet` for side drawer |
| CATL-04 | Admin can edit an existing book via a pre-populated form | Same `BookForm` component; `BookUpdate` schema; `PUT /books/{id}` via admin fetch function; pre-populate from selected book row state |
| CATL-05 | Admin can delete a book with a confirmation dialog | Existing `Dialog` component from `dialog.tsx`; `DELETE /books/{id}` (returns 204 No Content); `apiFetch` handles 204 correctly |
| CATL-06 | Admin can update a book's stock quantity via a modal, with a toast notification when restocking from zero triggers pre-booking emails | Extract stock update modal from inventory page into shared component; `updateBookStock` already in `admin.ts`; pre-booking count must be tracked client-side (backend returns `BookResponse`, NOT notification count) |
</phase_requirements>

## Summary

Phase 28 is a pure frontend phase building the admin book catalog CRUD interface. All backend endpoints are already implemented and tested: `POST/PUT/DELETE /books`, `PATCH /books/{id}/stock`, `GET /books` (with pagination/search/filter), and `GET /genres`. The admin fetch layer (`admin.ts`) needs extension with catalog fetch functions (`fetchAdminBooks`, `createBook`, `updateBook`, `deleteBook`) and an `adminKeys.catalog` query key namespace. The customer-facing `fetchBooks` and `fetchGenres` from `catalog.ts` can also be reused for the admin table.

Two new libraries need installation: `react-hook-form` and `@hookform/resolvers`. The `zod` library (v4.3.6) is already present in `node_modules`. One new shadcn component needs scaffolding: `dropdown-menu.tsx` (the underlying `radix-ui` package already includes `DropdownMenu` at `radix-ui.DropdownMenu`). The plan's mention of `@tanstack/react-table` (TanStack Table) is a locked decision for `DataTable.tsx`, so it also needs installation.

A critical nuance: the PATCH `/books/{id}/stock` endpoint returns `BookResponse` (the updated book), NOT the count of pre-booking notifications sent. The frontend must track whether the stock was previously zero before the mutation fires, then use `len(notified_user_ids)` — but since the backend does not return that count, the toast must reference a hardcoded N (or omit the count) unless we track pre-mutation stock. The cleanest approach: read `current_stock` from the selected book before mutation and if `current_stock === 0`, show the special toast with no count ("pre-booking notifications sent").

**Primary recommendation:** Build Plan 01 (DataTable + AdminPagination + catalog query layer) first to establish the foundational pattern that Plan 02's form, dialog, and stock modal rely on. Install `@tanstack/react-table`, `react-hook-form`, `@hookform/resolvers`, and add `dropdown-menu` via shadcn before writing any components.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tanstack/react-query` | ^5.90.21 (installed) | Async state, caching, invalidation | Already project standard for all admin pages |
| `react-hook-form` | ^7.x (needs install) | Form state, validation, submission | De-facto standard for React forms; integrates with zod via resolvers |
| `@hookform/resolvers` | ^3.x (needs install) | Bridges react-hook-form with zod schema validation | Required adapter for zod integration |
| `zod` | 4.3.6 (installed) | Schema definition and runtime validation | Already in node_modules; react-hook-form's `zodResolver` handles schema inference |
| `@tanstack/react-table` | ^8.x (needs install) | Headless table logic for DataTable.tsx | Project plan explicitly calls for it; provides sorting, pagination, filtering hooks without UI coupling |
| `use-debounce` | ^10.1.0 (installed) | Debounce search input to reduce API calls | Already used in inventory page |
| `sonner` | ^2.0.7 (installed) | Toast notifications | Already project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `radix-ui` (DropdownMenu) | ^1.4.3 (installed) | Accessible dropdown for row actions (⋮ menu) | Already installed; just needs shadcn wrapper scaffolded |
| `lucide-react` | ^0.575.0 (installed) | Icons (MoreHorizontal, Edit, Trash2, etc.) | All admin pages use it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@tanstack/react-table` | Plain HTML table (inventory page pattern) | TanStack Table adds complexity but is the phase's stated goal for DataTable.tsx — establishes reusable pattern for Phase 29 |
| `react-hook-form` | Controlled state (`useState`) | Hook-form gives better performance (uncontrolled), built-in dirty tracking, and field-level error messages with less code |
| `zod` (already installed) | `yup` | Zod is already in project; no reason to introduce yup |

**Installation:**
```bash
cd frontend
npm install react-hook-form @hookform/resolvers @tanstack/react-table
npx shadcn@latest add dropdown-menu
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── lib/
│   └── admin.ts                    # Extend: adminKeys.catalog, fetchAdminBooks, createBook, updateBook, deleteBook
├── components/
│   └── ui/
│       └── dropdown-menu.tsx       # New: scaffold via shadcn (radix-ui DropdownMenu wrapper)
├── components/admin/
│   ├── DataTable.tsx               # New: TanStack Table headless + shadcn HTML table rendering
│   ├── AdminPagination.tsx         # New: prev/next pagination with page/total display
│   ├── BookForm.tsx                # New: react-hook-form + zod, dual Add/Edit mode, Sheet side drawer
│   ├── ConfirmDialog.tsx           # New: reusable AlertDialog wrapper for delete confirmation
│   └── StockUpdateModal.tsx        # New: extract from inventory/page.tsx, add pre-booking toast logic
└── app/admin/catalog/
    └── page.tsx                    # Replace placeholder with full catalog page
```

### Pattern 1: Admin Query Key Factory Extension
**What:** Extend `adminKeys` in `admin.ts` with a `catalog` namespace following the existing hierarchical pattern.
**When to use:** All catalog queries and invalidations reference these keys.
**Example:**
```typescript
// Source: admin.ts pattern (existing)
export const adminKeys = {
  all: ['admin'] as const,
  sales: { /* existing */ },
  inventory: { /* existing */ },
  catalog: {
    all: ['admin', 'catalog'] as const,
    list: (params: CatalogQueryParams) => ['admin', 'catalog', 'list', params] as const,
    genres: ['admin', 'catalog', 'genres'] as const,
  },
} as const
```

### Pattern 2: Admin Fetch Functions in admin.ts
**What:** Add `fetchAdminBooks`, `createBook`, `updateBook`, `deleteBook` — all require `accessToken`.
**When to use:** Admin catalog page mutations and queries.
**Example:**
```typescript
// Source: existing admin.ts pattern
export async function fetchAdminBooks(
  accessToken: string,
  params: { q?: string; genre_id?: number; page?: number; size?: number }
): Promise<BookListResponse> {
  // Reuses catalog.ts fetchBooks logic but with auth header for consistency
  // OR: call the same /books endpoint without auth (it's public) using catalog.ts directly
  return fetchBooks({ ...params }) // catalog.ts already works without auth
}

export async function createBook(
  accessToken: string,
  data: BookCreate
): Promise<BookResponse> {
  return apiFetch<BookResponse>('/books', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function updateBook(
  accessToken: string,
  bookId: number,
  data: BookUpdate
): Promise<BookResponse> {
  return apiFetch<BookResponse>(`/books/${bookId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function deleteBook(
  accessToken: string,
  bookId: number
): Promise<void> {
  return apiFetch<void>(`/books/${bookId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

**Note on fetchAdminBooks:** `GET /books` is a public endpoint. The admin table can simply call the existing `fetchBooks` from `catalog.ts` directly — no auth header needed. No need to duplicate. However, the admin query key should use `adminKeys.catalog.list(params)` rather than a generic key.

### Pattern 3: Debounced Search with useState + useDebounce
**What:** Two separate state values — raw input state and debounced value. Only debounced value drives queryKey.
**When to use:** Search inputs where every keystroke should not fire an API call.
**Example:**
```typescript
// Source: inventory/page.tsx pattern (established in Phase 27)
const [searchInput, setSearchInput] = useState('')
const [debouncedSearch] = useDebounce(searchInput, 500)

// Query uses debounced value:
const catalogQuery = useQuery({
  queryKey: adminKeys.catalog.list({ q: debouncedSearch, genre_id: selectedGenre, page }),
  queryFn: () => fetchBooks({ q: debouncedSearch || undefined, genre_id: selectedGenre, page, size: 20 }),
  enabled: !!accessToken,
  staleTime: 30_000,
})
```

### Pattern 4: TanStack Table (DataTable.tsx) with shadcn HTML Table
**What:** Use `useReactTable` hook for headless table logic; render with project's HTML table + Tailwind pattern (NOT separate shadcn `table` component — per STATE.md: "No shadcn table component installed — used HTML table with Tailwind classes").
**When to use:** Any admin table needing column definitions, pagination state, and future sorting.
**Example:**
```typescript
// Source: TanStack Table v8 API
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table'

// DataTable.tsx generic component:
interface DataTableProps<TData> {
  columns: ColumnDef<TData>[]
  data: TData[]
  isLoading?: boolean
  emptyMessage?: string
}

export function DataTable<TData>({ columns, data, isLoading, emptyMessage }: DataTableProps<TData>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true, // Pagination handled server-side
  })
  // Render HTML table with Tailwind classes matching inventory page style
}
```

**Key TanStack Table v8 facts (HIGH confidence — verified):**
- Column definitions use `ColumnDef<TData>` type
- `accessorKey` for simple property access; `cell` for custom rendering
- `getCoreRowModel()` is always required
- `manualPagination: true` when server handles pagination (our case)
- `flexRender` renders header/cell content (handles both strings and JSX)

### Pattern 5: react-hook-form + zod for BookForm
**What:** Define zod schema for book fields, use `zodResolver` to wire into `useForm`, render controlled inputs with `register`, display errors via `formState.errors`.
**When to use:** BookForm in side drawer for Add and Edit modes.
**Example:**
```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const bookSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  author: z.string().min(1, 'Author is required'),
  price: z.string().min(1, 'Price is required').regex(/^\d+(\.\d{1,2})?$/, 'Invalid price format'),
  isbn: z.string().optional().nullable(),
  genre_id: z.number().optional().nullable(),
  description: z.string().optional().nullable(),
  cover_image_url: z.string().url('Invalid URL').optional().nullable().or(z.literal('')),
  publish_date: z.string().optional().nullable(), // ISO date string or null
})

type BookFormValues = z.infer<typeof bookSchema>

// In component:
const form = useForm<BookFormValues>({
  resolver: zodResolver(bookSchema),
  defaultValues: book ? {
    title: book.title,
    author: book.author,
    price: book.price, // BookResponse.price is string
    // ...
  } : { title: '', author: '', price: '' },
})
```

**Price field consideration:** `BookCreate.price` accepts `number | string`; `BookResponse.price` is always `string`. Use string in the form and let the backend parse it.

### Pattern 6: Mutation with onSuccess Invalidation + Toast
**What:** Standard mutation pattern from all admin pages — invalidate on success, toast on success/error.
**When to use:** createBook, updateBook, deleteBook, updateBookStock mutations.
**Example:**
```typescript
// Source: inventory/page.tsx established pattern
const createMutation = useMutation({
  mutationFn: (data: BookFormValues) => createBook(accessToken, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
    // Cross-cache: invalidate customer-facing book queries if they exist in TanStack cache
    queryClient.invalidateQueries({ queryKey: ['books'] })
    toast.success('Book added successfully')
    setDrawerOpen(false)
  },
  onError: (error) => {
    toast.error(error instanceof ApiError ? error.detail ?? 'Failed to save book' : 'Failed to save book')
  },
})
```

### Pattern 7: Stock Update Pre-Booking Toast Logic
**What:** Since `PATCH /books/{id}/stock` returns `BookResponse` (NOT notification count), track previous stock before mutation fires and derive whether pre-booking emails were triggered.
**When to use:** Stock update mutation `onSuccess` handler.
**Example:**
```typescript
// Track current stock before opening modal
const [selectedBook, setSelectedBook] = useState<{ book_id: number; title: string; current_stock: number } | null>(null)

const stockMutation = useMutation({
  mutationFn: ({ bookId, quantity }: { bookId: number; quantity: number }) =>
    updateBookStock(accessToken, bookId, quantity),
  onSuccess: (_, { quantity }) => {
    const wasZero = selectedBook?.current_stock === 0
    const isRestocking = wasZero && quantity > 0
    queryClient.invalidateQueries({ queryKey: adminKeys.catalog.all })
    queryClient.invalidateQueries({ queryKey: adminKeys.inventory.all })
    queryClient.invalidateQueries({ queryKey: ['books'] }) // customer-facing
    if (isRestocking) {
      toast.success('Stock updated — pre-booking notifications sent')
    } else {
      toast.success('Stock updated successfully')
    }
    setSelectedBook(null)
  },
  onError: () => toast.error('Failed to update stock'),
})
```

**Note:** The backend does not return notified user count in the API response. The CONTEXT.md mentions "N users" in the toast — however without the count from the API, the toast should say "pre-booking notifications sent" without a specific number, OR the frontend must call `GET /pre-bookings?book_id=X&status=pending` before the mutation to count them. The simpler and correct approach: omit the count from the toast ("Stock updated — pre-booking notifications sent").

### Pattern 8: DropdownMenu for Row Actions
**What:** Three-dot (⋮) button per row opens a dropdown with Edit, Delete, Update Stock options. Uses shadcn `dropdown-menu.tsx` wrapper.
**When to use:** Actions column in catalog table.
**Example:**
```typescript
// After scaffolding: npx shadcn@latest add dropdown-menu
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MoreHorizontal } from 'lucide-react'

// In column def:
{
  id: 'actions',
  cell: ({ row }) => {
    const book = row.original
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => onEdit(book)}>Edit</DropdownMenuItem>
          <DropdownMenuItem onClick={() => onUpdateStock(book)}>Update Stock</DropdownMenuItem>
          <DropdownMenuItem className="text-destructive" onClick={() => onDelete(book)}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  },
}
```

### Pattern 9: AdminPagination Component
**What:** Simple prev/next pagination component using `page` state and `total` from API response.
**When to use:** Below the catalog table.
**Example:**
```typescript
// BookListResponse shape: { items, total, page, size }
// totalPages = Math.ceil(total / size)

interface AdminPaginationProps {
  page: number
  total: number
  size: number
  onPageChange: (page: number) => void
}

export function AdminPagination({ page, total, size, onPageChange }: AdminPaginationProps) {
  const totalPages = Math.ceil(total / size)
  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <span>Showing {Math.min((page - 1) * size + 1, total)}–{Math.min(page * size, total)} of {total}</span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</Button>
        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</Button>
      </div>
    </div>
  )
}
```

### Anti-Patterns to Avoid
- **Mixing admin/catalog query keys with customer query keys:** Keep `adminKeys.catalog.*` for admin queries; use `['books']` only for cross-cache invalidation targeting customer components. Do NOT use the same key structure for both.
- **Fetching the full book list without pagination on admin side:** Always pass `page` and `size=20` to `fetchBooks`. The backend caps at `size=100` but 20 is the target UX.
- **Using `queryClient.resetQueries` instead of `invalidateQueries`:** Reset clears cache entirely; invalidate marks stale and refetches. Use invalidate so currently-displayed data updates in place.
- **Putting the DropdownMenu trigger button inside a `<form>` element:** Can cause unexpected form submission. The row actions column is outside the BookForm.
- **Forgetting `'use client'` directive:** The catalog page requires client-side state (search input, selected book, drawer state). It must be `'use client'` just like inventory/page.tsx.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom validation logic with `useState` per field | `react-hook-form` + `zod` | Handles uncontrolled inputs, dirty state, submission prevention, field-level errors — all the edge cases |
| Table row rendering with column definitions | Manual array map with custom column logic | `@tanstack/react-table` `useReactTable` + `flexRender` | Phase plan explicitly requires DataTable.tsx as reusable pattern for Phase 29 |
| Accessible dropdown menu | Custom `div` with click handlers + z-index | `dropdown-menu.tsx` (radix-ui wrapper) | Focus management, keyboard navigation, portal rendering, ARIA attributes |
| Toast notifications | Custom toast component | `sonner` (`toast.success`, `toast.error`) | Already project standard; consistent UX |
| Debounced input | `setTimeout`/`clearTimeout` pattern | `useDebounce` from `use-debounce` | Already installed; single-line API |
| Pagination math | Ad-hoc calculation | `AdminPagination` component using `BookListResponse.total` and `size` | Consistent with backend's 1-indexed page system |

**Key insight:** The project already uses the correct standard tools. The main risk is hand-rolling dropdown/form behavior instead of using the established patterns.

## Common Pitfalls

### Pitfall 1: Pre-Booking Notification Count Not in API Response
**What goes wrong:** Developer implements the toast as `"Stock updated — pre-booking notifications sent to ${count} users"` expecting count from API.
**Why it happens:** The CONTEXT.md mentions "N users" in the toast, but `PATCH /books/{id}/stock` returns `BookResponse` (not the count). The `notified_user_ids` list is internal to the router.
**How to avoid:** Track `current_stock` of the selected book before mutation. If `current_stock === 0` and new `quantity > 0`, show the special restock toast WITHOUT a count: `"Stock updated — pre-booking notifications sent"`. This is accurate and honest.
**Warning signs:** Any attempt to read notification count from mutation result data.

### Pitfall 2: Cross-Cache Invalidation for Customer Storefront
**What goes wrong:** Developer invalidates `adminKeys.catalog.all` but the customer catalog page (`/catalog`) still shows stale data.
**Why it happens:** The customer catalog page (`/app/(store)/catalog/page.tsx`) is a Server Component using direct `fetchBooks` calls — NOT TanStack Query. `queryClient.invalidateQueries` only affects the in-memory TanStack cache, which Server Components don't use.
**How to avoid:** The customer catalog page is Server Component-rendered and will show updated data on the next navigation/page load naturally. For the admin's own view, invalidating `adminKeys.catalog.*` is sufficient. Invalidating `['books']` only helps if there are customer-side Client Components using that key (currently only `ReviewsSection` uses TanStack Query in the book detail page, not the catalog). Include the `['books']` invalidation as a forward-compatibility measure but don't rely on it for the customer storefront.
**Warning signs:** Expecting real-time customer storefront updates from admin mutations in this phase.

### Pitfall 3: zod v4 API Differences
**What goes wrong:** Developer uses zod v3 examples (`.optional().nullable()`) but zod v4.3.6 has some API changes.
**Why it happens:** Most online examples target zod v3; the project has zod v4.
**How to avoid:** In zod v4, `.nullable().optional()` still works for `string | null | undefined`. `z.string().url()` still validates URLs. `z.coerce.number()` for numeric fields from string inputs. Key change in v4: `z.object().merge()` replaced by spread; `z.ZodError` format unchanged. The basic API used in this phase remains the same.
**Warning signs:** Import errors or unexpected type inference.

### Pitfall 4: Sheet (Side Drawer) vs Dialog Width
**What goes wrong:** The Sheet component defaults to `sm:max-w-sm` (~384px). With 8 form fields, this can feel cramped.
**Why it happens:** Default SheetContent sizing. Side is always `right`.
**How to avoid:** Override width on SheetContent: `className="sm:max-w-md"` or `sm:max-w-lg` depending on field layout. This is within Claude's Discretion per CONTEXT.md.

### Pitfall 5: TanStack Table manualPagination
**What goes wrong:** DataTable renders 20 items correctly but "Previous/Next" doesn't work because pagination state is managed by TanStack Table internally instead of parent component.
**Why it happens:** Forgetting `manualPagination: true` and `pageCount` when server handles pagination.
**How to avoid:** Set `manualPagination: true` in `useReactTable` config. Page state lives in the parent catalog page component (`useState<number>`), not inside DataTable. Pass `page` and `onPageChange` down via `AdminPagination`.

### Pitfall 6: react-hook-form `reset()` for Edit Mode Pre-Population
**What goes wrong:** Opening Edit drawer doesn't populate the form with the selected book's values.
**Why it happens:** `defaultValues` in `useForm` only applies on initial mount. When the same component instance re-renders for a different book, defaults don't re-apply.
**How to avoid:** Use `form.reset(bookToValues(selectedBook))` in a `useEffect` that runs when `selectedBook` changes (or when drawer opens with a book). Alternatively, use `key={selectedBook?.id}` on the BookForm to force remount.

### Pitfall 7: Delete returning 204 No Content
**What goes wrong:** `apiFetch` throws because it tries to parse empty body as JSON.
**Why it happens:** `DELETE /books/{id}` returns `HTTP 204 No Content` with no body.
**How to avoid:** `apiFetch` already handles this: `if (res.status === 204) return undefined as T`. Use `deleteBook` returning `Promise<void>` — confirmed safe with current `apiFetch` implementation.

## Code Examples

Verified patterns from existing codebase:

### Existing useDebounce Pattern (inventory/page.tsx)
```typescript
// Source: frontend/src/app/admin/inventory/page.tsx
const [thresholdInput, setThresholdInput] = useState<number>(10)
const [debouncedThreshold] = useDebounce(thresholdInput, 500)
// Query uses debouncedThreshold, not thresholdInput
```

### Existing Mutation + Toast + Invalidate Pattern (inventory/page.tsx)
```typescript
// Source: frontend/src/app/admin/inventory/page.tsx
const stockMutation = useMutation({
  mutationFn: ({ bookId, quantity }: { bookId: number; quantity: number }) =>
    updateBookStock(accessToken, bookId, quantity),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.inventory.all })
    toast.success('Stock updated successfully')
    setSelectedBook(null)
  },
  onError: () => {
    toast.error('Failed to update stock')
  },
})
```

### Existing adminKeys Structure (admin.ts)
```typescript
// Source: frontend/src/lib/admin.ts
export const adminKeys = {
  all: ['admin'] as const,
  sales: {
    all: ['admin', 'sales'] as const,
    summary: (period: string) => ['admin', 'sales', 'summary', period] as const,
    topBooks: (limit: number, sort_by: 'revenue' | 'volume' = 'revenue') =>
      ['admin', 'sales', 'top-books', limit, sort_by] as const,
  },
  inventory: {
    all: ['admin', 'inventory'] as const,
    lowStock: (threshold: number) => ['admin', 'inventory', 'low-stock', threshold] as const,
  },
} as const
```

### BookResponse and BookCreate Types (api.generated.ts)
```typescript
// Source: frontend/src/types/api.generated.ts
BookCreate: {
  title: string;          // required
  author: string;         // required
  price: number | string; // required
  isbn?: string | null;
  genre_id?: number | null;
  description?: string | null;
  cover_image_url?: string | null;
  publish_date?: string | null;  // ISO date string
}

BookResponse: {
  id: number;
  title: string;
  author: string;
  price: string;           // always string in response
  isbn: string | null;
  genre_id: number | null;
  description: string | null;
  cover_image_url: string | null;
  publish_date: string | null;
  stock_quantity: number;
}

BookListResponse: {
  items: BookResponse[];
  total: number;
  page: number;
  size: number;
}

GenreResponse: {
  id: number;
  name: string;
}
```

### Existing Select + Genre Filter Pattern (catalog page)
```typescript
// Source: frontend/src/app/(store)/catalog/_components/SearchControls.tsx
<Select value={currentGenreId} onValueChange={handleGenreChange}>
  <SelectTrigger>
    <SelectValue placeholder="All Genres" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All Genres</SelectItem>
    {genres.map((genre) => (
      <SelectItem key={genre.id} value={String(genre.id)}>
        {genre.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

### Dialog Pattern for Delete Confirmation
```typescript
// Source: frontend/src/components/ui/dialog.tsx — existing component
// Use Dialog (not AlertDialog — project uses Dialog from dialog.tsx, not a separate AlertDialog)
<Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete Book</DialogTitle>
      <DialogDescription>
        Are you sure you want to delete '{bookToDelete?.title}'? This action cannot be undone.
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
      <Button
        variant="destructive"
        onClick={() => deleteMutation.mutate(bookToDelete!.id)}
        disabled={deleteMutation.isPending}
      >
        {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Note:** The project does NOT have a separate `alert-dialog.tsx` component. The CONTEXT.md says "Standard AlertDialog (using existing `dialog.tsx` / shadcn AlertDialog)" — use the existing `Dialog` from `dialog.tsx` with a destructive `Button`. No need to install a separate AlertDialog component.

### Sheet Side Drawer Pattern
```typescript
// Source: frontend/src/components/ui/sheet.tsx — existing component
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '@/components/ui/sheet'

<Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
  <SheetContent side="right" className="sm:max-w-md overflow-y-auto">
    <SheetHeader>
      <SheetTitle>{selectedBook ? 'Edit Book' : 'Add Book'}</SheetTitle>
      <SheetDescription>
        {selectedBook ? 'Update book details' : 'Add a new book to the catalog'}
      </SheetDescription>
    </SheetHeader>
    <BookForm
      book={selectedBook}
      onSuccess={() => setDrawerOpen(false)}
    />
  </SheetContent>
</Sheet>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| shadcn `table` component | HTML table + Tailwind classes | Phase 26 decision | Per STATE.md: "No shadcn table component installed — used HTML table with Tailwind classes (sufficient for read-only display)" — DataTable.tsx wraps this pattern |
| Separate AlertDialog component | Reuse existing `dialog.tsx` Dialog | Phase 26 decision | No separate alert-dialog.tsx installed; Dialog + destructive Button achieves same result |
| `TableHeader`, `TableRow` etc. shadcn components | Raw `<table>`, `<thead>`, `<tr>`, `<th>`, `<td>` | Phase 26 decision | Consistent with all existing admin tables |

**Note:** The CONTEXT.md mentions "using existing `dialog.tsx` / shadcn AlertDialog" — these are the same thing for this project. The `dialog.tsx` IS the alert dialog; just compose it with a red "Delete" button.

## Open Questions

1. **DataTable.tsx generics vs catalog-specific component**
   - What we know: Phase plan says "DataTable.tsx (TanStack Table + shadcn Table)" as a reusable component
   - What's unclear: How generic should DataTable.tsx be? Generic `<TData>` component reused in Phase 29, or catalog-specific?
   - Recommendation: Make it generic (`DataTable<TData>`) from the start — Phase 29 will reuse it directly. Column definitions live in the catalog page (or a separate `catalog-columns.tsx`).

2. **Genre display in table (name vs ID)**
   - What we know: `BookResponse` has `genre_id: number | null`, not `genre_name`. Genres list comes from `GET /genres`.
   - What's unclear: Should the catalog page fetch genres separately to display genre names in the table?
   - Recommendation: Yes — fetch genres once with `useQuery({ queryKey: adminKeys.catalog.genres })` and build a `genreMap: Map<number, string>` for O(1) lookup in the table cell renderer. This is a necessary fetch for the genre filter dropdown anyway.

3. **Post-delete table behavior (refetch vs optimistic)**
   - What we know: CONTEXT.md marks this as Claude's Discretion
   - What's unclear: Should deletion optimistically remove the row or refetch?
   - Recommendation: Use `queryClient.invalidateQueries` (refetch) after delete — simpler, correct, and consistent with all existing admin mutations. Optimistic removal adds complexity for minimal perceived gain on an admin page.

4. **Price field in BookForm — string or number input?**
   - What we know: `BookCreate.price` is `number | string`; `BookResponse.price` is `string`. `<input type="number">` coerces to JS number.
   - What's unclear: Should the form use `type="number"` input or `type="text"` with string validation?
   - Recommendation: Use `type="text"` with zod regex validation (`/^\d+(\.\d{1,2})?$/`) — avoids floating point display issues and matches the string nature of the API response. Pre-populate with `book.price` directly.

## Sources

### Primary (HIGH confidence)
- Existing codebase — `frontend/src/app/admin/inventory/page.tsx` — established mutation, debounce, toast, dialog patterns
- Existing codebase — `frontend/src/lib/admin.ts` — `adminKeys` factory pattern, `updateBookStock`, `apiFetch` usage
- Existing codebase — `frontend/src/types/api.generated.ts` — `BookCreate`, `BookUpdate`, `BookResponse`, `BookListResponse`, `GenreResponse` exact field names and types
- Existing codebase — `backend/app/books/router.py` + `service.py` — confirmed endpoint behavior, 204 on DELETE, `BookResponse` (not notification count) returned from PATCH /stock
- Existing codebase — `frontend/src/components/ui/sheet.tsx`, `dialog.tsx`, `select.tsx`, `sonner.tsx` — confirmed available components and their APIs
- Existing codebase — `frontend/package.json` + `node_modules/` — confirmed installed packages: `@tanstack/react-query` 5.90.21, `zod` 4.3.6, `use-debounce` 10.1.0; confirmed NOT installed: `react-hook-form`, `@hookform/resolvers`, `@tanstack/react-table`
- Existing codebase — `frontend/node_modules/radix-ui/` — confirmed `DropdownMenu` available via `radix-ui` package (no separate install needed, just shadcn wrapper)

### Secondary (MEDIUM confidence)
- `frontend/src/app/(store)/catalog/page.tsx` — Server Component pattern confirmed (no TanStack Query); cross-cache invalidation for customer catalog is a no-op for this phase's actual storefront rendering
- `frontend/src/.planning/STATE.md` — "No shadcn table component installed" and "DataTable.tsx built in Phase 28 is reused directly in Phase 29" decisions confirmed

### Tertiary (LOW confidence)
- zod v4 API compatibility — inferred from version 4.3.6 in node_modules; basic `.string()`, `.number()`, `.optional()`, `.nullable()` API is confirmed stable but v4-specific edge cases not fully verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via node_modules inspection; exact versions confirmed
- Architecture patterns: HIGH — all patterns derived directly from existing codebase (inventory page, admin.ts, component files)
- Pitfalls: HIGH — pre-booking count gap verified by reading router.py and service.py; 204 handling verified in apiFetch; cross-cache behavior verified by reading catalog/page.tsx Server Component
- API types: HIGH — all types read directly from api.generated.ts

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable stack, no fast-moving dependencies)
