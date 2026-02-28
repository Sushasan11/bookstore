---
phase: 26-admin-foundation
plan: 01
subsystem: ui
tags: [next.js, shadcn, sidebar, route-groups, admin, auth, security]

# Dependency graph
requires: []
provides:
  - "(store)/ route group with Header + Footer customer layout"
  - "admin/ route group with collapsible sidebar layout"
  - "Defense-in-depth admin role enforcement (proxy.ts + Server Component)"
  - "shadcn sidebar component installed"
  - "AppSidebar with 5 nav items and active highlighting"
  - "SidebarFooterUser with user email and sign out"
  - "Admin link in UserMenu for admin-role users only"
affects:
  - "27-sales-analytics"
  - "28-book-catalog-crud"
  - "29-user-management-review-moderation"

# Tech tracking
tech-stack:
  added:
    - "shadcn sidebar component (sidebar.tsx, tooltip.tsx, use-mobile.ts)"
  patterns:
    - "Route groups: (store)/ for customer pages, admin/ for admin pages, (auth)/ for auth pages"
    - "Defense-in-depth: proxy.ts (UX redirect, Layer 1) + admin layout Server Component (security boundary, Layer 2)"
    - "Admin layout: SidebarProvider > AppSidebar + SidebarInset pattern"
    - "collapsible='icon' sidebar: desktop icon-only collapse, mobile Sheet drawer"

key-files:
  created:
    - "frontend/src/app/(store)/layout.tsx"
    - "frontend/src/app/admin/layout.tsx"
    - "frontend/src/app/admin/page.tsx"
    - "frontend/src/components/admin/AppSidebar.tsx"
    - "frontend/src/components/admin/SidebarFooterUser.tsx"
    - "frontend/src/components/ui/sidebar.tsx"
    - "frontend/src/components/ui/tooltip.tsx"
    - "frontend/src/hooks/use-mobile.ts"
  modified:
    - "frontend/src/app/layout.tsx"
    - "frontend/src/proxy.ts"
    - "frontend/src/components/layout/UserMenu.tsx"
    - "frontend/src/components/providers.tsx"

key-decisions:
  - "Route group restructure: all customer pages moved into (store)/ transparent group, root layout becomes Providers-only shell"
  - "CVE-2025-29927 mitigation: admin guard in BOTH proxy.ts middleware (UX layer) AND admin/layout.tsx Server Component (real security boundary)"
  - "Non-admin/unauthenticated /admin requests silently redirect to / — not /login — to avoid revealing admin route existence"
  - "TooltipProvider added to Providers component to support shadcn sidebar tooltips in icon-collapse mode"
  - "/admin page redirects to /admin/overview (dashboard built in Plan 02)"

patterns-established:
  - "Admin layout pattern: Server Component auth check + SidebarProvider wrapping AppSidebar and SidebarInset"
  - "Defense-in-depth: middleware redirect (UX) + layout Server Component redirect (security)"
  - "AppSidebar uses usePathname() + pathname.startsWith(href) for active nav item highlighting"

requirements-completed: [ADMF-01, ADMF-02, ADMF-03, ADMF-04]

# Metrics
duration: 30min
completed: 2026-02-28
---

# Phase 26 Plan 01: Admin Foundation Summary

**Next.js route group restructure with (store)/ customer layout, /admin route with collapsible shadcn sidebar, and defense-in-depth CVE-2025-29927 admin role enforcement**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-02-28T00:00:00Z
- **Completed:** 2026-02-28T00:30:00Z
- **Tasks:** 2
- **Files modified:** 42 (including all moved route files)

## Accomplishments
- Installed shadcn sidebar component and moved all customer pages into (store)/ route group
- Created admin layout with defense-in-depth role checking addressing CVE-2025-29927
- Built collapsible AppSidebar with 5 nav items, active highlighting, branding, and user footer
- Added Admin link to UserMenu visible only for admin-role users

## Task Commits

Each task was committed atomically:

1. **Task 1: Install shadcn sidebar and restructure routes into (store)/ group** - `19b8cac` (feat)
2. **Task 2: Create admin layout with defense-in-depth role check, sidebar, and UserMenu admin link** - `7296ecd` (feat)

## Files Created/Modified

- `frontend/src/app/(store)/layout.tsx` - Customer storefront layout with Header + Footer
- `frontend/src/app/layout.tsx` - Refactored to Providers-only shell (no Header/Footer)
- `frontend/src/app/admin/layout.tsx` - Admin layout with auth() role check + SidebarProvider
- `frontend/src/app/admin/page.tsx` - Redirects /admin to /admin/overview
- `frontend/src/components/admin/AppSidebar.tsx` - Collapsible sidebar with 5 nav items and active highlighting
- `frontend/src/components/admin/SidebarFooterUser.tsx` - User email + sign out in sidebar footer
- `frontend/src/proxy.ts` - Added adminPrefixes with silent redirect for non-admin users
- `frontend/src/components/layout/UserMenu.tsx` - Added Admin link for admin-role users
- `frontend/src/components/providers.tsx` - Added TooltipProvider for sidebar tooltip support
- `frontend/src/components/ui/sidebar.tsx` - shadcn sidebar component
- `frontend/src/components/ui/tooltip.tsx` - shadcn tooltip component
- `frontend/src/hooks/use-mobile.ts` - Mobile detection hook for sidebar
- All 28 customer route files moved to (store)/ group (catalog, books, cart, orders, wishlist, account, home)

## Decisions Made
- Route group (store)/ used for transparent URL grouping — all existing customer URLs unchanged
- Defense-in-depth: proxy.ts handles UX redirect fast (Layer 1), admin/layout.tsx Server Component provides real security boundary not bypassable by CVE-2025-29927 (Layer 2)
- Silent redirect to / for unauthenticated/non-admin /admin access — avoids revealing admin route exists
- TooltipProvider added to Providers component since sidebar tooltips require it in the React tree

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken import in MoreInGenre.tsx after route group move**
- **Found during:** Task 1 (route group restructure)
- **Issue:** `MoreInGenre.tsx` imported `BookCard` from `@/app/catalog/_components/BookCard` which became invalid after moving catalog into (store)/ group
- **Fix:** Updated import path to `@/app/(store)/catalog/_components/BookCard`
- **Files modified:** `frontend/src/app/(store)/books/[id]/_components/MoreInGenre.tsx`
- **Verification:** Next.js build passed without module-not-found errors
- **Committed in:** `19b8cac` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added TooltipProvider to Providers component**
- **Found during:** Task 1 (sidebar installation)
- **Issue:** shadcn sidebar uses Tooltip components for icon-mode tooltips which require TooltipProvider in the React tree — not adding it would cause runtime errors when sidebar is collapsed
- **Fix:** Imported TooltipProvider from @/components/ui/tooltip and wrapped children in Providers
- **Files modified:** `frontend/src/components/providers.tsx`
- **Verification:** Build passes, sidebar tooltip support enabled
- **Committed in:** `19b8cac` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- `git mv` failed with "Permission denied" on Windows for directory moves — used `cp -r` followed by `git rm -rf` + `git add` to achieve the same rename tracking. Git correctly detected the renames (100% similarity) in all cases.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Admin shell infrastructure complete: /admin route protected, sidebar renders with 5 nav items
- Plan 02 can now build /admin/overview dashboard page, /admin/sales, etc. on top of this layout
- All customer storefront URLs continue to work unchanged

---
*Phase: 26-admin-foundation*
*Completed: 2026-02-28*
