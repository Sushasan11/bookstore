---
status: complete
phase: 10-admin-user-management
source: [10-01-SUMMARY.md, 10-02-SUMMARY.md]
started: "2026-02-26T09:00:00Z"
updated: "2026-02-26T09:15:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. Admin can list users with pagination
expected: GET /admin/users (with admin auth) returns 200 with JSON body containing items array with user objects (id, email, full_name, role, is_active, created_at), total_count, page, per_page, total_pages metadata
result: pass

### 2. Admin can filter users by role
expected: GET /admin/users?role=user returns only users with role "user". GET /admin/users?role=admin returns only admin users.
result: pass

### 3. Admin can filter users by active status
expected: GET /admin/users?is_active=false returns only deactivated users. GET /admin/users?is_active=true returns only active users.
result: pass

### 4. Admin can deactivate a regular user
expected: PATCH /admin/users/{id}/deactivate returns 200 with user object showing is_active=false. The user's refresh tokens are all revoked.
result: pass

### 5. Deactivating an admin account is rejected
expected: PATCH /admin/users/{admin_id}/deactivate returns 403 with detail "Cannot deactivate admin accounts" — applies to self-deactivation and deactivating other admins.
result: pass

### 6. Deactivated user cannot log in
expected: POST /auth/login with correct credentials for a deactivated user returns 403 "Account deactivated. Contact support."
result: pass

### 7. Deactivated user's access token is rejected on protected routes
expected: Using a deactivated user's still-valid access token on GET /cart (or any protected endpoint) returns 403 "Account deactivated. Contact support."
result: pass

### 8. Admin can reactivate a deactivated user
expected: PATCH /admin/users/{id}/reactivate on a deactivated user returns 200 with is_active=true. The user can log in again after reactivation.
result: pass

### 9. Deactivation and reactivation are idempotent
expected: Deactivating an already-deactivated user returns 200 (is_active=false). Reactivating an already-active user returns 200 (is_active=true). No errors.
result: pass

### 10. Non-admin users cannot access admin endpoints
expected: GET /admin/users with a regular user's token returns 403. Unauthenticated request returns 401.
result: pass

### 11. Integration tests pass
expected: Running python -m pytest tests/test_admin_users.py -v shows all 21 tests passing.
result: pass

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
