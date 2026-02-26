---
status: complete
phase: 02-core-auth
source: 02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md, 02-05-PLAN.md
started: 2026-02-25T12:00:00Z
updated: 2026-02-25T12:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Register a new user
expected: POST /auth/register with valid email + password returns 201 with access_token, refresh_token, and token_type "bearer"
result: pass

### 2. Duplicate email rejected
expected: POST /auth/register with the same email again returns 409 with code "AUTH_EMAIL_CONFLICT"
result: pass

### 3. Login with correct credentials
expected: POST /auth/login with registered email + password returns 200 with access_token and refresh_token
result: pass

### 4. Login with wrong password
expected: POST /auth/login with wrong password returns 401 with detail "Invalid email or password" (generic — no email enumeration)
result: pass

### 5. Refresh token rotation
expected: POST /auth/refresh with the refresh_token from login returns 200 with a NEW access_token and a NEW refresh_token (different from original)
result: pass

### 6. Old refresh token rejected after rotation
expected: POST /auth/refresh with the OLD refresh_token (already rotated) returns 401
result: pass

### 7. Logout revokes refresh token
expected: POST /auth/logout with refresh_token returns 204. Then POST /auth/refresh with that same token returns 401
result: pass

### 8. Unauthenticated request rejected
expected: GET to a protected endpoint without Authorization header returns 401
result: pass

### 9. User role cannot access admin endpoint
expected: Using a regular user's access_token on an admin-guarded endpoint returns 403 with code "AUTH_FORBIDDEN"
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
