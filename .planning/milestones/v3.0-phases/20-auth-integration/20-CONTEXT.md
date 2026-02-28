# Phase 20: Auth Integration - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire NextAuth.js to the existing FastAPI auth backend (`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`) and add Google OAuth. Users can sign up with email/password, sign in with email or Google, stay signed in across refreshes, get redirected to login for protected routes, and be signed out automatically if deactivated. No profile editing, password reset, or admin auth features in this phase.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User delegated all implementation decisions to Claude. The following areas are open for Claude to decide based on codebase patterns and best practices:

**Sign-up / Sign-in UX:**
- Page structure: same page with toggle vs separate /login and /register pages
- Validation error display: inline under fields vs top-of-form banner
- Error message tone: neutral-specific vs security-conscious vague
- Password field approach: single field with show/hide vs confirm password field

**Google OAuth flow (not discussed — Claude decides):**
- Button placement relative to email/password form
- First-time Google sign-in behavior (auto-create account or require linking)
- Account linking when Google email matches existing email/password account

**Session & redirect behavior (not discussed — Claude decides):**
- Post-login landing page
- Redirect-back-to-protected-route flow
- Session expiry UX (silent refresh vs prompt)
- Signed-out state indicators in the UI

**Auth page design (not discussed — Claude decides):**
- Page layout (centered card, split, full-page)
- Branding treatment on auth pages
- Dark mode styling for auth forms
- Mobile responsiveness for auth forms

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The backend already provides all needed endpoints (`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`), so the frontend integration should follow NextAuth.js conventions and match the existing shadcn/ui design system from Phase 19.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-auth-integration*
*Context gathered: 2026-02-27*
