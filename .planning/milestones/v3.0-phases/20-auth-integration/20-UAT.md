---
status: complete
phase: 20-auth-integration
source: 20-01-SUMMARY.md, 20-02-SUMMARY.md, 20-03-SUMMARY.md
started: 2026-02-27T14:00:00Z
updated: 2026-02-27T14:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Register a New Account
expected: Navigate to /register. Fill in email, password, and confirm password. Submit. Account is created, you are automatically signed in and redirected home. Header shows your email and "Sign Out" button.
result: pass

### 2. Sign Out
expected: Click "Sign Out" in the Header. Session is cleared, Header shows "Sign In" link instead of your email. You are logged out.
result: pass

### 3. Login with Email/Password
expected: Navigate to /login. Enter the email and password you registered with. Submit. You are signed in and redirected home. Header shows your email and "Sign Out" button.
result: pass

### 4. Login with Wrong Password
expected: On /login, enter your email but a wrong password. Submit. An error message "Invalid email or password" appears on the form. No redirect, no console errors.
result: pass

### 5. Session Persists on Refresh
expected: While logged in, refresh the page (F5). After reload, you remain signed in — Header still shows your email and "Sign Out" button.
result: pass

### 6. Route Protection (Unauthenticated)
expected: Sign out first. Then navigate directly to /account in the browser address bar. You are redirected to /login?callbackUrl=%2Faccount. After logging in, you should be redirected back to /account (or home if /account page doesn't exist yet).
result: pass

### 7. Auth Page Redirect (Authenticated)
expected: While logged in, navigate to /login. You are automatically redirected away from the login page (to home page) since you are already authenticated.
result: pass

### 8. Register Form Validation
expected: On /register, enter a password and a different confirm password. Submit. A client-side validation error appears indicating passwords don't match. The form does not submit.
result: pass

### 9. Login Page Layout
expected: Navigate to /login. The page shows a centered card with email and password fields, a "Sign In" button, a divider ("or"), a "Sign in with Google" button with a Google logo, and a link to /register.
result: pass

### 10. Register Page Layout
expected: Navigate to /register. The page shows a centered card with email, password, and confirm password fields, a "Create Account" or similar button, a divider, a "Sign in with Google" button, and a link to /login.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
