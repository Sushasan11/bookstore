# Phase 19: Monorepo + Frontend Foundation - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the existing repo into a monorepo with `backend/` and `frontend/` directories. Scaffold a Next.js 15 app with TypeScript, shadcn/ui, and Tailwind v4. Set up auto-generated API types from FastAPI's OpenAPI spec. Deliver a responsive layout shell (header, nav, footer) that renders on mobile and desktop. Verify the full frontend-to-backend pipeline works without CORS errors.

</domain>

<decisions>
## Implementation Decisions

### Layout shell design
- Top navbar with logo, nav links, and user/cart actions
- Hamburger menu on mobile (slide-out or dropdown)
- Responsive layout: header, main content area, footer
- Mobile-first approach

### Monorepo structure
- Package manager: npm (not pnpm or bun)
- Move all existing backend code into `backend/` subfolder using `git mv` to preserve history
- Frontend scaffolded in `frontend/` directory
- No shared `packages/` directory for now — keep it simple with just `backend/` and `frontend/`

### Component & styling approach
- Clean & modern visual tone — white space, subtle shadows, rounded corners (Vercel/Linear aesthetic)
- Dark mode supported from the start with system preference detection and manual toggle
- System font stack (no custom web fonts) — zero load time, clean look
- shadcn/ui as the component library with Tailwind v4

### API integration setup
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

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants familiar e-commerce patterns and a clean, professional look.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-monorepo-frontend-foundation*
*Context gathered: 2026-02-27*
