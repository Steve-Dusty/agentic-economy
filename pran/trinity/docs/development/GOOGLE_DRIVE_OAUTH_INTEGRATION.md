# Google Drive OAuth Integration Requirements

> **⚠️ OUTDATED (2026-02-06)**: This document references the old Redis-based credential system (`credentials.py`).
> As of CRED-002 (2026-02-05), credentials are now stored as files in agent containers (`.env`, `.credentials.enc`).
> The OAuth flow may still work, but the storage/injection mechanism described here is no longer accurate.
> See `docs/memory/feature-flows/credential-injection.md` for the current system.

**Date**: 2025-12-01
**Status**: ⚠️ Needs Update (CRED-002)
**Priority**: High
**Estimated Effort**: 2-3 hours

---

## Overview

Enable Google Drive access in Trinity agents via OAuth credentials acquired through the frontend UI, injected into agent containers, and used by Google Drive MCP servers.

## Problem Statement

Trinity already has:
- ✅ Google OAuth2 flow with `drive.readonly` scope
- ✅ Credential storage in Redis
- ✅ Credential injection into agent containers
- ✅ Template-based `.mcp.json` generation with `${VAR}` placeholders

**Gap**: OAuth credentials stored in Redis don't match the naming convention expected by Google Drive MCP servers.

### Current State

**OAuth tokens stored in Redis** (after OAuth callback):
```json
{
  "access_token": "ya29...",
  "refresh_token": "1//...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "..."
}
```

**What Google Drive MCP expects** (in `.mcp.json.template`):
```json
{
  "mcpServers": {
    "google-drive": {
      "env": {
        "GOOGLE_CLIENT_ID": "${GOOGLE_CLIENT_ID}",
        "GOOGLE_CLIENT_SECRET": "${GOOGLE_CLIENT_SECRET}",
        "GOOGLE_REFRESH_TOKEN": "${GOOGLE_REFRESH_TOKEN}"
      }
    }
  }
}
```

**Mismatch**:
1. Token names: `refresh_token` vs `GOOGLE_REFRESH_TOKEN`
2. Missing: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (currently backend env vars)

---

## Solution Architecture: Option A (Per-User OAuth Credentials)

Store complete OAuth configuration (including client ID/secret) in user credentials for maximum flexibility and security.

### Benefits
- ✅ More secure - isolated OAuth apps per user
- ✅ Multi-tenant ready - different orgs can use different OAuth apps
- ✅ Cleaner architecture - all credentials in Redis
- ✅ Already 80% compatible - `get_agent_credentials` handles name matching

---

## Implementation Requirements

### 1. Modify OAuth Token Exchange

**File**: `src/backend/credentials.py`
**Function**: `exchange_oauth_code` (lines 304-336)

**Current behavior**: Returns only tokens from Google
**Required behavior**: Include client credentials in return value

**Code change**:
```python
async def exchange_oauth_code(
    self,
    provider: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> Optional[Dict]:
    config = OAuthConfig.PROVIDERS.get(provider)
    if not config:
        return None

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                config["token_url"],
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                },
                headers={"Accept": "application/json"}
            )

            if response.status_code == 200:
                tokens = response.json()

                # ADD: Include client credentials for MCP compatibility
                tokens['client_id'] = client_id
                tokens['client_secret'] = client_secret

                return tokens

        except Exception as e:
            print(f"OAuth exchange error: {e}")

    return None
```

**Test**: Verify `tokens` dict includes `client_id` and `client_secret` keys

---

### 2. Normalize Credential Names in OAuth Callback

**File**: `src/backend/routers/credentials.py`
**Function**: `oauth_callback` (lines 286-339)

**Current behavior**: Stores raw OAuth response in Redis
**Required behavior**: Store with both raw names AND MCP-compatible names

**Code change**:
```python
@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request
):
    # ... existing validation code ...

    tokens = await credential_manager.exchange_oauth_code(
        provider,
        code,
        config["client_id"],
        config["client_secret"],
        state_data["redirect_uri"]
    )

    if not tokens:
        raise HTTPException(status_code=500, detail="Failed to exchange OAuth code")

    # MODIFY: Normalize credential names for MCP compatibility
    normalized_creds = {
        # Original OAuth response fields
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
        "scope": tokens.get("scope"),
    }

    # ADD: MCP-compatible naming for Google Drive (and other Google services)
    if provider == "google":
        normalized_creds.update({
            "GOOGLE_ACCESS_TOKEN": tokens.get("access_token"),
            "GOOGLE_REFRESH_TOKEN": tokens.get("refresh_token"),
            "GOOGLE_CLIENT_ID": tokens.get("client_id"),
            "GOOGLE_CLIENT_SECRET": tokens.get("client_secret"),
        })

    # ADD: Similar normalization for other providers if needed
    elif provider == "slack":
        normalized_creds.update({
            "SLACK_ACCESS_TOKEN": tokens.get("access_token"),
            "SLACK_BOT_TOKEN": tokens.get("bot_token"),
        })

    # Continue with existing credential creation
    cred_data = CredentialCreate(
        name=f"{provider.title()} OAuth - {datetime.now().strftime('%Y-%m-%d')}",
        service=provider,
        type="oauth2",
        credentials=normalized_creds,  # Use normalized credentials
        description=f"OAuth connection created via authorization flow"
    )

    credential = credential_manager.create_credential(state_data["user_id"], cred_data)

    # ... rest of function ...
```

**Test**: After OAuth flow, check Redis has both `refresh_token` AND `GOOGLE_REFRESH_TOKEN`

---

### 3. Verify Existing Code Handles Name Matching

**File**: `src/backend/credentials.py`
**Function**: `get_agent_credentials` (lines 211-249)

**No changes needed** - existing code already handles this!

**Verification**: Confirm this code correctly extracts GOOGLE_* credentials:
```python
# Line 236-248
if user_id:
    user_credentials = self.list_credentials(user_id)
    for cred in user_credentials:
        secret = self.get_credential_secret(cred.id, user_id)
        if secret:
            # Add each key-value pair from the credential
            for key, value in secret.items():
                key_upper = key.upper()
                if key_upper not in agent_creds:
                    agent_creds[key_upper] = value
```

This means `GOOGLE_CLIENT_ID` in Redis → available as `agent_creds['GOOGLE_CLIENT_ID']` ✅

---

### 4. Verify Template Processing Works

**File**: `src/backend/services/template_service.py`
**Function**: `generate_credential_files` (lines 228-299)

**No changes needed** - existing code handles `${VAR}` replacement:
```python
# Line 258-263
for env_key, env_val in server_config["env"].items():
    if isinstance(env_val, str) and env_val.startswith("${") and env_val.endswith("}"):
        var_name = env_val[2:-1]
        real_value = agent_credentials.get(var_name, "")
        server_config["env"][env_key] = real_value
```

**Test**: Verify `${GOOGLE_CLIENT_ID}` → actual client ID value

---

## Testing Plan

### Test 1: OAuth Flow Credential Storage

**Steps**:
1. Go to Credentials page → Click "Connect Google"
2. Complete OAuth flow
3. Check Redis for credential:
   ```bash
   redis-cli
   > GET credentials:{cred_id}:secret
   ```
4. **Expected**: JSON contains all keys:
   - `access_token`
   - `refresh_token`
   - `GOOGLE_ACCESS_TOKEN`
   - `GOOGLE_REFRESH_TOKEN`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

**Pass Criteria**: All 6 keys present with correct values

---

### Test 2: Create Google Drive Test Template

**File**: `config/agent-templates/google-drive-test/template.yaml`
```yaml
name: google-drive-test
display_name: "Google Drive Test Agent"
description: "Test agent for Google Drive access"
version: "1.0"

resources:
  cpu: "1"
  memory: "2g"

credentials:
  mcp_servers:
    google-drive:
      env_vars:
        - GOOGLE_CLIENT_ID
        - GOOGLE_CLIENT_SECRET
        - GOOGLE_REFRESH_TOKEN
```

**File**: `config/agent-templates/google-drive-test/.mcp.json`
```json
{
  "mcpServers": {
    "google-drive": {
      "command": "npx",
      "args": ["-y", "google-drive-mcp"],
      "env": {
        "GOOGLE_CLIENT_ID": "${GOOGLE_CLIENT_ID}",
        "GOOGLE_CLIENT_SECRET": "${GOOGLE_CLIENT_SECRET}",
        "GOOGLE_REFRESH_TOKEN": "${GOOGLE_REFRESH_TOKEN}"
      }
    }
  }
}
```

**File**: `config/agent-templates/google-drive-test/CLAUDE.md`
```markdown
# Google Drive Test Agent

You can access Google Drive files using the google-drive MCP server.

Available tools:
- List files and folders
- Search Drive
- Read file contents
- Get file metadata

Test by asking: "List the files in my Google Drive"
```

---

### Test 3: Agent Creation with Google Drive

**Steps**:
1. Complete Test 1 (have Google OAuth credential)
2. Create agent from `google-drive-test` template via UI
3. Check agent logs:
   ```bash
   docker logs agent-google-drive-test
   ```
4. Exec into container and check credentials:
   ```bash
   docker exec -it agent-google-drive-test bash
   cat ~/.mcp.json
   ```
5. **Expected**: `.mcp.json` has real values (no `${...}` placeholders)

**Pass Criteria**: All placeholders replaced with actual credential values

---

### Test 4: Google Drive MCP Functionality

**Steps**:
1. Start agent from Test 3
2. Open agent chat in UI
3. Send message: "List the files in my Google Drive"
4. **Expected**: Agent responds with actual Drive files

**Pass Criteria**: Agent successfully calls Google Drive API and returns file list

---

## Success Criteria

- [ ] OAuth flow stores 6+ credential keys in Redis (including normalized names)
- [ ] Agent creation extracts GOOGLE_* credentials from Redis
- [ ] Template processing replaces `${GOOGLE_CLIENT_ID}` with real value
- [ ] Agent container has working `.mcp.json` with no placeholders
- [ ] Agent can successfully call Google Drive MCP tools
- [ ] No breaking changes to existing OAuth flows (Slack, GitHub, Notion)

---

## Rollback Plan

If issues arise:
1. Revert changes to `exchange_oauth_code`
2. Revert changes to `oauth_callback`
3. Existing credentials in Redis remain intact (backward compatible)
4. Users can re-authorize OAuth connections

---

## Edge Cases to Handle

### 1. Existing Credentials
**Issue**: Users who already have Google OAuth credentials won't have normalized names
**Solution**:
- Add migration endpoint: `POST /api/credentials/{id}/normalize`
- Or: Prompt user to re-authorize Google connection
- Or: Auto-detect and normalize on next agent creation

### 2. Token Expiry
**Issue**: Access tokens expire, need refresh
**Solution**: Google Drive MCP servers typically handle refresh automatically using refresh_token

### 3. Scope Changes
**Issue**: If scopes change in `OAuthConfig`, existing tokens may not have permission
**Solution**: Document required scopes in template.yaml, prompt re-auth if needed

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `src/backend/credentials.py` | Add client creds to token response | ~330 |
| `src/backend/routers/credentials.py` | Normalize credential names | ~315-323 |
| `config/agent-templates/google-drive-test/` | Create test template | NEW |

**No changes needed**:
- `src/backend/credentials.py::get_agent_credentials` (already handles name matching)
- `src/backend/services/template_service.py::generate_credential_files` (already replaces placeholders)

---

## Documentation Updates

After implementation, update:
- `docs/development/CREDENTIAL_MANAGEMENT.md` - Add Google Drive example
- `docs/AGENT_TEMPLATE_SPEC.md` - Add Google OAuth credential pattern
- `docs/memory/changelog.md` - Document feature addition
- `docs/memory/requirements.md` - Mark OAuth credential enhancement complete

---

## Future Enhancements (Out of Scope)

- [ ] Token refresh UI indicator
- [ ] Per-MCP-server credential scoping
- [ ] OAuth app marketplace (multiple OAuth apps per provider)
- [ ] Credential sharing between agents
- [ ] Audit logging for credential access from MCP servers

---

## References

- Current OAuth flow: `src/backend/routers/credentials.py:246-339`
- Credential injection: `src/backend/routers/agents.py:195-210`
- Template processing: `src/backend/services/template_service.py:228-299`
- Google Drive MCP: https://github.com/piotr-agier/google-drive-mcp
- Alternative MCP: https://github.com/felores/gdrive-mcp-server

---

## Questions for Implementation

1. Should we normalize credentials for ALL providers (Slack, GitHub, Notion) or just Google initially?
2. Should we auto-normalize existing Google credentials or require re-authorization?
3. Should client ID/secret be optional (fallback to env vars) or required?

**Recommended answers**:
1. Normalize ALL providers for consistency
2. Add re-authorization prompt in UI if normalized keys missing
3. Required (store per-user for multi-tenant support)
