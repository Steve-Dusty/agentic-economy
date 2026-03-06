# Subscription Credentials (SUB-001)

## Find Credentials on macOS

Claude Code stores OAuth credentials in the system Keychain, not a file.

```bash
# Extract credentials from Keychain
security find-generic-password -s "Claude Code-credentials" -a "$(whoami)" -w
```

This returns JSON with `claudeAiOauth` containing `accessToken`, `refreshToken`, `expiresAt`, `subscriptionType`, and `rateLimitTier`.

## Register Subscription

```bash
# Get credentials
CREDS=$(security find-generic-password -s "Claude Code-credentials" -a "$(whoami)" -w)

# Register via API (requires admin token)
curl -X POST "http://localhost:8000/api/subscriptions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"my-max\", \"credentials_json\": $(echo "$CREDS" | jq -Rs .), \"subscription_type\": \"max\"}"
```

## Assign to Agent

```bash
curl -X PUT "http://localhost:8000/api/subscriptions/agents/{agent_name}?subscription_name=my-max" \
  -H "Authorization: Bearer $TOKEN"
```

## Validate Agent Uses Subscription

### 1. Check auth status API
```bash
curl "http://localhost:8000/api/subscriptions/agents/{agent_name}/auth" \
  -H "Authorization: Bearer $TOKEN"
# Should return: {"auth_mode": "subscription", "subscription_name": "my-max", ...}
```

### 2. Verify credentials file in container
```bash
docker exec agent-{name} python3 -c "
import json
with open('/home/developer/.claude/.credentials.json') as f:
    d = json.load(f)
    oauth = d.get('claudeAiOauth', {})
    print('subscriptionType:', oauth.get('subscriptionType'))
    print('rateLimitTier:', oauth.get('rateLimitTier'))
"
```

### 3. Test Claude works without API key
```bash
docker exec agent-{name} bash -c "unset ANTHROPIC_API_KEY && claude --print 'hello'"
# Should respond without login prompt
```

## Credential Locations by OS

| OS | Location |
|----|----------|
| macOS | Keychain: `Claude Code-credentials` |
| Linux | `~/.claude/.credentials.json` |
| Windows | `~/.claude/.credentials.json` |
