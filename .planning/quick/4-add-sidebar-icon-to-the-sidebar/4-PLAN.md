---
phase: quick-4
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/admin/AppSidebar.tsx
autonomous: true
requirements: [QUICK-4]

must_haves:
  truths:
    - "Sidebar header displays a toggle icon that collapses/expands the sidebar"
    - "Toggle icon is visible in both expanded and collapsed sidebar states"
    - "Clicking the toggle icon toggles the sidebar between full and icon-only mode"
  artifacts:
    - path: "frontend/src/components/admin/AppSidebar.tsx"
      provides: "Sidebar with integrated toggle trigger"
      contains: "SidebarTrigger"
  key_links:
    - from: "frontend/src/components/admin/AppSidebar.tsx"
      to: "useSidebar or SidebarTrigger"
      via: "shadcn sidebar toggle mechanism"
      pattern: "SidebarTrigger|toggleSidebar"
---

<objective>
Add a sidebar toggle icon inside the admin sidebar header so users can collapse and expand the sidebar from within the sidebar itself.

Purpose: The sidebar currently uses `collapsible="icon"` mode, but the only toggle trigger is in the layout header outside the sidebar. Adding a trigger inside the sidebar header provides a more intuitive and standard UX pattern where users can collapse the sidebar from within it.
Output: Updated AppSidebar.tsx with an integrated toggle icon in the sidebar header.
</objective>

<execution_context>
@C:/Users/Sushasan/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Sushasan/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/admin/AppSidebar.tsx
@frontend/src/app/admin/layout.tsx
@frontend/src/components/ui/sidebar.tsx

<interfaces>
<!-- Key components and hooks from shadcn sidebar -->

From frontend/src/components/ui/sidebar.tsx:
- `SidebarTrigger` — A ghost Button that calls `toggleSidebar()` from `useSidebar()` hook. Renders `PanelLeftIcon` with sr-only text.
- `useSidebar()` — Hook providing `{ state, open, setOpen, openMobile, setOpenMobile, isMobile, toggleSidebar }`
- `SidebarHeader` — Layout wrapper for the top of the sidebar

From frontend/src/components/admin/AppSidebar.tsx:
- Currently imports: `Sidebar, SidebarContent, SidebarHeader, SidebarFooter, SidebarMenu, SidebarMenuItem, SidebarMenuButton, SidebarGroup, SidebarGroupContent`
- Currently imports icons: `LayoutDashboard, TrendingUp, BookOpen, Package, Users, Star` from lucide-react
- Uses `BookStoreLogo` component with `group-data-[collapsible=icon]:hidden` pattern for collapse behavior
- Sidebar uses `collapsible="icon"` mode
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add SidebarTrigger to sidebar header</name>
  <files>frontend/src/components/admin/AppSidebar.tsx</files>
  <action>
Modify AppSidebar.tsx to add a sidebar toggle icon in the sidebar header:

1. Add `SidebarTrigger` to the import from `@/components/ui/sidebar` (it is already exported from that module).

2. Update the `SidebarHeader` section to include the `SidebarTrigger` positioned at the right side of the header. The current header structure is:
```tsx
<SidebarHeader>
  <div className="flex items-center gap-2 px-2 py-1.5">
    <BookStoreLogo ... />
    <Badge ...>Admin</Badge>
  </div>
</SidebarHeader>
```

Change it to place a `SidebarTrigger` at the trailing end using `justify-between` and `ml-auto`:
```tsx
<SidebarHeader>
  <div className="flex items-center gap-2 px-2 py-1.5">
    <BookStoreLogo
      variant="full"
      iconSize={22}
      textClassName="text-sm font-semibold group-data-[collapsible=icon]:hidden"
      className="px-1"
    />
    <Badge variant="secondary" className="text-xs group-data-[collapsible=icon]:hidden">Admin</Badge>
    <SidebarTrigger className="ml-auto size-7 group-data-[collapsible=icon]:ml-0" />
  </div>
</SidebarHeader>
```

Key details:
- `ml-auto` pushes the trigger to the right in expanded mode
- `group-data-[collapsible=icon]:ml-0` ensures proper centering when sidebar is collapsed to icon-only
- The `SidebarTrigger` already handles the toggle logic internally via `useSidebar()` hook — no extra wiring needed
- The `PanelLeftIcon` used by `SidebarTrigger` is appropriate for a sidebar toggle affordance
  </action>
  <verify>
    <automated>cd D:/Python/claude-test/frontend && npx next build 2>&1 | tail -5</automated>
  </verify>
  <done>
    - SidebarTrigger icon appears in the sidebar header, right-aligned next to the logo and Admin badge
    - Clicking it toggles the sidebar between expanded and icon-only collapsed state
    - In collapsed state, the trigger icon remains visible and clickable to re-expand
    - No build errors
  </done>
</task>

</tasks>

<verification>
- `cd frontend && npx next build` completes without errors
- Visual check: sidebar header shows the PanelLeftIcon toggle button at the right end
- Functional check: clicking the icon collapses sidebar to icon-only mode; clicking again expands it
</verification>

<success_criteria>
- Admin sidebar has an integrated toggle icon in its header
- Toggle works in both directions (collapse and expand)
- Build passes cleanly
</success_criteria>

<output>
After completion, create `.planning/quick/4-add-sidebar-icon-to-the-sidebar/4-SUMMARY.md`
</output>
