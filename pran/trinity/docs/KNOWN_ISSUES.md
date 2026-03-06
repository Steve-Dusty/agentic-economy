# Known Issues & Troubleshooting

## Active Issues

### 🔴 OAuth Redirect May Go to localhost in Production

**Status**: Check your deployment
**Priority**: HIGH
**Affects**: Google OAuth flow when `BACKEND_URL` is misconfigured

**Symptoms:**
- User clicks OAuth button on production credentials page
- After authorizing, redirected to `localhost:8000` instead of production URL

**Solution:**
1. Ensure `BACKEND_URL` is set correctly in your production `.env`:
   ```bash
   BACKEND_URL=https://your-domain.com/api
   ```
2. Add production redirect URI to Google Cloud Console OAuth client
3. Restart backend service
4. Clear browser cache and try again

**Related Files:**
- `src/backend/config.py` - BACKEND_URL config
- `src/backend/routers/credentials.py` - OAuth init endpoint
- `.env.example` - BACKEND_URL documentation

---

### 🟡 Human Approval Timeout Not Enforced

**Status**: KNOWN LIMITATION
**Priority**: MEDIUM
**Affects**: Process Engine - human_approval steps

**Symptoms:**
- Setting `timeout: 5m` on a `human_approval` step does nothing
- Execution stays paused indefinitely until manual approve/reject

**Cause:**
- When execution pauses for approval, no background process monitors the timeout
- Requires a scheduler/cron job to periodically check for timed-out approvals

**Workaround:**
- Manually approve or reject pending approvals
- Don't rely on approval timeouts for critical workflows

**Fix Required:**
- Add background job to check for timed-out approvals
- Could integrate with existing `src/scheduler/` service

---

## Resolved Issues

_No resolved issues yet_

---

## Workarounds

### For OAuth Issues on Production
**Temporary workaround**: Use local development environment
1. Set up Trinity locally
2. Add OAuth credentials locally
3. Export credentials from Redis
4. Import to production Redis manually

---

## Investigation Tools

### Check Backend Logs
```bash
# Local
docker-compose logs backend --tail=100

# Production (replace with your deployment method)
# Check your container orchestration logs
```

### Check Environment Variables
```bash
# Local
docker-compose exec backend env | grep -E "(BACKEND|GOOGLE)"
```

### Test OAuth Init Endpoint
```bash
# Get auth_url from init endpoint
curl -X POST https://your-domain.com/api/oauth/google/init \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" | jq .

# Check the auth_url in the response - should contain correct redirect_uri
```

---

## How to Report New Issues

When adding a new issue to this document:

1. **Title**: Brief description with emoji (🔴 High, 🟡 Medium, 🟢 Low)
2. **Status**: UNRESOLVED / IN PROGRESS / RESOLVED
3. **Priority**: HIGH / MEDIUM / LOW
4. **Affects**: What feature/environment is broken
5. **Symptoms**: What the user sees
6. **What Was Tried**: Steps already taken to fix it
7. **Possible Causes**: List of theories
8. **Next Steps to Debug**: Concrete actions to investigate
9. **Related Files**: Code locations
10. **Commits**: Git commits related to this issue
11. **Impact**: Who/what is affected
