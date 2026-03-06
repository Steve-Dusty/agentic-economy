# Phase 27: Public Access

> **Purpose**: Validate public shareable links for unauthenticated agent access
> **Duration**: ~20 minutes
> **Assumes**: Phase 1 PASSED (authenticated), Phase 2 PASSED (agent running)
> **Output**: Public link creation, access, and revocation verified

---

## Background

**Public Agent Links** (PUB-001 to PUB-007):
- Create shareable public URLs for agents
- Optional email verification before access
- Usage tracking and rate limiting
- Can revoke/disable links anytime
- Public users can chat with agent

**User Stories**:
- PUB-001: Create public link
- PUB-002: List public links
- PUB-003: Update link settings
- PUB-004: Revoke public link
- PUB-005: Access agent via public link
- PUB-006: Email verification for public
- PUB-007: Chat via public link

---

## Prerequisites

- [ ] Phase 1 PASSED (authenticated as owner)
- [ ] Phase 2 PASSED (agent running)
- [ ] Incognito browser window for testing public access

---

## Test: Create Public Link

### Step 1: Navigate to Public Links Tab
**Action**:
- Go to agent detail page for an agent you own
- Click "Public Links" tab

**Expected**:
- [ ] Public Links tab loads
- [ ] "Create Public Link" button visible
- [ ] Existing links list (may be empty)

**Verify**:
- [ ] Tab accessible to owner only

---

### Step 2: Create Public Link (No Email Verification)
**Action**:
- Click "Create Public Link"
- Configure:
  - Name: "Public Demo Link"
  - Email Verification: OFF
  - Rate Limit: 10 requests/minute
  - Max Uses: Unlimited (or 100)
- Click Create

**Expected**:
- [ ] Link created successfully
- [ ] Public URL displayed
- [ ] Copy button available
- [ ] QR code (if implemented)

**Example URL**:
```
http://localhost/public/abc123xyz
```

---

### Step 3: Copy Public Link
**Action**:
- Click copy button
- Paste URL somewhere to verify

**Expected**:
- [ ] URL copied to clipboard
- [ ] Full URL with domain
- [ ] Unique link ID in URL

---

## Test: Access Public Link

### Step 4: Open Public Link (Incognito)
**Action**:
- Open incognito/private browser window
- Paste the public link URL
- Press Enter

**Expected**:
- [ ] Public agent page loads
- [ ] Agent name/description visible
- [ ] Chat interface available
- [ ] No login required

**Verify**:
- [ ] Not logged in (check no JWT)
- [ ] Limited UI (no settings, no admin)
- [ ] Agent info displayed

---

### Step 5: Chat via Public Link
**Action**:
- In public chat interface
- Send message: "Hello, this is a public test"
- Wait for response

**Expected**:
- [ ] Message sent successfully
- [ ] Agent responds
- [ ] Chat history visible (for session)

**Verify**:
- [ ] No errors
- [ ] Response displayed properly
- [ ] No authentication prompts

---

### Step 6: Test Rate Limiting
**Action**:
- Send multiple messages quickly (10+)

**Expected**:
- [ ] Rate limit triggered
- [ ] Error message: "Rate limit exceeded"
- [ ] Cooldown before next message

**Verify**:
- [ ] Rate limit enforced
- [ ] User feedback on limit

---

## Test: Email Verification Link

### Step 7: Create Email-Required Link
**Action**:
- Back in authenticated session
- Create another public link:
  - Name: "Email Verified Link"
  - Email Verification: ON
  - Rate Limit: 5 requests/minute
- Create

**Expected**:
- [ ] Link created with email requirement
- [ ] Different configuration saved

---

### Step 8: Access Email-Required Link
**Action**:
- Open new incognito window
- Navigate to the email-required link

**Expected**:
- [ ] Email verification form displayed
- [ ] Cannot access chat without email
- [ ] "Enter your email to continue"

---

### Step 9: Complete Email Verification
**Action**:
- Enter email address
- Submit
- (If email provider configured) Check email for code
- Enter verification code

**Expected**:
- [ ] Code sent to email (or shown in console for dev)
- [ ] Code entry form displayed
- [ ] After verification: chat available

**Note**: If using console email provider, check backend logs for code.

---

### Step 10: Chat After Verification
**Action**:
- After email verified
- Send message in chat

**Expected**:
- [ ] Full chat access
- [ ] Agent responds
- [ ] Email recorded for usage tracking

---

## Test: List Public Links

### Step 11: View All Public Links
**Action**:
- In Public Links tab
- Review the list of created links

**Expected Display**:
```
Public Links:
1. "Public Demo Link"
   - URL: http://localhost/public/abc123
   - Email Required: No
   - Uses: 5 / Unlimited
   - Created: 2026-01-14
   - Status: Active
   [Edit] [Revoke]

2. "Email Verified Link"
   - URL: http://localhost/public/xyz789
   - Email Required: Yes
   - Uses: 2 / Unlimited
   - Created: 2026-01-14
   - Status: Active
   [Edit] [Revoke]
```

**Verify**:
- [ ] All links listed
- [ ] Usage statistics shown
- [ ] Status displayed

---

## Test: Update Link Settings

### Step 12: Edit Public Link
**Action**:
- Click "Edit" on first link
- Change rate limit to 20/minute
- Save

**Expected**:
- [ ] Edit modal opens
- [ ] Can modify settings
- [ ] Changes saved
- [ ] Link continues working

**Verify**:
- [ ] New rate limit applies
- [ ] URL unchanged (same link ID)

---

## Test: Revoke Public Link

### Step 13: Revoke Link
**Action**:
- Click "Revoke" on first link
- Confirm revocation

**Expected**:
- [ ] Confirmation dialog
- [ ] Link marked as revoked
- [ ] Status changes to "Revoked"

---

### Step 14: Test Revoked Link Access
**Action**:
- Open incognito window
- Try to access the revoked link URL

**Expected**:
- [ ] Access denied page
- [ ] "This link has been revoked"
- [ ] Cannot chat with agent

**Verify**:
- [ ] Revocation enforced immediately
- [ ] No workaround possible

---

## Test: Usage Tracking

### Step 15: Check Usage Statistics
**Action**:
- In Public Links tab
- Look at usage counts

**Expected**:
- [ ] Message count per link
- [ ] Unique visitors (if tracked)
- [ ] Last used timestamp

**API Check**:
```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/agents/{name}/public-links/{id}/usage
```

---

## Test: Delete Link

### Step 16: Delete Public Link
**Action**:
- Click "Delete" on revoked link (if option available)
- Or: Revoke permanently removes

**Expected**:
- [ ] Link removed from list
- [ ] URL returns 404

---

## Test: Edge Cases

### Step 17: Access with Agent Stopped
**Action**:
- Stop the agent
- Try to access public link

**Expected**:
- [ ] Message: "Agent is offline"
- [ ] Cannot chat
- [ ] Public page shows status

---

### Step 18: Concurrent Public Users
**Action**:
- Multiple incognito windows access same link
- All send messages

**Expected**:
- [ ] Each user gets responses
- [ ] No cross-session contamination
- [ ] Rate limits per-IP or per-session

---

## Critical Validations

### Authentication Bypass
**Validation**: Public links work without JWT

```bash
# No auth header
curl http://localhost/public/{link_id}
# Should return public page content
```

### Link Security
**Validation**: Cannot guess link IDs

- [ ] Link IDs are cryptographically random
- [ ] Cannot enumerate links
- [ ] Brute-force protected

### Session Isolation
**Validation**: Public users isolated

- [ ] Cannot see other users' messages
- [ ] Cannot access agent settings
- [ ] Limited to chat only

---

## Success Criteria

Phase 27 is **PASSED** when:
- [ ] Public Links tab accessible to owners
- [ ] Can create public link without email verification
- [ ] Public link URL generated and copyable
- [ ] Public access works without login (incognito)
- [ ] Chat functional via public link
- [ ] Rate limiting enforced
- [ ] Can create email-verified link
- [ ] Email verification form displayed
- [ ] Verification code flow works
- [ ] Usage statistics tracked
- [ ] Link settings can be updated
- [ ] Links can be revoked
- [ ] Revoked links deny access
- [ ] Stopped agent shows offline message

---

## Troubleshooting

**Public Links tab not visible**:
- Feature may be disabled
- Owner-only tab - check ownership
- Check feature flag in settings

**Link creation fails**:
- Check backend logs
- Verify database write
- Check unique link ID generation

**Public page doesn't load**:
- Check frontend routing for /public/*
- Verify backend endpoint exists
- Check nginx configuration for public routes

**Email verification not sending**:
- Check email provider configuration
- Check console for code in dev mode
- Verify EMAIL_PROVIDER env var

**Rate limit not working**:
- Check Redis connection
- Verify rate limit middleware
- Check per-IP vs per-link settings

---

## Next Phase

Once Phase 27 is **PASSED**, proceed to:
- **Phase 28**: Agent Dashboard

---

**Status**: Ready for Testing
**Last Updated**: 2026-01-14
**User Stories**: PUB-001 to PUB-007
