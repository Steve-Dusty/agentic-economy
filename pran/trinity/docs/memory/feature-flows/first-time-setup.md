# Feature: First-Time Setup

## Overview
First-time setup wizard for admin password and API key configuration. On fresh install, users are redirected to `/setup` to set an admin password before accessing the platform. After login, admins can configure the Anthropic API key in Settings.

## User Story
As a platform administrator deploying Trinity for the first time, I want to be guided through initial configuration so that the platform is secured with a proper password and agents have access to the required API key.

## Requirements Reference
- **Requirement 11.4** - First-Time Setup Wizard (Phase 12.3)
- Password: bcrypt-hashed, minimum 8 characters
- API key: Stored in `system_settings` table, validated against Anthropic API

---

## Entry Points

### First Launch Flow
- **UI**: Any route visited on fresh install triggers redirect to `/setup`
- **API**: `GET /api/setup/status` (no auth) - Check if setup completed

### API Key Configuration Flow
- **UI**: `src/frontend/src/views/Settings.vue` - API Keys section
- **API**: `PUT /api/settings/api-keys/anthropic` (admin-only)

---

## Flow 1: First Launch Setup

### Frontend Layer

#### Router Guard
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/router/index.js:165-220`

```javascript
// Cache for setup status check (avoid repeated API calls)
let setupStatusCache = null
let setupStatusCacheTime = 0
const SETUP_CACHE_DURATION = 5000 // 5 seconds

async function checkSetupStatus() {
  const now = Date.now()
  // Use cached value if recent
  if (setupStatusCache !== null && (now - setupStatusCacheTime) < SETUP_CACHE_DURATION) {
    return setupStatusCache
  }

  try {
    const response = await fetch('/api/setup/status')
    const data = await response.json()
    setupStatusCache = data.setup_completed
    setupStatusCacheTime = now
    return setupStatusCache
  } catch (e) {
    console.error('Failed to check setup status:', e)
    // Assume setup is completed if check fails (don't block access)
    return true
  }
}

// Navigation guard
router.beforeEach(async (to, from, next) => {
  // ... auth initialization check

  // Check setup status for login and protected routes
  if (!to.meta.isSetup) {
    const setupCompleted = await checkSetupStatus()

    // If setup not completed, redirect to setup page
    if (!setupCompleted) {
      // Allow access to public routes that don't need setup
      if (to.path === '/chat' || to.path.startsWith('/chat/')) {
        next()
        return
      }
      next('/setup')
      return
    }

    // If setup completed and trying to access setup page, redirect to login
    if (to.path === '/setup') {
      next('/login')
      return
    }
  }
  // ... rest of guard
})
```

#### Setup Route
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/router/index.js:6-10`

```javascript
{
  path: '/setup',
  name: 'Setup',
  component: () => import('../views/SetupPassword.vue'),
  meta: { requiresAuth: false, isSetup: true }
}
```

#### Clear Setup Cache Export
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/router/index.js:242-245`

```javascript
// Clear setup cache on successful setup
export function clearSetupCache() {
  setupStatusCache = null
  setupStatusCacheTime = 0
}
```

#### SetupPassword Component
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/SetupPassword.vue`

**Key Features**:
- Password + Confirm Password fields with visibility toggle
- Password strength indicator (Weak/Fair/Good/Strong/Excellent)
- Client-side validation: min 8 chars, passwords must match
- Submits to `/api/setup/admin-password`

```javascript
// Submit handler (lines 209-236)
async function handleSubmit() {
  if (!isValid.value) return

  loading.value = true
  error.value = null

  try {
    await axios.post('/api/setup/admin-password', {
      password: password.value,
      confirm_password: confirmPassword.value
    })

    // Clear the cache so router knows setup is done
    clearSetupCache()

    // Redirect to login page
    router.push('/login')
  } catch (e) {
    if (e.response?.status === 403) {
      error.value = 'Setup has already been completed.'
      setTimeout(() => router.push('/login'), 2000)
    } else {
      error.value = e.response?.data?.detail || 'Failed to set password. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
```

**Password Strength Calculation** (lines 166-176):
```javascript
const passwordStrength = computed(() => {
  const p = password.value
  if (!p) return 0
  let strength = 0
  if (p.length >= 8) strength++
  if (p.length >= 12) strength++
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) strength++
  if (/[0-9]/.test(p)) strength++
  if (/[^A-Za-z0-9]/.test(p)) strength++
  return Math.min(strength, 4)
})
```

**Validation Logic** (lines 205-207):
```javascript
const isValid = computed(() => {
  return password.value.length >= 8 && passwordsMatch.value
})
```

### Backend Layer

#### Setup Router
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/setup.py`

**Router Registration** in `main.py:46, 294`:
```python
from routers.setup import router as setup_router
# ...
app.include_router(setup_router)
```

**Request Model** (lines 16-19):
```python
class SetAdminPasswordRequest(BaseModel):
    """Request body for setting admin password."""
    password: str
    confirm_password: str
```

#### GET /api/setup/status (lines 22-34)
```python
@router.get("/status")
async def get_setup_status():
    """
    Check if initial setup is complete. No auth required.

    Returns:
        - setup_completed: Whether the admin password has been set
        - dev_mode_hint: Hint for dev mode (if applicable)
    """
    setup_completed = db.get_setting_value('setup_completed', 'false') == 'true'
    return {
        "setup_completed": setup_completed
    }
```

#### POST /api/setup/admin-password (lines 37-81)
```python
@router.post("/admin-password")
async def set_admin_password(data: SetAdminPasswordRequest, request: Request):
    """
    Set admin password on first launch. No auth required, only works once.

    This endpoint is only available before setup is completed.
    Once setup_completed=true is set, this endpoint returns 403.

    Requirements:
    - Password must be at least 8 characters
    - Password and confirm_password must match
    """
    # 1. Check setup not already completed
    if db.get_setting_value('setup_completed', 'false') == 'true':
        raise HTTPException(
            status_code=403,
            detail="Setup already completed. Password cannot be changed through this endpoint."
        )

    # 2. Validate password length
    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    # 3. Validate passwords match
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    # 4. Hash password with bcrypt
    hashed_password = hash_password(data.password)

    # 5. Update admin user's password (creates user if doesn't exist)
    db.update_user_password('admin', hashed_password)

    # 6. Mark setup as completed
    db.set_setting('setup_completed', 'true')

    return {"success": True}
```

#### Password Hashing
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/dependencies.py:15-34`

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verify password against stored bcrypt hash.

    Security: Plaintext fallback removed (M-003, 2026-02-23).
    All passwords must be bcrypt hashed.
    """
    try:
        return pwd_context.verify(plain_password, stored_password)
    except Exception:
        # Invalid hash format - reject
        return False
```

**Security Note (M-003)**: The plaintext password fallback was removed on 2026-02-23. All passwords must be stored as bcrypt hashes. Invalid hash formats are rejected, returning `False` for authentication.

### Database Layer

#### User Password Update (Upsert Pattern)
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/db/users.py:129-162`

```python
def update_user_password(self, username: str, hashed_password: str) -> bool:
    """Update user's password hash, creating the user if it doesn't exist.

    For the admin user during first-time setup, this will create the user
    if it doesn't exist yet.

    Args:
        username: The username to update
        hashed_password: The bcrypt-hashed password

    Returns:
        True if the user was updated or created successfully
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        # Try to update existing user
        cursor.execute("""
            UPDATE users SET password_hash = ?, updated_at = ? WHERE username = ?
        """, (hashed_password, now, username))
        conn.commit()

        if cursor.rowcount > 0:
            return True

        # User doesn't exist - create it (for admin user during first-time setup)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, hashed_password, 'admin', username, now, now))
        conn.commit()
        return cursor.rowcount > 0
```

**Upsert Logic**:
1. First attempts UPDATE on existing user
2. If UPDATE affects 0 rows (user doesn't exist), performs INSERT
3. New admin users are created with role='admin' and username as email
4. This pattern ensures first-time setup works even on fresh deployments with no existing admin user

#### Settings Storage
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/db/settings.py:60-83`

```python
def set_setting(self, key: str, value: str) -> SystemSetting:
    """
    Set a system setting value (upsert).

    Creates the setting if it doesn't exist, updates if it does.
    Returns the updated setting.
    """
    now = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Use INSERT OR REPLACE for upsert
        cursor.execute("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, now))
        conn.commit()

        return SystemSetting(
            key=key,
            value=value,
            updated_at=datetime.fromisoformat(now)
        )
```

**Get Setting Value** (lines 49-58):
```python
def get_setting_value(self, key: str, default: str = None) -> Optional[str]:
    """
    Get just the value of a setting.

    Returns the default if the setting doesn't exist.
    """
    setting = self.get_setting(key)
    if setting:
        return setting.value
    return default
```

#### Database Table
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/database.py:522-527`

```sql
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Settings Used**:
| Key | Value | Purpose |
|-----|-------|---------|
| `setup_completed` | `"true"` / `"false"` | Gate setup endpoint, redirect logic |
| `anthropic_api_key` | `"sk-ant-..."` | API key for Claude |

### Login Block During Setup

**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/auth.py`

**Setup Check Function** (lines 20-22):
```python
def is_setup_completed() -> bool:
    """Check if initial setup is completed."""
    return db.get_setting_value('setup_completed', 'false') == 'true'
```

**Admin Login Block** (lines 49-78):
```python
@router.post("/token", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with username/password and get JWT token.

    Used for admin login (username 'admin' with password).
    Regular users should use email authentication.
    """
    # Block login if setup is not completed
    if not is_setup_completed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="setup_required"
        )
    # ... rest of login logic
```

**Email Login Request Block** (lines 153-158):
```python
# Block if setup is not completed
if not is_setup_completed():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="setup_required"
    )
```

**Email Login Verify Block** (lines 210-215):
```python
# Block if setup is not completed
if not is_setup_completed():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="setup_required"
    )
```

**Auth Mode Endpoint Reports Setup Status** (lines 27-46):
```python
@router.get("/api/auth/mode")
async def get_auth_mode():
    """
    Get authentication mode configuration.

    This endpoint requires NO authentication - it's called before login
    to determine which login options to show.

    Returns:
        - email_auth_enabled: Whether email-based login is enabled
        - setup_completed: Whether first-time setup is complete
    """
    email_auth_setting = db.get_setting_value("email_auth_enabled", str(EMAIL_AUTH_ENABLED).lower())
    email_auth_enabled = email_auth_setting.lower() == "true"

    return {
        "email_auth_enabled": email_auth_enabled,
        "setup_completed": is_setup_completed()
    }
```

---

## Flow 2: API Key Configuration

### Frontend Layer

#### Settings Page
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/Settings.vue`

**API Key Section** (lines 23-127):
- Input field with show/hide toggle
- Test button - calls `/api/settings/api-keys/anthropic/test`
- Save button - calls `PUT /api/settings/api-keys/anthropic`
- Status indicator showing: Not configured / Configured (from settings/env)

**Key Methods** (lines 313-374):
```javascript
async function loadApiKeyStatus() {
  const response = await axios.get('/api/settings/api-keys')
  anthropicKeyStatus.value = response.data.anthropic || { configured: false }
}

async function testApiKey() {
  const response = await axios.post('/api/settings/api-keys/anthropic/test', {
    api_key: anthropicKey.value
  })
  apiKeyTestResult.value = response.data.valid
}

async function saveApiKey() {
  const response = await axios.put('/api/settings/api-keys/anthropic', {
    api_key: anthropicKey.value
  })
  anthropicKeyStatus.value = {
    configured: true,
    masked: response.data.masked,
    source: 'settings'
  }
}
```

### Backend Layer

#### API Keys Endpoints
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/settings.py:361-588`

**GET /api/settings/api-keys** (line 394-430):
```python
@router.get("/api-keys")
async def get_api_keys_status(current_user: User = Depends(get_current_user)):
    """Get status of configured API keys. Admin-only."""
    require_admin(current_user)

    anthropic_key = get_anthropic_api_key()
    anthropic_configured = bool(anthropic_key)
    key_from_settings = bool(db.get_setting_value('anthropic_api_key', None))

    return {
        "anthropic": {
            "configured": anthropic_configured,
            "masked": mask_api_key(anthropic_key) if anthropic_configured else None,
            "source": "settings" if key_from_settings else ("env" if anthropic_configured else None)
        }
    }
```

**PUT /api/settings/api-keys/anthropic** (line 433-483):
```python
@router.put("/api-keys/anthropic")
async def update_anthropic_key(body: ApiKeyUpdate, current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    key = body.api_key.strip()
    if not key.startswith('sk-ant-'):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    db.set_setting('anthropic_api_key', key)
    return {"success": True, "masked": mask_api_key(key)}
```

**DELETE /api/settings/api-keys/anthropic** (line 486-519):
```python
@router.delete("/api-keys/anthropic")
async def delete_anthropic_key(current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    deleted = db.delete_setting('anthropic_api_key')
    env_key = os.getenv('ANTHROPIC_API_KEY', '')

    return {
        "success": True,
        "deleted": deleted,
        "fallback_configured": bool(env_key)
    }
```

**POST /api/settings/api-keys/anthropic/test** (line 522-587):
```python
@router.post("/api-keys/anthropic/test")
async def test_anthropic_key(body: ApiKeyTest, current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    key = body.api_key.strip()
    if not key.startswith('sk-ant-'):
        return {"valid": False, "error": "Invalid format"}

    # Make lightweight API call to validate
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            timeout=10.0
        )

        if response.status_code == 200:
            return {"valid": True}
        elif response.status_code == 401:
            return {"valid": False, "error": "Invalid API key"}
```

#### Key Retrieval Function
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/settings.py:379-384`

```python
def get_anthropic_api_key() -> str:
    """Get Anthropic API key from settings, fallback to env var."""
    key = db.get_setting_value('anthropic_api_key', None)
    if key:
        return key
    return os.getenv('ANTHROPIC_API_KEY', '')
```

---

## Flow 3: Agent Uses Stored API Key

### Agent Creation
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/agents.py:508-512`

```python
env_vars = {
    'AGENT_NAME': config.name,
    'AGENT_TYPE': config.type,
    'ANTHROPIC_API_KEY': get_anthropic_api_key(),  # Uses settings value OR env fallback
    # ...
}
```

### System Agent Service
**File**: `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/system_agent_service.py:24, 180`

```python
from routers.settings import get_anthropic_api_key

# During system agent container creation:
env_vars = {
    # ...
    'ANTHROPIC_API_KEY': get_anthropic_api_key(),
}
```

---

## Side Effects

### Audit Logging

| Event | Type | Action | Details |
|-------|------|--------|---------|
| Password set | `setup` | `admin_password` | `result: success` |
| Setup blocked | `setup` | `admin_password` | `result: blocked, reason: already completed` |
| API key read | `system_settings` | `read_api_keys` | - |
| API key update | `system_settings` | `update_anthropic_key` | `key_masked: ...xxxx` |
| API key delete | `system_settings` | `delete_anthropic_key` | `deleted: true/false` |
| API key test | `system_settings` | `test_anthropic_key` | `valid: true/false` |

---

## Error Handling

| Error Case | HTTP Status | Message | Handling |
|------------|-------------|---------|----------|
| Setup already completed | 403 | "Setup already completed" | Frontend redirects to /login after 2s |
| Password too short | 400 | "Password must be at least 8 characters" | Form validation |
| Passwords don't match | 400 | "Passwords do not match" | Form validation |
| Invalid API key format | 400 | "Invalid API key format. Keys start with 'sk-ant-'" | Inline error |
| API key invalid | N/A | `{valid: false, error: "..."}` | Test result display |
| Not admin | 403 | "Admin access required" | Redirect to dashboard |
| Login blocked (no setup) | 403 | "setup_required" | Frontend checks and redirects |

---

## Security Considerations

1. **Password Security**:
   - Bcrypt hashing with auto-configured work factor
   - **No plaintext fallback (M-003)**: Plaintext password comparison removed as of 2026-02-23. All passwords must be bcrypt hashed.
   - Invalid hash formats are rejected (returns authentication failure)
   - Minimum 8 character requirement
   - Setup endpoint only works ONCE

2. **API Key Security**:
   - Never exposed in full (masked in responses)
   - Format validation (`sk-ant-` prefix)
   - Admin-only access to all API key endpoints
   - Fallback to environment variable if not in settings

3. **Setup Endpoint Protection**:
   - No auth required (must work on fresh install)
   - Self-disabling after first use via `setup_completed` flag
   - Audit logged even on blocked attempts

4. **Login Block**:
   - Login endpoint returns 403 with `setup_required` until admin password set
   - Prevents access with default password

---

## Testing

### Prerequisites
- Fresh database (delete `~/trinity-data/trinity.db`) or reset `setup_completed` setting
- Backend and frontend running

### Test Steps

**Flow 1: First-Time Setup**

1. **Delete existing setup flag**
   ```sql
   DELETE FROM system_settings WHERE key = 'setup_completed';
   ```

2. **Visit any page** (e.g., `http://localhost:3000/`)
   - **Expected**: Redirect to `/setup`
   - **Verify**: URL shows `/setup`, setup form displayed

3. **Try weak password** (less than 8 chars)
   - **Expected**: Submit button disabled
   - **Verify**: Strength indicator shows "Weak"

4. **Enter mismatched passwords**
   - **Expected**: "Passwords do not match" indicator
   - **Verify**: Submit button disabled

5. **Enter valid password** (8+ chars, matching)
   - **Expected**: Submit enabled, strength indicator updates
   - **Verify**: Click "Set Password & Continue"

6. **After successful setup**
   - **Expected**: Redirect to `/login`
   - **Verify**: Can log in with `admin` / new password

7. **Try accessing /setup again**
   - **Expected**: Redirect to `/login` (setup already done)

**Flow 2: API Key Configuration**

1. **Login as admin**, navigate to Settings

2. **Check initial status**
   - **Expected**: "Not configured" warning if no env var

3. **Enter invalid key format** (e.g., "test123")
   - Click Test
   - **Expected**: "Invalid format" error

4. **Enter valid format but invalid key** (e.g., "sk-ant-fake123")
   - Click Test
   - **Expected**: "Invalid API key" error

5. **Enter valid API key**
   - Click Test
   - **Expected**: "API key is valid!" success

6. **Save the key**
   - Click Save
   - **Expected**: Status changes to "Configured (from settings)"

7. **Create an agent**
   - **Verify**: Agent can use Claude (API key injected)

### Edge Cases

- **Multiple setup attempts**: Second POST to `/api/setup/admin-password` returns 403
- **Env fallback**: Delete key from settings, env var should be used
- **Non-admin access**: Settings page returns 403 for non-admin users

### Cleanup

```sql
-- Reset to fresh state
DELETE FROM system_settings WHERE key IN ('setup_completed', 'anthropic_api_key');
UPDATE users SET password_hash = 'changeme' WHERE username = 'admin';
```

### Status
- First-Time Setup: **Working** (Implemented 2025-12-23)
- API Key Configuration: **Working** (Implemented 2025-12-23)

---

## Related Flows

### Upstream
- None (this is the entry point for fresh installations)

### Downstream
- **Agent Lifecycle**: Uses stored API key via `get_anthropic_api_key()`
- **System Agent**: Uses stored API key for trinity-system operations
- **Authentication**: Login blocked until setup completed

---

## Revision History

| Date | Change | Details |
|------|--------|---------|
| 2025-12-23 | Initial documentation | First-time setup and API key configuration flows |
| 2026-01-14 | Bug fix: Admin user upsert | Fixed `update_user_password()` to create admin user if it doesn't exist. Previously, on fresh deployment with empty ADMIN_PASSWORD env var, the UPDATE query affected 0 rows but setup_completed was still set to true, leaving users unable to login. The method now uses an upsert pattern: UPDATE first, then INSERT if no rows affected. See `src/backend/db/users.py:129-162`. |
| 2026-01-23 | Line number verification | Updated all line numbers to match current codebase. Verified: setup.py endpoints (22-34, 37-81), auth.py login blocks (20-22, 49-78, 153-158, 210-215), dependencies.py password hashing (15-37), db/users.py upsert (129-162), db/settings.py (49-83), router/index.js guards (165-220, 242-245), SetupPassword.vue (166-176, 205-207, 209-236). Added documentation for email auth login blocking and password strength validation. |
| 2026-02-23 | Security Fix M-003 | Removed plaintext password fallback from `verify_password()` in dependencies.py:24-34. All passwords must now be bcrypt hashed. Invalid hash formats are rejected. Updated Password Hashing section and Security Considerations. |
