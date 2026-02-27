---
phase: 19-monorepo-frontend-foundation
plan: 02
subsystem: frontend
tags: [nextjs, tailwind, shadcn-ui, tanstack-query, next-themes, openapi-typescript]

# Dependency graph
requires:
  - "19-01: monorepo structure with backend/ and CORSMiddleware"
provides:
  - "frontend/ Next.js 15 app with TypeScript, Tailwind v4, shadcn/ui"
  - "frontend/src/lib/api.ts: apiFetch wrapper and ApiError class"
  - "frontend/src/types/api.generated.ts: TypeScript types from FastAPI OpenAPI spec"
  - "frontend/src/components/providers.tsx: QueryClientProvider + ThemeProvider + Toaster"
  - "frontend/src/app/layout.tsx: root layout with Providers and suppressHydrationWarning"
affects: [20-nextjs-auth, 21-product-catalog, 22-cart-checkout, 23-reviews, 24-admin]

# Tech tracking
tech-stack:
  added:
    - "next@16.1.6 (Next.js 15 App Router)"
    - "react@19.2.3 + react-dom@19.2.3"
    - "tailwindcss@4 with @tailwindcss/postcss"
    - "shadcn@3.8.5 (New York style, CSS variables)"
    - "@tanstack/react-query@5.90.21"
    - "@tanstack/react-query-devtools@5.91.3"
    - "next-themes@0.4.6"
    - "openapi-typescript@7.13.0 (dev)"
    - "sonner@2.0.7, radix-ui@1.4.3, lucide-react@0.575.0"
  patterns:
    - "src/ directory layout for Next.js (app, components, lib, types all under src/)"
    - "shadcn/ui New York style with @theme inline CSS variables in globals.css"
    - "QueryClient created inside useState(() => ...) factory to prevent SSR shared state"
    - "QueryClientProvider wraps ThemeProvider — devtools outside ThemeProvider"
    - "suppressHydrationWarning on <html> for next-themes anti-flicker"
    - "openapi-typescript generates types from live FastAPI /openapi.json endpoint"
    - "apiFetch<T> with credentials: include for future cookie-based auth"
    - "ApiError class extends Error with status and detail fields for TanStack Query"

key-files:
  created:
    - "frontend/ - entire Next.js 15 app scaffold"
    - "frontend/src/lib/api.ts - apiFetch wrapper with ApiError class"
    - "frontend/src/types/api.generated.ts - auto-generated types from FastAPI OpenAPI"
    - "frontend/src/components/providers.tsx - QueryClientProvider + ThemeProvider + Toaster"
    - "frontend/src/components/ui/button.tsx - shadcn/ui Button component"
    - "frontend/src/components/ui/sheet.tsx - shadcn/ui Sheet component (mobile nav)"
    - "frontend/src/components/ui/sonner.tsx - shadcn/ui Sonner toast component"
    - "frontend/src/app/globals.css - Tailwind v4 with shadcn/ui @theme inline tokens"
    - "frontend/.env.local - NEXT_PUBLIC_API_URL=http://localhost:8000 (gitignored)"
  modified:
    - "frontend/src/app/layout.tsx - wraps with <Providers>, suppressHydrationWarning"
    - "frontend/package.json - added generate-types script"
    - "frontend/tsconfig.json - @/* path alias updated to ./src/*"
    - "frontend/components.json - css path updated to src/app/globals.css"

key-decisions:
  - "Restructured Next.js scaffold from flat layout to src/ directory (tsconfig @/* -> ./src/*) to match plan spec and Next.js conventions"
  - "QueryClient created in useState factory pattern to prevent shared state across SSR requests"
  - ".env.local kept gitignored (security) — documented NEXT_PUBLIC_API_URL pattern instead"
  - "openapi-typescript v7 generates types directly from live backend — backend must be running to regenerate"

# Metrics
duration: 10min
completed: 2026-02-27
---

# Phase 19 Plan 02: Next.js 15 Frontend Foundation Summary

**Next.js 15 frontend scaffolded with Tailwind v4 + shadcn/ui (New York style), TanStack Query v5 + next-themes providers, auto-generated TypeScript types from FastAPI OpenAPI spec, and thin apiFetch wrapper with typed ApiError class**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-27T10:25:23Z
- **Completed:** 2026-02-27T10:35:06Z
- **Tasks:** 2
- **Files modified:** 8 created + 4 modified

## Accomplishments

- Scaffolded Next.js 15 (v16.1.6) app via `create-next-app@latest` with TypeScript, Tailwind v4, App Router; restructured to `src/` layout (tsconfig @/* -> ./src/*) to match plan spec
- Initialized shadcn/ui (New York style, CSS variables): `globals.css` now has `@import "tailwindcss"`, `@theme inline`, and full light/dark CSS custom properties
- Added shadcn/ui components: Button, Sheet (mobile nav), Sonner (toast) to `src/components/ui/`
- Installed TanStack Query v5 + devtools, next-themes, openapi-typescript v7
- Generated `src/types/api.generated.ts` from live FastAPI `/openapi.json` (255ms, full bookstore API types)
- Created `src/lib/api.ts`: `apiFetch<T>` with `ApiError` class, `credentials: include`, 204 No Content handling
- Created `src/components/providers.tsx`: `QueryClientProvider` (useState factory pattern) + `ThemeProvider` (system default) + `Toaster` + `ReactQueryDevtools`
- Updated `src/app/layout.tsx`: Providers wrapper, `suppressHydrationWarning` on `<html>`, Bookstore metadata
- TypeScript compiles with zero errors; production build succeeds

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js 15 app with shadcn/ui and dependencies** - `7c06e79` (chore)
2. **Task 2: Create API fetch wrapper, generate types, and configure providers** - `f3dd206` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

### Created
- `frontend/src/lib/api.ts` - apiFetch<T> wrapper, ApiError class, NEXT_PUBLIC_API_URL base
- `frontend/src/types/api.generated.ts` - TypeScript types from FastAPI OpenAPI spec
- `frontend/src/components/providers.tsx` - QueryClientProvider + ThemeProvider + Toaster + ReactQueryDevtools
- `frontend/src/components/ui/button.tsx` - shadcn/ui Button
- `frontend/src/components/ui/sheet.tsx` - shadcn/ui Sheet (mobile nav drawer)
- `frontend/src/components/ui/sonner.tsx` - shadcn/ui Sonner toast
- `frontend/src/app/globals.css` - Tailwind v4 + shadcn/ui @theme inline tokens
- `frontend/.env.local` - NEXT_PUBLIC_API_URL=http://localhost:8000 (gitignored, not committed)

### Modified
- `frontend/src/app/layout.tsx` - Providers wrapper, suppressHydrationWarning, Bookstore metadata
- `frontend/package.json` - Added generate-types script (openapi-typescript)
- `frontend/tsconfig.json` - @/* path alias -> ./src/*
- `frontend/components.json` - css path -> src/app/globals.css

## Decisions Made

- Next.js 16 `create-next-app --yes` defaulted to flat layout (no `src/`); manually restructured to `src/` by moving `app/`, `components/`, `lib/` into `src/` and updating `tsconfig.json` + `components.json` path references
- `QueryClient` created inside `useState(() => new QueryClient(...))` factory — prevents shared state across SSR requests (per plan's Pitfall 5)
- `.env.local` correctly remains gitignored (security best practice); plan's suggestion to commit it was not followed — `NEXT_PUBLIC_API_URL` documented in SUMMARY instead
- `openapi-typescript` v7 output format differs slightly from v6 — uses `paths`, `components`, `operations` interfaces matching the OpenAPI 3.x structure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] npx shadcn cache corruption on first run**
- **Found during:** Task 1 (shadcn/ui init)
- **Issue:** `ECOMPROMISED` lock error then `ERR_MODULE_NOT_FOUND` for diff package in npx cache directory `d66c5096c7023bfb`
- **Fix:** Ran `npm cache clean --force` then deleted the corrupt npx cache directory `~/.npm-cache/_npx/d66c5096c7023bfb/`; second run succeeded
- **Files modified:** None (infrastructure fix only)

**2. [Rule 3 - Blocking] Next.js 16 scaffold does not create src/ directory by default**
- **Found during:** Task 1 (after scaffold)
- **Issue:** `create-next-app@latest --yes` in Next.js 16 created `frontend/app/`, `frontend/components/`, `frontend/lib/` without `src/` prefix, despite the plan specifying `src/` paths throughout
- **Fix:** Moved all directories into `src/` (`mv app/* src/app/`, `mv components/ui/* src/components/ui/`, `mv lib/utils.ts src/lib/`); updated `tsconfig.json` (`@/*` -> `./src/*`) and `components.json` (css path -> `src/app/globals.css`)
- **Files modified:** `tsconfig.json`, `components.json`

**3. [Rule 2 - Security] .env.local not committed**
- **Found during:** Task 2 (git add)
- **Issue:** `.env.local` is in `.gitignore` (correct security behavior); plan's note to "commit this file" for `api.generated.ts` was about the generated types file, not `.env.local`
- **Fix:** Staged all files except `.env.local`; file exists locally for dev but is correctly excluded from git
- **Files modified:** None

## User Setup Required

- To regenerate API types when backend schema changes: ensure backend is running (`cd backend && poetry run task dev`), then run `cd frontend && npm run generate-types`
- `.env.local` is gitignored — if setting up fresh clone, create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`

## Next Phase Readiness

- Next.js 15 app at `frontend/` — Plan 19-03 can add header/footer layout shell and dark mode toggle
- All providers configured — TanStack Query and next-themes work at root layout level
- `apiFetch` ready for all future API calls with proper error typing
- `api.generated.ts` types available for all FastAPI endpoints

---
*Phase: 19-monorepo-frontend-foundation*
*Completed: 2026-02-27*
