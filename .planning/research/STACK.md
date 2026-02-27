# Technology Stack

**Project:** BookStore v3.0 — Customer Storefront (Next.js Frontend)
**Researched:** 2026-02-27
**Scope:** NEW frontend additions only. Backend stack (FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, Poetry, fastapi-mail) is unchanged and not re-researched.

---

## What This File Answers

The backend is complete and validated across 18 phases. This file covers only the frontend stack additions and the integration points where frontend meets backend.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js | 15.x (latest 15.x) | Full-stack React framework | SSR for public catalog pages (SEO), App Router for nested layouts (auth/guest shells), built-in middleware for route guards. |
| React | 19.x (bundled with Next.js 15) | UI runtime | Ships with Next.js 15 — no separate install. |
| TypeScript | 5.x | Type safety | Required. openapi-typescript generates TS types from FastAPI OpenAPI spec; without TypeScript the type-safe API client provides zero value. |
| Node.js | 20.x LTS | Runtime | Required by Next.js 15. Use 20 LTS over 22 for stability during active development. |

**Why Next.js 15, not 16:** Next.js 16.1 released December 2025 and is too new for this build cycle. 15.x is the production-stable choice. Next.js 16.x will be available to upgrade to after v3.0 ships if desired.

**Why Next.js over Vite SPA:** Book catalog pages (`/books`, `/books/[id]`) need server-side rendering for search-engine indexing — a Vite SPA renders client-only. App Router provides first-class layout nesting (shared header, route-level auth shells) without a third-party router.

---

### Auth

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| next-auth | 5.0.0-beta.x (latest beta) | Session management, OAuth flow | v5 is App Router-native. v4 (4.24.13 stable) requires `getServerSession` shims for RSC — documented workarounds, not a clean fit. v5's universal `auth()` function works in Server Components, Route Handlers, and middleware without shims. |

**On the "beta" label:** next-auth v5 has been in production use across large projects for 18+ months. The community consensus (including the maintainers) is that it is production-ready. No critical unresolved bugs block this use case. The package is actively maintained for security patches by the Auth.js team (now under the better-auth umbrella). LOW confidence on official "stable" designation; MEDIUM-HIGH confidence on production readiness based on community adoption.

**Critical integration point — custom backend JWT:**
NextAuth.js does NOT replace FastAPI's JWT system. The pattern:

1. `CredentialsProvider` sends email+password to `POST /auth/login` → receives `access_token` + `refresh_token` from FastAPI.
2. `GoogleProvider` sends the OAuth code to `POST /auth/google` → receives same FastAPI-issued tokens.
3. Both tokens stored in NextAuth's encrypted server-side session cookie (never exposed to browser JS).
4. `jwt()` callback checks expiry and calls `POST /auth/refresh` to rotate before the access token expires.
5. `session()` callback exposes only what client components need (user info, access token for API calls).

**Known race condition in v5 refresh:** When multiple browser tabs trigger simultaneous refresh, the `jwt()` callback may receive a stale token. Mitigation: keep FastAPI access tokens short-lived (15 min is already the backend default). Accept occasional 401 → re-login rather than implementing complex distributed locking. Acceptable for v3.0.

---

### API Type Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openapi-typescript | 7.x (7.13.0) | Generate TypeScript types from FastAPI OpenAPI spec | FastAPI exports OpenAPI 3.1 at `/openapi.json`. openapi-typescript v7 supports OpenAPI 3.1 fully. Zero runtime cost — pure type generation only. |
| openapi-fetch | 0.17.x | Type-safe HTTP client using generated types | Companion to openapi-typescript. 6 KB, uses native `fetch`. Provides fully typed `GET`, `POST`, `PUT`, `DELETE`, `PATCH` — request params, body, and response types all inferred from generated schema. Eliminates manual `as` type casts when calling FastAPI endpoints. |

**Workflow:**
```bash
# Add to frontend/package.json scripts:
"generate:api": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.d.ts"
```
Run once at project bootstrap, and again after any FastAPI Pydantic model change. FastAPI server must be running to serve the spec.

**Why not openapi-generator:** openapi-generator produces full SDK boilerplate (classes, interceptors, runtime dependencies). openapi-typescript produces only type definitions — lighter, zero runtime dependency, and composable with any fetch client.

---

### Server State

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| @tanstack/react-query | 5.x (5.90.x) | Async server-state, caching, mutations | Handles cache invalidation for cart/wishlist mutations, background refetch of catalog data, pagination, and loading/error states. Eliminates manual `useEffect`/`useState` data-fetching patterns in Client Components. |
| @tanstack/react-query-devtools | 5.x | Dev-mode cache inspector | devDependency only; displays cache state in browser during development. |

**Integration with App Router:** Server Components fetch data directly with `apiClient` (no TanStack Query). Client Components that need reactivity — cart badge, wishlist toggle, review submit/edit — use `useQuery` and `useMutation`. Use `HydrationBoundary` + `dehydrate` to prefetch on the server and stream hydrated state to the client, avoiding a double-fetch waterfall.

---

### UI Components

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| shadcn/ui | CLI-managed (no version — components are copied into project) | Accessible component library | Components are copied into `src/components/ui/` and fully owned. No versioned peer-dep conflicts. Built on Radix UI primitives (keyboard navigation, ARIA, focus management by default). Ships pre-styled with Tailwind CSS. |
| Tailwind CSS | 4.x | Utility-first CSS | shadcn CLI now defaults to Tailwind v4 for new projects. All shadcn components updated for v4. Tailwind v4 removes `tailwind.config.js` in favor of CSS-first `@theme` directive — simpler setup for a new project. |
| @radix-ui/* | Latest (installed by shadcn CLI per-component) | Headless UI primitives | Do not install manually. The shadcn CLI installs exactly what each component needs. |
| lucide-react | Latest | Icon set | Default icon library for shadcn components. |
| class-variance-authority | Latest (via shadcn) | Component variant styling | Installed by shadcn CLI. |
| clsx + tailwind-merge | Latest (via shadcn) | Class merging utility | Installed as `cn()` in `src/lib/utils.ts` by shadcn CLI. |

**Tailwind v4 note:** v4 uses `@import "tailwindcss"` in `globals.css` and `@theme` blocks for customization — there is no `tailwind.config.ts` file. The `npx shadcn@latest init` command configures this automatically. This is the correct path for a new project starting in 2026.

---

### Form Handling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| react-hook-form | 7.x (7.71.x) | Uncontrolled form management | The default form library for shadcn/ui. Minimal re-renders (uncontrolled inputs vs. controlled). Used for: login, registration, checkout, review create/edit. |
| @hookform/resolvers | Latest | Zod-to-RHF bridge | Connects Zod schemas to react-hook-form via the `zodResolver` option. Supports Zod v4. |
| zod | 4.x (4.1.x) | Schema validation | v4 stable released May 2025. 14x faster string parsing vs v3. Built-in JSON Schema output (no external conversion library needed). Use for: client-side form validation, API response shape assertion, environment variable validation. |

**Why Zod v4 over v3:** v4 is stable, faster, and the current default. No breaking changes that affect this project's usage patterns. `@hookform/resolvers` supports Zod v4 with the identical `zodResolver` import.

---

### Client-Side State

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| zustand | 5.x (5.0.11) | Global client-only state | For UI state that belongs neither in TanStack Query (server data) nor the URL: shopping cart contents before checkout. v5 drops React <18 support and uses native `useSyncExternalStore` — cleaner SSR behavior. |

**Strict scope for Zustand:**
- Auth state → NextAuth `useSession()`
- Server data (catalog, orders, wishlist) → TanStack Query
- Cart contents before checkout → Zustand with `persist` middleware to `localStorage`

**App Router SSR requirement:** Do NOT define the Zustand store as a module-level global. Use `createStore` (vanilla) wrapped in a React context provider. This is required to prevent request bleedover between users during server rendering. The official Zustand docs have a Next.js guide specifically for this.

---

### Development Tooling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ESLint | 9.x | Linting | Ships with `create-next-app`. Uses flat config format (ESLint 9 default). |
| Prettier | 3.x | Formatting | Add `prettier-plugin-tailwindcss` to auto-sort Tailwind utility classes. |

---

## Monorepo Structure

**Approach:** Flat monorepo — no Turborepo, no Nx, no npm/pnpm workspaces. This project has exactly two apps (Python backend, Next.js frontend) in different languages with zero shared code packages. Turborepo's build pipeline caching and task graph offer no benefit at this scale.

```
bookstore/                        # repo root
├── backend/                      # existing FastAPI project (moved from root)
│   ├── app/
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── poetry.lock
│   └── docker-compose.yml
├── frontend/                     # NEW: Next.js 15 customer storefront
│   ├── src/
│   │   ├── app/                  # App Router: pages and layouts
│   │   │   ├── (auth)/           # Route group: login, register (no nav)
│   │   │   ├── (store)/          # Route group: catalog, cart, orders, wishlist
│   │   │   └── layout.tsx        # Root layout with SessionProvider, QueryClientProvider
│   │   ├── components/
│   │   │   ├── ui/               # shadcn components (CLI-managed)
│   │   │   └── [feature]/        # Feature-specific components
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── client.ts     # openapi-fetch client instance
│   │   │   │   └── schema.d.ts   # Generated by openapi-typescript (gitignored or committed)
│   │   │   └── auth/
│   │   │       └── config.ts     # NextAuth configuration (providers, callbacks)
│   │   ├── hooks/                # Custom React hooks (useCart, useWishlist, etc.)
│   │   └── stores/               # Zustand stores (cart.ts)
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   ├── globals.css               # Tailwind v4 entry (@import "tailwindcss", @theme blocks)
│   └── tsconfig.json
├── README.md
└── .env.example                  # Documents both backend and frontend env vars
```

**Backend restructure:** Existing FastAPI files move from repo root into `backend/`. The `docker-compose.yml` moves to `backend/` (or is updated at root to reference `backend/` paths). No Python code changes — only path relocation.

---

## Integration Points

### CORS

FastAPI needs CORS enabled for the Next.js origin. Add to `backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # dev; use env var in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Client

```typescript
// frontend/src/lib/api/client.ts
import createClient from "openapi-fetch";
import type { paths } from "./schema";  // generated by openapi-typescript

export const apiClient = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
});
```

`NEXT_PUBLIC_API_URL` is a build-time variable. In development it defaults to `http://localhost:8000`. In production it points to the deployed FastAPI service URL.

### Auth Token Injection

Pass the FastAPI access token per-request from the NextAuth session. In Server Components:

```typescript
import { auth } from "@/lib/auth/config";

const session = await auth();
const { data, error } = await apiClient.GET("/books/{id}", {
  params: { path: { id: bookId } },
  headers: { Authorization: `Bearer ${session?.accessToken}` },
});
```

In Client Components, access the session via `useSession()` from next-auth/react and thread the token through a custom hook that wraps `apiClient`.

### Dev Proxy (Optional)

Next.js rewrites can proxy API calls to avoid CORS complexity in development:

```typescript
// frontend/next.config.ts
async rewrites() {
  return [
    { source: "/api/v1/:path*", destination: "http://localhost:8000/api/v1/:path*" }
  ];
}
```

This is optional — direct cross-origin calls with CORS configured above work correctly. The proxy approach avoids CORS entirely if preferred.

### GitHub OAuth Exclusion

GitHub OAuth is explicitly out of scope for v3.0 (per PROJECT.md). NextAuth GoogleProvider only. The FastAPI backend has GitHub OAuth; do not wire it up on the frontend in this milestone.

---

## Installation

```bash
# 1. Scaffold Next.js 15 in frontend/
npx create-next-app@15 frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-turbopack    # Turbopack still experimental for some edge cases

cd frontend

# 2. Auth
npm install next-auth@beta

# 3. Server state
npm install @tanstack/react-query
npm install -D @tanstack/react-query-devtools

# 4. API types + client
npm install openapi-fetch
npm install -D openapi-typescript

# 5. Forms + validation
npm install react-hook-form @hookform/resolvers zod

# 6. Client-side state (cart)
npm install zustand

# 7. shadcn/ui init (configures Tailwind v4, installs Radix UI deps, creates globals.css)
npx shadcn@latest init
# Select: New York style, default color, CSS variables: yes

# 8. Add initial shadcn component set
npx shadcn@latest add button input label card badge avatar
npx shadcn@latest add form dialog sheet toast sonner
npx shadcn@latest add skeleton select textarea separator

# 9. Formatter
npm install -D prettier prettier-plugin-tailwindcss

# 10. Generate API types (FastAPI must be running at localhost:8000)
npm run generate:api
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Auth | next-auth v5 beta | next-auth v4 stable | v4 built for Pages Router; App Router integration requires documented shims. v5 is App Router-native. |
| Auth | next-auth v5 | Clerk | External vendor, subscription cost, and requires a custom backend proxy to integrate with the existing FastAPI JWT system. Adds a non-trivial vendor dependency. |
| API Client | openapi-fetch + openapi-typescript | axios + manual TypeScript types | Manual types drift from Pydantic models on every backend change. openapi-typescript regenerates types from the live spec automatically. |
| API Client | openapi-fetch | openapi-generator (full SDK) | openapi-generator produces runtime boilerplate (classes, interceptors). openapi-fetch is 6 KB with zero runtime — just typed `fetch`. |
| Forms | react-hook-form | Formik | react-hook-form is the shadcn/ui default; uses uncontrolled inputs (better performance); smaller bundle. |
| Client State | zustand | Redux Toolkit | RTK is over-engineered for a single cart store. Zustand is ~3 KB vs Redux ~50 KB. RTK's patterns add indirection without benefit at this scope. |
| Client State | zustand | React Context | Context causes full subtree re-renders on any state change. The cart count in the header renders on every page — Context would re-render the entire layout on every add-to-cart. |
| CSS | Tailwind v4 | Tailwind v3 | v4 is now the shadcn CLI default for new projects. v3 works but requires `--legacy-peer-deps` with newer React and adds maintenance overhead. Starting fresh in 2026 — use the current default. |
| Framework | Next.js 15.x | Next.js 16.x | 16.x released December 2025 — too new. 15.x is the LTS-equivalent stable track. |
| Monorepo Tool | None (flat structure) | Turborepo | No shared packages between frontend (TypeScript) and backend (Python). Turborepo's task caching benefits apply to JavaScript monorepos with shared libraries. No benefit here. |

---

## What NOT to Add

| Avoid | Why |
|-------|-----|
| **Stripe or payment SDK** | Mock payment only per PROJECT.md. No real payment gateway in v3.0. |
| **Admin dashboard routes** | Explicitly out of scope for v3.0. Admin UI deferred to v3.1+. |
| **GitHub OAuth (frontend)** | Out of scope per PROJECT.md — email + Google sufficient for v3.0. |
| **WebSocket / SSE** | No real-time features in v3.0. Restock alerts are email-only (backend handles). |
| **i18n (next-intl, react-i18next)** | Single-language bookstore. Not mentioned in requirements. |
| **Storybook** | UI components are shadcn/ui primitives — Storybook overhead not justified for a single-milestone frontend build. |
| **Cypress / Playwright E2E** | Not planned in requirements. Unit + integration tests via Jest/Vitest cover component behavior. Defer E2E until v4.0. |
| **next-auth database adapter** | Sessions stored in encrypted JWT cookie (stateless). No DB adapter needed — FastAPI's DB handles user state. |
| **SWR** | TanStack Query is already chosen. Do not introduce a competing data-fetching layer. |

---

## Sources

- [Next.js 15 release post](https://nextjs.org/blog/next-15) — HIGH confidence
- [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16) — HIGH confidence (confirmed 16.x exists; chose 15.x intentionally)
- [Auth.js v5 migration guide](https://authjs.dev/getting-started/migrating-to-v5) — HIGH confidence
- [Auth.js v5 Next.js reference](https://authjs.dev/reference/nextjs) — HIGH confidence
- [Auth.js refresh token rotation guide](https://authjs.dev/guides/refresh-token-rotation) — HIGH confidence
- [Auth.js v5 production readiness discussion](https://github.com/nextauthjs/next-auth/discussions/9511) — MEDIUM confidence (community assessment)
- [TanStack Query v5 Advanced SSR / Next.js App Router](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr) — HIGH confidence
- [TanStack Query v5 npm](https://www.npmjs.com/package/@tanstack/react-query) (v5.90.21 confirmed current) — HIGH confidence
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — HIGH confidence
- [shadcn/ui Next.js installation](https://ui.shadcn.com/docs/installation/next) — HIGH confidence
- [shadcn/ui React 19 compatibility](https://ui.shadcn.com/docs/react-19) — HIGH confidence
- [openapi-typescript GitHub releases](https://github.com/openapi-ts/openapi-typescript) (v7.13.0 confirmed) — HIGH confidence
- [openapi-fetch docs](https://openapi-ts.dev/openapi-fetch/) (v0.17.x confirmed) — HIGH confidence
- [Zod v4 release notes](https://zod.dev/v4) (stable May 2025, v4.1.x current) — HIGH confidence
- [react-hook-form with shadcn/ui](https://ui.shadcn.com/docs/forms/react-hook-form) — HIGH confidence
- [react-hook-form v7.71.x on npm](https://github.com/react-hook-form/react-hook-form/releases) — HIGH confidence
- [Zustand v5 announcement](https://pmnd.rs/blog/announcing-zustand-v5) (v5.0.11 current) — HIGH confidence
- [Zustand Next.js App Router guide](https://zustand.docs.pmnd.rs/guides/nextjs) — HIGH confidence
- [FastAPI client generation docs](https://fastapi.tiangolo.com/advanced/generate-clients/) — HIGH confidence
- [Next.js rewrites docs](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites) — HIGH confidence

---

*Stack research for: BookStore v3.0 Customer Storefront (Next.js frontend)*
*Researched: 2026-02-27*
