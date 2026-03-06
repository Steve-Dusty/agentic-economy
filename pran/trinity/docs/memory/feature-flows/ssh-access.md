# Feature: SSH Access

## Overview
Generate ephemeral SSH credentials for direct terminal access to agent containers. Supports key-based (ED25519) or password-based authentication with configurable TTL (default 4 hours, max 24 hours). Controlled by system-wide `ssh_access_enabled` ops setting.

## User Story
As an agent operator, I want to generate temporary SSH credentials for my agent containers so that I can access them directly via SSH from my local terminal (especially useful with Tailscale/VPN setups).

## Revision History
| Date | Change |
|------|--------|
| 2026-02-24 | **Async Docker Operations**: All SshService methods now async (DOCKER-001). Uses `container_exec_run` wrapper to prevent event loop blocking. |
| 2026-02-13 | **Fixed localhost bug**: Added FRONTEND_URL domain extraction as priority #2 in host detection. Production deployments now correctly return domain instead of localhost. |
| 2026-01-23 | Updated line numbers: ssh_service.py, agents.py, agents.ts, client.ts, types.ts |
| 2026-01-02 | Fixed password setting (sed → usermod), improved host detection |
| 2026-01-02 | Added UI toggle in Settings.vue for ssh_access_enabled |
| 2026-01-02 | Initial documentation |

---

## Entry Points

- **MCP Tool**: `get_agent_ssh_access` - Primary entry point for external clients (Claude Code, etc.)
- **API**: `POST /api/agents/{agent_name}/ssh-access` - Backend REST endpoint

---

## MCP Layer

### Tool Definition

**agents.ts** (`src/mcp-server/src/tools/agents.ts:383-420`)

```typescript
getAgentSshAccess: {
  name: "get_agent_ssh_access",
  description:
    "Generate ephemeral SSH credentials for direct terminal access to an agent container. " +
    "Supports two auth methods: 'key' (save private key locally) or 'password' (one-liner with sshpass). " +
    "Credentials expire automatically (default: 4 hours). Agent must be running. " +
    "Ideal for Tailscale/VPN environments where you need direct SSH access. " +
    "IMPORTANT: For key auth, save the private key immediately - it cannot be retrieved again.",
  parameters: z.object({
    agent_name: z.string().describe("Name of the agent to access"),
    ttl_hours: z
      .number()
      .optional()
      .default(4)
      .describe("How long the SSH key should be valid (0.1-24 hours, default: 4)"),
    auth_method: z
      .enum(["key", "password"])
      .optional()
      .default("key")
      .describe("Authentication method: 'key' for SSH key pair (more secure, requires saving key file), 'password' for one-liner with sshpass (convenient, requires sshpass installed)"),
  }),
  execute: async (
    { agent_name, ttl_hours = 4, auth_method = "key" }: { agent_name: string; ttl_hours?: number; auth_method?: "key" | "password" },
    context?: { session?: McpAuthContext }
  ) => {
    const authContext = context?.session;
    const apiClient = getClient(authContext);
    const response = await apiClient.createSshAccess(agent_name, ttl_hours, auth_method);
    return JSON.stringify(response, null, 2);
  },
}
```

### Client Method

**client.ts** (`src/mcp-server/src/client.ts:314-324`)

```typescript
async createSshAccess(
  name: string,
  ttlHours: number = 4,
  authMethod: "key" | "password" = "key"
): Promise<SshAccessResponse> {
  return this.request<SshAccessResponse>(
    "POST",
    `/api/agents/${encodeURIComponent(name)}/ssh-access`,
    { ttl_hours: ttlHours, auth_method: authMethod }
  );
}
```

### Type Definitions

**types.ts** (`src/mcp-server/src/types.ts:116-135`)

```typescript
export interface SshConnectionInfo {
  command: string;      // Full SSH command to connect
  host: string;         // SSH host (tailscale IP, SSH_HOST env, or localhost)
  port: number;         // SSH port (from container label trinity.ssh-port)
  user: string;         // Always "developer"
  password?: string;    // Only for password auth
}

export interface SshAccessResponse {
  status: string;           // "success"
  agent: string;            // Agent name
  auth_method: "key" | "password";
  connection: SshConnectionInfo;
  private_key?: string;     // Only for key auth - one-time display!
  expires_at: string;       // ISO timestamp
  expires_in_hours: number; // TTL value used
  instructions: string[];   // Step-by-step usage instructions
}
```

---

## Backend Layer

### Endpoint

**agents.py** (`src/backend/routers/agents.py:999-1166`)

#### Request Model (Line 999)

```python
class SshAccessRequest(BaseModel):
    """Request body for SSH access."""
    ttl_hours: float = 4.0
    auth_method: str = "key"  # "key" for SSH key, "password" for ephemeral password
```

#### POST /{agent_name}/ssh-access (Line 1005)

```python
@router.post("/{agent_name}/ssh-access")
async def create_ssh_access(
    agent_name: str,
    body: SshAccessRequest = SshAccessRequest(),
    current_user: User = Depends(get_current_user)
):
    # 1. Check if SSH access is enabled system-wide
    if not get_ops_setting("ssh_access_enabled", as_type=bool):
        raise HTTPException(
            status_code=403,
            detail="SSH access is disabled. Enable it in Settings -> Ops Settings -> ssh_access_enabled"
        )

    # 2. Check user has access to agent
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Access denied")

    # 3. Verify agent exists and is running
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running")

    # 4. Validate and clamp TTL (0.1 - 24 hours)
    ttl_hours = max(0.1, min(body.ttl_hours, SSH_ACCESS_MAX_TTL_HOURS))

    # 5. Get SSH port and host
    labels = container.attrs.get("Config", {}).get("Labels", {})
    ssh_port = int(labels.get("trinity.ssh-port", "2222"))
    host = get_ssh_host()  # Tailscale IP, SSH_HOST env, or localhost

    # 6. Generate credentials based on auth_method
    if auth_method == "password":
        # Password flow
        password = ssh_service.generate_password()
        ssh_service.set_container_password(agent_name, password)
        ssh_service.store_credential_metadata(...)
        return { password response }
    else:
        # Key flow
        keypair = ssh_service.generate_ssh_keypair(agent_name)
        ssh_service.inject_ssh_key(agent_name, keypair["public_key"])
        ssh_service.store_key_metadata(...)
        return { key response }
```

### SSH Service

**ssh_service.py** (`src/backend/services/ssh_service.py`)

#### Configuration (Lines 30-35)

```python
SSH_ACCESS_DEFAULT_TTL_HOURS = int(os.getenv("SSH_ACCESS_DEFAULT_TTL_HOURS", "4"))
SSH_ACCESS_MAX_TTL_HOURS = int(os.getenv("SSH_ACCESS_MAX_TTL_HOURS", "24"))
SSH_ACCESS_CLEANUP_INTERVAL = int(os.getenv("SSH_ACCESS_CLEANUP_INTERVAL", "900"))  # 15 min
SSH_ACCESS_PREFIX = "ssh_access:"  # Redis key prefix
```

#### Key Generation (Lines 44-82) - SshService.generate_ssh_keypair()

```python
def generate_ssh_keypair(self, agent_name: str) -> Dict[str, str]:
    """Generate an ED25519 SSH key pair."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Unique comment for tracking/cleanup
    timestamp = int(time.time())
    comment = f"trinity-ephemeral-{agent_name}-{timestamp}"

    # Serialize in OpenSSH format
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )

    return {
        "private_key": private_key_bytes.decode('utf-8'),
        "public_key": f"{public_key_bytes.decode('utf-8')} {comment}",
        "comment": comment
    }
```

#### Key Injection (Lines 85-134) - SshService.inject_ssh_key()

```python
async def inject_ssh_key(self, agent_name: str, public_key: str) -> bool:
    """Inject SSH public key into agent's authorized_keys file."""
    container = get_agent_container(agent_name)

    # Ensure .ssh directory exists with correct permissions (async to avoid blocking)
    await container_exec_run(
        container,
        'sh -c "mkdir -p /home/developer/.ssh && chmod 700 /home/developer/.ssh"',
        user="developer"
    )

    # Append public key to authorized_keys
    escaped_key = public_key.replace("'", "'\"'\"'")
    await container_exec_run(
        container,
        f"sh -c 'printf \"%s\\n\" '\"'{escaped_key}'\"' >> /home/developer/.ssh/authorized_keys'",
        user="developer"
    )

    # Set correct permissions
    await container_exec_run(container, 'chmod 600 /home/developer/.ssh/authorized_keys', user="developer")
    return True
```

> **Note**: As of DOCKER-001, all SshService methods use `container_exec_run` from `services/docker_utils.py` to avoid blocking the FastAPI event loop.

#### Password Generation (Lines 132-144) - SshService.generate_password()

```python
def generate_password(self, length: int = 24) -> str:
    """Generate a secure random password for SSH access."""
    # Alphanumeric only - safe for shell commands
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
```

#### Password Setting (Lines 150-211) - SshService.set_container_password()

```python
async def set_container_password(self, agent_name: str, password: str) -> bool:
    """Set SSH password for developer user in agent container."""
    import crypt

    container = get_agent_container(agent_name)

    # Generate encrypted password using SHA-512
    salt = crypt.mksalt(crypt.METHOD_SHA512)
    encrypted = crypt.crypt(password, salt)

    # Use usermod -p with single-quoted password (handles $ in hash correctly)
    result = await container_exec_run(
        container,
        f"usermod -p '{encrypted}' developer",
        user="root"
    )

    if result.exit_code != 0:
        # Fallback to chpasswd with plaintext password
        result = await container_exec_run(
            container,
            f"sh -c 'echo \"developer:{password}\" | chpasswd'",
            user="root"
        )

    # Enable password authentication in sshd_config
    await container_exec_run(
        container,
        "sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config",
        user="root"
    )

    # Restart SSH daemon to apply changes
    await container_exec_run(container, "pkill sshd", user="root")
    await container_exec_run(container, "sh -c '/usr/sbin/sshd'", user="root")

    return True
```

#### Redis Metadata Storage (Lines 273-318) - SshService.store_credential_metadata()

```python
def store_credential_metadata(
    self,
    agent_name: str,
    credential_id: str,
    auth_type: Literal["key", "password"],
    created_by: str,
    ttl_hours: float,
    public_key: Optional[str] = None
) -> None:
    """Store SSH credential metadata in Redis with TTL."""
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=ttl_hours)

    redis_key = f"{SSH_ACCESS_PREFIX}{agent_name}:{credential_id}"

    metadata = {
        "agent_name": agent_name,
        "credential_id": credential_id,
        "auth_type": auth_type,
        "created_at": now.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "created_by": created_by
    }
    if public_key:
        metadata["public_key"] = public_key

    # Store with TTL - Redis auto-expires
    ttl_seconds = int(ttl_hours * 3600)
    self.redis_client.setex(
        redis_key,
        ttl_seconds,
        json.dumps(metadata)
    )
    logger.info(f"Stored SSH {auth_type} metadata: {redis_key} (TTL: {ttl_hours}h)")
```

#### Host Detection (Lines 479-567) - get_ssh_host()

```python
def get_ssh_host() -> str:
    """
    Get the host IP/domain for SSH connections.

    Priority:
    1. SSH_HOST environment variable (explicit configuration)
    2. FRONTEND_URL domain extraction (production deployment)
    3. Tailscale IP detection
    4. host.docker.internal (Docker Desktop for Mac/Windows)
    5. Default gateway IP (often the Docker host on Linux)
    6. Fallback to localhost

    Note: This runs inside the backend container, so we need special
    handling to get the actual Docker host IP, not the container's IP.
    """
    # Option 1: Explicit environment variable (most reliable)
    ssh_host = os.getenv("SSH_HOST")
    if ssh_host:
        return ssh_host

    # Option 2: Extract host from FRONTEND_URL (production deployment)
    # FRONTEND_URL is set to production domain like "https://trinity.abilityai.dev"
    frontend_url = os.getenv("FRONTEND_URL", "")
    if frontend_url:
        parsed = urlparse(frontend_url)
        host = parsed.hostname or parsed.netloc
        if host and host not in ("localhost", "127.0.0.1", ""):
            return host

    # Option 3: Try to detect Tailscale IP
    try:
        result = subprocess.run(["tailscale", "ip", "-4"], ...)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Option 4: Try host.docker.internal (Docker Desktop Mac/Windows)
    try:
        ip = socket.gethostbyname("host.docker.internal")
        if ip and not ip.startswith("172.") and not ip.startswith("127."):
            return ip
    except socket.gaierror:
        pass

    # Option 5: Get default gateway IP (Linux Docker host)
    try:
        result = subprocess.run(["ip", "route", "show", "default"], ...)
        # Parse "default via 192.168.1.1 dev eth0" → 192.168.1.1
        if gateway_ip and not gateway_ip.startswith("172."):
            return gateway_ip
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Option 6: Fallback to localhost with warning
    return "localhost"
```

---

## Credential Cleanup

### Automatic Expiry (Redis TTL)

Redis handles metadata expiry automatically via `setex()`. When TTL expires, the key is deleted.

### Proactive Container Cleanup (Lines 368-413) - SshService.cleanup_expired_credentials()

```python
async def cleanup_expired_credentials(self) -> int:
    """
    Clean up expired SSH credentials from containers.
    Called periodically by background task.
    Redis TTL handles metadata cleanup automatically,
    but we need to remove credentials from containers.
    """
    cleaned = 0
    pattern = f"{SSH_ACCESS_PREFIX}*"

    # Find credentials about to expire (within 60 seconds)
    for redis_key in self.redis_client.keys(pattern):
        ttl = self.redis_client.ttl(redis_key)

        # If TTL is very low or negative, credential is about to expire
        if ttl is not None and 0 <= ttl <= 60:
            try:
                data = self.redis_client.get(redis_key)
                if data:
                    metadata = json.loads(data)
                    agent_name = metadata.get("agent_name")
                    auth_type = metadata.get("auth_type", "key")
                    credential_id = metadata.get("credential_id") or metadata.get("comment")

                    if agent_name and credential_id:
                        if auth_type == "password":
                            await self.clear_container_password(agent_name)
                        else:
                            await self.remove_ssh_key(agent_name, credential_id)
                        cleaned += 1
            except Exception as e:
                logger.warning(f"Error during credential cleanup for {redis_key}: {e}")

    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} expired SSH credentials")
    return cleaned
```

### Key Removal (Lines 243-279) - SshService.remove_ssh_key()

```python
async def remove_ssh_key(self, agent_name: str, comment: str) -> bool:
    """Remove SSH key by comment from agent's authorized_keys."""
    container = get_agent_container(agent_name)
    if not container:
        return True  # Container may have been deleted

    # Use sed to remove lines containing the comment
    escaped_comment = comment.replace("/", "\\/").replace(".", "\\.")
    await container_exec_run(
        container,
        f"sed -i '/{escaped_comment}/d' /home/developer/.ssh/authorized_keys",
        user="developer"
    )
    return True
```

### Password Clearing (Lines 213-241) - SshService.clear_container_password()

```python
async def clear_container_password(self, agent_name: str) -> bool:
    """Clear/lock the developer user password in agent container."""
    container = get_agent_container(agent_name)
    if not container:
        return True  # Container may have been deleted

    # Lock the account password (user can still use key auth)
    await container_exec_run(container, "passwd -l developer", user="root")
    return True
```

### Agent Stop/Delete Cleanup (Lines 441-484) - SshService.cleanup_agent_credentials()

```python
async def cleanup_agent_credentials(self, agent_name: str) -> int:
    """Clean up all SSH credentials for an agent (called on agent stop/delete)."""
    pattern = f"{SSH_ACCESS_PREFIX}{agent_name}:*"
    redis_keys = self.redis_client.keys(pattern)

    has_password_creds = False
    for key in redis_keys:
        try:
            data = self.redis_client.get(key)
            if data:
                metadata = json.loads(data)
                auth_type = metadata.get("auth_type", "key")
                credential_id = metadata.get("credential_id") or metadata.get("comment")

                if auth_type == "password":
                    has_password_creds = True
                elif credential_id:
                    await self.remove_ssh_key(agent_name, credential_id)
        except Exception as e:
            logger.warning(f"Error cleaning up credential {key}: {e}")

        self.redis_client.delete(key)

    # Clear password once if any password credentials existed
    if has_password_creds:
        await self.clear_container_password(agent_name)

    if redis_keys:
        logger.info(f"Cleaned up {len(redis_keys)} SSH credentials for agent {agent_name}")

    return len(redis_keys)
```

---

## Settings Layer

### Ops Setting Definition

**settings_service.py** (`src/backend/services/settings_service.py:32, 45`)

```python
OPS_SETTINGS_DEFAULTS = {
    # ... other settings ...
    "ssh_access_enabled": "false",  # Enable SSH access via MCP tool
}

OPS_SETTINGS_DESCRIPTIONS = {
    # ... other settings ...
    "ssh_access_enabled": "Enable ephemeral SSH access to agent containers via MCP tool (default: false)",
}
```

### Admin Configuration

SSH access must be explicitly enabled in the UI:
**Settings page → SSH Access section → Enable SSH Access toggle**

Or via API:
```bash
curl -X PUT /api/settings/ops/config \
  -H "Authorization: Bearer TOKEN" \
  -d '{"ssh_access_enabled": "true"}'
```

---

## Container Security Requirements

### Linux Capabilities

**lifecycle.py** (`src/backend/services/agent_service/lifecycle.py:31-37`)

```python
# Restricted mode capabilities - minimum for agent operation (default)
RESTRICTED_CAPABILITIES = [
    'NET_BIND_SERVICE',  # Bind to ports < 1024
    'SETGID', 'SETUID',  # Change user/group (for su/sudo)
    'CHOWN',             # Change file ownership
    'SYS_CHROOT',        # Use chroot
    'AUDIT_WRITE',       # Write to audit log
]
```

| Capability | Purpose |
|------------|---------|
| `SETGID` | SSH privilege separation (sshd changes GID) |
| `SETUID` | SSH privilege separation (sshd changes UID) |
| `CHOWN` | Ownership changes for SSH files |
| `SYS_CHROOT` | SSH ChrootDirectory support |
| `AUDIT_WRITE` | PAM session logging |
| `NET_BIND_SERVICE` | Bind to privileged ports (SSH) |

### Security Options

```python
security_opt=['apparmor:docker-default'],  # no-new-privileges removed for SSH support
```

**Important**: `no-new-privileges` is NOT set because SSH privilege separation requires setuid/setgid transitions.

---

## Complete Flow

### Key-Based Authentication

```
1. MCP Client calls get_agent_ssh_access(agent_name, ttl_hours=4, auth_method="key")
   |
2. MCP Tool (agents.ts:406-419) -> apiClient.createSshAccess()
   |
3. POST /api/agents/{name}/ssh-access (agents.py:1005)
   |-- Check ssh_access_enabled ops setting (lines 1031-1036)
   |   └── 403 if disabled
   |-- Check can_user_access_agent (line 1039)
   |   └── 403 if no access
   |-- Get container, verify running (lines 1042-1052)
   |   └── 404 if not found, 400 if not running
   |-- Validate TTL (0.1-24 hours) (lines 1054-1059)
   |-- Get SSH port from container labels (lines 1066-1068)
   |-- Get host (SSH_HOST env or Tailscale or localhost) (line 1071)
   |
4. Key Generation (ssh_service.py:44-82)
   |-- Generate ED25519 private key
   |-- Extract public key
   |-- Create unique comment: trinity-ephemeral-{agent}-{timestamp}
   |-- Return { private_key, public_key, comment }
   |
5. Key Injection (ssh_service.py:84-130)
   |-- docker exec: mkdir -p /home/developer/.ssh, chmod 700
   |-- docker exec: printf >> /home/developer/.ssh/authorized_keys
   |-- docker exec: chmod 600 authorized_keys
   |
6. Store Metadata in Redis (ssh_service.py:273-318)
   |-- Key: ssh_access:{agent_name}:{comment}
   |-- TTL: ttl_hours * 3600 seconds
   |-- Value: { agent_name, credential_id, auth_type, created_at, expires_at, created_by, public_key }
   |
7. Return Response to Client
   {
     "status": "success",
     "agent": "my-agent",
     "auth_method": "key",
     "connection": {
       "command": "ssh -p 2222 -i ~/.trinity/keys/my-agent.key developer@100.x.x.x",
       "host": "100.x.x.x",
       "port": 2222,
       "user": "developer"
     },
     "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----...",
     "expires_at": "2026-01-02T20:00:00Z",
     "expires_in_hours": 4,
     "instructions": [
       "Save the private key to a file: ~/.trinity/keys/my-agent.key",
       "Set permissions: chmod 600 ~/.trinity/keys/my-agent.key",
       "Connect: ssh -p 2222 -i ~/.trinity/keys/my-agent.key developer@100.x.x.x",
       "Key expires in 4 hours"
     ]
   }
```

### Password-Based Authentication

```
1-3. Same as key-based flow
   |
4. Password Generation (ssh_service.py:132-144)
   |-- Generate 24-char alphanumeric password
   |
5. Password Setting (ssh_service.py:146-204)
   |-- Generate SHA-512 hash with crypt.mksalt()
   |-- docker exec: usermod -p 'encrypted' developer (set password)
   |-- docker exec: sed /etc/ssh/sshd_config (enable PasswordAuthentication)
   |-- docker exec: pkill sshd && /usr/sbin/sshd (restart daemon)
   |
6. Store Metadata in Redis
   |-- Key: ssh_access:{agent_name}:pwd-{agent_name}-{timestamp}
   |-- TTL: ttl_hours * 3600 seconds
   |
7. Return Response
   {
     "status": "success",
     "agent": "my-agent",
     "auth_method": "password",
     "connection": {
       "command": "sshpass -p 'ABC123xyz...' ssh -o StrictHostKeyChecking=no -p 2222 developer@100.x.x.x",
       "host": "100.x.x.x",
       "port": 2222,
       "user": "developer",
       "password": "ABC123xyz..."
     },
     "expires_at": "2026-01-02T20:00:00Z",
     "expires_in_hours": 4,
     "instructions": [
       "Install sshpass if needed: brew install sshpass (macOS) or apt install sshpass (Linux)",
       "Connect: sshpass -p '...' ssh -o StrictHostKeyChecking=no -p 2222 developer@100.x.x.x",
       "Password expires in 4 hours"
     ]
   }
```

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| SSH access disabled globally | 403 | "SSH access is disabled. Enable it in Settings -> Ops Settings -> ssh_access_enabled" |
| User cannot access agent | 403 | "Access denied" |
| Agent container not found | 404 | "Agent not found" |
| Agent not running | 400 | "Agent must be running to generate SSH access. Start the agent first." |
| Invalid auth_method | 400 | "auth_method must be 'key' or 'password'" |
| Key injection failed | 500 | "Failed to inject SSH key into agent container" |
| Password setting failed | 500 | "Failed to set SSH password in agent container" |

---

## Security Considerations

1. **System-Level Control**: SSH access is disabled by default (`ssh_access_enabled = false`). Admin must explicitly enable.

2. **Access Control**: Endpoint requires authenticated user with `can_user_access_agent` permission.

3. **Ephemeral Credentials**: All credentials auto-expire via Redis TTL. Maximum TTL is 24 hours.

4. **One-Time Private Key**: Private keys are returned only once and never stored on server.

5. **Password Security**:
   - 24-char alphanumeric passwords (144+ bits of entropy)
   - SHA-512 hashing in container
   - Password locked when credential expires

6. **Container Isolation**: Each agent has its own container with isolated SSH configuration.

7. **No Persistent Keys**: Ephemeral keys are appended to authorized_keys with unique comments, allowing targeted removal.

8. **Container Capabilities**: Minimal capabilities granted - only those required for SSH privilege separation.

9. **Tailscale Priority**: Prefers Tailscale IP over localhost for secure network access.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SSH_ACCESS_DEFAULT_TTL_HOURS` | 4 | Default credential lifetime |
| `SSH_ACCESS_MAX_TTL_HOURS` | 24 | Maximum allowed TTL |
| `SSH_ACCESS_CLEANUP_INTERVAL` | 900 | Background cleanup interval (seconds) |
| `SSH_HOST` | (auto-detect) | Override host for SSH commands (highest priority) |
| `FRONTEND_URL` | `http://localhost` | Used to auto-detect SSH host in production (e.g., `https://trinity.abilityai.dev` → `trinity.abilityai.dev`) |

---

## Related Flows

- **Upstream**: [agent-lifecycle.md](agent-lifecycle.md) - Container creation with SSH capabilities
- **Related**: [agent-terminal.md](agent-terminal.md) - Alternative browser-based terminal access
- **Related**: [mcp-orchestration.md](mcp-orchestration.md) - MCP tool registration
- **Related**: [async-docker-operations.md](async-docker-operations.md) - Async wrappers for all Docker exec calls (DOCKER-001)

---

## Testing

### Prerequisites
- Backend running at localhost:8000
- MCP server running at localhost:8080
- At least one agent running
- `ssh_access_enabled` set to `true` in Ops Settings

### Test Steps

1. **Enable SSH Access**
   - Action: Navigate to Settings -> Ops Settings -> ssh_access_enabled = true
   - Verify: Setting saved successfully

2. **Generate Key-Based Credentials via MCP**
   - Action: Call `get_agent_ssh_access` with `auth_method: "key"`
   - Expected: Response contains private_key and connection.command
   - Verify: Save private key, run SSH command, verify connection

3. **Generate Password-Based Credentials via MCP**
   - Action: Call `get_agent_ssh_access` with `auth_method: "password"`
   - Expected: Response contains connection.password and sshpass command
   - Verify: Run command (requires sshpass installed), verify connection

4. **TTL Validation**
   - Action: Call with `ttl_hours: 0.01` (too low) and `ttl_hours: 100` (too high)
   - Expected: TTL clamped to 0.1 and 24 respectively
   - Verify: Check expires_at in response

5. **Stopped Agent Rejection**
   - Action: Stop agent, then call `get_agent_ssh_access`
   - Expected: 400 error "Agent must be running"

6. **Disabled Setting Rejection**
   - Action: Set `ssh_access_enabled = false`, call `get_agent_ssh_access`
   - Expected: 403 error with enable instructions

7. **Credential Expiry**
   - Action: Generate credential with short TTL (0.1 hours = 6 min)
   - Expected: After expiry, SSH connection fails
   - Verify: Redis key deleted, authorized_keys cleaned

### Edge Cases
- Multiple concurrent SSH sessions (should work)
- Key generation for agent with existing keys (appends to authorized_keys)
- Password generation when password auth already enabled (overwrites)
- Container restart during credential lifetime (credentials lost)

### Status
Not Tested
