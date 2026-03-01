---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/admin/AppSidebar.tsx
autonomous: true
requirements: ["QUICK-3"]
must_haves:
  truths:
    - "Admin sidebar no longer shows a 'Back to Store' link"
    - "Sidebar header still shows BookStore logo and Admin badge"
    - "All navigation items remain functional"
  artifacts:
    - path: "frontend/src/components/admin/AppSidebar.tsx"
      provides: "Admin sidebar without Back to Store link"
  key_links: []
---

<objective>
Remove the "Back to Store" link from the admin sidebar header.

Purpose: The user wants to remove the "Back to Store" navigation element from the admin sidebar.
Output: Updated AppSidebar.tsx without the Back to Store link.
</objective>

<execution_context>
@C:/Users/Sushasan/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Sushasan/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/admin/AppSidebar.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove "Back to Store" link from admin sidebar</name>
  <files>frontend/src/components/admin/AppSidebar.tsx</files>
  <action>
In `frontend/src/components/admin/AppSidebar.tsx`:

1. Remove the entire SidebarMenu block inside SidebarHeader (lines 38-47) that contains the "Back to Store" link:
   ```tsx
   <SidebarMenu>
     <SidebarMenuItem>
       <SidebarMenuButton asChild tooltip="Back to Store">
         <Link href="/">
           <ChevronLeft className="h-4 w-4" />
           <span>Back to Store</span>
         </Link>
       </SidebarMenuButton>
     </SidebarMenuItem>
   </SidebarMenu>
   ```

2. Remove `ChevronLeft` from the lucide-react import (line 8) since it will no longer be used. The import should become:
   ```tsx
   import { LayoutDashboard, TrendingUp, BookOpen, Package, Users, Star } from 'lucide-react'
   ```

3. Keep everything else intact: the SidebarHeader with BookStoreLogo and Admin badge, the SidebarContent with nav items, and the SidebarFooter.
  </action>
  <verify>
    <automated>cd D:/Python/claude-test/frontend && npx next lint --quiet 2>&1 | head -20</automated>
  </verify>
  <done>The "Back to Store" link and ChevronLeft import are removed. The sidebar header only shows the BookStore logo and Admin badge. All other navigation items remain unchanged.</done>
</task>

</tasks>

<verification>
- `grep -i "back to store" frontend/src/components/admin/AppSidebar.tsx` returns no matches
- `grep "ChevronLeft" frontend/src/components/admin/AppSidebar.tsx` returns no matches
- The admin sidebar still renders the logo, badge, nav items, and footer user section
</verification>

<success_criteria>
- "Back to Store" link completely removed from admin sidebar
- No unused imports remain
- Lint passes with no errors
</success_criteria>

<output>
After completion, create `.planning/quick/3-remove-back-to-store-from-admin-sidebar/3-SUMMARY.md`
</output>
