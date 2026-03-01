---
phase: 29-user-management-and-review-moderation
plan: "01"
subsystem: ui
tags: [react, tanstack-query, tanstack-table, next-auth, shadcn, admin]

# Dependency graph
requires:
  - phase: 28-book-catalog-crud
    provides: DataTable, ConfirmDialog, AdminPagination shared admin components
provides:
  - adminKeys.users and adminKeys.reviews namespaces in admin.ts
  - fetchAdminUsers, deactivateUser, reactivateUser, fetchAdminReviews, deleteSingleReview, bulkDeleteReviews functions in admin.ts
  - User Management page at /admin/users with paginated filterable table and deactivate/reactivate actions
affects:
  - 29-02 (review moderation page uses the reviews functions added to admin.ts in this plan)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - adminKeys extended with users and reviews namespaces following existing catalog pattern
    - Inline badge components (RoleBadge, ActiveBadge) following StockBadge pattern from catalog/inventory pages
    - Single ConfirmDialog driven by pendingAction state for multiple mutation actions in one page
    - total_count (not total) used for AdminPagination when consuming UserListResponse
    - Deactivate DropdownMenuItem disabled+opacity-50 for admin-role rows (frontend guard matching backend 403)

key-files:
  created:
    - frontend/src/app/admin/users/page.tsx
  modified:
    - frontend/src/lib/admin.ts

key-decisions:
  - "DropdownMenu shows Deactivate (active users only) or Reactivate (inactive users only) based on is_active — not both at once — so the menu is unambiguous"
  - "Deactivate DropdownMenuItem uses disabled prop with opacity-50 for admin-role users rather than hiding — transparent about the restriction"
  - "ConfirmDialog description text is severity-differentiated: deactivate warns about immediate token revocation, reactivate is lower-severity"
  - "AdminPagination receives total_count (not total) from UserListResponse — different pagination envelope from catalog PaginatedResponse"

patterns-established:
  - "Pattern: Two-action page with single ConfirmDialog — pendingAction state ('deactivate'|'reactivate'|null) drives title, description, confirmLabel, and onConfirm handler"
  - "Pattern: Filter + page reset — all filter change handlers reset page to 1"

requirements-completed: [USER-01, USER-02, USER-03, USER-04]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 29 Plan 01: User Management Page Summary

**Paginated filterable user table at /admin/users with role/status badges, deactivate/reactivate mutations, and admin-role guard using extended admin.ts data layer**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-01T08:55:22Z
- **Completed:** 2026-03-01T08:57:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Extended `admin.ts` with `users` and `reviews` namespaces in `adminKeys` and 6 new fetch/mutation functions covering full Phase 29 data needs
- Built `/admin/users` replacing the placeholder with a full paginated, filterable user management page
- Admin-role deactivate guard (disabled+muted menu item) with ConfirmDialog showing severity-aware description text

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend admin.ts with users and reviews namespaces and all fetch/mutation functions** - `86c84fb` (feat)
2. **Task 2: Build User Management page with DataTable, filters, and deactivate/reactivate** - `55bb890` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/lib/admin.ts` - Extended adminKeys with users/reviews namespaces; added 6 new functions: fetchAdminUsers, deactivateUser, reactivateUser, fetchAdminReviews, deleteSingleReview, bulkDeleteReviews
- `frontend/src/app/admin/users/page.tsx` - Full User Management page: DataTable with 5 columns, role/status Select filters, DropdownMenu with Deactivate/Reactivate actions, ConfirmDialog, AdminPagination using total_count

## Decisions Made
- DropdownMenu shows only the contextually relevant action: Deactivate (for active users) OR Reactivate (for inactive users) — not both simultaneously — to avoid confusion
- Admin-role users show Deactivate as disabled+opacity-50 rather than hidden — the restriction is visible and consistent with how stock badges show state
- ConfirmDialog uses severity-differentiated text: deactivate warns about immediate session token revocation and lockout, reactivate is a lighter confirmation
- `total_count` field from `UserListResponse` (not `total`) correctly passed to AdminPagination — different pagination envelope than catalog's `PaginatedResponse`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 6 Phase 29 fetch/mutation functions are in admin.ts and ready for Plan 02 (review moderation page)
- adminKeys.reviews namespace is ready for the reviews page useQuery key
- DataTable, ConfirmDialog, AdminPagination patterns established for direct reuse in reviews page
- Plan 02 adds checkbox bulk-select and bulk-delete mutation to the reviews page

---
*Phase: 29-user-management-and-review-moderation*
*Completed: 2026-03-01*
