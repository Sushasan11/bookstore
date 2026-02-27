# Project Research Summary

**Project:** BookStore v3.0 — Next.js 15 Customer Storefront
**Domain:** E-commerce storefront frontend integration with existing FastAPI backend
**Researched:** 2026-02-27
**Confidence:** HIGH

## Executive Summary

BookStore v3.0 adds a Next.js 15 customer-facing storefront to a fully built FastAPI backend (v2.1, 13,743 LOC, 18 phases, 306 passing tests). This is an integration project, not a greenfield build. The backend already provides every required API endpoint — catalog with FTS, JWT auth (email + Google OAuth), cart, checkout (mock payment), orders, wishlist, pre-booking, reviews, and email notifications. The frontend's job is to expose all of this to customers through a polished, SEO-optimized interface. The recommended approach: Next.js 15 App Router with Server Components for public catalog pages (SEO), Client Components + TanStack Query for interactive features (cart, checkout, wishlist, reviews), and NextAuth.js v5 as a JWT bridge between the browser session and FastAPI's token system.

The build order is dictated by hard dependencies: monorepo restructure and frontend foundation must come first (CORS, type generation, layout shell), auth integration second (nothing else works without tokens in the session), then catalog and search (public pages with highest SEO value), then cart and checkout (core transaction flow), then orders and account, then wishlist and pre-booking, and finally reviews. Google OAuth is the highest-complexity single task because it requires a two-step token exchange (Google id_token — FastAPI JWT) that most tutorials do not document. The custom backend JWT handoff in NextAuth.js callbacks is the most critical integration point; if it is wrong, every authenticated endpoint returns 401.

The primary risks are concentrated in two areas: authentication plumbing (5 distinct pitfalls documented) and the monorepo restructure (3 pitfalls). Auth risks — CORS misconfiguration, NextAuth session not carrying the FastAPI token, refresh token race conditions with single-use opaque tokens, deactivated user sessions persisting, and Google token not being exchanged for a FastAPI token — all have clear prevention strategies documented in PITFALLS.md. The monorepo restructure risk is mitigated by doing the move in a single commit that updates all path references simultaneously. A critical security note: Next.js < 15.2.3 has a CVE-2025-29927 middleware bypass; the project must use >= 15.2.3.

---

## Key Findings

### Recommended Stack

The frontend stack is entirely new; the FastAPI/PostgreSQL/SQLAlchemy 2.0/Alembic backend is unchanged. Next.js 15.x (not 16.x — too new) with the App Router is the correct choice because public catalog and book detail pages require SSR for SEO, and App Router provides first-class layout nesting without a third-party router. TypeScript 5.x is required because the type-safe API client (openapi-fetch + openapi-typescript) provides zero value without it. All UI is built on shadcn/ui with Tailwind CSS v4, which is now the shadcn CLI default and eliminates the `tailwind.config.ts` file in favor of a CSS-first `@theme` directive.

The data layer splits cleanly: TanStack Query v5 handles server state (all FastAPI API calls, caching, mutations, optimistic updates) for Client Components; Server Components fetch directly using `apiClient` with no TanStack Query involved. Zustand v5 handles the one piece of client-only state that fits neither pattern — the shopping cart display before checkout (though the backend is the true source of truth). react-hook-form + Zod v4 handles all forms. The flat monorepo structure (no Turborepo, no workspaces) is correct for exactly two apps in different languages with zero shared packages.

**Core technologies:**
- **Next.js 15.x:** App Router SSR/RSC for SEO-critical catalog pages; built-in middleware for auth route guards
- **TypeScript 5.x:** Required for openapi-typescript type-safe API client; catches API contract drift at compile time
- **next-auth 5.0.0-beta.x:** App Router-native session management; JWT bridge to FastAPI's token system; production-ready despite beta label (18+ months community adoption)
- **openapi-typescript 7.x + openapi-fetch 0.17.x:** Auto-generated TypeScript types from FastAPI's `/openapi.json`; zero runtime cost; eliminates manual type maintenance
- **TanStack Query 5.x:** Server state caching, mutations, and optimistic updates for all Client Components; HydrationBoundary for server-prefetched data
- **shadcn/ui + Tailwind CSS 4.x:** Component library with Tailwind v4 CSS-first config; Radix UI primitives for accessibility
- **react-hook-form 7.x + Zod 4.x:** Form management and validation; Zod v4 is stable and 14x faster than v3
- **Zustand 5.x:** Cart display state only; must use context-provider pattern (not module-level global) for SSR safety
- **Node.js 20 LTS:** Required by Next.js 15; prefer 20 over 22 for stability

### Expected Features

The full feature set is determined by the existing backend API coverage — every endpoint that exists should be surfaced to the customer. The key distinction is between table stakes (a broken or untrustworthy storefront without them) and differentiators (features that elevate the experience).

**Must have (table stakes):**
- Catalog browsing with paginated book grid (cover, title, author, price, stock status) — RSC + ISR
- Book detail page with average rating, review count, stock status, description — RSC + ISR + generateMetadata()
- Full-text search with genre/price filters — URL-persisted state (bookmarkable, back-button safe)
- Email + password authentication — sign up, sign in, sign out, protected route redirects
- Google OAuth login — custom NextAuth + FastAPI token exchange handoff
- Shopping cart (add, update quantity, remove) — server as source of truth, optimistic updates
- Checkout flow — single-page, mock payment, "Place Order" button, POST to /orders/checkout
- Order history and order detail pages — auth-gated RSC pages
- Authentication-gated routes — Next.js middleware + auth() validation in Server Components
- Responsive mobile-first layout — Tailwind breakpoints, shadcn components
- Loading skeletons and error boundaries — loading.tsx and error.tsx per route segment

**Should have (differentiators):**
- Wishlist with optimistic toggle — heart icon on card and detail page, dedicated wishlist page
- Pre-booking for out-of-stock books — "Pre-book" replaces "Add to Cart" when stock == 0
- Verified-purchase reviews with star ratings — read display on book detail, write/edit/delete after purchase
- Book detail SEO with JSON-LD Book schema — Open Graph + structured data for rich search results
- URL-persisted search/filter state — shareable, bookmarkable search URLs
- Optimistic cart updates — instant UI feedback with rollback on server error
- Order confirmation page — dedicated post-checkout confirmation, not just redirect to order history
- Account page — active pre-bookings with cancel action, links to orders and wishlist

**Defer (v3.x / v4+):**
- Admin dashboard UI — explicitly deferred to v3.1+ in PROJECT.md; separate layouts, access control, components
- GitHub OAuth on frontend — PROJECT.md defers; email + Google covers the majority of users
- Review helpfulness voting — needs sufficient review volume before ranking is meaningful
- Real payment gateway (Stripe) — adds PCI scope; separate milestone
- Recommendation engine — requires transaction history data
- Real-time stock notifications (WebSocket) — backend is email-only for restock

**Anti-features to explicitly avoid:**
- Infinite scroll on catalog pages — use pagination; infinite scroll breaks bookmarking, back-navigation, and comparison browsing
- Client-only localStorage cart — server is the source of truth; TanStack Query caches for responsiveness
- Forced registration before cart — show a non-intrusive "Sign in to save your cart" prompt; do not hard-block cart viewing
- Real-time stock polling — show stock status on page load; no continuous polling
- Intrusive popups — no email capture popups, exit-intent modals, or newsletter overlays

### Architecture Approach

The architecture is a direct API consumer: Next.js frontend calls FastAPI REST endpoints directly (no BFF proxy layer), with CORS enabled on the backend for the Next.js origin. NextAuth.js v5 acts exclusively as a JWT bridge — it does not own the user database, does not have a database adapter, and does not issue its own tokens. FastAPI is the auth authority. The session cookie stores FastAPI-issued access and refresh tokens, encrypted by NextAuth's `NEXTAUTH_SECRET`. All API calls from both Server Components and Client Components attach the FastAPI access token as `Authorization: Bearer <token>`. Only two backend changes are required to support the frontend: CORS middleware (explicit origins, not wildcard) and a Google `id_token` exchange endpoint at `/auth/google/callback`.

The rendering strategy divides cleanly by page type: public catalog and book detail pages are Server Components with ISR (60s revalidate) for SEO and caching; interactive user-specific pages (cart, checkout, wishlist, reviews) are Client Components; auth-gated read pages (orders, account) prefer RSC with dynamic rendering to minimize client bundle. The "push interactivity to the leaves" rule must be applied consistently — page-level files must not acquire `"use client"`, or server-rendered data fetching moves to the client and SEO value is lost.

**Major components:**
1. **Next.js App Router pages** — route structure, layouts, RSC data fetching; two route groups: `(auth)` for login/register, `(store)` for catalog, cart, orders, wishlist
2. **NextAuth.js v5 config** — Credentials provider + Google provider; `jwt` callback stores FastAPI tokens; `session` callback exposes them to client; `jwt` callback handles token refresh with a 60s expiry buffer
3. **openapi-fetch API client** — typed HTTP client using generated schema; single client instance in `src/lib/api/client.ts`; types regenerated from `/openapi.json` after any backend Pydantic model change
4. **TanStack Query layer** — `QueryClientProvider` at root layout; `HydrationBoundary` + `prefetchQuery` pattern for server-prefetched data; `useMutation` + `invalidateQueries` for writes; explicit `staleTime` on all queries to prevent double-fetch
5. **Zustand cart store** — `createStore` wrapped in React context (not module-level global) to prevent SSR request bleedover; `persist` middleware to `localStorage` for cart count display
6. **shadcn/ui component layer** — components copied into `src/components/ui/`; fully owned, no version conflicts; Tailwind v4 CSS-first config in `globals.css`

**Key architectural decisions:**
- No BFF proxy — FastAPI is already a well-designed API; proxying doubles the surface area without benefit
- No database adapter for NextAuth — sessions are stateless encrypted JWT cookies; FastAPI's DB owns user state
- openapi-typescript v7 over manual types — auto-generation from live spec; stale type CI check enforced
- next-auth v5 beta over v4 stable — v4 requires App Router shims; v5 is App Router-native
- Flat monorepo over Turborepo — no shared JS packages between Python backend and TS frontend; Turborepo adds complexity without benefit

### Critical Pitfalls

1. **CORS wildcard + credentials breaks all auth** — `allow_origins=["*"]` with `allow_credentials=True` is rejected by every browser; use explicit origin list from environment variables; server logs show 200 OK while browser blocks every credentialed request (deceptive failure mode)

2. **NextAuth session does not carry FastAPI access token by default** — `authorize()` return value is not automatically available via `useSession()`; must explicitly map `accessToken` and `refreshToken` through both the `jwt` callback (into the cookie) and the `session` callback (onto the session object); without this, every FastAPI call sends `Authorization: Bearer undefined`

3. **Google OAuth sends Google token to FastAPI instead of FastAPI token** — NextAuth Google provider receives a Google `access_token`, not a FastAPI JWT; must exchange the Google `id_token` for a FastAPI JWT via `/auth/google/callback` in the `jwt` callback; store the FastAPI token, never the Google token; two separate OAuth systems that do not auto-connect

4. **Refresh token race condition with single-use opaque tokens** — multiple browser tabs can simultaneously trigger refresh when the access token expires; FastAPI's family-based theft detection treats the second refresh (using the now-revoked token) as a stolen token and revokes the entire family, logging the user out; mitigation: add a 60s buffer before expiry in the `jwt` callback so refresh is triggered only once per expiry window

5. **Deactivated users retain valid NextAuth session** — NextAuth middleware only checks session cookie validity, not FastAPI `is_active` status; deactivated users can navigate protected pages until their session expires; mitigation: handle 401 from any FastAPI API call by calling `signOut()` — treat FastAPI 401 as a session invalidation signal

6. **API type drift after FastAPI schema changes** — `openapi-typescript` generates types once; after any Pydantic model change, types go stale; TypeScript continues to compile (stale types still satisfy the compiler) but runtime breaks silently; mitigation: enforce `npm run generate-types && git diff --exit-code src/types/api.generated.ts` in CI

7. **Monorepo restructure breaks backend CI** — moving FastAPI from root to `backend/` breaks all path references in CI workflows, docker-compose, alembic.ini, and pytest config; mitigation: move all files and update all config references in a single commit; verify all 306 backend tests pass before adding any frontend CI

8. **Server/Client component boundary — `"use client"` at page level loses SSR** — adding a hook to a catalog page file forces `"use client"` on the page itself, moving data fetching to the client and losing SEO value; mitigation: extract all interactive elements to focused leaf Client Components; pages stay as Server Components

---

## Implications for Roadmap

Based on combined research, the build order is dictated by hard dependency chains. Auth is the gateway to every authenticated feature. The catalog is the entry point to everything else. The dependency graph from FEATURES.md maps directly to a 7-phase frontend build.

### Phase 19: Monorepo Restructure + Frontend Foundation

**Rationale:** Everything else depends on this. The repo structure, CORS configuration, API type generation, and TanStack Query provider must exist before any feature work can begin. Backend CI must continue to pass after the restructure — verify before proceeding.

**Delivers:** Working monorepo with `backend/` and `frontend/` directories; Next.js 15 app scaffolded with TypeScript, shadcn/ui, Tailwind v4, TanStack Query provider, and root layout shell; CORS enabled on FastAPI backend; openapi-typescript types generated from `/openapi.json`; CI configured for both workspaces with separate environment variable sets.

**Addresses features from FEATURES.md:** Foundation checklist (monorepo restructure, Next.js scaffold, openapi-typescript, TanStack Query provider, layout shell)

**Avoids pitfalls from PITFALLS.md:**
- CORS: explicit origin list, not wildcard (Pitfall 1)
- openapi-typescript v7 to avoid Pydantic v2 `never` type generation (Pitfall 6)
- Monorepo path references updated in one commit; backend CI verified before proceeding (Pitfall 12)
- Separate `backend/.env` and `frontend/.env.local`; CI uses secrets, not file loading (Pitfall 16)
- `NEXT_PUBLIC_` naming discipline established from day one — secrets never get the prefix (Pitfall 10)
- `await cookies()` / `await headers()` patterns established for Next.js 15 (Pitfall 11)

### Phase 20: Auth Integration

**Rationale:** The single largest integration complexity in the project. Every authenticated feature (cart, orders, wishlist, reviews, pre-booking) requires the auth plumbing to be correct. The Google OAuth token exchange (NextAuth → FastAPI) is the hardest single task; doing it early prevents rework. Middleware-based route guards depend on a working NextAuth session.

**Delivers:** NextAuth.js v5 with Credentials provider (email + password → FastAPI `/auth/login`), Google OAuth provider (Google id_token → FastAPI `/auth/google/callback`), JWT session storing FastAPI access and refresh tokens, token refresh with 60s expiry buffer, middleware route guards, login/signup/logout pages, 401-triggered signOut handler.

**Addresses features from FEATURES.md:** All auth flows (sign up, sign in, Google OAuth, sign out, protected route redirect with callbackUrl)

**Avoids pitfalls from PITFALLS.md:**
- Explicit `jwt` and `session` callback token mapping (Pitfall 2)
- Google `id_token` exchange for FastAPI JWT (Pitfall 13)
- 60s buffer before refresh + RefreshAccessTokenError handling (Pitfall 4)
- FastAPI 401 triggers `signOut()` to handle `is_active` lockout (Pitfall 3)

**Research flag:** NEEDS RESEARCH — the Google OAuth token exchange between NextAuth and a custom FastAPI backend is not a standard documented pattern; implement in a focused sub-task with explicit code review against the prevention examples in PITFALLS.md.

### Phase 21: Catalog and Search

**Rationale:** The highest-SEO-value pages. Book catalog and detail pages must be Server Components with ISR to be indexed by search engines. This phase establishes the rendering pattern (RSC + HydrationBoundary + Client leaf components) that all subsequent pages follow. URL-persisted search state enables bookmarkable/shareable search URLs.

**Delivers:** Home/catalog page (paginated book grid, RSC + ISR), book detail page (generateMetadata, JSON-LD Book schema, avg rating, stock status, Open Graph), search page with genre/price filters (URL-persisted via useSearchParams), pagination, loading skeletons, error boundaries.

**Addresses features from FEATURES.md:** Catalog browse, book detail, full-text search with filters, SEO differentiator, URL-persisted filter state

**Avoids pitfalls from PITFALLS.md:**
- No `"use client"` on page files; interactive elements extracted to leaf Client Components (Pitfall 7)
- HydrationBoundary + prefetchQuery pattern for server-prefetched catalog data (Pitfall 9)
- ThemeProvider setup with `suppressHydrationWarning` on `<html>` and `mounted` guard (Pitfall 8)

**Research flag:** Standard patterns — App Router RSC patterns and TanStack Query advanced SSR are thoroughly documented in official docs and the Vercel Commerce reference implementation. No additional research needed.

### Phase 22: Cart and Checkout

**Rationale:** The core transaction flow. Cart must be built before checkout (checkout consumes cart state). Cart operations demonstrate the full optimistic update pattern (useMutation + onMutate + onError rollback + onSettled invalidation) that wishlist operations will reuse. The cart count badge in the navbar must update reactively — establishing the shared query cache pattern.

**Delivers:** Add to cart from catalog and detail page, cart page (view items, update quantity, remove, cart total), checkout page (order summary, "Place Order" button), order confirmation page (order ID, items, total), cart count badge in navbar with reactive updates, optimistic quantity updates with toast rollback.

**Addresses features from FEATURES.md:** Full cart management, checkout flow, order confirmation page, optimistic cart updates

**Avoids pitfalls from PITFALLS.md:**
- `invalidateQueries({ queryKey: ["cart"] })` in `onSettled` of every cart mutation (Pitfall 14)
- Checkout initiation can be Server Action; any payment callback logic must be a Route Handler, not a Server Action (Pitfall 15)

**Research flag:** Standard patterns — TanStack Query optimistic update pattern is well-documented. No additional research needed.

### Phase 23: Orders and Account

**Rationale:** Order history is a trust-building feature and unlocks the review eligibility check (backend enforces verified purchase; frontend checks order history to decide whether to show the review form). Account page centralizes user navigation and is required for pre-booking cancellation. Both are auth-gated RSC pages with low interactivity.

**Delivers:** Order history list page (date, total, items summary, paginated), individual order detail page (full item list, price snapshots, status), account page (active pre-bookings section, links to order history and wishlist).

**Addresses features from FEATURES.md:** Order history, order detail, account page, links between sections

**Avoids pitfalls from PITFALLS.md:**
- These are auth-gated RSC pages — no `"use client"` at page level; TanStack Query used only for mutations (Pitfall 7)

**Research flag:** Standard patterns — auth-gated RSC pages with dynamic rendering are straightforward. No additional research needed.

### Phase 24: Wishlist and Pre-booking

**Rationale:** Wishlist and pre-booking are tightly related — the wishlist page surfaces "Out of Stock — Pre-book now" CTAs for wishlisted books that are unavailable. The optimistic toggle pattern (wishlist heart icon) is identical to the cart add pattern from Phase 22; implementation is straightforward given the established mutation + invalidation pattern.

**Delivers:** Wishlist toggle (optimistic) from book card and detail page, dedicated wishlist page with "Add to Cart" and remove actions, pre-book button on out-of-stock book detail pages, pre-booking cancellation from account page, active pre-bookings list, "You'll receive an email when back in stock" confirmation message.

**Addresses features from FEATURES.md:** Full wishlist management, pre-booking flow, out-of-stock → pre-book CTA, pre-booking cancellation

**Avoids pitfalls from PITFALLS.md:**
- Stock status (`stock_quantity == 0`) should use a short staleTime (60s) — revalidate on cart operations so pre-book/add-to-cart button stays current (noted in FEATURES.md dependency notes)

**Research flag:** Standard patterns — same mutation + optimistic update patterns as cart. No additional research needed.

### Phase 25: Reviews

**Rationale:** Reviews are last because they depend on the full auth + order history infrastructure (verified purchase check requires order data) and the book detail page (read-only review list is displayed there). The interactive star selector requires a custom component (shadcn does not ship a native star rating component). Review write/edit/delete are the most complex client-side interactions in the project.

**Delivers:** Read-only reviews section on book detail page (star display, reviewer name, rating, text, date), write review form (visible only after purchase verification), interactive 1–5 star selector (custom component), edit own review (in-place, pre-populated), delete own review (confirmation dialog), 409 handling ("You've already reviewed this — edit your existing review").

**Addresses features from FEATURES.md:** All review CRUD features, verified-purchase gate UI, star display

**Avoids pitfalls from PITFALLS.md:**
- Review write form should only render after confirming purchase eligibility via `GET /orders?book_id={id}` — avoid showing a form that will always 403 (noted in FEATURES.md dependency notes)

**Research flag:** Needs attention — the star rating selector requires a custom component since shadcn/ui does not ship one natively. Research community extensions or plan a small custom implementation before this phase starts.

### Phase Ordering Rationale

- **Foundation before auth:** CORS must be correct before any browser-based auth test can succeed; type generation must exist before any API calls can be written type-safely.
- **Auth before everything authenticated:** Cart, orders, wishlist, reviews, and pre-booking all require a working session with FastAPI tokens. Auth is the critical path.
- **Catalog before cart:** The catalog is the entry point for adding items to the cart; establishing the RSC + ISR rendering pattern in the catalog phase avoids retrofit work.
- **Cart before orders:** Checkout creates orders; order confirmation is the post-checkout landing page. The cart phase delivers the full transaction loop before orders/account builds on top of it.
- **Orders before reviews:** Review write eligibility requires order history; building orders first avoids rework in the reviews phase.
- **Wishlist + pre-booking together:** These features are tightly coupled at the UI level (wishlist surfaces pre-book CTAs for out-of-stock items); co-implementing them avoids a partial wishlist page in an intermediate state.
- **Reviews last:** Maximum dependency on prior phases; the custom star selector is the only genuinely novel UI component in the project.

### Research Flags

Phases needing deeper research during planning:
- **Phase 20 (Auth):** Google OAuth token exchange with custom FastAPI backend is not widely documented; plan a dedicated sub-task using the code patterns in PITFALLS.md as the implementation spec; review the NextAuth.js GitHub discussions linked in PITFALLS.md sources before coding.
- **Phase 25 (Reviews):** Star rating selector component is not in shadcn/ui; evaluate community extensions vs. a small custom component before the phase begins.

Phases with standard patterns (skip `/gsd:research-phase`):
- **Phase 19 (Foundation):** Next.js scaffold + CORS + openapi-typescript setup is thoroughly documented in official docs and STACK.md.
- **Phase 21 (Catalog):** RSC + ISR + HydrationBoundary patterns have official Next.js docs and the Vercel Commerce reference implementation.
- **Phase 22 (Cart):** TanStack Query mutation + optimistic update pattern is fully documented with examples.
- **Phase 23 (Orders/Account):** Auth-gated RSC pages with dynamic rendering are straightforward Next.js patterns.
- **Phase 24 (Wishlist/Pre-booking):** Same mutation patterns as cart; no novel patterns required.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against official docs, npm, and release notes as of 2026-02-27; Next.js 15.x stability confirmed; next-auth v5 production readiness assessed via community adoption (18+ months); Tailwind v4 confirmed as shadcn CLI default |
| Features | HIGH (table stakes), MEDIUM (rendering strategy specifics) | Table stakes verified against Amazon, Barnes & Noble, Goodreads, and Baymard Institute UX research; rendering strategy recommendations are from official Next.js docs and Vercel Commerce reference; conversion rate claims from vendor sources are LOW confidence and not relied upon |
| Architecture | HIGH | Architecture derives directly from official Next.js App Router docs, NextAuth.js v5 docs, TanStack Query advanced SSR guide, and direct codebase inspection of the existing FastAPI backend; two-system OAuth flow verified against NextAuth GitHub discussions |
| Pitfalls | HIGH | 16 pitfalls documented; all critical pitfalls verified against official docs or confirmed GitHub issues; CORS + credentials incompatibility is official FastAPI CORS docs; NextAuth token threading is NextAuth.js callback documentation; `cookies()` async requirement is Next.js 15 official migration docs; Google token exchange race is a confirmed GitHub discussion |

**Overall confidence:** HIGH

### Gaps to Address

- **next-auth v5 beta stability:** The "beta" label is a documentation lag, not a quality signal — but if next-auth releases a stable v5.x between research and implementation, upgrade immediately and recheck breaking changes. Monitor the Auth.js GitHub for releases.
- **Star rating component for reviews:** No decision made on community extension vs. custom implementation. This must be resolved before Phase 25 begins. A 5-star interactive selector is approximately 30–50 lines of custom React if built from scratch, which is acceptable scope for a single component.
- **`POST /auth/google/callback` backend endpoint:** ARCHITECTURE.md confirms this endpoint must be added to the FastAPI backend as one of only two backend changes. Verify the endpoint exists or plan its creation as the first task of Phase 20, before any frontend auth work.
- **ISR revalidation TTL for book detail pages:** 60s revalidate is recommended for catalog and book detail pages. Stock status changes after a checkout event — if a book sells out mid-ISR window, the "Add to Cart" button may display for up to 60s after the book goes out of stock. For v3.0 this is an acceptable trade-off; revisit before launch.
- **`generateStaticParams` for book detail pages:** Skipping static generation is acceptable in early phases (every book detail page will be SSR on first request), but should be revisited before production launch for catalog performance and CDN caching.

---

## Sources

### Primary (HIGH confidence)

- [Next.js 15 release post](https://nextjs.org/blog/next-15) — version choice and App Router stability
- [Auth.js v5 migration guide](https://authjs.dev/getting-started/migrating-to-v5) — NextAuth.js v5 App Router-native integration
- [Auth.js refresh token rotation guide](https://authjs.dev/guides/refresh-token-rotation) — official JWT callback + refresh pattern
- [TanStack Query v5 Advanced SSR / Next.js App Router](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr) — HydrationBoundary + prefetchQuery + dehydrate pattern
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — CSS-first Tailwind v4 config; shadcn CLI defaults
- [shadcn/ui Next.js installation](https://ui.shadcn.com/docs/installation/next) — exact install sequence
- [openapi-typescript GitHub](https://github.com/openapi-ts/openapi-typescript) — v7.13.0 confirmed; Pydantic v2 anyOf support
- [openapi-fetch docs](https://openapi-ts.dev/openapi-fetch/) — typed HTTP client companion
- [Zod v4 release notes](https://zod.dev/v4) — stable May 2025; hookform/resolvers support
- [Zustand Next.js App Router guide](https://zustand.docs.pmnd.rs/guides/nextjs) — context-provider pattern for SSR safety
- [FastAPI CORS Tutorial](https://fastapi.tiangolo.com/tutorial/cors/) — wildcard + credentials incompatibility documented officially
- [Next.js Dynamic APIs are Asynchronous](https://nextjs.org/docs/messages/sync-dynamic-apis) — `await cookies()` requirement in Next.js 15
- [Next.js Common App Router Mistakes (Vercel blog)](https://vercel.com/blog/common-mistakes-with-the-next-js-app-router-and-how-to-fix-them) — server/client boundary and `"use client"` overuse
- [TanStack Query Advanced Server Rendering](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr) — HydrationBoundary double-fetch prevention
- [Vercel Next.js Commerce (GitHub)](https://github.com/vercel/commerce) — official reference implementation for headless storefront with App Router
- [Baymard Institute — Product Page UX Best Practices 2025](https://baymard.com/blog/current-state-ecommerce-product-page-ux) — catalog UX decisions (pagination over infinite scroll, forced registration avoidance)
- [Next.js Metadata API Docs](https://nextjs.org/docs/app/getting-started/metadata-and-og-images) — generateMetadata() and JSON-LD structured data
- [CVE-2025-29927 — Next.js middleware bypass](https://nextjs.org/docs/messages/middleware-upgrade-guide) — use >= 15.2.3

### Secondary (MEDIUM confidence)

- [NextAuth.js v5 — Using FastAPI discussion (GitHub #8064)](https://github.com/nextauthjs/next-auth/discussions/8064) — community-verified FastAPI + NextAuth.js integration pattern
- [Next Auth Google OAuth with custom backend (GitHub #8884)](https://github.com/nextauthjs/next-auth/discussions/8884) — Google token exchange pattern for custom backends
- [Various issues with refresh token rotation (NextAuth GitHub #3940)](https://github.com/nextauthjs/next-auth/discussions/3940) — race condition with single-use refresh tokens
- [Auth.js v5 production readiness discussion (GitHub #9511)](https://github.com/nextauthjs/next-auth/discussions/9511) — community assessment of v5 beta stability
- [shadcn/ui Next.js 15 dark mode issue #5552](https://github.com/shadcn-ui/ui/issues/5552) — ThemeProvider hydration error confirmed in Next.js 15
- [Achieving Full-Stack Type Safety with FastAPI, Next.js, and OpenAPI Spec](https://abhayramesh.com/blog/type-safe-fullstack) — openapi-typescript workflow for FastAPI → Next.js
- [Managing type safety challenges using FastAPI + Next.js (Vinta Software)](https://www.vintasoftware.com/blog/type-safety-fastapi-nextjs-architecture) — type drift prevention workflow
- [Setting Up Auth.js v5 with Next.js 15 (CodeVoweb)](https://codevoweb.com/how-to-set-up-next-js-15-with-nextauth-v5/) — practical credentials + OAuth implementation patterns
- [Infinite Scroll vs Pagination (NinjaTables)](https://ninjatables.com/infinite-scroll-vs-pagination/) — pagination UX evidence for catalog browsing

### Tertiary (LOW confidence)

- Vendor-reported conversion rate claims (Baymard Institute, Yotpo) — not relied upon for feature decisions; directional only

---

*Research completed: 2026-02-27*
*Ready for roadmap: yes*
