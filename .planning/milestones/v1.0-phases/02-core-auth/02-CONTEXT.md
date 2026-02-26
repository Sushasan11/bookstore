# Phase 2: Core Auth - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Email/password registration and login with JWT access + refresh tokens, token revocation, and role-based access control. Users can register, log in, refresh sessions, log out, and be authorized by role. OAuth login (Google/GitHub) is Phase 3 — not in scope here.

</domain>

<decisions>
## Implementation Decisions

### Password & registration policy
- No email verification required — register and immediately receive tokens
- Minimum 8 characters password length, no complexity rules (follows NIST guidance)
- Email is the only identifier — no username or display name field at registration
- Duplicate email on registration returns 409 Conflict with clear message (email enumeration accepted for bookstore context)

### Token behavior & session rules
- Refresh token rotation on use — each refresh issues a new refresh token and revokes the old one; if a revoked token is reused, revoke the entire family (theft detection)
- Multiple active sessions allowed — each login creates an independent refresh token; devices don't interfere with each other
- Access token TTL: 15 minutes (from roadmap success criteria)
- Refresh token TTL: 7 days
- Logout revokes only the current session's refresh token (the one sent in the request); other sessions remain active

### Error responses & security posture
- Generic error on login failure: always "Invalid email or password" regardless of whether email exists (prevents email enumeration via login)
- No rate limiting in this phase — defer to a future middleware/infrastructure concern
- No account lockout mechanism — failed logins return 401 each time
- Standard REST HTTP status codes: 401 bad credentials / expired token, 403 insufficient role, 409 duplicate email, 422 validation errors

### Role model & admin bootstrapping
- Fixed role enum: `user` and `admin` — no roles table, no extensibility needed
- First admin created via CLI seed command (management script), not through the API
- Registration always defaults to `user` role — no request payload can set or elevate the role
- Role embedded in JWT claims (`role` field) — no DB lookup needed for authorization checks; role changes take effect at next token issuance

### Claude's Discretion
- Refresh token storage schema design (DB table structure, indexes)
- Password hashing configuration (argon2 parameters)
- JWT signing algorithm choice
- Exact JSON response shapes for auth endpoints
- Seed command implementation approach (Click CLI, standalone script, etc.)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The roadmap already specifies pwdlib/argon2 for password hashing and PyJWT for token handling.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-core-auth*
*Context gathered: 2026-02-25*
