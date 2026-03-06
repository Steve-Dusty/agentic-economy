# Phase 24: Credential Management

> **Purpose**: Validate credential CRUD, bulk import, OAuth, and agent credential assignment
> **Duration**: ~25 minutes
> **Assumes**: Phase 1 PASSED (authenticated)
> **Output**: Full credential management flow verified

---

## Background

**Credential Management** (CRED-001 to CRED-013):
- Store API keys and secrets securely in Redis
- Assign credentials to agents for MCP server access
- Bulk import from .env file format
- OAuth2 flows for Google, Slack, GitHub, Notion
- Hot-reload credentials on running agents

**User Stories**:
- CRED-001: Add credentials
- CRED-002: List credentials
- CRED-003: Update credentials
- CRED-004: Delete credentials
- CRED-005: Bulk import from .env
- CRED-006: OAuth provider authentication
- CRED-007: See OAuth provider status
- CRED-008: See agent credential requirements
- CRED-009: Assign credentials to agents
- CRED-010: Bulk assign credentials
- CRED-011: Reload credentials on running agent
- CRED-012: Hot-reload credentials via paste
- CRED-013: Check credential file status

---

## Prerequisites

- [ ] Phase 1 PASSED (authenticated)
- [ ] Redis running
- [ ] At least one agent created (for assignment testing)

---

## Test: Add Credentials

### Step 1: Navigate to Credentials Page
**Action**:
- Go to http://localhost/credentials
- Or click "Credentials" in navigation

**Expected**:
- [ ] Credentials page loads
- [ ] List of existing credentials (may be empty)
- [ ] "Add Credential" button visible

---

### Step 2: Add New Credential
**Action**:
- Click "Add Credential" button
- Fill in form:
  - Name: `TEST_API_KEY`
  - Value: `test-secret-value-12345`
  - Service: `testing`
- Click Save

**Expected**:
- [ ] Form accepts input
- [ ] Value field is password type (masked)
- [ ] Save button submits
- [ ] Success message displayed

**Verify**:
- [ ] Credential appears in list
- [ ] Name shown, value hidden
- [ ] Service/type shown

---

### Step 3: Add Second Credential
**Action**:
- Add another credential:
  - Name: `OPENAI_API_KEY`
  - Value: `sk-test-openai-key`
  - Service: `openai`
- Save

**Expected**:
- [ ] Second credential added
- [ ] List shows both credentials
- [ ] Sorted by name or date

---

## Test: List Credentials

### Step 4: Verify Credential List
**Action**:
- Review the credentials list
- Check displayed information

**Expected**:
- [ ] All credentials listed
- [ ] Name visible
- [ ] Service/type visible
- [ ] Value is HIDDEN (not displayed)
- [ ] Created date shown

**Verify**:
- [ ] No secret values exposed in UI
- [ ] Cannot copy secret from list view

---

### Step 5: Search/Filter Credentials (if implemented)
**Action**:
- Look for search or filter input
- Search for "API"

**Expected**:
- [ ] Results filtered to matching credentials
- [ ] Both TEST_API_KEY and OPENAI_API_KEY shown

---

## Test: Update Credentials

### Step 6: Edit Credential
**Action**:
- Click edit icon on TEST_API_KEY
- Change value to: `updated-secret-value-67890`
- Save

**Expected**:
- [ ] Edit modal/form opens
- [ ] Can modify value
- [ ] Save updates credential
- [ ] Success message

**Verify**:
- [ ] Timestamp updated
- [ ] Old value replaced

---

## Test: Delete Credentials

### Step 7: Delete Credential
**Action**:
- Click delete icon on OPENAI_API_KEY
- Confirm deletion

**Expected**:
- [ ] Confirmation dialog appears
- [ ] "Are you sure?" message
- [ ] Confirm deletes credential
- [ ] Credential removed from list

**Verify**:
- [ ] Credential no longer in list
- [ ] Cannot retrieve deleted credential

---

## Test: Bulk Import

### Step 8: Bulk Import from .env Format
**Action**:
- Click "Bulk Import" or "Import" button
- Paste the following:
```
GOOGLE_API_KEY=google-test-key-123
SLACK_BOT_TOKEN=xoxb-slack-test-token
GITHUB_TOKEN=ghp_test_github_token
```
- Submit import

**Expected**:
- [ ] Parser accepts .env format
- [ ] Preview shows 3 credentials to import
- [ ] Import button available
- [ ] Success: 3 credentials imported

**Verify**:
- [ ] All three appear in credentials list
- [ ] Names match exactly
- [ ] Service auto-detected or set to default

---

### Step 9: Bulk Import with Template
**Action**:
- Look for template selector in bulk import
- Select a template (e.g., "google-workspace")
- Paste credentials matching template

**Expected**:
- [ ] Template shows required credentials
- [ ] Validator checks required fields
- [ ] Missing credentials highlighted

---

## Test: Agent Credential Requirements

### Step 10: Navigate to Agent Credentials Tab
**Action**:
- Go to agent detail page
- Click "Credentials" tab

**Expected**:
- [ ] Credentials tab loads
- [ ] Shows credential requirements from template
- [ ] Status: Configured vs Missing

---

### Step 11: View Credential Requirements
**Action**:
- Review the requirements list

**Expected Display**:
```
Required Credentials:
- ANTHROPIC_API_KEY: ✅ Configured
- GOOGLE_API_KEY: ⚠️ Missing
- SLACK_BOT_TOKEN: ⚠️ Missing
```

**Verify**:
- [ ] Requirements from .mcp.json.template
- [ ] Status accurate (configured/missing)
- [ ] Clear visual indicators

---

## Test: Assign Credentials to Agent

### Step 12: Assign Credential to Agent
**Action**:
- In Credentials tab, click "Assign" on a missing credential
- Or select from dropdown of available credentials
- Choose GOOGLE_API_KEY
- Save assignment

**Expected**:
- [ ] Credential linked to agent
- [ ] Status changes to "Configured"
- [ ] No immediate restart needed

---

### Step 13: Bulk Assign Credentials
**Action**:
- Click "Bulk Assign" or "Assign All"
- Select multiple credentials to assign
- Apply

**Expected**:
- [ ] Multiple credentials assigned at once
- [ ] All status updated
- [ ] Efficient operation

---

## Test: Reload Credentials

### Step 14: Test Credential Reload
**Action**:
- With agent running, click "Reload Credentials"
- Or use reload button in Credentials tab

**Expected**:
- [ ] Credentials written to agent .env file
- [ ] .mcp.json regenerated from template
- [ ] Agent receives updated credentials
- [ ] No restart required (hot-reload)

**Verify**:
```bash
# Check .env file in container
docker exec agent-{name} cat /home/developer/.env | grep GOOGLE
```

---

### Step 15: Hot-Reload via Paste
**Action**:
- Click "Hot-Reload" or "Quick Paste"
- Paste credentials:
```
NEW_CREDENTIAL=hot-reload-test-value
```
- Apply

**Expected**:
- [ ] Credential parsed from paste
- [ ] Written directly to agent
- [ ] Available immediately
- [ ] No credential store update (temporary)

**Verify**:
```bash
docker exec agent-{name} cat /home/developer/.env | grep NEW_CREDENTIAL
```

---

## Test: Check Credential File Status

### Step 16: Verify Credential Files
**Action**:
- In Credentials tab, look for file status section
- Or use "Check Status" button

**Expected**:
- [ ] .env file status: Present/Missing
- [ ] .mcp.json file status: Present/Missing
- [ ] Last updated timestamp
- [ ] File size or line count

**API Check**:
```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/credentials/status
```

Expected Response:
```json
{
  "env_file_exists": true,
  "env_file_size": 256,
  "mcp_json_exists": true,
  "mcp_json_valid": true,
  "last_updated": "2026-01-14T10:00:00Z"
}
```

---

## Test: OAuth Flows (if configured)

### Step 17: Check OAuth Provider Status
**Action**:
- Look for OAuth providers section
- Check status of Google, Slack, GitHub, Notion

**Expected**:
- [ ] Provider list displayed
- [ ] Status: Connected/Not Connected
- [ ] Connect button for each

**Note**: OAuth requires backend configuration. Skip if not configured.

---

### Step 18: Test OAuth Connection (Optional)
**Action**:
- Click "Connect" for a provider (e.g., Google)
- Complete OAuth flow in popup

**Expected**:
- [ ] OAuth popup opens
- [ ] Redirect to provider login
- [ ] Authorization granted
- [ ] Popup closes
- [ ] Status: Connected

**Note**: Requires valid OAuth credentials in backend.

---

## Critical Validations

### Credential Security
**Validation**: Credentials stored encrypted in Redis

```bash
# Check Redis (should NOT show plaintext)
docker exec redis redis-cli GET "credentials:{id}"
```

### No Credential Leakage
**Validation**: Credentials not exposed in:
- [ ] API responses (values masked)
- [ ] Browser network requests
- [ ] Container logs
- [ ] Database (SQLite stores metadata only)

### Credential Isolation
**Validation**: User A cannot see User B's credentials
- [ ] API filters by owner_id
- [ ] UI shows only owned credentials

---

## Success Criteria

Phase 24 is **PASSED** when:
- [ ] Credentials page loads
- [ ] Add credential with name/value/service
- [ ] Credentials listed without exposing values
- [ ] Edit credential value
- [ ] Delete credential with confirmation
- [ ] Bulk import from .env format
- [ ] Agent credential requirements displayed
- [ ] Status shows configured vs missing
- [ ] Assign credential to agent
- [ ] Bulk assign multiple credentials
- [ ] Reload writes to agent .env
- [ ] Hot-reload via paste works
- [ ] Credential file status displayed
- [ ] (Optional) OAuth connection works

---

## Troubleshooting

**Credentials page empty**:
- No credentials created yet
- Check Redis connection
- Verify API returns data

**Bulk import fails**:
- Check .env format (KEY=VALUE)
- No quotes around values
- One credential per line

**Reload not working**:
- Agent must be running
- Check agent-server health
- Verify hot-reload endpoint exists

**OAuth popup blocked**:
- Browser blocking popups
- Check OAuth callback URL configuration
- Verify provider credentials

**Credential assignment fails**:
- Check credential belongs to user
- Agent may not have credential schema
- Verify database writes

---

## Next Phase

Once Phase 24 is **PASSED**, proceed to:
- **Phase 25**: Agent Sharing

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: CRED-001 to CRED-013
