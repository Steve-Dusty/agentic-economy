# Implementation Plan: MCP SSH Access Tool

## Overview

Add an MCP tool `get_agent_ssh_access` that generates ephemeral SSH credentials for direct terminal access to agent containers. Designed for Tailscale/VPN environments where users want secure, direct SSH access without UI.

## User Flow

```
User (Claude Code) → MCP Tool → Trinity Backend → Agent Container
       ↓
   Receives:
   - SSH connection string: ssh -p 2222 developer@100.x.x.x
   - Private key (one-time display)
   - Expiration time (default: 4 hours)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  MCP Tool: get_agent_ssh_access                                  │
│  Parameters: agent_name, ttl_hours (optional, default: 4)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend: POST /api/agents/{name}/ssh-access                     │
│  1. Validate agent exists and is running                         │
│  2. Generate ED25519 key pair                                    │
│  3. Inject public key into container authorized_keys             │
│  4. Store key metadata in Redis (with TTL for auto-cleanup)      │
│  5. Return private key + connection string                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Agent Container                                                 │
│  /home/developer/.ssh/authorized_keys                            │
│  ssh-ed25519 AAAA... trinity-ephemeral-{agent}-{timestamp}       │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### 1. Backend: SSH Access Endpoint

**File:** `src/backend/routers/agents.py`

```python
@router.post("/{agent_name}/ssh-access")
async def create_ssh_access(
    agent_name: str,
    ttl_hours: int = 4,  # Default 4 hours
    current_user: User = Depends(get_current_user)
):
    """
    Generate ephemeral SSH credentials for direct agent access.
    Returns private key (one-time) and connection command.
    """
```

**Logic:**
1. Verify agent exists, user has access, agent is running
2. Generate ED25519 key pair using `cryptography` library
3. Create unique key comment: `trinity-ephemeral-{agent_name}-{unix_timestamp}`
4. Execute in container: append public key to `~/.ssh/authorized_keys`
5. Store in Redis: `ssh_key:{agent_name}:{timestamp}` with TTL = ttl_hours
6. Return response with private key, connection string, expiry time

### 2. Backend: SSH Key Cleanup Service

**File:** `src/backend/services/ssh_service.py` (new)

```python
async def inject_ssh_key(agent_name: str, public_key: str, comment: str) -> bool:
    """Inject SSH public key into agent's authorized_keys"""

async def remove_ssh_key(agent_name: str, comment: str) -> bool:
    """Remove SSH key by comment from agent's authorized_keys"""

async def cleanup_expired_keys():
    """Called periodically to remove expired keys from containers"""
```

**Key cleanup approach:**
- Redis stores: `{agent_name, comment, expiry_timestamp}`
- Background task runs every 15 minutes
- On expiry: exec into container, remove line with matching comment
- Also cleanup on agent stop/delete

### 3. Backend: Redis Schema

```
Key: ssh_access:{agent_name}:{timestamp}
Value: {
    "comment": "trinity-ephemeral-{agent_name}-{timestamp}",
    "public_key": "ssh-ed25519 AAAA...",
    "created_at": "2025-01-02T10:00:00Z",
    "expires_at": "2025-01-02T14:00:00Z",
    "created_by": "user@example.com"
}
TTL: ttl_hours * 3600
```

### 4. MCP Tool

**File:** `src/mcp-server/src/tools/agents.ts`

```typescript
// get_agent_ssh_access - Get ephemeral SSH access to an agent
getAgentSshAccess: {
  name: "get_agent_ssh_access",
  description:
    "Generate ephemeral SSH credentials for direct terminal access to an agent container. " +
    "Returns a private key (display once, save locally) and SSH connection command. " +
    "Keys expire automatically (default: 4 hours). Agent must be running. " +
    "Ideal for Tailscale/VPN environments where you need direct SSH access.",
  parameters: z.object({
    agent_name: z.string().describe("Name of the agent to access"),
    ttl_hours: z.number().optional().default(4)
      .describe("How long the SSH key should be valid (1-24 hours, default: 4)"),
  }),
  execute: async (args, context) => {
    // Call backend POST /api/agents/{name}/ssh-access
    // Return formatted response with instructions
  }
}
```

### 5. MCP Client Extension

**File:** `src/mcp-server/src/client.ts`

```typescript
async createSshAccess(agentName: string, ttlHours: number = 4): Promise<SshAccessResponse> {
  return this.request<SshAccessResponse>(
    "POST",
    `/api/agents/${agentName}/ssh-access`,
    { ttl_hours: ttlHours }
  );
}
```

### 6. Response Format

```json
{
  "status": "success",
  "agent": "my-agent",
  "ssh_command": "ssh -p 2222 -i ~/.trinity/keys/my-agent.key developer@100.64.0.1",
  "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1r...\n-----END OPENSSH PRIVATE KEY-----",
  "host": "100.64.0.1",
  "port": 2222,
  "user": "developer",
  "expires_at": "2025-01-02T14:00:00Z",
  "expires_in_hours": 4,
  "instructions": [
    "Save the private key to a file: ~/.trinity/keys/my-agent.key",
    "Set permissions: chmod 600 ~/.trinity/keys/my-agent.key",
    "Connect: ssh -p 2222 -i ~/.trinity/keys/my-agent.key developer@100.64.0.1",
    "Key expires in 4 hours"
  ]
}
```

## Security Considerations

1. **Key Isolation:** Each request generates a new unique key pair
2. **Auto-Expiry:** Keys automatically removed from containers after TTL
3. **Audit Trail:** All key creations logged with user, agent, timestamp
4. **No Key Storage:** Private key shown once, never stored on server
5. **Tailscale/VPN:** SSH ports only accessible within VPN network
6. **User Scoping:** Only accessible to users with agent access

## Configuration

Add to settings (optional, for customization):

```python
# Environment variables
SSH_ACCESS_DEFAULT_TTL_HOURS=4      # Default key lifetime
SSH_ACCESS_MAX_TTL_HOURS=24         # Maximum allowed TTL
SSH_ACCESS_CLEANUP_INTERVAL=900     # Cleanup check interval (seconds)
```

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/backend/services/ssh_service.py` | Create | SSH key generation, injection, cleanup |
| `src/backend/routers/agents.py` | Modify | Add `/ssh-access` endpoint |
| `src/mcp-server/src/tools/agents.ts` | Modify | Add `get_agent_ssh_access` tool |
| `src/mcp-server/src/client.ts` | Modify | Add `createSshAccess` method |

## Testing

1. **Manual Test:**
   ```
   # Via MCP
   get_agent_ssh_access(agent_name="test-agent", ttl_hours=1)

   # Save key, connect
   ssh -p 2222 -i /tmp/test.key developer@<tailscale-ip>
   ```

2. **Expiry Test:**
   - Create key with ttl_hours=0.1 (6 minutes)
   - Verify key works immediately
   - Wait 6+ minutes, verify key no longer works

## Host Detection

For Tailscale, the backend needs to determine the correct host IP to return:

```python
def get_ssh_host():
    """Get the host IP for SSH connections"""
    # Option 1: Environment variable (explicit configuration)
    if os.getenv("SSH_HOST"):
        return os.getenv("SSH_HOST")

    # Option 2: Try to detect Tailscale IP
    try:
        result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    # Option 3: Fallback to localhost
    return "localhost"
```

## Estimated Effort

- Backend SSH service: ~2 hours
- Backend endpoint: ~1 hour
- MCP tool: ~1 hour
- Testing & refinement: ~1 hour

**Total: ~5 hours**
