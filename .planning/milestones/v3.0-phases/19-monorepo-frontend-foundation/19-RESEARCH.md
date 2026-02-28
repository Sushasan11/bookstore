# Phase 19: Monorepo + Frontend Foundation - Research

**Researched:** 2026-02-27
**Domain:** Monorepo restructuring, Next.js 15 App Router, Tailwind v4, shadcn/ui, openapi-typescript, TanStack Query v5, CORS
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Layout shell design:**
- Top navbar with logo, nav links, and user/cart actions
- Hamburger menu on mobile (slide-out or dropdown)
- Responsive layout: header, main content area, footer
- Mobile-first approach

**Monorepo structure:**
- Package manager: npm (not pnpm or bun)
- Move all existing backend code into `backend/` subfolder using `git mv` to preserve history
- Frontend scaffolded in `frontend/` directory
- No shared `packages/` directory for now — keep it simple with just `backend/` and `frontend/`

**Component & styling approach:**
- Clean & modern visual tone — white space, subtle shadows, rounded corners (Vercel/Linear aesthetic)
- Dark mode supported from the start with system preference detection and manual toggle
- System font stack (no custom web fonts) — zero load time, clean look
- shadcn/ui as the component library with Tailwind v4

**API integration setup:**
- `npm run generate-types` script that hits running FastAPI `/openapi.json` and outputs `frontend/src/types/api.generated.ts`
- Thin `api.ts` fetch wrapper with base URL, auth headers, and JSON parsing
- TanStack Query provider at root layout, query hooks call the fetch wrapper
- Toast notifications (shadcn/ui) for API error display
- Health check smoke test: layout shell calls a backend health/version endpoint to prove CORS, fetch wrapper, and TanStack Query work end-to-end

### Claude's Discretion
- Header contents beyond logo and nav links (search bar placement, cart icon, user menu layout)
- Footer style and content (minimal vs rich)
- Root-level dev script coordination (concurrently vs separate terminals)
- Primary accent color choice (within the clean modern aesthetic)
- Exact shadcn/ui theme token customization
- Loading and error state patterns for the layout shell

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Monorepo restructured with `backend/` and `frontend/` directories, backend CI passing | git mv sequence + pyproject.toml/alembic.ini path adjustments section |
| FOUND-02 | Next.js 15 app scaffolded with TypeScript, shadcn/ui, Tailwind v4, and root layout shell | create-next-app + shadcn init + Tailwind v4 CSS-first config section |
| FOUND-03 | CORS enabled on FastAPI backend for frontend origin | CORSMiddleware setup section — existing ALLOWED_ORIGINS field in config.py already seeds this |
| FOUND-04 | openapi-typescript types auto-generated from FastAPI `/openapi.json` | openapi-typescript v7.13.0 CLI section + npm script pattern |
| FOUND-05 | TanStack Query provider configured at root layout | Providers component pattern + layout wrapping section |
| FOUND-06 | Responsive mobile-first layout with header, navigation, and footer | shadcn/ui Sheet for mobile nav + Tailwind responsive utilities section |
</phase_requirements>

## Summary

Phase 19 combines three distinct sub-tasks: (1) restructuring the existing flat Python repo into `backend/` + `frontend/` directories while keeping git history intact, (2) scaffolding a full Next.js 15 frontend with the locked stack (TypeScript, Tailwind v4, shadcn/ui, TanStack Query), and (3) wiring the frontend to the FastAPI backend via CORS, openapi-typescript types, and a TanStack Query-powered health-check smoke test.

The monorepo restructuring is mechanical but has several config-file landmines: `alembic.ini`'s `%(here)s` token and `prepend_sys_path`, `pyproject.toml`'s `packages` include, and pytest's `testpaths` all use relative paths that will break when source files move to `backend/`. These must all be audited and updated in the same commit as the `git mv`. The preferred approach is a flat monorepo root with no npm workspaces — just a root `package.json` with `concurrently` for convenience scripts.

The frontend stack choices (Next.js 15, Tailwind v4, shadcn/ui) are now fully stable together as of early 2025. The key change from Tailwind v3: configuration is CSS-first (`@import "tailwindcss"` + `@theme inline` in globals.css instead of tailwind.config.js). shadcn/ui's CLI handles this automatically when you run `npx shadcn@latest init` on a Tailwind v4 project. Dark mode with next-themes is the standard pattern; `suppressHydrationWarning` on the `<html>` element prevents flicker.

**Primary recommendation:** Run `npx create-next-app@latest frontend --yes` to scaffold with TypeScript + Tailwind defaults, then immediately run `npx shadcn@latest init` inside `frontend/` to layer in shadcn/ui (which handles Tailwind v4 CSS config). Wire TanStack Query via a `'use client'` Providers component and add `concurrently` at the repo root for a single dev command.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.x (latest) | React framework, App Router, SSR/SSG | Official choice; App Router is the current paradigm |
| TypeScript | 5.1+ (bundled) | Type safety | Required by Next.js App Router patterns |
| Tailwind CSS | v4 (latest, Jan 2025) | Utility-first styling | Locked decision; CSS-first config removes tailwind.config.js |
| shadcn/ui | latest (supports Tailwind v4) | Copy-paste component library | Locked decision; owns the component source in-repo |
| next-themes | ^0.4.x | Dark mode with system detection + manual toggle | Standard for Next.js dark mode; no flicker solution |
| TanStack Query | v5 (latest) | Server state, caching, background refetch | Locked in STATE.md roadmap decisions |
| openapi-typescript | 7.13.0 | Generate TypeScript types from FastAPI OpenAPI spec | Locked in STATE.md roadmap decisions |
| concurrently | ^9.x | Run backend + frontend dev servers together | Claude's discretion — standard for flat monorepos |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tw-animate-css | latest | CSS animations for shadcn/ui components | Replaces `tailwindcss-animate` in Tailwind v4 projects |
| @tanstack/react-query-devtools | v5 | Query cache inspector in dev | Dev-only; wrap with `process.env.NODE_ENV !== 'production'` check |
| lucide-react | latest | Icon library | shadcn/ui default icon set |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| next-themes | CSS media query only | next-themes gives localStorage persistence + manual toggle; pure CSS can't do manual toggle |
| concurrently | Separate terminals (user runs both manually) | Concurrently is simpler DX but adds root package.json complexity — within Claude's discretion |
| openapi-typescript | @hey-api/openapi-ts | hey-api generates full SDK client code; openapi-typescript generates types only — matches locked decision to write thin fetch wrapper |

**Installation (frontend):**
```bash
# Scaffold
npx create-next-app@latest frontend --yes

# Inside frontend/
cd frontend
npx shadcn@latest init

# Add components as needed
npx shadcn@latest add button sheet toaster

# Type generation (devDependency)
npm install -D openapi-typescript

# TanStack Query
npm install @tanstack/react-query @tanstack/react-query-devtools

# Dark mode
npm install next-themes
```

**Installation (root, optional):**
```bash
# Root-level package.json for dev coordination
npm install -D concurrently
```

## Architecture Patterns

### Recommended Project Structure

```
/ (repo root)
├── backend/                    # All existing Python/FastAPI code (moved with git mv)
│   ├── app/
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── poetry.lock
│   └── docker-compose.yml
├── frontend/                   # Next.js 15 App Router
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Root layout — Providers, ThemeProvider, Header, Footer
│   │   │   ├── page.tsx        # Home page (placeholder)
│   │   │   └── globals.css     # Tailwind v4 @import + @theme inline tokens
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui copy-paste components live here
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx  # Navbar with logo, nav links, mobile hamburger
│   │   │   │   ├── Footer.tsx  # Footer
│   │   │   │   └── MobileNav.tsx  # Sheet-based slide-out drawer
│   │   │   └── providers.tsx   # 'use client' QueryClientProvider + ThemeProvider
│   │   ├── lib/
│   │   │   └── api.ts          # Thin fetch wrapper (base URL, auth headers, JSON)
│   │   └── types/
│   │       └── api.generated.ts  # Output of openapi-typescript (gitignored or committed)
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.ts
├── package.json                # Root-level (concurrently dev script only)
└── README.md
```

### Pattern 1: Tailwind v4 CSS-First Configuration
**What:** All theming is done in `globals.css` — no `tailwind.config.js` exists.
**When to use:** Always for new Tailwind v4 projects; shadcn/ui init creates this automatically.
**Example:**
```css
/* Source: https://ui.shadcn.com/docs/tailwind-v4 */
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  /* ... other token mappings */
}

:root {
  --background: hsl(0 0% 100%);
  --foreground: hsl(0 0% 3.9%);
  --primary: hsl(221.2 83.2% 53.3%);
  /* ... rest of light mode tokens */
}

.dark {
  --background: hsl(222.2 84% 4.9%);
  --foreground: hsl(210 40% 98%);
  /* ... rest of dark mode tokens */
}
```

### Pattern 2: TanStack Query Provider (App Router Safe)
**What:** QueryClient must be created per-request on the server and singleton on the client to prevent shared state across SSR requests.
**When to use:** Always when combining TanStack Query with Next.js App Router.
**Example:**
```typescript
// Source: https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr
// frontend/src/components/providers.tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { ThemeProvider } from 'next-themes'

export function Providers({ children }: { children: React.ReactNode }) {
  // useState ensures one client per browser session (not shared across SSR requests)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

### Pattern 3: Root Layout Shell
**What:** Root `layout.tsx` wraps all pages in Providers, Header, and Footer. The `<html>` tag needs `suppressHydrationWarning` for next-themes.
**Example:**
```typescript
// frontend/src/app/layout.tsx
import { Providers } from '@/components/providers'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>
          <div className="relative flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  )
}
```

### Pattern 4: openapi-typescript Type Generation
**What:** CLI fetches the live FastAPI `/openapi.json` endpoint and outputs a TypeScript declaration file.
**When to use:** Run once during setup, re-run when backend schema changes.
**Example:**
```json
// frontend/package.json scripts
{
  "scripts": {
    "generate-types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.generated.ts"
  }
}
```
```bash
# FastAPI must be running first
npm run generate-types
```

### Pattern 5: FastAPI CORSMiddleware
**What:** Add CORSMiddleware before other middleware in the FastAPI app factory. The existing `ALLOWED_ORIGINS` setting in `config.py` already seeds `["http://localhost:3000"]`.
**Critical constraint:** `allow_credentials=True` cannot be combined with `allow_origins=["*"]` — browsers reject this. Must use explicit origin list.
**Example:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/cors/
# backend/app/main.py — add inside create_app()
from fastapi.middleware.cors import CORSMiddleware

application.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().ALLOWED_ORIGINS,  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Pattern 6: git mv Monorepo Restructure
**What:** Use `git mv` to move all backend files into `backend/` subdirectory. Git tracks renames and `git log --follow` preserves history.
**Sequence (execute from repo root):**
```bash
# 1. Create the backend/ subdirectory structure
mkdir -p backend

# 2. Move everything into backend/ using git mv
git mv app backend/app
git mv tests backend/tests
git mv alembic backend/alembic
git mv alembic.ini backend/alembic.ini
git mv pyproject.toml backend/pyproject.toml
git mv poetry.lock backend/poetry.lock
git mv docker-compose.yml backend/docker-compose.yml
git mv scripts backend/scripts   # if exists

# 3. Update path references (see Pitfalls section)
# 4. Commit as a single atomic restructure commit
git commit -m "refactor: restructure repo into monorepo with backend/ directory"
```

### Pattern 7: Thin API Fetch Wrapper
**What:** A minimal wrapper that adds the base URL, auth headers, and handles JSON + error responses. Uses types from `api.generated.ts`.
**Example:**
```typescript
// frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include', // sends cookies for future auth
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail ?? 'API error')
  }

  return res.json() as Promise<T>
}
```

### Anti-Patterns to Avoid
- **`allow_origins=["*"]` with `allow_credentials=True`:** Browsers reject this combination. Must enumerate origins explicitly.
- **Creating new QueryClient outside useState/useRef in a client component:** Causes a new client on every render, destroying the cache. Use `useState(() => new QueryClient(...))`.
- **Importing client components in Server Components without `'use client'`:** Providers component must have `'use client'` directive — it uses `useState` and React Context.
- **Forgetting `suppressHydrationWarning` on `<html>`:** next-themes modifies the html element on the client; without this attribute, React will warn about hydration mismatches.
- **Running `npm run generate-types` without FastAPI running:** The CLI fetches from a live URL — the backend must be up. Add a note in README or make the script check first.
- **Committing `api.generated.ts` to git with stale types:** Either gitignore it (regenerate in CI) or commit it and re-run after every schema change. The locked decision says it "exists and was generated" — commit it but document the regenerate command.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dark mode with system preference | Custom CSS media query + localStorage | `next-themes` | Handles flicker (script injection before hydration), localStorage sync, SSR, manual toggle |
| Type-safe API client | Manual TypeScript interfaces for every endpoint | `openapi-typescript` | FastAPI's openapi.json is the single source of truth; hand-rolled interfaces drift |
| Mobile nav drawer | Custom CSS slide-out | `shadcn/ui Sheet` | Handles focus trapping, keyboard nav, ARIA, and Tailwind v4 styling automatically |
| Toast/error notifications | Custom toast component | `shadcn/ui Toaster + toast()` | Locked decision; handles stacking, positioning, auto-dismiss, accessibility |
| CSS animation utilities | Custom keyframe CSS | `tw-animate-css` | Replaces `tailwindcss-animate` for Tailwind v4; provides shadcn/ui's standard animation tokens |

**Key insight:** The entire UI toolkit exists at the package level — the only custom code should be component composition and application logic.

## Common Pitfalls

### Pitfall 1: Backend Config Paths Break After git mv
**What goes wrong:** `alembic.ini` has `script_location = %(here)s/alembic` and `prepend_sys_path = .` — both use paths relative to the file location. After moving to `backend/`, the paths still resolve correctly relative to `backend/alembic.ini`, so these are fine. However, the `packages` field in `pyproject.toml` (`packages = [{include = "app"}]`) and `testpaths = ["tests"]` in pytest config also resolve relative to the file — these also remain correct after the move because they're relative to `pyproject.toml` (which moves with everything). **The critical check:** any path in CI scripts, Makefile, or `.env` files that hard-codes the old project root structure will break.
**Why it happens:** Flat repo assumes CWD = project root. After move, commands must be run from `backend/` (e.g., `cd backend && poetry run pytest`) or use absolute paths.
**How to avoid:** Update all CI scripts, taskipy tasks, and README commands to prefix with `cd backend &&`. Add a root-level `package.json` with convenience scripts.
**Warning signs:** `ModuleNotFoundError: No module named 'app'` when running tests from repo root.

### Pitfall 2: Poetry Virtual Environment Path After Move
**What goes wrong:** Poetry creates its venv relative to the project root. After the move, `poetry env info` may point to a stale path and `poetry install` must be re-run from `backend/`.
**Why it happens:** Poetry stores venv metadata with the project hash — moving the directory may invalidate it on some systems.
**How to avoid:** After the `git mv` + commit, run `cd backend && poetry install` to re-create the venv from the new location.
**Warning signs:** `poetry run pytest` fails with import errors even though `poetry install` appears to have succeeded.

### Pitfall 3: Tailwind v4 + shadcn/ui Initialization Order Matters
**What goes wrong:** If you run `create-next-app --tailwind` (which creates Tailwind v4 config) and then try to manually layer shadcn/ui by editing globals.css yourself, you may end up with conflicting setups.
**Why it happens:** shadcn/ui init rewrites `globals.css` with its own token setup. Running it after manual edits overwrites your work.
**How to avoid:** Run `npx shadcn@latest init` immediately after `create-next-app` before making any custom CSS changes. Let shadcn/ui own the initial `globals.css` setup.
**Warning signs:** Missing CSS custom property variables (e.g., `--primary`, `--background`) in the browser.

### Pitfall 4: CORSMiddleware Position in FastAPI Middleware Stack
**What goes wrong:** Adding CORSMiddleware after `SessionMiddleware` may cause CORS headers to be missing on preflight (OPTIONS) responses.
**Why it happens:** FastAPI middleware runs in reverse order of registration — last added = first to process. CORS middleware must process the request before session middleware adds overhead.
**How to avoid:** Add `CORSMiddleware` as the LAST `add_middleware` call in `create_app()` so it runs FIRST in the stack.
**Warning signs:** CORS error in browser console on preflight (OPTIONS) requests but not on GET requests.

### Pitfall 5: TanStack Query QueryClient Shared Across SSR Requests
**What goes wrong:** Creating `new QueryClient()` at module level (outside a React component or factory function) causes the same client instance to be shared across all SSR requests, leaking data between users.
**Why it happens:** Module-level variables persist across Node.js requests on the server.
**How to avoid:** Always create the client inside `useState(() => new QueryClient(...))` in the Providers component. This is a client component (`'use client'`), so useState runs only in the browser.
**Warning signs:** Data from one user's session appearing in another's — typically only visible in production with real users.

### Pitfall 6: openapi-typescript Generates `readonly` Properties
**What goes wrong:** The generated types use `readonly` on all object properties, which prevents direct mutation. Code that tries to modify a generated type (e.g., setting a field) gets a TypeScript error.
**Why it happens:** This is intentional — OpenAPI types describe API responses, which should be treated as immutable.
**How to avoid:** When you need a mutable version, map the generated type to a local interface or use `Writable<T>`. Don't fight the generated types.
**Warning signs:** `Cannot assign to 'field' because it is a read-only property` TypeScript errors.

## Code Examples

Verified patterns from official sources:

### Health Check Query (Smoke Test)
```typescript
// Source: TanStack Query v5 docs
// frontend/src/app/page.tsx (temporary smoke test)
'use client'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export default function HomePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<{ status: string; version: string }>('/health'),
  })

  if (isLoading) return <p>Checking backend...</p>
  if (error) return <p className="text-destructive">Backend unreachable: {error.message}</p>
  return <p className="text-green-600">Backend OK — v{data?.version}</p>
}
```

### shadcn/ui Mobile Nav with Sheet
```typescript
// Source: https://ui.shadcn.com/docs/components/sheet
// frontend/src/components/layout/MobileNav.tsx
'use client'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'
import Link from 'next/link'

const navLinks = [
  { href: '/', label: 'Home' },
  { href: '/books', label: 'Books' },
  { href: '/cart', label: 'Cart' },
]

export function MobileNav() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[300px]">
        <nav className="flex flex-col gap-4 pt-8">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-lg font-medium hover:text-primary"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
```

### Dark Mode Toggle
```typescript
// Source: https://github.com/pacocoursey/next-themes
// frontend/src/components/layout/ThemeToggle.tsx
'use client'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const { setTheme, theme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // Avoid hydration mismatch — only render after client mount
  useEffect(() => setMounted(true), [])
  if (!mounted) return null

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  )
}
```

### Root-Level Package.json (Concurrently)
```json
// /package.json (repo root)
{
  "name": "bookstore-monorepo",
  "private": true,
  "scripts": {
    "dev": "concurrently -n backend,frontend -c blue,green \"cd backend && poetry run task dev\" \"cd frontend && npm run dev\"",
    "dev:backend": "cd backend && poetry run task dev",
    "dev:frontend": "cd frontend && npm run dev"
  },
  "devDependencies": {
    "concurrently": "^9.x"
  }
}
```

### NEXT_PUBLIC_API_URL Environment Variable
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```
```typescript
// next.config.ts — no special config needed; NEXT_PUBLIC_* vars are auto-exposed to browser
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tailwind.config.js` | CSS-first `@theme` in `globals.css` | Tailwind v4 (Jan 2025) | No JS config file; all tokens in CSS |
| `tailwindcss-animate` plugin | `tw-animate-css` import | Tailwind v4 | Plugin system changed; use CSS import instead |
| `create-next-app` with manual Tailwind setup | `create-next-app --yes` ships Tailwind v4 + Turbopack | Next.js 15 + Tailwind v4 | Scaffolding handles the full setup |
| `QueryClient` module-level singleton | `useState(() => new QueryClient())` in Providers | TanStack Query v5 + App Router | Prevents SSR data leakage |
| Manual TypeScript interfaces for API | `openapi-typescript` from live server | v7 is current stable | Types always match backend |
| Pages Router + getServerSideProps | App Router + Server Components | Next.js 13+ | This phase uses App Router exclusively |

**Deprecated/outdated:**
- `tailwind.config.js`: Not used in Tailwind v4 projects; shadcn/ui init will not create one
- `tailwindcss-animate`: Replaced by `tw-animate-css` in Tailwind v4
- `npx shadcn-ui` (old CLI name): Use `npx shadcn@latest` (renamed CLI package)
- `getServerSideProps` / `getStaticProps`: Pages Router patterns; not applicable to App Router

## Open Questions

1. **Should `api.generated.ts` be committed to git or gitignored?**
   - What we know: The success criterion says "exists and was generated from the live FastAPI /openapi.json" — implies it must be present but doesn't say committed
   - What's unclear: If gitignored, every developer must run `npm run generate-types` after cloning (backend must be running). If committed, types can drift from actual backend.
   - Recommendation: Commit it in Phase 19 for simplicity. Add a comment header noting it's auto-generated and the regenerate command. Revisit in CI setup.

2. **Does `concurrently` need a root `package.json` npm workspace setup?**
   - What we know: Locked decision says "no shared packages/ directory" and "keep it simple." A root `package.json` without workspaces field is valid.
   - What's unclear: Some tools assume a workspace-aware monorepo.
   - Recommendation: Create a minimal root `package.json` (`private: true`, no workspaces field) with only the `concurrently` devDependency. This keeps things maximally simple.

3. **Does `alembic.ini`'s `prepend_sys_path = .` break after move to `backend/`?**
   - What we know: `%(here)s` resolves to the directory containing `alembic.ini`. After the move, `alembic.ini` is at `backend/alembic.ini`, so `%(here)s` = `backend/`. `prepend_sys_path = .` adds the alembic.ini directory to sys.path — which would be `backend/`, where `app/` lives. This should remain correct.
   - What's unclear: Whether alembic resolves `prepend_sys_path` relative to CWD or relative to `%(here)s`.
   - Recommendation: Verify by running `cd backend && poetry run alembic current` after the restructure. If it fails, explicitly set `prepend_sys_path = %(here)s`.

## Sources

### Primary (HIGH confidence)
- [Next.js official installation docs](https://nextjs.org/docs/app/getting-started/installation) — Node.js 20.9+ requirement, `create-next-app --yes` defaults, App Router structure
- [FastAPI CORS official docs](https://fastapi.tiangolo.com/tutorial/cors/) — CORSMiddleware parameters, credential/wildcard incompatibility
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — CSS-first token setup, tw-animate-css migration
- [shadcn/ui Next.js installation](https://ui.shadcn.com/docs/installation/next) — `npx shadcn@latest init` command, components.json
- [openapi-typescript CLI docs](https://openapi-ts.dev/cli) — CLI usage, URL input, `-o` output flag
- [TanStack Query advanced SSR docs](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr) — QueryClient SSR-safe instantiation
- [next-themes GitHub](https://github.com/pacocoursey/next-themes) — ThemeProvider props, suppressHydrationWarning pattern

### Secondary (MEDIUM confidence)
- [Tailwind CSS Next.js install guide](https://tailwindcss.com/docs/guides/nextjs) — v4 PostCSS setup verified against official docs
- [concurrently npm](https://www.npmjs.com/package/concurrently) — v9.2.1 latest, options verified
- Multiple community guides confirming shadcn/ui + Tailwind v4 + Next.js 15 are stable together as of early 2025

### Tertiary (LOW confidence)
- Community guides on git mv history preservation — consistent advice but git behavior can vary by version; validate with `git log --follow` after the move

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against official npm, GitHub, and official docs; openapi-typescript v7.13.0 confirmed as latest
- Architecture: HIGH — patterns verified against Next.js, TanStack Query, and shadcn/ui official documentation
- Pitfalls: MEDIUM-HIGH — CORS credential constraint is from official FastAPI docs (HIGH); Poetry/alembic path behavior after move is based on known behavior patterns (MEDIUM) and should be validated empirically

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 for Next.js/shadcn/ui (moderately stable); 2026-03-06 for openapi-typescript (fast-moving patch releases don't affect API)
