# Phase 19: First-Time Setup

> **Purpose**: Validate fresh install experience - admin password wizard and login blocking
> **Duration**: ~10 minutes
> **Assumes**: Phase 0 PASSED (services running), NO existing admin user
> **Output**: First-time setup flow verified, admin account created

---

## Background

**First-Time Setup** (AUTH-001, AUTH-002):
- On fresh install, no admin user exists
- Users are blocked from login until admin password is set
- Wizard guides admin through password creation
- After setup, normal login flows work

**User Stories**:
- AUTH-001: First-time admin password setup
- AUTH-002: Block login until setup complete

---

## Prerequisites

- [ ] Trinity services running (Phase 0)
- [ ] Fresh database (no existing users)
- [ ] Or: Database reset to simulate fresh install

**To Reset Database (Caution - Destructive)**:
```bash
# Stop services
docker-compose down

# Remove database
rm ~/trinity-data/trinity.db

# Restart services
docker-compose up -d
```

---

## Test: Setup Required Detection

### Step 1: Navigate to Login Page
**Action**:
- Open http://localhost in browser
- Observe the login page

**Expected**:
- [ ] Login page loads
- [ ] "Setup Required" message displayed
- [ ] Normal login form is disabled or hidden
- [ ] Setup wizard is prominent

**Verify**:
- [ ] Cannot bypass to other pages
- [ ] API returns setup_required status

---

### Step 2: Check API Setup Status
**Action**:
- Open browser DevTools (F12) → Network tab
- Observe API calls on page load

**Expected**:
- [ ] `GET /api/auth/mode` returns `setup_required: true`
- [ ] No JWT token in localStorage
- [ ] UI shows setup wizard

**API Response Example**:
```json
{
  "mode": "setup_required",
  "setup_required": true,
  "email_enabled": false
}
```

---

## Test: Password Setup Wizard

### Step 3: Open Setup Wizard
**Action**:
- Click "Set Admin Password" or similar button
- Wizard/modal should appear

**Expected**:
- [ ] Password input field visible
- [ ] Confirm password field visible
- [ ] Password requirements shown (min length, complexity)
- [ ] Submit button

**Verify**:
- [ ] Form is accessible
- [ ] Password fields are type="password"

---

### Step 4: Test Password Validation - Weak Password
**Action**:
- Enter weak password: "123"
- Enter same in confirm field
- Click Submit

**Expected**:
- [ ] Validation error displayed
- [ ] "Password too short" or similar message
- [ ] Form does not submit
- [ ] Admin user NOT created

**Verify**:
- [ ] Client-side validation works
- [ ] No API call made (or API rejects)

---

### Step 5: Test Password Mismatch
**Action**:
- Enter strong password: "SecurePass123!"
- Enter different confirm: "DifferentPass456!"
- Click Submit

**Expected**:
- [ ] Validation error displayed
- [ ] "Passwords do not match" message
- [ ] Form does not submit

**Verify**:
- [ ] Mismatch detected before API call

---

### Step 6: Complete Valid Setup
**Action**:
- Enter strong password: "AdminPassword123!"
- Enter same in confirm field
- Click Submit
- Wait 5 seconds

**Expected**:
- [ ] Success message displayed
- [ ] "Admin account created successfully"
- [ ] Redirect to login page OR auto-login
- [ ] Setup wizard closes

**Verify**:
- [ ] No errors
- [ ] Password stored securely (bcrypt hashed)

---

## Test: Post-Setup Login

### Step 7: Verify Setup Complete Status
**Action**:
- Refresh the page (F5)
- Check login page state

**Expected**:
- [ ] Normal login page displayed
- [ ] No "Setup Required" message
- [ ] Admin login option available
- [ ] Email login option available (if configured)

**API Response Example**:
```json
{
  "mode": "email",
  "setup_required": false,
  "email_enabled": true
}
```

---

### Step 8: Login with New Admin Password
**Action**:
- Click "Admin Login" or switch to admin mode
- Enter username: "admin"
- Enter password: "AdminPassword123!"
- Click Login
- Wait 3 seconds

**Expected**:
- [ ] Login successful
- [ ] Redirected to Dashboard
- [ ] User profile shows "admin"
- [ ] JWT token stored in localStorage

**Verify**:
- [ ] Admin has full access
- [ ] Settings page accessible
- [ ] Can create agents

---

### Step 9: Verify Password Cannot Be Reset Without Auth
**Action**:
- Log out
- Try to access setup wizard again

**Expected**:
- [ ] Setup wizard NOT accessible
- [ ] Normal login flow required
- [ ] Cannot re-run first-time setup

**Verify**:
- [ ] Setup is one-time only
- [ ] Password change requires authenticated admin

---

## Critical Validations

### Password Security
**Validation**: Password is properly hashed

```bash
# Check user table (DO NOT log actual hash)
sqlite3 ~/trinity-data/trinity.db "SELECT id, email, password_hash IS NOT NULL FROM users WHERE email='admin@localhost'"
```

Expected: password_hash column has value (bcrypt hash, NOT plaintext)

### Setup State Persistence
**Validation**: Setup complete state survives restart

- [ ] Stop backend: `docker-compose restart backend`
- [ ] Wait 30 seconds
- [ ] Refresh login page
- [ ] Setup wizard should NOT appear
- [ ] Normal login should work

---

## Success Criteria

Phase 19 is **PASSED** when:
- [ ] Fresh install shows "Setup Required" message
- [ ] Normal login is blocked until setup complete
- [ ] Password validation enforces minimum requirements
- [ ] Password mismatch is detected
- [ ] Valid password creates admin account
- [ ] After setup, normal login works
- [ ] Admin can access all features
- [ ] Setup cannot be re-run after completion
- [ ] Password is stored as bcrypt hash
- [ ] Setup state persists across restarts

---

## Troubleshooting

**Setup wizard doesn't appear**:
- Database may already have admin user
- Reset database to test fresh install
- Check `/api/auth/mode` response

**Password setup fails**:
- Check backend logs: `docker logs backend`
- Verify bcrypt is installed in container
- Check for database write errors

**Login fails after setup**:
- Verify password was saved correctly
- Check bcrypt comparison in auth flow
- Review backend logs for auth errors

**Setup state not persisting**:
- Check SQLite file exists: `ls -la ~/trinity-data/trinity.db`
- Verify Docker volume is mounted
- Check for database corruption

---

## Next Phase

Once Phase 19 is **PASSED**, proceed to:
- **Phase 20**: Live Execution Streaming

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: AUTH-001, AUTH-002
