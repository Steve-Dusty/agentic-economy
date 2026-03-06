# Feature: System-Wide Trinity Prompt

## Overview
Allows admins to set a custom system prompt (Trinity Prompt) that gets injected into ALL agents' CLAUDE.md files at startup, enabling platform-wide custom instructions for all agents.

## User Story
As an admin, I want to define custom instructions that apply to all agents so that I can enforce platform-wide policies, coding standards, or behavioral guidelines without configuring each agent individually.

## Entry Points
- **UI**: `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/Settings.vue` - Settings page with Trinity Prompt textarea editor
- **API**: `GET/PUT/DELETE /api/settings/{key}` where key is `trinity_prompt`

## Frontend Layer

### Components
- `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/views/Settings.vue` - Full Settings page with:
  - Textarea for editing Trinity Prompt (lines 240-252)
  - Save/Clear buttons (lines 267-286)
  - Character count display (line 262)
  - Unsaved changes indicator (line 263)
  - Error message display (lines 456-468)
  - Success message display (lines 470-482)
  - Info box explaining how it works (lines 432-452)

### State Management
- `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/stores/settings.js`
  - `fetchSettings()` - Fetches all settings from backend (lines 23-43)
  - `updateSetting(key, value)` - Updates a setting via PUT (lines 66-81)
  - `deleteSetting(key)` - Deletes a setting via DELETE (lines 87-102)
  - `trinityPrompt` getter - Returns settings['trinity_prompt'] (lines 13-15)

### API Calls
```javascript
// Fetch all settings
await axios.get('/api/settings')

// Update trinity_prompt
await axios.put('/api/settings/trinity_prompt', { value: promptText })

// Delete/clear trinity_prompt
await axios.delete('/api/settings/trinity_prompt')
```

### Routing
- `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/router/index.js:138-142`
  - Route: `/settings` -> `Settings.vue`
  - Meta: `requiresAuth: true, requiresAdmin: true`

### Navigation
- `/Users/eugene/Dropbox/trinity/trinity/src/frontend/src/components/NavBar.vue:46-53`
  - Settings link conditionally rendered: `v-if="isAdmin"` (line 47)
  - Admin check via `GET /api/users/me` response role field (lines 254-261)

## Backend Layer

### Settings Service
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/settings_service.py` - Centralized settings retrieval
  - `SettingsService` class (lines 49-101)
  - `get_setting(key, default)` method (lines 59-62)
  - Singleton instance `settings_service` (line 104)

### Endpoints
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/routers/settings.py`
  - `GET /api/settings` (line 75) - List all settings (admin-only)
  - `GET /api/settings/{key}` (line 510) - Get specific setting (admin-only)
  - `PUT /api/settings/{key}` (line 537) - Create/update setting (admin-only)
  - `DELETE /api/settings/{key}` (line 559) - Delete setting (admin-only)

### Business Logic
1. **Admin Check** (lines 69-72):
   ```python
   def require_admin(current_user: User):
       if current_user.role != "admin":
           raise HTTPException(status_code=403, detail="Admin access required")
   ```

2. **Setting Storage**: Uses `db.set_setting(key, value)` for upsert

### Database Operations
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/db/settings.py` - `SettingsOperations` class

**Table**: `system_settings`
```sql
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Setting Key**: `trinity_prompt`

**Operations**:
- `get_setting(key)` - SELECT by key (lines 31-47)
- `get_setting_value(key, default)` - Get just the value (lines 49-58)
- `set_setting(key, value)` - INSERT OR REPLACE (lines 60-83)
- `delete_setting(key)` - DELETE by key (lines 85-98)
- `get_all_settings()` - Get all settings (lines 100-114)
- `get_settings_dict()` - Get settings as key-value dict (lines 116-123)

### Models
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/db_models.py:285-294`
  ```python
  class SystemSetting(BaseModel):
      key: str
      value: str
      updated_at: datetime

  class SystemSettingUpdate(BaseModel):
      value: str
  ```

## Agent Injection Flow

### Backend Agent Startup
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/agent_service/lifecycle.py:62-89`
  - `inject_trinity_meta_prompt(agent_name)` function
  - Called during `start_agent_internal()` (line 211)

**Injection Logic** (lines 77-89):
```python
# Fetch system-wide custom prompt setting
custom_prompt = db.get_setting_value("trinity_prompt", default=None)
if custom_prompt:
    logger.info(f"Found trinity_prompt setting ({len(custom_prompt)} chars), will inject into {agent_name}")

# Use AgentClient for injection (handles retries internally)
client = get_agent_client(agent_name)
return await client.inject_trinity_prompt(
    custom_prompt=custom_prompt,
    force=False,
    max_retries=max_retries,
    retry_delay=retry_delay
)
```

### Agent Client
- `/Users/eugene/Dropbox/trinity/trinity/src/backend/services/agent_client.py:390-456`
  - `inject_trinity_prompt()` method handles retries and HTTP communication
  - Sends POST to `/api/trinity/inject` with `custom_prompt` payload

**Client Injection Code** (lines 390-456):
```python
async def inject_trinity_prompt(
    self,
    custom_prompt: Optional[str] = None,
    force: bool = False,
    timeout: float = None,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Dict[str, Any]:
    payload = {"force": force}
    if custom_prompt:
        payload["custom_prompt"] = custom_prompt
    # ... retries and HTTP request to /api/trinity/inject
```

### Agent-Server Injection
- `/Users/eugene/Dropbox/trinity/trinity/docker/base-image/agent_server/routers/trinity.py:54-202`
  - `POST /api/trinity/inject` endpoint (line 54)
  - Handles `TrinityInjectRequest.custom_prompt` field

**Custom Instructions Injection** (lines 137-145):
```python
# Build the custom instructions section if provided
custom_section = ""
if request.custom_prompt and request.custom_prompt.strip():
    custom_section = f"""

## Custom Instructions

{request.custom_prompt.strip()}
"""
    logger.info("Custom prompt provided, will inject into CLAUDE.md")
```

**CLAUDE.md Update** (lines 148-187):
- If CLAUDE.md exists and has Trinity section: Update/append Custom Instructions
- If CLAUDE.md exists without Trinity: Add both sections
- If CLAUDE.md doesn't exist: Create with Trinity + Custom sections
- Removes existing "## Custom Instructions" before updating (lines 152-161)
- Tracks `had_custom_instructions` flag to ensure removal when prompt is cleared (lines 153, 160)

**Key Logic** (lines 163-178):
```python
if "## Trinity Agent System" not in content:
    with open(claude_md_path, "a") as f:
        f.write(trinity_section)
        f.write(custom_section)
    claude_md_updated = True
elif custom_section or had_custom_instructions:
    # Trinity section exists, update file if custom section changed
    with open(claude_md_path, "w") as f:
        f.write(content)
        f.write(custom_section)
    claude_md_updated = True
```

### Models
- `/Users/eugene/Dropbox/trinity/trinity/docker/base-image/agent_server/models.py:186-189`
  ```python
  class TrinityInjectRequest(BaseModel):
      force: bool = False  # If true, re-inject even if already done
      custom_prompt: Optional[str] = None  # System-wide custom prompt to inject into CLAUDE.md
  ```

## Data Flow Diagram

```
+-------------+      +----------------+      +------------------+
| Settings.vue| ---> | settings.js    | ---> | PUT /api/settings|
| (Admin UI)  |      | (Pinia Store)  |      | /trinity_prompt  |
+-------------+      +----------------+      +------------------+
                                                    |
                                                    v
                                            +------------------+
                                            | system_settings  |
                                            | (SQLite table)   |
                                            +------------------+

                            (Later, when agent starts)

+------------------+      +------------------------+      +-------------------+
| POST /api/agents | ---> | inject_trinity_meta_   | ---> | AgentClient       |
| /{name}/start    |      | prompt()               |      | inject_trinity_   |
+------------------+      | (reads trinity_prompt) |      | prompt()          |
                          +------------------------+      +-------------------+
                                                                   |
                                                                   v
                                                          +-------------------+
                                                          | agent-server      |
                                                          | POST /api/trinity |
                                                          | /inject           |
                                                          +-------------------+
                                                                   |
                                                                   v
                                                          +-------------------+
                                                          | CLAUDE.md         |
                                                          | ## Custom         |
                                                          | Instructions      |
                                                          +-------------------+
```

## Side Effects

### No Audit Logging
The current implementation does not log settings CRUD operations via audit logging.

### No WebSocket Broadcasts
This feature does not broadcast changes via WebSocket. Agents only receive the prompt when they start/restart.

## Error Handling

| Error Case | HTTP Status | Message | Location |
|------------|-------------|---------|----------|
| Not admin | 403 | "Admin access required" | settings.py:72 |
| Setting not found (GET) | 404 | "Setting '{key}' not found" | settings.py:528 |
| Database error | 500 | "Failed to get/update/delete setting: {error}" | settings.py |
| Agent not reachable | N/A | Returns error in injection result | agent_client.py:450 |

## Security Considerations

### Authorization
- All `/api/settings` endpoints require admin role
- `require_admin()` check on every endpoint (lines 85, 110, 152, 186, 214, 274, 308, 336, 439, 458, 492, 522, 549, 570, 595, 631, 664 in settings.py)
- Frontend NavBar hides Settings link for non-admins (NavBar.vue line 47)
- Router meta requires admin: `requiresAdmin: true` (router/index.js line 141)

### Input Validation
- Pydantic `SystemSettingUpdate` model validates request body
- No character limit enforced (could store large prompts)
- Markdown content allowed (injected as-is into CLAUDE.md)

## Testing

### Prerequisites
- Trinity platform running (`./scripts/deploy/start.sh`)
- Admin user logged in

### Test Steps

1. **Access Settings Page**
   - Action: Navigate to `/settings` as admin
   - Expected: Settings page loads with Trinity Prompt section
   - Verify: Textarea visible, Save/Clear buttons present

2. **Non-Admin Access Denied**
   - Action: Try to access `/settings` as non-admin user
   - Expected: Redirected to `/` or 403 error on API call
   - Verify: Settings link not visible in NavBar

3. **Save Trinity Prompt**
   - Action: Enter text in textarea, click "Save Changes"
   - Expected: Success message appears, "Unsaved changes" clears
   - Verify: `GET /api/settings/trinity_prompt` returns saved value

4. **Clear Trinity Prompt**
   - Action: Click "Clear" button
   - Expected: Textarea emptied, setting deleted
   - Verify: `GET /api/settings/trinity_prompt` returns 404

5. **Agent Receives Prompt**
   - Action: Save a prompt, then start a new agent
   - Expected: Agent's CLAUDE.md contains "## Custom Instructions" section
   - Verify: SSH into agent, check CLAUDE.md content

6. **Restart Agent Updates Prompt**
   - Action: Update trinity_prompt, restart existing agent
   - Expected: Agent's CLAUDE.md updated with new content
   - Verify: Check CLAUDE.md after restart

### Automated Tests

**Test File**: `/Users/eugene/Dropbox/trinity/trinity/tests/test_settings.py`

**Test Classes**:

| Class | Lines | Tests | Coverage |
|-------|-------|-------|----------|
| `TestSettingsEndpointsAuthentication` | 24-51 | 4 | Auth required for all endpoints |
| `TestSettingsEndpointsAdmin` | 54-149 | 6 | Admin CRUD operations |
| `TestTrinityPromptSetting` | 151-238 | 3 | Trinity prompt specific operations |
| `TestTrinityPromptInjection` | 241-415 | 3 | Agent injection verification (slow) |
| `TestSettingsValidation` | 418-454 | 3 | Input validation |

**Key Test Cases**:
- `test_list_settings_requires_auth` (line 29) - Verifies 401 without token
- `test_create_and_get_setting` (line 75) - Full CRUD cycle
- `test_trinity_prompt_crud` (line 156) - Specific trinity_prompt handling
- `test_agent_receives_prompt_on_creation` (line 249) - Verifies CLAUDE.md injection
- `test_prompt_removed_when_cleared` (lines 355-415) - Verifies bug fix

### Status
**Last Tested**: 2025-12-14
**Tested By**: claude
**Status**: All tests passed (19/19)

**Test Results**:
- Settings API (CRUD operations): Working
- Trinity Prompt injection on agent creation: Working
- Trinity Prompt update on agent restart: Working
- Trinity Prompt removal when cleared: Working (bug fixed)

## Known Issues / Bug Fixes

### Bug Fix: Custom Instructions Not Removed When Cleared (2025-12-14)

**Issue**: When clearing the `trinity_prompt` setting, the "## Custom Instructions" section was not being removed from CLAUDE.md on agent restart.

**Root Cause**: The condition only checked for `custom_section` being non-empty, so when the prompt was cleared (empty `custom_section`), the code would not rewrite CLAUDE.md even though it had stripped out the old Custom Instructions section.

**Fix Location**: `/Users/eugene/Dropbox/trinity/trinity/docker/base-image/agent_server/routers/trinity.py`

**Changes**:
1. Added `had_custom_instructions` flag tracking at lines 153-161:
   ```python
   had_custom_instructions = False
   if "## Custom Instructions" in content:
       # ... strip existing section ...
       had_custom_instructions = True
   ```

2. Modified condition at line 169 from:
   ```python
   elif custom_section:
   ```
   to:
   ```python
   elif custom_section or had_custom_instructions:
   ```

3. Added log message at line 178:
   ```python
   logger.info("Removed Custom Instructions from CLAUDE.md")
   ```

**Verification**: Test `test_prompt_removed_when_cleared` in `/Users/eugene/Dropbox/trinity/trinity/tests/test_settings.py` validates the fix.

## Related Flows
- **Upstream**: Admin authentication (auth0-authentication.md)
- **Downstream**: Agent Lifecycle (agent-lifecycle.md) - Trinity injection at startup

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-13 | claude | Document created, feature implemented |
| 2025-12-14 | claude | Bug fix: Custom instructions removal when cleared |
| 2025-12-19 | claude | Verified line numbers against current codebase |
| 2026-01-23 | claude | Updated line numbers after refactoring: settings_service.py extracted, agent_client.py added, router line numbers updated, test file expanded |
