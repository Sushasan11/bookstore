# Phase 29: User Management and Review Moderation - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin can manage user accounts and moderate reviews from paginated, filterable tables. User management includes deactivating and reactivating non-admin users. Review moderation includes single-delete and bulk-delete with checkbox selection. Backend endpoints for both are fully implemented — this phase is frontend-only.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All four areas discussed were delegated to Claude's judgement. The user trusts Claude to make decisions based on existing codebase patterns and success criteria. Below are the specific areas and guidance:

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

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User deferred all visual and interaction decisions to Claude's discretion, guided by existing codebase patterns.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DataTable.tsx`: Generic paginated table with TanStack React Table, loading skeletons, configurable columns, empty state
- `ConfirmDialog.tsx`: Delete/dangerous action confirmation dialog with loading state and customizable label
- `AdminPagination.tsx`: Previous/Next pagination with item count display
- `Badge` component: Color variants for status indicators (red/amber/green patterns from stock badges)
- `Select/SelectContent/SelectItem`: Dropdown filter components
- `DropdownMenu`: Row-level action menus
- `Sheet`: Side drawer for forms/details

### Established Patterns
- React Query with hierarchical query keys (`adminKeys.catalog.list(params)`)
- `useMutation` with `queryClient.invalidateQueries` on success
- `toast.success/error` for mutation feedback
- `ApiError` catch in `onError` for structured error messages
- `useState` for filter state with page reset on filter change
- `apiFetch` with Bearer token for all admin API calls
- Zod + React Hook Form for form validation

### Integration Points
- Backend endpoints fully registered: `GET/PATCH /admin/users/*`, `GET/DELETE /admin/reviews/*`
- Sidebar navigation already has Users and Reviews menu items with icons
- Admin layout (`/admin/layout.tsx`) enforces admin role check
- Placeholder pages exist: `/admin/users/page.tsx`, `/admin/reviews/page.tsx`
- Catalog page (`/admin/catalog/page.tsx`) serves as the reference CRUD implementation
- `adminKeys` query key factory needs extension for `users` and `reviews` namespaces

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-user-management-and-review-moderation*
*Context gathered: 2026-03-01*
