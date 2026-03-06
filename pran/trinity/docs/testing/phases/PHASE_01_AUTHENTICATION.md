# Phase 1: Authentication & UI Readiness

> **Purpose**: Validate authentication flows (Email Auth + Admin Login) and browser login
> **Duration**: ~5 minutes
> **Assumes**: Phase 0 PASSED (services running, clean slate)
> **Output**: Logged-in browser session, valid JWT token

---

## Prerequisites

- ✅ Phase 0 PASSED
- ✅ Backend healthy
- ✅ Frontend accessible
- ✅ No test agents exist

> **Note**: JWT tokens are invalidated when backend restarts. If you see 401 errors after a deploy/restart, logout and login again to get a fresh token.

---

## Authentication Methods

Trinity supports two authentication methods:

| Method | Description | Login Flow |
|--------|-------------|------------|
| **Email Auth** | Primary (whitelisted users) | Email + 6-digit verification code |
| **Admin Login** | Secondary (admin only) | Fixed username 'admin' + password |

**Check Current Mode**:
```bash
curl http://localhost:8000/api/auth/mode
```

**Expected Response**:
```json
{
  "email_auth_enabled": true,
  "setup_completed": true
}
```

---

## Test Steps

### Step 1: Navigate to Login Page
**Action**:
- Open browser to http://localhost
- Refresh page (Ctrl+F5) to clear any cached state
- If already logged in, logout first

**Expected** (Email Auth - Default):
- [ ] Page loads
- [ ] Email input field visible
- [ ] "Send Verification Code" button visible
- [ ] "Admin Login" button visible at bottom

**Verify**:
- [ ] No console errors
- [ ] Form is interactive (not disabled)

---

### Step 2: Test Admin Login
**Action**:
- Click "Admin Login" button
- Verify username field shows "admin" (fixed, non-editable)
- Enter password: `YOUR_PASSWORD` (from `.env` ADMIN_PASSWORD)
- Click "Sign In as Admin"
- Wait for page to load (10 seconds max)

**Expected**:
- [ ] Redirects to http://localhost/ (dashboard)
- [ ] Navigation bar visible
- [ ] "Connected" indicator in navbar
- [ ] Admin profile button shows "admin"
- [ ] Dashboard loads with "No agents" message

**Verify**:
- [ ] No console errors during redirect
- [ ] Page title shows "Trinity"
- [ ] All nav items visible: Dashboard, Agents, Templates, Schedules (or similar)

---

### Step 3: Test Invalid Admin Password
**Action**:
- Logout if logged in
- Click "Admin Login"
- Enter password: `wrongpassword`
- Click "Sign In as Admin"

**Expected**:
- [ ] Login fails with error message
- [ ] Stays on login page
- [ ] Error message displays: "Incorrect username or password"
- [ ] Form remains interactive

**Verify**:
- [ ] Error message shown
- [ ] Can retry login

---

### Step 4: Test Email Login Flow (Optional)
**Action** (requires whitelisted email):
- Return to email login (click "← Back to email login")
- Enter email: `admin@your-domain.com` (whitelisted email)
- Click "Send Verification Code"
- Wait for code email (check backend logs for console output)
- Enter 6-digit code received
- Click "Verify & Sign In"

**Expected**:
- [ ] "We sent a 6-digit code to..." message appears
- [ ] Code input field shown
- [ ] Countdown timer starts
- [ ] After verify: Redirects to dashboard

**Note**: Email auth requires:
1. Email in whitelist (Settings → Email Whitelist)
2. Email provider configured (use EMAIL_PROVIDER=console for dev)

---

### Step 5: Verify Session Token
**Action**: Open browser DevTools Console
```javascript
localStorage.getItem('token')
```

**Expected**:
- [ ] Returns JWT token (starts with `eyJ`)
- [ ] Token contains `.` separators (3 parts)

**Verify**:
- [ ] Token is valid JWT format
- [ ] Token not empty

---

### Step 6: Verify User Profile
**Action**: Click "admin" button in top-right navbar

**Expected**:
- [ ] Dropdown menu appears
- [ ] Shows username: "admin"
- [ ] "Sign out" button visible

**Verify**:
- [ ] Profile information displayed correctly
- [ ] No console errors

---

### Step 7: Verify Dashboard Initial State
**Action**: Look at main content area

**Expected**:
- [ ] Page title: "Dashboard" or "Agent Network"
- [ ] Message: "No agents · 0 running · 0 messages"
- [ ] "Create Agent" button visible
- [ ] Empty graph area (no agent nodes)
- [ ] No error messages

**Verify**:
- [ ] Clean slate confirmed
- [ ] UI is responsive
- [ ] No pending API errors

---

### Step 8: Logout Test
**Action**:
- Click "admin" dropdown
- Click "Sign out"

**Expected**:
- [ ] Redirects to login page
- [ ] Login form visible
- [ ] Session cleared

**Verify**:
- [ ] Token removed from localStorage
- [ ] Cannot access dashboard directly (redirect to login)

---

### Step 9: Login Again (Session Persistence)
**Action**:
- Login again with admin/YOUR_PASSWORD
- Navigate away (click Agents in navbar)
- Refresh page (F5)

**Expected**:
- [ ] Page loads without redirect to login
- [ ] Session persists
- [ ] Still on Agents page
- [ ] "admin" button shows in navbar

**Verify**:
- [ ] Token still in localStorage
- [ ] Session survived page refresh

---

## Critical Validations

### Auth Mode Detection
**Validation**: Backend correctly reports auth mode

```bash
curl http://localhost:8000/api/auth/mode
```

**Expected Response**:
```json
{
  "email_auth_enabled": true,
  "setup_completed": true
}
```

---

### Token Structure
**Validation**: JWT token has correct claims

Decode token at https://jwt.io:
- [ ] Header: `{"alg":"HS256","typ":"JWT"}`
- [ ] Payload has: `"mode":"admin"` or `"mode":"email"` claim
- [ ] Payload has: `"sub"` claim (user ID)
- [ ] Payload has: `"exp"` claim (expiration)

---

## Success Criteria

Phase 1 is **PASSED** when:
- ✅ Admin login works (admin/YOUR_PASSWORD)
- ✅ Invalid login fails with error
- ✅ Session token obtained and stored
- ✅ User profile displays correctly
- ✅ Logout clears session
- ✅ Session persists across page refresh
- ✅ Dashboard shows clean state (no agents)

---

## Troubleshooting

**Login fails**:
- Check backend logs: `docker logs trinity-backend | grep -i auth`
- Verify ADMIN_PASSWORD is set correctly
- Try clearing browser cache

**Token missing**:
- Check localStorage in DevTools
- Verify response from `/api/token` endpoint
- Check CORS settings

**Session doesn't persist**:
- Check cookie settings in browser
- Verify localStorage is enabled
- Check for JavaScript errors in console

---

## Next Phase

Once Phase 1 is **PASSED**, proceed to:
- **Phase 2**: Agent Creation (test-echo - GitHub template)
- **Phase 3**: Basic Chat & Context Validation

---

**Status**: Ready for agent creation testing
