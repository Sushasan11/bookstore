# Architecture Research

**Domain:** BookStore v3.0 — Next.js 15 Customer Storefront
**Researched:** 2026-02-27
**Confidence:** HIGH

---

## Context: Frontend Integration, Not Greenfield

v3.0 adds a Next.js 15 customer-facing frontend to an existing FastAPI backend with 13,743 LOC Python across 18 phases. The backend API is complete and stable. This document answers: how does the Next.js frontend integrate with what already exists?

**Monorepo structure:**
```
claude-test/
├── backend/       ← existing Python code (moved from root)
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   ├── scripts/
│   └── pyproject.toml
├── frontend/      ← new Next.js app
│   ├── src/
│   │   ├── app/          # App Router pages
│   │   ├── components/   # React components
│   │   ├── lib/          # API client, auth, utils
│   │   └── hooks/        # Custom React hooks
│   ├── package.json
│   └── next.config.ts
└── .planning/     ← stays at root
```

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Browser (Customer)                             │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│                     Next.js 15 Frontend                               │
│                                                                       │
│  PUBLIC PAGES (Server Components)     PROTECTED PAGES (Client + SC)   │
│  ┌─────────────┐ ┌──────────────┐    ┌──────────────┐ ┌───────────┐  │
│  │ / (catalog) │ │ /books/[id]  │    │ /cart        │ │ /orders   │  │
│  │ /search     │ │ /auth/login  │    │ /checkout    │ │ /wishlist │  │
│  └─────────────┘ └──────────────┘    │ /reviews     │ │ /prebooks │  │
│                                       └──────────────┘ └───────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    Shared Infrastructure                        │   │
│  │  NextAuth.js v5    TanStack Query v5    openapi-fetch client   │   │
│  │  (JWT session)     (server state)       (typed API calls)      │   │
│  └────────────────────────────────┬───────────────────────────────┘   │
└───────────────────────────────────┼───────────────────────────────────┘
                                    │ HTTP (REST)
┌───────────────────────────────────▼───────────────────────────────────┐
│                     FastAPI Backend (existing)                         │
│                                                                       │
│  /auth/*  /books/*  /cart/*  /orders/*  /wishlist/*  /reviews/*       │
│  /prebooks/*                                                          │
│                                                                       │
│  + CORS middleware (NEW — allows frontend origin)                     │
│  + POST /auth/google/token (NEW — Google OAuth token exchange)        │
└───────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Location | Responsibility |
|-----------|----------|----------------|
| App Router pages | frontend/src/app/ | Route structure, layouts, server components |
| NextAuth.js v5 | frontend/src/lib/auth.ts | Session management, JWT storage, token refresh |
| TanStack Query | frontend/src/lib/query.ts | Server state caching, mutations, optimistic updates |
| openapi-fetch client | frontend/src/lib/api/ | Auto-generated typed API client from FastAPI OpenAPI spec |
| Zod schemas | frontend/src/lib/validations/ | Form validation (signup, login, checkout, reviews) |
| shadcn/ui components | frontend/src/components/ui/ | Reusable UI primitives |
| Feature components | frontend/src/components/ | Domain-specific components (BookCard, CartItem, ReviewForm) |

---

## Key Integration Patterns

### Pattern 1: NextAuth.js v5 as JWT Bridge

NextAuth.js manages the session but does NOT own the user database. FastAPI is the auth authority.

**Email+password flow:**
```
User submits login form
  → NextAuth Credentials provider `authorize()` callback
    → POST /auth/login to FastAPI (email + password)
    → FastAPI returns { access_token, refresh_token }
    → Store both tokens in NextAuth encrypted session cookie
  → `jwt` callback: attach access_token to session
  → `session` callback: expose access_token to client
```

**Google OAuth flow (requires new backend endpoint):**
```
User clicks "Sign in with Google"
  → NextAuth Google provider gets Google id_token
  → `jwt` callback: POST /auth/google/token to FastAPI with Google id_token
  → FastAPI verifies Google token, creates/finds user, returns { access_token, refresh_token }
  → Store FastAPI tokens in NextAuth session (NOT the Google tokens)
```

**Token refresh:**
```
`jwt` callback runs on every request:
  → Check if access_token is expired (decode exp claim or use stored expiry)
  → If expired: POST /auth/refresh to FastAPI with refresh_token
  → If refresh succeeds: update tokens in session
  → If refresh fails: set session.error = "RefreshAccessTokenError"
    → Client detects error, calls signOut()
```

### Pattern 2: API Client via openapi-typescript + openapi-fetch

```
FastAPI /openapi.json → openapi-typescript codegen → TypeScript types
                       → openapi-fetch client uses generated types
```

**Type generation script (in frontend/package.json):**
```json
{
  "scripts": {
    "generate-types": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.d.ts"
  }
}
```

All API calls are fully typed. When backend Pydantic schemas change, regenerate types to catch drift at compile time.

### Pattern 3: Server Components (SSR) for Public Pages, Client Components for Interactive

| Page | Rendering | Why |
|------|-----------|-----|
| / (catalog) | Server Component + ISR | SEO-critical, cacheable |
| /books/[id] | Server Component + ISR | SEO-critical, cacheable |
| /search | Hybrid (server initial, client interactivity) | SEO for initial results, client for filters |
| /auth/* | Client Component | No SEO value, interactive forms |
| /cart | Client Component | User-specific, mutations |
| /checkout | Client Component | User-specific, forms |
| /orders | Client Component | User-specific, authenticated |
| /wishlist | Client Component | User-specific, mutations |
| /reviews | Client Component | User-specific, forms |
| /prebooks | Client Component | User-specific, mutations |

### Pattern 4: TanStack Query for Server State

**Server components:** Use `prefetchQuery` in server components, dehydrate to client via `HydrationBoundary`.

**Client components:** Use `useQuery` for reads, `useMutation` + `invalidateQueries` for writes.

**Optimistic updates:** Cart add/remove and wishlist toggle use optimistic updates with rollback on error.

---

## Data Flow

### Catalog Browsing (Server-Rendered)

```
GET /books (browser)
  → Next.js server component
    → fetch GET /books?page=1&size=20 from FastAPI (server-side, no CORS)
    → prefetchQuery into TanStack Query cache
    → Render BookGrid with HydrationBoundary
  → HTML sent to browser with pre-rendered book list
  → Client hydrates, TanStack Query picks up cached data
  → Subsequent pages fetched client-side via TanStack Query
```

### Add to Cart (Client-Side Mutation)

```
User clicks "Add to Cart"
  → useMutation: POST /cart/items with { book_id, quantity }
    → Header: Authorization: Bearer {access_token from session}
  → onSuccess: invalidateQueries(["cart"]) → refetch cart count
  → onError: show toast notification
```

### Checkout Flow

```
User clicks "Place Order"
  → useMutation: POST /orders/checkout
    → Sends cart contents (backend handles stock validation + decrement)
  → onSuccess:
    → invalidateQueries(["cart", "orders"])
    → redirect to /orders/{id}/confirmation
  → onError:
    → Show specific error (insufficient stock, empty cart, etc.)
```

---

## Backend Changes Required

Only 2 changes to the existing backend:

| Change | File | Purpose |
|--------|------|---------|
| CORS middleware | backend/app/main.py | Allow frontend origin (localhost:3000 dev, production domain) |
| Google token exchange endpoint | backend/app/core/oauth.py or auth router | Accept Google id_token, return FastAPI JWT pair |

**CORS configuration:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # NOT "*" — explicit origin required with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Build Order

Dependencies flow: monorepo setup → auth → public pages → authenticated features.

```
Phase 19: Monorepo Restructure + Frontend Foundation
  - Move existing code to backend/
  - Scaffold Next.js app in frontend/
  - Add CORS to backend
  - Set up openapi-typescript type generation
  - TanStack Query provider + layout shell

Phase 20: Auth Integration
  - NextAuth.js v5 with Credentials provider (email+password)
  - Google OAuth with FastAPI token exchange
  - Middleware auth guards
  - Login/signup/logout pages

Phase 21: Catalog & Search
  - Server-rendered catalog page with ISR
  - Book detail page with ratings display
  - Search with filters (title, author, genre)
  - Pagination

Phase 22: Cart & Checkout
  - Cart management (add/remove/update quantity)
  - Checkout flow with order confirmation
  - Stock validation error handling

Phase 23: Orders & Account
  - Order history with details
  - User profile/account page

Phase 24: Wishlist & Pre-booking
  - Wishlist add/remove/view
  - Pre-booking for out-of-stock books
  - View/cancel reservations

Phase 25: Reviews
  - Leave review on purchased books (verified purchase gate)
  - Edit/delete own reviews
  - Review display on book detail page
```

---

## Architectural Decisions

### Decision 1: No BFF (Backend-for-Frontend) Proxy

**Choice:** Frontend calls FastAPI directly (with CORS), not through Next.js API routes acting as proxy.

**Rationale:** The FastAPI backend is already a well-designed API. Adding a proxy layer doubles the API surface area to maintain. CORS is sufficient for browser-to-API communication. NextAuth.js handles token storage securely in httpOnly cookies.

**Exception:** Google OAuth token exchange goes through NextAuth's callback — this is inherent to NextAuth's design, not a BFF pattern.

### Decision 2: openapi-typescript for Type Generation (not manual types)

**Choice:** Auto-generate TypeScript types from FastAPI's OpenAPI spec.

**Rationale:** FastAPI automatically generates OpenAPI JSON from Pydantic models. openapi-typescript converts this to TypeScript types. This keeps frontend types in sync with backend schemas without manual maintenance. Type drift is caught at compile time.

### Decision 3: NextAuth.js v5 (Auth.js) over v4

**Choice:** Use next-auth v5 (Auth.js) which is designed for App Router.

**Rationale:** v4 is built for Pages Router and requires documented workarounds for App Router. v5 has native App Router support, uses `auth()` helper in server components, and has been production-stable for 18+ months despite the beta label.

### Decision 4: TanStack Query over Server Actions for Reads

**Choice:** TanStack Query for all data fetching; Server Actions only for mutations where beneficial.

**Rationale:** TanStack Query provides caching, background refetch, optimistic updates, and request deduplication. Server Actions are simpler for write-only operations but lack caching semantics for reads.

---

## Security Considerations

- **CVE-2025-29927:** Next.js < 15.2.3 has middleware bypass vulnerability. Use >= 15.2.3.
- **Token storage:** Access/refresh tokens stored in NextAuth encrypted httpOnly session cookie — not accessible to client JS.
- **CORS:** Explicit origin (not wildcard) required when `allow_credentials=True`.
- **is_active enforcement:** Backend checks `is_active` per request. Frontend must handle 401 by calling `signOut()`.
- **Middleware alone is insufficient:** Always validate `auth()` in server components for protected pages, not just middleware.

---

*Architecture research for: BookStore v3.0 — Next.js 15 Customer Storefront*
*Researched: 2026-02-27*
