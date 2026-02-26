# Phase 10: Admin User Management - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin endpoints to view, filter, deactivate, and reactivate user accounts. Deactivated users lose API access immediately (access token rejected, refresh tokens revoked). Admin accounts are protected from deactivation. This phase covers admin-side user management only — no user self-service account deletion, no role changes, no audit logging.

</domain>

<decisions>
## Implementation Decisions

### User list & filtering
- Offset-based pagination (?page=1&per_page=20) — consistent with existing catalog/order endpoints
- Default sort: newest first (created_at DESC)
- Admin user response includes: id, email, full_name, role, is_active, created_at
- Filters are combinable: ?role=user&is_active=false both optional, omit = all values
- Response includes full page metadata: total_count, page, per_page, total_pages

### Deactivation behavior
- Immediate lockout: check is_active on every protected request, reject deactivated users instantly (don't wait for token expiry)
- Deactivation revokes all refresh tokens AND blocks current access tokens via is_active check
- Generic 403 error for deactivated users: "Account deactivated. Contact support." — same for login and protected endpoints
- Deactivation only affects authentication — orders, cart, wishlist data remain untouched
- Deactivate is idempotent: deactivating an already-deactivated user returns 200 with user object

### Reactivation behavior
- Fresh login required after reactivation (is_active flipped but no tokens issued)
- Reactivate is idempotent: reactivating an already-active user returns 200 with user object
- No special restriction on reactivating admin accounts (they can't be deactivated anyway)

### Admin self-protection
- Blanket rule: no admin can deactivate any admin account (self or others) — matches ADMN-05
- 403 Forbidden with message "Cannot deactivate admin accounts" — same response regardless of target
- No superadmin concept

### API design
- Dedicated admin namespace: /admin/users
- GET /admin/users — paginated list with filters
- PATCH /admin/users/{id}/deactivate — deactivate user
- PATCH /admin/users/{id}/reactivate — reactivate user
- All endpoints return updated AdminUserResponse (full user object with is_active)

### Claude's Discretion
- Exact admin router/module structure
- How to implement is_active check in the auth dependency (middleware vs dependency injection)
- Test organization and fixture design
- Error handling for non-existent user IDs

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing project patterns for pagination, error handling, and response schemas.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-admin-user-management*
*Context gathered: 2026-02-26*
