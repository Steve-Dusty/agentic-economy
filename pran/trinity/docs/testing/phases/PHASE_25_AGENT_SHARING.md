# Phase 25: Agent Sharing

> **Purpose**: Validate sharing agents with team members and permission management
> **Duration**: ~15 minutes
> **Assumes**: Phase 1 PASSED (authenticated), Phase 2 PASSED (agents created)
> **Output**: Agent sharing and access control verified

---

## Background

**Agent Sharing** (SHARE-001 to SHARE-004):
- Share agents with other users via email
- Shared users can view/interact with agent
- Only owners can delete or change settings
- Auto-whitelist emails on share

**User Stories**:
- SHARE-001: Share agent with users
- SHARE-002: See who agent is shared with
- SHARE-003: Revoke sharing
- SHARE-004: Auto-whitelist shared emails

---

## Prerequisites

- [ ] Phase 1 PASSED (authenticated as owner)
- [ ] Phase 2 PASSED (at least one agent created)
- [ ] Know an email address to share with
- [ ] (Optional) Second browser/device for testing shared access

---

## Test: View Sharing Tab

### Step 1: Navigate to Sharing Tab
**Action**:
- Go to agent detail page for an agent you own
- Click "Sharing" tab

**Expected**:
- [ ] Sharing tab loads
- [ ] "Share with" input visible
- [ ] Current shares list (may be empty)
- [ ] Your email shown as "Owner"

**Verify**:
- [ ] Tab accessible for owners
- [ ] UI elements present

---

### Step 2: Verify Owner Display
**Action**:
- Check the owner section of sharing

**Expected**:
- [ ] Your email shown
- [ ] "Owner" badge/label
- [ ] No option to remove self

---

## Test: Share Agent

### Step 3: Share Agent with Email
**Action**:
- Enter email address: `testuser@example.com`
- Click "Share" or press Enter

**Expected**:
- [ ] Sharing initiated
- [ ] Loading indicator while processing
- [ ] Success message: "Agent shared with testuser@example.com"
- [ ] Email appears in shared users list

**Verify**:
- [ ] Database record created
- [ ] Email added to list

```bash
# Check database
sqlite3 ~/trinity-data/trinity.db "SELECT * FROM agent_sharing WHERE agent_name='{name}'"
```

---

### Step 4: Share with Multiple Users
**Action**:
- Add another email: `seconduser@example.com`
- Share

**Expected**:
- [ ] Second user added
- [ ] Both emails in shared list
- [ ] Each shows "Shared" badge

---

### Step 5: Verify Auto-Whitelist
**Action**:
- Navigate to Settings → Email Whitelist
- Look for shared emails

**Expected**:
- [ ] `testuser@example.com` in whitelist
- [ ] `seconduser@example.com` in whitelist
- [ ] Auto-added when shared

**Verify**:
- [ ] Users can now login via email auth
- [ ] Whitelist includes shared emails

---

## Test: View Shared Users

### Step 6: List Shared Users
**Action**:
- In Sharing tab, review the shared users list

**Expected Display**:
```
Owner:
- your@email.com (Owner) [Cannot remove]

Shared With:
- testuser@example.com (Shared) [Remove]
- seconduser@example.com (Shared) [Remove]
```

**Verify**:
- [ ] All shared users listed
- [ ] Role/access level shown
- [ ] Remove button for shared users
- [ ] No remove for owner

---

## Test: Shared User Access

### Step 7: Test Shared User View (requires second browser/user)
**Action**:
- Login as shared user (testuser@example.com)
- Navigate to /agents
- Find the shared agent

**Expected**:
- [ ] Shared agent visible in list
- [ ] "Shared" badge on agent card
- [ ] Can click to view details

**Note**: If testing alone, verify via API:
```bash
# As shared user
curl -H "Authorization: Bearer {shared_user_token}" \
  http://localhost:8000/api/agents
```

---

### Step 8: Verify Shared User Permissions
**Action**:
- As shared user, open agent detail

**Expected Permissions**:
- [ ] Can view agent status
- [ ] Can view logs
- [ ] Can send messages via Terminal
- [ ] Can view files
- [ ] Cannot delete agent
- [ ] Cannot access Sharing tab
- [ ] Cannot access Settings

**Verify**:
- [ ] Sharing tab hidden for non-owners
- [ ] Delete button hidden/disabled
- [ ] Settings restricted

---

## Test: Revoke Sharing

### Step 9: Remove Shared User
**Action**:
- As owner, go to Sharing tab
- Click "Remove" next to testuser@example.com
- Confirm if prompted

**Expected**:
- [ ] Confirmation dialog (optional)
- [ ] User removed from list
- [ ] Success message

**Verify**:
- [ ] Database record deleted
- [ ] User no longer has access

---

### Step 10: Verify Revoked Access
**Action**:
- As the removed user, try to access agent

**Expected**:
- [ ] Agent not in user's agent list
- [ ] Direct URL returns 403 Forbidden
- [ ] Cannot interact with agent

**Verify**:
```bash
# As removed user
curl -H "Authorization: Bearer {removed_user_token}" \
  http://localhost:8000/api/agents/{name}
# Should return 403
```

---

## Test: Edge Cases

### Step 11: Share with Invalid Email
**Action**:
- Try to share with: `invalid-email`

**Expected**:
- [ ] Validation error
- [ ] "Invalid email format" message
- [ ] Share not processed

---

### Step 12: Share with Self
**Action**:
- Try to share with your own email

**Expected**:
- [ ] Error or no-op
- [ ] "Cannot share with yourself" or already owner message
- [ ] No duplicate entries

---

### Step 13: Share Already Shared
**Action**:
- Try to share with already shared user

**Expected**:
- [ ] No duplicate entries created
- [ ] "Already shared" message or idempotent success

---

## Test: Admin Access

### Step 14: Admin View of Sharing
**Action**:
- As admin, view any agent's sharing

**Expected**:
- [ ] Admin can see sharing for all agents
- [ ] Admin can manage sharing
- [ ] Admin treated as super-owner

**Verify**:
- [ ] Admin sees Sharing tab for all agents
- [ ] Admin can add/remove shares

---

## Critical Validations

### Access Control Enforcement
**Validation**: Sharing rules enforced at API level

- [ ] Non-shared users get 403
- [ ] Shared users can access
- [ ] Owners have full control
- [ ] Admins bypass sharing rules

### Database Integrity
**Validation**: Sharing records consistent

```bash
sqlite3 ~/trinity-data/trinity.db "SELECT agent_name, shared_with_email, shared_by_id FROM agent_sharing"
```

### Cascading Deletion
**Validation**: Shares deleted when agent deleted

- [ ] Delete a shared agent
- [ ] Verify sharing records removed
- [ ] No orphan records

---

## Success Criteria

Phase 25 is **PASSED** when:
- [ ] Sharing tab accessible to owners
- [ ] Owner displayed correctly
- [ ] Can share agent with email address
- [ ] Shared emails auto-whitelisted
- [ ] Multiple users can be shared
- [ ] Shared users list displays correctly
- [ ] Shared users can access agent
- [ ] Shared users cannot delete/configure
- [ ] Sharing can be revoked
- [ ] Revoked users lose access
- [ ] Invalid emails rejected
- [ ] Duplicate shares handled
- [ ] Admin has full access

---

## Troubleshooting

**Sharing tab not visible**:
- User may not own the agent
- Check agent_ownership table
- Only owners see Sharing tab

**Share fails**:
- Check backend logs
- Verify email format
- Check database constraints

**Auto-whitelist not working**:
- Whitelist may be disabled
- Check settings configuration
- Verify trigger in backend

**Access not revoked**:
- Cache may be stale
- Force refresh
- Check database record deleted

**Admin can't access**:
- Verify admin role in database
- Check is_admin flag on user

---

## Next Phase

Once Phase 25 is **PASSED**, proceed to:
- **Phase 26**: Shared Folders

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: SHARE-001 to SHARE-004
