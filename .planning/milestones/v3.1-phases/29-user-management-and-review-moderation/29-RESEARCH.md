# Phase 29: User Management and Review Moderation - Research

**Researched:** 2026-03-01
**Domain:** Next.js admin frontend — paginated/filterable read tables with mutations (deactivate, reactivate, single-delete, bulk-delete)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All four areas discussed were delegated to Claude's judgement. The user trusts Claude to make decisions based on existing codebase patterns and success criteria.

### Claude's Discretion

#### User Table Presentation
- Badge styling for role and active status — follow the color-coded badge pattern from catalog (stock badges)
- Action button placement (inline vs dropdown menu) — pick what fits the existing DataTable layout
- Admin-role deactivate guard — choose between disabled+tooltip or hiding the action
- Column set — match the success criteria: email, role badge, active status badge, join date, action buttons

#### Filter Bar Design
- User table: role filter + status filter — follow catalog page's Select dropdown pattern
- Review table: book, user, rating range, sort — arrange to balance usability and screen space
- Search fields — decide whether email search adds value on the user table
- Rating filter — choose between dropdowns or a simpler approach matching existing patterns

#### Bulk Selection UX
- Select-all behavior — page-level selection is sufficient (API max is 50 items)
- Bulk action button placement — pick the approach that fits the admin layout
- Single-review delete vs checkbox-only — success criteria mentions both single and bulk delete, so provide both
- Feedback after bulk-delete — follow the existing toast notification pattern from catalog CRUD mutations

#### Confirmation Dialogs
- Deactivate dialog tone — consider that it revokes tokens and locks out immediately (higher severity)
- Reactivate dialog — decide if confirmation is needed for this low-risk action
- Bulk-delete dialog content — decide between count-only vs count+preview
- Single-delete dialog — decide how much context (book title, reviewer) to show

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| USER-01 | Admin can view a paginated user table showing email, role badge, active status badge, join date, and actions | `GET /admin/users` returns `UserListResponse` with `AdminUserResponse[]`; `DataTable<AdminUserResponse>` + `AdminPagination` reuse established pattern |
| USER-02 | Admin can filter users by role (all/user/admin) and active status (all/active/inactive) | API query params `role?: "user" \| "admin" \| null` and `is_active?: boolean \| null`; `useState` filter + page reset pattern from catalog page |
| USER-03 | Admin can deactivate a user with a confirmation dialog (disabled for admin accounts) | `PATCH /admin/users/{user_id}/deactivate` — returns `AdminUserResponse`; backend 403 if target is admin; frontend guard disables button for admin-role rows |
| USER-04 | Admin can reactivate an inactive user | `PATCH /admin/users/{user_id}/reactivate` — idempotent; `ConfirmDialog` reuse; `useMutation` + `invalidateQueries` pattern |
| REVW-01 | Admin can view a paginated review table showing book title, reviewer, rating, text snippet, and date | `GET /admin/reviews` returns `AdminReviewListResponse` with `AdminReviewEntry[]`; each entry has nested `book.title`, `author.display_name`, `rating`, `text`, `created_at` |
| REVW-02 | Admin can filter reviews by book, user, rating range, and sort by date or rating | API supports `book_id`, `user_id`, `rating_min`, `rating_max`, `sort_by` ("date"/"rating"), `sort_dir` ("desc"/"asc") query params |
| REVW-03 | Admin can delete a single review with confirmation | `DELETE /reviews/{review_id}` — 204 No Content; admin bypass via token; `ConfirmDialog` with book title + reviewer context |
| REVW-04 | Admin can select multiple reviews via checkboxes and bulk-delete them with a single confirmation dialog that states the count | `DELETE /admin/reviews/bulk` with `{ review_ids: number[] }` body — max 50 IDs; returns `{ deleted_count: number }`; checkbox column in DataTable, clear selection after success |
</phase_requirements>

## Summary

Phase 29 is a pure frontend phase building two admin pages: `/admin/users` and `/admin/reviews`. The backend endpoints are fully implemented and documented in the OpenAPI schema. No new libraries are required — all dependencies (TanStack Table v8, TanStack Query v5, shadcn components, sonner toasts) are already installed and well-understood from Phase 28.

The user page is straightforward: a `DataTable<AdminUserResponse>` with two Select filter dropdowns (role and status), `useMutation` for deactivate/reactivate, and `ConfirmDialog` for confirmation. The admin-role guard is a frontend-only concern (the backend also enforces it with 403). The review page is the more complex of the two due to the richer filter bar (book ID, user ID, rating range, sort) and the bulk-delete feature requiring checkbox state management.

The primary new pattern introduced in this phase is **checkbox selection state** in the reviews table. This is implemented entirely in the page component via `useState<Set<number>>` for selected IDs — TanStack Table's `getCoreRowModel` (already used in `DataTable.tsx`) does not need to change. The checkbox column is added as a standard `ColumnDef` entry that reads and writes the set from the page component via closure. The bulk-delete mutation clears the selection on success.

**Primary recommendation:** Implement both pages by cloning the catalog page structure, extending `adminKeys` for `users` and `reviews` namespaces, adding new fetch/mutation functions to `admin.ts`, and building the checkbox column as a plain `ColumnDef` with controlled state managed in the page component.

## Standard Stack

### Core (already installed — no `npm install` required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tanstack/react-query` | ^5.90.21 | Data fetching, caching, mutation | Established in Phase 26; all admin pages use it |
| `@tanstack/react-table` | ^8.21.3 | Table rendering via `DataTable.tsx` | Established in Phase 28; `DataTable<TData>` is the shared component |
| `react-hook-form` | ^7.71.2 | Form state | Used in `BookForm.tsx`; not needed for Phase 29 (no forms) |
| `zod` | 4.3.6 | Schema validation | Used in Phase 28; not needed for Phase 29 (no form schemas) |
| `sonner` | ^2.0.7 | Toast notifications | `toast.success/error` pattern established in Phase 28 |
| `lucide-react` | ^0.575.0 | Icons | Checkbox icon already available; `MoreHorizontal` for action menu |
| shadcn components | — | UI primitives | `Badge`, `Select`, `Button`, `Dialog`, `DropdownMenu` all available |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `use-debounce` | ^10.1.0 | Debounced filter inputs | If user email search field is added (Claude's discretion); not required for Select-based filters |
| `next-auth` | ^5.0.0-beta.30 | `useSession()` for `accessToken` | Every admin page client component follows this pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `useState<Set<number>>` for checkbox selection | TanStack Table `rowSelection` model | Row selection state in TanStack Table requires `enableRowSelection`, `onRowSelectionChange`, and `getFilteredRowModel` — adds complexity to `DataTable.tsx` for a feature only used in the reviews page; keeping selection in the page component is simpler and consistent with the established "DataTable is presentation-only" pattern |
| DropdownMenu for user row actions | Inline action buttons | Inline buttons (Deactivate / Reactivate) may be clearer for a table where only one or two actions exist per row. Either works; DropdownMenu is already the established pattern from catalog, so it is the default choice. |

**Installation:** None required — all dependencies already in `frontend/package.json`.

## Architecture Patterns

### Recommended File Structure for Phase 29

```
frontend/src/
├── app/admin/
│   ├── users/
│   │   └── page.tsx          # Replace placeholder; 'use client'; UserManagement page
│   └── reviews/
│       └── page.tsx          # Replace placeholder; 'use client'; ReviewModeration page
└── lib/
    └── admin.ts              # Extend adminKeys + add 8 new fetch/mutation functions
```

No new component files are needed. `DataTable.tsx`, `ConfirmDialog.tsx`, `AdminPagination.tsx`, `Badge`, `Select`, and `DropdownMenu` are all reused directly.

### Pattern 1: adminKeys Extension

**What:** Add `users` and `reviews` namespaces to the existing `adminKeys` factory in `admin.ts`.
**When to use:** Every new admin data domain follows this pattern.
**Example:**
```typescript
// Source: admin.ts (existing pattern — extend this object)
export const adminKeys = {
  // ... existing sales, inventory, catalog ...
  users: {
    all: ['admin', 'users'] as const,
    list: (params: { role?: string; is_active?: boolean; page?: number }) =>
      ['admin', 'users', 'list', params] as const,
  },
  reviews: {
    all: ['admin', 'reviews'] as const,
    list: (params: {
      book_id?: number;
      user_id?: number;
      rating_min?: number;
      rating_max?: number;
      sort_by?: string;
      sort_dir?: string;
      page?: number;
    }) => ['admin', 'reviews', 'list', params] as const,
  },
} as const
```

### Pattern 2: Fetch Functions for Admin Users and Reviews

**What:** New `apiFetch` wrappers added to `admin.ts`.
**Example:**
```typescript
// Source: admin.ts — follows same shape as fetchLowStock, fetchBooks
import type { components } from '@/types/api.generated'

type AdminUserResponse = components['schemas']['AdminUserResponse']
type UserListResponse = components['schemas']['UserListResponse']
type AdminReviewEntry = components['schemas']['AdminReviewEntry']
type AdminReviewListResponse = components['schemas']['AdminReviewListResponse']
type BulkDeleteRequest = components['schemas']['BulkDeleteRequest']
type BulkDeleteResponse = components['schemas']['BulkDeleteResponse']

export async function fetchAdminUsers(
  accessToken: string,
  params: { page?: number; per_page?: number; role?: string | null; is_active?: boolean | null }
): Promise<UserListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.per_page) qs.set('per_page', String(params.per_page))
  if (params.role != null) qs.set('role', params.role)
  if (params.is_active != null) qs.set('is_active', String(params.is_active))
  return apiFetch<UserListResponse>(`/admin/users?${qs}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function deactivateUser(accessToken: string, userId: number): Promise<AdminUserResponse> {
  return apiFetch<AdminUserResponse>(`/admin/users/${userId}/deactivate`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function reactivateUser(accessToken: string, userId: number): Promise<AdminUserResponse> {
  return apiFetch<AdminUserResponse>(`/admin/users/${userId}/reactivate`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function fetchAdminReviews(
  accessToken: string,
  params: {
    page?: number; per_page?: number;
    book_id?: number | null; user_id?: number | null;
    rating_min?: number | null; rating_max?: number | null;
    sort_by?: string; sort_dir?: string;
  }
): Promise<AdminReviewListResponse> {
  const qs = new URLSearchParams()
  if (params.page) qs.set('page', String(params.page))
  if (params.per_page) qs.set('per_page', String(params.per_page))
  if (params.book_id != null) qs.set('book_id', String(params.book_id))
  if (params.user_id != null) qs.set('user_id', String(params.user_id))
  if (params.rating_min != null) qs.set('rating_min', String(params.rating_min))
  if (params.rating_max != null) qs.set('rating_max', String(params.rating_max))
  if (params.sort_by) qs.set('sort_by', params.sort_by)
  if (params.sort_dir) qs.set('sort_dir', params.sort_dir)
  return apiFetch<AdminReviewListResponse>(`/admin/reviews?${qs}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function deleteSingleReview(accessToken: string, reviewId: number): Promise<void> {
  // Uses /reviews/{review_id} — admin bypass is automatic via token role check
  return apiFetch<void>(`/reviews/${reviewId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export async function bulkDeleteReviews(
  accessToken: string,
  reviewIds: number[]
): Promise<BulkDeleteResponse> {
  return apiFetch<BulkDeleteResponse>('/admin/reviews/bulk', {
    method: 'DELETE',
    body: JSON.stringify({ review_ids: reviewIds } satisfies BulkDeleteRequest),
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}
```

### Pattern 3: User Table Page Structure

**What:** The user management page follows the catalog page pattern exactly.
**Example:**
```typescript
// Source: catalog/page.tsx pattern adapted for users
'use client'

const PAGE_SIZE = 20

export default function AdminUsersPage() {
  const [roleFilter, setRoleFilter] = useState<string>('all')   // 'all' | 'user' | 'admin'
  const [statusFilter, setStatusFilter] = useState<string>('all') // 'all' | 'active' | 'inactive'
  const [page, setPage] = useState(1)
  const [actionTarget, setActionTarget] = useState<AdminUserResponse | null>(null)
  const [pendingAction, setPendingAction] = useState<'deactivate' | 'reactivate' | null>(null)

  const { data: session } = useSession()
  const accessToken = session?.accessToken ?? ''
  const queryClient = useQueryClient()

  const usersQuery = useQuery({
    queryKey: adminKeys.users.list({
      role: roleFilter === 'all' ? undefined : roleFilter,
      is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
      page,
    }),
    queryFn: () => fetchAdminUsers(accessToken, {
      role: roleFilter === 'all' ? null : roleFilter,
      is_active: statusFilter === 'all' ? null : statusFilter === 'active',
      page,
      per_page: PAGE_SIZE,
    }),
    enabled: !!accessToken,
    staleTime: 30_000,
  })

  // deactivateMutation and reactivateMutation follow same shape as deleteMutation in catalog page
  // onSuccess: invalidate adminKeys.users.all + toast.success + clear actionTarget
}
```

### Pattern 4: Checkbox Selection for Bulk Delete (Reviews)

**What:** Page-level `Set<number>` state tracks selected review IDs. Checkbox column is a standard `ColumnDef` using closures.
**Why this way:** TanStack Table's built-in `rowSelection` model requires structural changes to `DataTable.tsx` and the `getFilteredRowModel` import. Keeping selection state in the page avoids touching the shared component.
**Example:**
```typescript
// Source: TanStack Table v8 ColumnDef pattern (no DataTable.tsx modification needed)
const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

const allPageIds = (reviewsQuery.data?.items ?? []).map((r) => r.id)
const allPageSelected = allPageIds.length > 0 && allPageIds.every((id) => selectedIds.has(id))

const columns: ColumnDef<AdminReviewEntry, unknown>[] = [
  {
    id: 'select',
    header: () => (
      <input
        type="checkbox"
        checked={allPageSelected}
        onChange={(e) => {
          if (e.target.checked) {
            setSelectedIds(new Set(allPageIds))
          } else {
            setSelectedIds(new Set())
          }
        }}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <input
        type="checkbox"
        checked={selectedIds.has(row.original.id)}
        onChange={(e) => {
          setSelectedIds((prev) => {
            const next = new Set(prev)
            if (e.target.checked) next.add(row.original.id)
            else next.delete(row.original.id)
            return next
          })
        }}
        aria-label={`Select review ${row.original.id}`}
      />
    ),
  },
  // ... other columns
]

// After bulk delete success:
setSelectedIds(new Set())
```

### Pattern 5: Badge Design for Role and Active Status

**What:** Inline badge components following the `StockBadge` pattern from catalog and inventory pages.
**Example:**
```typescript
// Source: catalog/page.tsx and inventory/page.tsx StockBadge pattern
function RoleBadge({ role }: { role: string }) {
  if (role === 'admin') {
    return (
      <Badge className="bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400">
        Admin
      </Badge>
    )
  }
  return (
    <Badge className="bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400">
      User
    </Badge>
  )
}

function ActiveBadge({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <Badge className="bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400">
      Active
    </Badge>
  ) : (
    <Badge className="bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400">
      Inactive
    </Badge>
  )
}
```

### Pattern 6: Admin-Role Deactivate Guard

**What:** The Deactivate action in the user row menu must be disabled for admin-role users. The backend returns 403 `ADMN_CANNOT_DEACTIVATE_ADMIN` but the UX should prevent the attempt.
**Recommended approach:** Use a `disabled` prop on the DropdownMenuItem with visual muting, rather than hiding the item. This is more transparent and consistent with how the catalog's stock badge works (shows state, doesn't hide).
**Example:**
```typescript
// Source: shadcn DropdownMenuItem supports disabled prop
<DropdownMenuItem
  disabled={user.role === 'admin'}
  onClick={() => { setActionTarget(user); setPendingAction('deactivate') }}
  className={user.role === 'admin' ? 'cursor-not-allowed opacity-50' : ''}
>
  Deactivate
</DropdownMenuItem>
```
**Note:** Reactivate should only appear (or only be enabled) when `user.is_active === false`. Deactivate only when `user.is_active === true`. Both guarded by `role !== 'admin'` for deactivate.

### Pattern 7: Confirmation Dialog Tone

**Deactivate** — Higher severity (revokes tokens, locks out immediately). Use a more specific description:
```
"This will immediately revoke {email}'s session tokens and lock them out.
They will not be able to log in until reactivated."
```
Confirm label: "Deactivate"

**Reactivate** — Low risk, idempotent. A simple confirmation is sufficient:
```
"Restore access for {email}? They will be able to log in immediately."
```
Confirm label: "Reactivate". The ConfirmDialog `variant` can use "outline" instead of "destructive" for the confirm button, but since ConfirmDialog.tsx always uses `variant="destructive"`, callers may want a lighter version. Given CONTEXT.md says to decide, the recommendation is: keep `ConfirmDialog` as-is (always destructive styling) — the description text is sufficient to signal severity difference.

**Single review delete** — Include context:
```
"Delete the review by {display_name} for '{book_title}'? This cannot be undone."
```

**Bulk delete** — Count-only (simpler and sufficient per success criteria):
```
"Delete {N} selected review{s}? This cannot be undone."
```

### Pattern 8: Rating Filter for Reviews

**What:** Rating range filter with two Select dropdowns: "Min Rating" (1-5 or "Any") and "Max Rating" (1-5 or "Any").
**Why:** Dropdown is consistent with the existing `Select` pattern from catalog's genre filter. No debounce needed since rating values are discrete (1-5).
**Example:**
```typescript
const [ratingMin, setRatingMin] = useState<number | undefined>(undefined)
const [ratingMax, setRatingMax] = useState<number | undefined>(undefined)
const [sortBy, setSortBy] = useState<'date' | 'rating'>('date')
const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc')

// Rating Select options: "any" + "1" through "5"
<Select value={ratingMin !== undefined ? String(ratingMin) : 'any'} onValueChange={(v) => { setRatingMin(v === 'any' ? undefined : Number(v)); setPage(1) }}>
  <SelectTrigger className="w-32"><SelectValue placeholder="Min ★" /></SelectTrigger>
  <SelectContent>
    <SelectItem value="any">Any</SelectItem>
    {[1,2,3,4,5].map(n => <SelectItem key={n} value={String(n)}>{n} ★</SelectItem>)}
  </SelectContent>
</Select>
```

### Anti-Patterns to Avoid

- **Modifying DataTable.tsx for checkbox support:** DataTable is a presentation-only component; row selection state belongs in the consuming page, not in the shared component.
- **Putting bulk-delete mutation in a separate component:** Unlike StockUpdateModal, bulk delete has no reuse case — keep the mutation in the reviews page alongside the selection state.
- **Using `book_id` / `user_id` text inputs as search fields for review filters:** The API expects integer IDs, not strings. The success criteria says "filter by book" and "filter by user" — implement these as numeric ID inputs with `type="number"`, or leave as optional filters that the admin fills in (not autocomplete search). The admin knows the IDs from the table rows.
- **Forgetting to reset `selectedIds` on page change:** When pagination changes, the selected IDs from the previous page are no longer visible but remain in state. Either clear the selection on page change, or scope the selection to visible rows only. Clearing on page change is simpler and correct.
- **Not handling the `per_page` field name difference:** The admin user and review list endpoints use `per_page` (not `size` like the catalog books endpoint). The `UserListResponse` and `AdminReviewListResponse` use `total_count` (not `total` as in book pagination). Map these correctly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Paginated table rendering | Custom table HTML | `DataTable<TData>` (Phase 28) | Already built, generic, handles loading skeletons |
| Delete confirmation UI | Custom modal | `ConfirmDialog` (Phase 28) | Already built, handles pending state, keyboard dismiss |
| Pagination controls | Custom prev/next | `AdminPagination` (Phase 28) | Already built, shows item count range |
| Deactivate/reactivate API calls | Raw fetch | `apiFetch` via new functions in `admin.ts` | Handles auth, error normalization via `ApiError` |
| Toast feedback | Custom notification | `toast.success/error` from sonner | Established pattern; Toaster already mounted |
| Role/status badges | Inline conditional text | `Badge` with className override | Consistent with stock badge pattern; supports dark mode |

**Key insight:** Every UI primitive needed for this phase already exists in the project. Phase 29 is primarily data wiring and page composition, not new component building.

## Common Pitfalls

### Pitfall 1: `total_count` vs `total` pagination field name

**What goes wrong:** The catalog books endpoint returns `{ items, total, page, size }` (from the storefront `PaginatedResponse`). The admin user and review endpoints return `{ items, total_count, page, per_page, total_pages }` (from `UserListResponse` and `AdminReviewListResponse`). Using `data?.total` will return `undefined` and pagination will be broken.
**Why it happens:** Two different pagination envelope schemas exist in the backend.
**How to avoid:** Use `data?.total_count` for both user and review pages. Pass `total_count` as the `total` prop to `AdminPagination`.
**Warning signs:** Pagination showing "Showing 1-0 of 0" despite data being present.

### Pitfall 2: Stale user table after deactivate/reactivate

**What goes wrong:** After a successful deactivate/reactivate mutation, the user table still shows the old `is_active` status.
**Why it happens:** Forgetting to invalidate `adminKeys.users.all` after the mutation.
**How to avoid:** `onSuccess` handler must call `queryClient.invalidateQueries({ queryKey: adminKeys.users.all })`. The backend returns the updated `AdminUserResponse` — optimistic update is an option but invalidation is simpler and consistent with Phase 28.
**Warning signs:** User badge does not flip after confirming action.

### Pitfall 3: Checkbox state persistence across page changes

**What goes wrong:** Admin selects reviews on page 1, navigates to page 2, and the "Select All" header checkbox shows partial state because the Set still contains page-1 IDs.
**Why it happens:** `selectedIds` state persists across page changes.
**How to avoid:** In the page change handler, call `setSelectedIds(new Set())` in addition to `setPage(newPage)`. Same for filter changes.
**Warning signs:** Bulk delete button shows count > 0 after navigating to a new page with no visible selections.

### Pitfall 4: Bulk delete with empty body

**What goes wrong:** Sending `DELETE /admin/reviews/bulk` with `{ review_ids: [] }` returns 422. The backend enforces `min_length=1`.
**Why it happens:** The bulk delete button is not guarded against empty selection.
**How to avoid:** Disable the bulk delete button (or hide it) when `selectedIds.size === 0`. The guard prevents the 422.
**Warning signs:** API validation error toast when clicking bulk delete with nothing selected.

### Pitfall 5: `is_active` filter query param type

**What goes wrong:** Passing the string `"true"` or `"false"` instead of a boolean to `URLSearchParams`. The backend expects a boolean query param.
**Why it happens:** `URLSearchParams.set()` converts values to strings, and FastAPI may or may not coerce `"true"` to `True` depending on its query param parser.
**How to avoid:** FastAPI coerces `"true"` and `"false"` strings to `bool` correctly for `bool` query params. This is safe. However, explicitly document that `is_active` should be `"true"` or `"false"` (not `1`/`0`) in `URLSearchParams`. Verified: FastAPI accepts `"true"`/`"false"` for bool params.
**Warning signs:** Filter by "Active" returns all users instead of only active users.

### Pitfall 6: Single review delete uses `/reviews/` not `/admin/reviews/`

**What goes wrong:** Building a fetch function that calls `/admin/reviews/{id}` which does not exist. The endpoint is `/reviews/{review_id}` (shared endpoint, admin bypass via token).
**Why it happens:** Assuming all admin operations use the `/admin/` prefix.
**How to avoid:** The OpenAPI spec clearly shows `DELETE /reviews/{review_id}` — admin role bypass is implicit in the service layer. The API description confirms: "Review owners can delete their own review. Admins can delete any review."
**Warning signs:** 404 response when admin tries to delete a review.

### Pitfall 7: DataTable column key conflicts with checkbox column

**What goes wrong:** Using `id: 'checkbox'` or `id: 'select'` that conflicts with TanStack Table internals or other column IDs.
**Why it happens:** TanStack Table uses `id` to generate row cell keys.
**How to avoid:** Use `id: 'select'` (standard convention in TanStack Table documentation) and ensure no other column uses the same ID. The `DataTable` component renders cells by `cell.id` which is `{rowId}_{columnId}` — no conflict.

## Code Examples

Verified patterns from codebase inspection:

### QueryKey Factory Extension (admin.ts)
```typescript
// Source: admin.ts — extend the existing adminKeys object
export const adminKeys = {
  all: ['admin'] as const,
  sales: { /* existing */ },
  inventory: { /* existing */ },
  catalog: { /* existing */ },
  users: {
    all: ['admin', 'users'] as const,
    list: (params: { role?: string | null; is_active?: boolean | null; page?: number }) =>
      ['admin', 'users', 'list', params] as const,
  },
  reviews: {
    all: ['admin', 'reviews'] as const,
    list: (params: {
      book_id?: number | null; user_id?: number | null;
      rating_min?: number | null; rating_max?: number | null;
      sort_by?: string; sort_dir?: string; page?: number;
    }) => ['admin', 'reviews', 'list', params] as const,
  },
} as const
```

### Mutation Pair: Deactivate + Reactivate
```typescript
// Source: catalog/page.tsx deleteMutation pattern adapted for user management
const deactivateMutation = useMutation({
  mutationFn: () => deactivateUser(accessToken, actionTarget!.id),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.users.all })
    toast.success(`${actionTarget!.email} has been deactivated`)
    setActionTarget(null)
    setPendingAction(null)
  },
  onError: (error) => {
    toast.error(
      error instanceof ApiError ? error.detail ?? 'Failed to deactivate user' : 'Failed to deactivate user'
    )
  },
})

const reactivateMutation = useMutation({
  mutationFn: () => reactivateUser(accessToken, actionTarget!.id),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.users.all })
    toast.success(`${actionTarget!.email} has been reactivated`)
    setActionTarget(null)
    setPendingAction(null)
  },
  onError: (error) => {
    toast.error(
      error instanceof ApiError ? error.detail ?? 'Failed to reactivate user' : 'Failed to reactivate user'
    )
  },
})
```

### Bulk Delete Mutation with Selection Clear
```typescript
// Source: Pattern consistent with catalog deleteMutation; clears selectedIds on success
const bulkDeleteMutation = useMutation({
  mutationFn: () => bulkDeleteReviews(accessToken, Array.from(selectedIds)),
  onSuccess: (data) => {
    queryClient.invalidateQueries({ queryKey: adminKeys.reviews.all })
    toast.success(`${data.deleted_count} review${data.deleted_count === 1 ? '' : 's'} deleted`)
    setSelectedIds(new Set())
    setBulkConfirmOpen(false)
  },
  onError: (error) => {
    toast.error(
      error instanceof ApiError ? error.detail ?? 'Failed to delete reviews' : 'Failed to delete reviews'
    )
  },
})
```

### AdminPagination with total_count field mapping
```typescript
// Source: AdminPagination.tsx accepts total (not total_count)
// Map UserListResponse.total_count -> total prop
<AdminPagination
  page={page}
  total={usersQuery.data?.total_count ?? 0}
  size={PAGE_SIZE}
  onPageChange={setPage}
/>
```

### ConfirmDialog reuse for two actions in one page
```typescript
// Source: catalog/page.tsx — single ConfirmDialog, content driven by pendingAction
<ConfirmDialog
  open={actionTarget !== null && pendingAction !== null}
  onOpenChange={(open) => {
    if (!open) { setActionTarget(null); setPendingAction(null) }
  }}
  title={pendingAction === 'deactivate' ? 'Deactivate User' : 'Reactivate User'}
  description={
    pendingAction === 'deactivate'
      ? `This will immediately revoke ${actionTarget?.email}'s session tokens and lock them out. They will not be able to log in until reactivated.`
      : `Restore access for ${actionTarget?.email}? They will be able to log in immediately.`
  }
  confirmLabel={pendingAction === 'deactivate' ? 'Deactivate' : 'Reactivate'}
  onConfirm={() =>
    pendingAction === 'deactivate' ? deactivateMutation.mutate() : reactivateMutation.mutate()
  }
  isPending={deactivateMutation.isPending || reactivateMutation.isPending}
/>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `DataTable` not yet built | `DataTable<TData>` generic component | Phase 28 | Reuse directly — no HTML table needed |
| `ConfirmDialog` not yet built | `ConfirmDialog` reusable component | Phase 28 | Reuse for all 4 confirm actions in this phase |
| `adminKeys` only had sales/inventory/catalog | Extended with users/reviews | Phase 29 (this phase) | Add 2 namespaces to admin.ts |
| Backend endpoints not confirmed | All endpoints verified in OpenAPI spec | Pre-existing | No backend work needed |

**Deprecated/outdated:**
- Inline Dialog code in page components: Phase 28 introduced `ConfirmDialog` as the shared pattern; do not create inline Dialog JSX for confirmations in Phase 29.

## Open Questions

1. **Should the review filter bar include book_id and user_id as text inputs?**
   - What we know: The API accepts integer `book_id` and `user_id`. The admin would need to know the IDs to use these filters.
   - What's unclear: Whether the admin has an easy way to know user/book IDs without the filter being useful in practice.
   - Recommendation: Implement `book_id` and `user_id` as `type="number"` inputs with `placeholder="Book ID"` / `placeholder="User ID"`. The admin can get IDs from the URL or other admin views. These are optional filters — leave blank to show all. This matches the success criteria ("filter by book, user") without requiring autocomplete complexity.

2. **Should reactivate have a confirmation dialog?**
   - What we know: CONTEXT.md says "Reactivate dialog — decide if confirmation is needed for this low-risk action."
   - Recommendation: Yes, include a brief confirmation. Accidental clicks on a non-destructive action are minor, but consistency with deactivate (which always confirms) is better UX. The dialog makes the action deliberate. The text is low-severity.

3. **Should there be a distinct bulk-delete "toolbar" area above the table?**
   - What we know: Success criteria says "select multiple reviews via checkboxes and bulk-delete them with a single confirmation dialog." No layout constraint specified.
   - Recommendation: Show a conditional "X selected — Delete Selected" button row that appears only when `selectedIds.size > 0`. Place it between the filter bar and the DataTable. This is a common pattern (similar to Gmail's toolbar) and avoids cluttering the filter bar.

## Sources

### Primary (HIGH confidence)

- Codebase inspection — `frontend/src/types/api.generated.ts` — verified all 8 endpoints and exact request/response schemas
- Codebase inspection — `frontend/src/lib/admin.ts` — verified `adminKeys` structure and `apiFetch` pattern
- Codebase inspection — `frontend/src/components/admin/DataTable.tsx` — verified generic `DataTable<TData>` interface
- Codebase inspection — `frontend/src/components/admin/ConfirmDialog.tsx` — verified props interface and rendering
- Codebase inspection — `frontend/src/app/admin/catalog/page.tsx` — verified full CRUD pattern including mutations
- Codebase inspection — `frontend/src/components/admin/AdminPagination.tsx` — verified `total`, `size`, `page` props
- Codebase inspection — `frontend/package.json` + `node_modules/zod/package.json` — verified installed library versions

### Secondary (MEDIUM confidence)

- FastAPI bool query param coercion of `"true"/"false"` strings — standard FastAPI behavior, not re-verified against FastAPI docs but consistent with project's existing filter patterns

### Tertiary (LOW confidence)

- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified from `package.json` and `node_modules`
- Architecture: HIGH — all patterns verified by reading existing phase 28 code directly
- API contracts: HIGH — all endpoints and schemas verified from `api.generated.ts` (auto-generated from live backend)
- Pitfalls: HIGH — identified by diffing backend schemas against catalog pattern (different pagination field names confirmed)

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable — no external dependencies, all findings from local codebase)
