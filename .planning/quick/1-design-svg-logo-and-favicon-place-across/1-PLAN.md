---
phase: quick-1
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/brand/BookStoreLogo.tsx
  - frontend/src/app/favicon.ico
  - frontend/public/favicon-16x16.png
  - frontend/public/favicon-32x32.png
  - frontend/public/apple-touch-icon.png
  - frontend/public/favicon.svg
  - frontend/src/app/layout.tsx
  - frontend/src/components/layout/Header.tsx
  - frontend/src/components/layout/MobileNav.tsx
  - frontend/src/components/layout/Footer.tsx
  - frontend/src/app/(auth)/layout.tsx
  - frontend/src/components/admin/AppSidebar.tsx
  - backend/app/email/templates/base.html
autonomous: true
requirements: []

must_haves:
  truths:
    - "A book-icon SVG logo component exists and renders correctly in light and dark mode"
    - "The favicon shows the book icon in browser tabs"
    - "Header shows logo icon + BookStore text instead of plain text"
    - "Admin sidebar shows logo icon always, text hides when collapsed"
    - "Auth layout shows logo above the login card"
    - "Email template header shows BookStore branding"
  artifacts:
    - path: "frontend/src/components/brand/BookStoreLogo.tsx"
      provides: "Reusable SVG logo React component with size/variant props"
    - path: "frontend/public/favicon.svg"
      provides: "SVG favicon for modern browsers"
    - path: "frontend/src/app/layout.tsx"
      provides: "Favicon <link> tags in metadata"
  key_links:
    - from: "frontend/src/components/brand/BookStoreLogo.tsx"
      to: "frontend/src/components/layout/Header.tsx"
      via: "import and render BookStoreLogo"
    - from: "frontend/src/components/brand/BookStoreLogo.tsx"
      to: "frontend/src/components/admin/AppSidebar.tsx"
      via: "import and render BookStoreLogo with icon-only variant when collapsed"
---

<objective>
Design a custom SVG book-themed logo and deploy it across the entire application: browser favicon, site header, mobile nav, admin sidebar, auth/login page, and email templates.

Purpose: Replace default placeholder branding with a consistent, professional identity that matches the existing shadcn/Tailwind grayscale theme.
Output: BookStoreLogo React component + favicon assets + all placement updates.
</objective>

<execution_context>
@C:/Users/Sushasan/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Sushasan/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md

Theme facts (from globals.css):
- Light: primary = oklch(0.205 0 0) [near-black], background = oklch(1 0 0) [white]
- Dark: primary = oklch(0.922 0 0) [near-white], background = oklch(0.145 0 0) [very dark]
- The design is a clean grayscale — no color accents
- Tailwind CSS class for primary color: `text-primary`, `fill-primary`; background: `bg-background`
- Radius base: 0.625rem (rounded corners)

Key files to modify (from existing_code_context):
- `frontend/src/components/layout/Header.tsx` — plain text "Bookstore" Link
- `frontend/src/components/layout/MobileNav.tsx` — SheetTitle "Bookstore"
- `frontend/src/components/layout/Footer.tsx` — copyright "© 2026 Bookstore."
- `frontend/src/components/admin/AppSidebar.tsx` — SidebarHeader span + Admin badge
- `frontend/src/app/(auth)/layout.tsx` — centered flex container, logo above card
- `frontend/src/app/layout.tsx` — metadata title, favicon <link> tags
- `backend/app/email/templates/base.html` — Jinja2 HTML email, dark header (#1a202c) with `<h1>Bookstore</h1>`
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create BookStoreLogo SVG component and favicon assets</name>
  <files>
    frontend/src/components/brand/BookStoreLogo.tsx,
    frontend/public/favicon.svg,
    frontend/public/favicon-32x32.png,
    frontend/public/favicon-16x16.png,
    frontend/public/apple-touch-icon.png,
    frontend/src/app/favicon.ico
  </files>
  <action>
Create the brand directory and logo component, then generate all favicon assets.

**Step 1 — Create `frontend/src/components/brand/BookStoreLogo.tsx`:**

Design: An open book icon (two pages fanning open, simple geometric, works at all sizes) + the word "BookStore" in a semibold sans-serif. The SVG icon uses `currentColor` so it inherits Tailwind `text-primary` / theme colors automatically.

```tsx
import { cn } from "@/lib/utils";

interface BookStoreLogoProps {
  /** Controls which parts render */
  variant?: "full" | "icon-only" | "text-only";
  /** Icon size in px (width = height) */
  iconSize?: number;
  /** Extra Tailwind classes for the wrapper */
  className?: string;
  /** Extra Tailwind classes for the text span */
  textClassName?: string;
}

export function BookStoreLogo({
  variant = "full",
  iconSize = 28,
  className,
  textClassName,
}: BookStoreLogoProps) {
  const showIcon = variant === "full" || variant === "icon-only";
  const showText = variant === "full" || variant === "text-only";

  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      {showIcon && (
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* Left page of open book */}
          <path
            d="M16 26 C16 26 7 22 4 8 L4 8 C4 7 5 6 6 6 L15 6 C15.6 6 16 6.4 16 7 L16 26Z"
            fill="currentColor"
            opacity="0.15"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Right page of open book */}
          <path
            d="M16 26 C16 26 25 22 28 8 L28 8 C28 7 27 6 26 6 L17 6 C16.4 6 16 6.4 16 7 L16 26Z"
            fill="currentColor"
            opacity="0.15"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Center spine */}
          <line
            x1="16"
            y1="7"
            x2="16"
            y2="26"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          {/* Left page lines (text suggestion) */}
          <line x1="8" y1="11" x2="14" y2="11" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="7" y1="14" x2="14" y2="14" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="7" y1="17" x2="14" y2="17" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          {/* Right page lines */}
          <line x1="18" y1="11" x2="24" y2="11" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="18" y1="14" x2="25" y2="14" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
          <line x1="18" y1="17" x2="25" y2="17" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
        </svg>
      )}
      {showText && (
        <span
          className={cn(
            "font-semibold tracking-tight",
            textClassName
          )}
        >
          BookStore
        </span>
      )}
    </span>
  );
}
```

**Step 2 — Create `frontend/public/favicon.svg`:**

Write an SVG file containing only the book icon (no text), using a hardcoded near-black fill (#1a1a1a) so it is readable on white browser UI in light mode. Size 32×32 viewBox. Copy the same path shapes as the icon above but with explicit `fill="#1a1a1a"` and `stroke="#1a1a1a"` instead of `currentColor`.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <path d="M16 26 C16 26 7 22 4 8 L4 8 C4 7 5 6 6 6 L15 6 C15.6 6 16 6.4 16 7 L16 26Z"
    fill="#1a1a1a" fill-opacity="0.15" stroke="#1a1a1a" stroke-width="1.5" stroke-linejoin="round"/>
  <path d="M16 26 C16 26 25 22 28 8 L28 8 C28 7 27 6 26 6 L17 6 C16.4 6 16 6.4 16 7 L16 26Z"
    fill="#1a1a1a" fill-opacity="0.15" stroke="#1a1a1a" stroke-width="1.5" stroke-linejoin="round"/>
  <line x1="16" y1="7" x2="16" y2="26" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="8" y1="11" x2="14" y2="11" stroke="#1a1a1a" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
  <line x1="7" y1="14" x2="14" y2="14" stroke="#1a1a1a" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
  <line x1="7" y1="17" x2="14" y2="17" stroke="#1a1a1a" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
  <line x1="18" y1="11" x2="24" y2="11" stroke="#1a1a1a" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
  <line x1="18" y1="14" x2="25" y2="14" stroke="#1a1a1a" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
  <line x1="18" y1="17" x2="25" y2="17" stroke="#1a1a1a" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
</svg>
```

**Step 3 — Generate PNG favicon files using Node.js/sharp or a CLI:**

Run: `cd frontend && npx sharp-cli --input public/favicon.svg --output public/favicon-32x32.png --width 32 --height 32 2>/dev/null`

If sharp-cli is not available, use the `canvas` approach or write the PNGs programmatically. Alternatively, generate the PNG files by writing a small Node script `scripts/gen-favicons.js` that uses the `sharp` package (already likely available as a Next.js dependency):

```js
// frontend/scripts/gen-favicons.js
const sharp = require('sharp');
const path = require('path');

const svgPath = path.join(__dirname, '../public/favicon.svg');

sharp(svgPath).resize(16, 16).png().toFile(path.join(__dirname, '../public/favicon-16x16.png'));
sharp(svgPath).resize(32, 32).png().toFile(path.join(__dirname, '../public/favicon-32x32.png'));
sharp(svgPath).resize(180, 180).png().toFile(path.join(__dirname, '../public/apple-touch-icon.png'));
```

Run: `cd frontend && node scripts/gen-favicons.js`

If sharp is not installed: `cd frontend && npm install --save-dev sharp` first.

For `favicon.ico`: Convert the 32×32 PNG to ICO. If no ico tool available, copy the 32×32 PNG as `favicon.ico` (modern browsers accept PNG-encoded ICO) using: `cp public/favicon-32x32.png src/app/favicon.ico`

The `.ico` file only needs to exist; Next.js serves it from `src/app/favicon.ico` automatically.
  </action>
  <verify>
    <automated>test -f frontend/src/components/brand/BookStoreLogo.tsx &amp;&amp; test -f frontend/public/favicon.svg &amp;&amp; echo "Logo component and SVG favicon exist"</automated>
  </verify>
  <done>BookStoreLogo.tsx exports the component with variant/iconSize/className props. frontend/public/favicon.svg exists with valid SVG content. PNG files generated at 16×16, 32×32, and 180×180.</done>
</task>

<task type="auto">
  <name>Task 2: Place logo across Header, MobileNav, Footer, Auth layout, and Admin sidebar</name>
  <files>
    frontend/src/components/layout/Header.tsx,
    frontend/src/components/layout/MobileNav.tsx,
    frontend/src/components/layout/Footer.tsx,
    frontend/src/app/(auth)/layout.tsx,
    frontend/src/components/admin/AppSidebar.tsx,
    frontend/src/app/layout.tsx,
    backend/app/email/templates/base.html
  </files>
  <action>
Update all placement sites to use BookStoreLogo or equivalent inline branding.

**Header.tsx:**
Read the file first. Find the plain text "Bookstore" Link. Replace the text content with `<BookStoreLogo iconSize={24} textClassName="text-sm" />`. Import BookStoreLogo from `@/components/brand/BookStoreLogo`.

**MobileNav.tsx:**
Read the file first. Find the SheetTitle containing "Bookstore". Replace its text content with `<BookStoreLogo iconSize={22} textClassName="text-sm" />`. Import BookStoreLogo.

**Footer.tsx:**
Read the file first. Find the copyright span/text "© 2026 Bookstore." Keep the © symbol and year, but replace plain "Bookstore" text with `<BookStoreLogo variant="icon-only" iconSize={16} className="inline-flex align-middle mx-1" />` followed by "Bookstore" — or simply update the text node to keep "BookStore" with proper casing for brand consistency. No component needed here if layout doesn't suit it; just correct the capitalization to "BookStore" to match the logo.

**Auth layout (`frontend/src/app/(auth)/layout.tsx`):**
Read the file first. Add `<BookStoreLogo iconSize={36} textClassName="text-xl font-bold" className="mb-6" />` as the first child inside the centering flex container, above where the `{children}` (login card) is rendered. Import BookStoreLogo.

**AppSidebar.tsx:**
Read the file first. Find the SidebarHeader section with `<span className="font-bold text-lg group-data-[collapsible=icon]:hidden">BookStore</span>`. Replace the entire SidebarHeader content with:
```tsx
<BookStoreLogo
  variant="full"
  iconSize={22}
  textClassName="text-sm font-semibold group-data-[collapsible=icon]:hidden"
  className="px-1"
/>
```
The icon will always show; the text span (via `textClassName`) hides when the sidebar is collapsed to icon mode. Import BookStoreLogo.

**Root layout (`frontend/src/app/layout.tsx`):**
Read the file first. In the `metadata` export, update `title` to `"BookStore"` (capitalize properly). Add favicon link tags inside the metadata object:
```ts
export const metadata: Metadata = {
  title: "BookStore",
  description: "...",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
};
```

**Email template (`backend/app/email/templates/base.html`):**
Read the file first. Find the dark header section (background #1a202c) containing `<h1>Bookstore</h1>` or similar. Replace with styled text-based branding since email clients have limited SVG support:
```html
<div style="background-color: #1a202c; padding: 24px 32px; text-align: center;">
  <span style="display: inline-flex; align-items: center; gap: 8px; color: #f7fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
    <!-- Inline SVG book icon — works in most modern email clients -->
    <svg width="24" height="24" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;">
      <path d="M16 26 C16 26 7 22 4 8 L4 8 C4 7 5 6 6 6 L15 6 C15.6 6 16 6.4 16 7 L16 26Z" fill="#f7fafc" fill-opacity="0.2" stroke="#f7fafc" stroke-width="1.5" stroke-linejoin="round"/>
      <path d="M16 26 C16 26 25 22 28 8 L28 8 C28 7 27 6 26 6 L17 6 C16.4 6 16 6.4 16 7 L16 26Z" fill="#f7fafc" fill-opacity="0.2" stroke="#f7fafc" stroke-width="1.5" stroke-linejoin="round"/>
      <line x1="16" y1="7" x2="16" y2="26" stroke="#f7fafc" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    <span style="font-size: 20px; font-weight: 600; letter-spacing: -0.025em; color: #f7fafc;">BookStore</span>
  </span>
</div>
```
Remove the old `<h1>Bookstore</h1>` heading and replace the header block entirely with the above.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx tsc --noEmit 2>&amp;1 | head -20</automated>
  </verify>
  <done>All 7 files updated. TypeScript compilation passes with no new errors. BookStoreLogo imported and rendered in Header, MobileNav, Auth layout, and AppSidebar. Footer brand name updated. layout.tsx metadata icons configured. Email template header replaced with inline SVG + styled text.</done>
</task>

</tasks>

<verification>
After both tasks complete:
1. Start dev server: `cd frontend && npm run dev`
2. Visit http://localhost:3000 — browser tab should show book icon favicon
3. Header shows book icon + "BookStore" text
4. Visit http://localhost:3000/login — logo appears above the login card
5. Check dark mode toggle — logo adapts (currentColor follows theme)
6. Visit http://localhost:3000/admin — sidebar shows book icon always; when collapsed to icon-only, text hides
7. TypeScript: `cd frontend && npx tsc --noEmit` — no new errors
</verification>

<success_criteria>
- BookStoreLogo component renders in light and dark mode using currentColor (no hardcoded colors in the React component)
- Browser tab favicon shows the book icon (SVG favicon served from /favicon.svg)
- Header, MobileNav, Auth layout, and Admin sidebar all use BookStoreLogo component
- Admin sidebar collapses to icon-only correctly
- Email template has inline SVG book icon + "BookStore" text in dark header
- `npx tsc --noEmit` passes with no new TypeScript errors
</success_criteria>

<output>
After completion, create `.planning/quick/1-design-svg-logo-and-favicon-place-across/1-SUMMARY.md`
</output>
