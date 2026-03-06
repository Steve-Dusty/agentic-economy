# Feature: Authentication Mode System

> **❌ REMOVED (2026-01-01)**: Auth0 has been completely removed from both frontend and backend.
> See [email-authentication.md](email-authentication.md) for the current authentication flow.

---

## Removal Summary (2026-01-01)

Auth0 SDK was causing blank white pages when accessing Trinity via HTTP on local network IPs (e.g., `http://192.168.1.127:3000`) because Auth0 requires "secure origins" (HTTPS or localhost).

Since Auth0 login was already disabled in the UI (2025-12-29), all Auth0 code was removed entirely.

### Frontend Removed

- `@auth0/auth0-vue` package
- `src/frontend/src/config/auth0.js`
- `createAuth0()` and `app.use(auth0)` from main.js
- `useAuth0()` from NavBar.vue
- `handleAuth0Callback()` from auth.js

### Backend Removed

- `/api/auth/exchange` endpoint
- `Auth0TokenExchange` model
- `AUTH0_DOMAIN`, `AUTH0_ALLOWED_DOMAIN` config vars

### Kept for Backward Compatibility

- `auth0_sub` column in users table (no DB migration needed)
- `get_user_by_auth0_sub()`, `get_or_create_auth0_user()` methods (unused but harmless)

---

## Current Authentication

See [email-authentication.md](email-authentication.md) for the active authentication system:

| Method | Description |
|--------|-------------|
| **Email Login** (primary) | Email → 6-digit code → Verify |
| **Admin Login** (secondary) | Password-based for 'admin' user |

---

## Related

- **Current Auth**: [email-authentication.md](email-authentication.md)
- **First-Time Setup**: [first-time-setup.md](first-time-setup.md)

---

**Status**: ❌ Removed (2026-01-01)
**Replaced By**: Email Authentication + Admin Login
