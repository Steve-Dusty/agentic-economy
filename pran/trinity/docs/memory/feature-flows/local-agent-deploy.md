# Feature: Local Agent Deployment via MCP

> **Updated**: 2026-02-05 - CRED-002: Removed credential_manager dependency, credentials now injected via direct API call.

## Overview

Deploy Trinity-compatible local Claude Code agents to a remote Trinity platform with a single MCP command. The **local agent** (Claude Code on your machine) packages the directory into a tar.gz archive and sends it to the remote Trinity backend for deployment.

**Key Architecture Point**: The MCP server runs remotely and cannot access your local filesystem. Therefore, the **calling agent** must package the archive locally before invoking the MCP tool.

## User Story

As a developer working with a Trinity-compatible local agent, I want to deploy it to a remote Trinity instance with one command so I can run it on the platform without manual file transfer.

## Entry Points

- **MCP Tool**: `deploy_local_agent` via Trinity MCP server
- **API**: `POST /api/agents/deploy-local`

---

## Architecture

```
+-------------------------------------+                     +-----------------------------+
|  Your Local Machine                 |                     |  Remote Trinity Server      |
|                                     |                     |                             |
|  Claude Code (local agent)          |     HTTP POST       |  MCP Server                 |
|  1. tar -czf archive.tar.gz ...     |  ---------------->  |  deploy_local_agent tool    |
|  2. base64 archive.tar.gz           |   archive +         |         |                   |
|  3. Read .env for credentials       |   credentials       |         v                   |
|  4. Call deploy_local_agent         |                     |  Backend API                |
|                                     |                     |  /api/agents/deploy-local   |
|  /home/you/my-agent/                |                     |         |                   |
|  |-- template.yaml                  |                     |         v                   |
|  |-- CLAUDE.md                      |                     |  Extract, validate, deploy  |
|  +-- .env                           |                     |  Agent container created    |
+-------------------------------------+                     +-----------------------------+
```

---

## MCP Tool Layer

### Tool: `deploy_local_agent`

**Location**: `src/mcp-server/src/tools/agents.ts:426-525`

**Parameters**:
```typescript
{
  archive: string,                    // Base64-encoded tar.gz archive (REQUIRED)
  credentials?: Record<string, string>, // Key-value pairs from .env (optional)
  name?: string                       // Override agent name (optional)
}
```

**Tool Definition** (lines 437-456):
```typescript
parameters: z.object({
  archive: z
    .string()
    .describe(
      "Base64-encoded tar.gz archive of the agent directory. " +
      "The archive should contain the agent files at the root level (template.yaml, CLAUDE.md, etc.). " +
      "Exclude .git, node_modules, __pycache__, .venv, and .env from the archive."
    ),
  credentials: z
    .record(z.string())
    .optional()
    .describe(
      "Key-value pairs of credentials to inject (e.g., {\"API_KEY\": \"sk-xxx\", \"SECRET\": \"yyy\"}). " +
      "Read these from the local .env file before calling."
    ),
  name: z
    .string()
    .optional()
    .describe("Agent name override (defaults to name from template.yaml)"),
}),
```

**Validation** (lines 464-476):
- Checks archive is provided and non-empty
- Validates base64 format with regex: `/^[A-Za-z0-9+/=]+$/`

**Description**: The tool receives a pre-packaged archive from the calling agent and forwards it to the backend. It does NOT access the local filesystem - that's the calling agent's responsibility.

---

## Calling Agent Workflow

The local Claude Code agent must perform these steps before calling `deploy_local_agent`:

### Step 1: Create tar.gz Archive

```bash
# Package the agent directory, excluding unnecessary files
tar -czf /tmp/agent-deploy.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='.env' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  -C /path/to/parent agent-directory-name
```

### Step 2: Base64 Encode

```bash
# macOS
base64 -i /tmp/agent-deploy.tar.gz > /tmp/agent-deploy.b64

# Linux
base64 /tmp/agent-deploy.tar.gz > /tmp/agent-deploy.b64
```

### Step 3: Read Credentials (Optional)

```bash
# Read .env file and parse KEY=VALUE pairs
cat /path/to/agent/.env
```

### Step 4: Call MCP Tool

The agent then calls `deploy_local_agent` with:
- `archive`: Contents of the base64 file
- `credentials`: Parsed key-value pairs from .env
- `name`: Optional name override

---

## Backend Layer

### Architecture (Service Layer)

The local agent deployment uses a **thin router + service layer** architecture:

| Layer | File | Purpose |
|-------|------|---------|
| Router | `src/backend/routers/agents.py:212-225` | Endpoint definition |
| Service | `src/backend/services/agent_service/deploy.py` (437 lines) | Deployment business logic |

### Endpoint: POST /api/agents/deploy-local

**Router**: `src/backend/routers/agents.py:212-225`

```python
@router.post("/deploy-local")
async def deploy_local_agent(
    body: DeployLocalRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Deploy a Trinity-compatible local agent."""
    return await deploy_local_agent_logic(
        body=body,
        current_user=current_user,
        request=request,
        create_agent_fn=create_agent_internal
    )
```

> **CRED-002 (2026-02-05)**: `credential_manager` parameter removed. Credentials are now injected
> after agent creation via `inject_credentials` endpoint or imported from `.credentials.enc` on startup.

**Request Model** (`src/backend/models.py:308-312`):
```python
class DeployLocalRequest(BaseModel):
    """Request to deploy a local agent."""
    archive: str  # Base64-encoded tar.gz
    credentials: Optional[Dict[str, str]] = None  # KEY=VALUE pairs
    name: Optional[str] = None  # Override name from template.yaml
```

**Response Model** (`src/backend/models.py:315-323`):
```python
class DeployLocalResponse(BaseModel):
    """Response from local agent deployment."""
    status: str  # "success" or "error"
    agent: Optional[AgentStatus] = None
    versioning: Optional[VersioningInfo] = None
    credentials_imported: Dict[str, CredentialImportResult] = {}
    credentials_injected: int = 0
    error: Optional[str] = None
    code: Optional[str] = None  # Error code for machine-readable errors
```

### Deployment Flow (`deploy.py:183-437`)

1. **Decode & Validate Archive** (lines 214-232)
   - Decode base64 archive
   - Check size limit (50MB max)

2. **Validate Credentials Count** (lines 234-242)
   - Check credentials count (100 max)

3. **Extract Archive** (lines 244-260)
   - Extract to temp directory using `_safe_extract_tar()`
   - Security: Full path validation via `_validate_tar_member()`

4. **Find Root Directory** (lines 262-267)
   - Handle nested extraction (single directory case)

5. **Trinity-Compatible Validation** (lines 269-278)
   - `is_trinity_compatible()` in `services/template_service.py:309-358`
   - Requires template.yaml with `name` and `resources` fields

6. **Determine Agent Name** (lines 280-291)
   - Use body.name override or template.yaml name
   - Sanitize with `sanitize_agent_name()`

7. **Version Handling** (lines 293-307)
   - `get_next_version_name()` in `helpers.py:207-237` finds next available version
   - Pattern: `my-agent` -> `my-agent-2` -> `my-agent-3`
   - Stops previous version if running via `get_latest_version()` (helpers.py:240-264)

8. **Template Copy** (lines 309-330)
   - Try `/agent-configs/templates` first (with write test)
   - Fall back to `./config/agent-templates/{version_name}/`

9. **Agent Creation** (lines 332-357)
    - Extract runtime config from template
    - Call `create_agent_fn()` (injected `create_agent_internal`) with local template

10. **Credential Injection** (lines 359-385) - CRED-002
    - If credentials provided, inject via `POST /api/agents/{name}/credentials/inject`
    - Writes .env file directly to agent workspace
    - No longer uses credential_manager or Redis

12. **CLAUDE.md Injection** (lines 391-407)
    - If CLAUDE.md exists, inject custom instructions via `/api/trinity/inject`

13. **Return Response** (lines 409-421)
    - Return DeployLocalResponse with agent status, versioning info, credential results

### Safe Tar Extraction (`deploy.py:39-181`)

The extraction uses comprehensive security validation:

**Path Validation** (`_is_path_within()`, lines 43-60):
- Uses `Path.resolve()` to normalize paths
- Checks target stays within base directory

**Member Validation** (`_validate_tar_member()`, lines 63-135):
- Rejects absolute paths
- Rejects path traversal (`..` in paths)
- Validates destination stays within base_dir
- Rejects device files (chr, blk) and FIFOs
- Validates symlink targets stay within base_dir
- Validates hardlink targets stay within base_dir

**Safe Extraction** (`_safe_extract_tar()`, lines 138-180):
- Checks file count (1000 max)
- Validates all members before extraction
- Only extracts validated members

---

## Template Validation

**Location**: `src/backend/services/template_service.py:309-358`

```python
def is_trinity_compatible(path: Path) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Check if a directory contains a Trinity-compatible agent.

    A Trinity-compatible agent must have:
    1. template.yaml file
    2. name field in template.yaml
    3. resources field in template.yaml
    """
```

**Validation Checks**:
1. `template.yaml` exists
2. File is valid YAML
3. File is not empty
4. `name` field present
5. `resources` field present and is a dictionary
6. Warning (non-blocking) if `CLAUDE.md` missing

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `NOT_TRINITY_COMPATIBLE` | 400 | Missing or invalid template.yaml |
| `ARCHIVE_TOO_LARGE` | 400 | Exceeds 50MB limit |
| `INVALID_ARCHIVE` | 400 | Not valid tar.gz, bad base64, or path traversal |
| `TOO_MANY_FILES` | 400 | Exceeds 1000 file limit |
| `TOO_MANY_CREDENTIALS` | 400 | Exceeds 100 credential limit |
| `MISSING_NAME` | 400 | No name specified and template.yaml has no name |

---

## Size Limits

| Limit | Value | Constant Location |
|-------|-------|-------------------|
| Archive size | 50 MB | `deploy.py:34` MAX_ARCHIVE_SIZE |
| Credential count | 100 | `deploy.py:35` MAX_CREDENTIALS |
| File count | 1000 | `deploy.py:36` MAX_FILES |

---

## Security Considerations

1. **Path Traversal Prevention**: Archive paths validated via `_validate_tar_member()`:
   - No `..` in paths
   - No absolute paths
   - Symlinks/hardlinks validated to stay within extraction dir
   - Device files and FIFOs rejected

2. **Temp Cleanup**: Temp directory always cleaned up in finally block (lines 430-436)

3. **Credential Handling**: Credentials sent separately from archive, not stored in archive

4. **Auth Required**: Uses standard JWT authentication via `get_current_user`

5. **Write Permission Check**: Templates directory write-tested before use (lines 328-334)

---

## Testing

### Prerequisites
- Trinity backend running (local or remote)
- MCP server running and accessible
- Valid MCP API key configured in Claude Code
- Local agent directory with valid template.yaml

### Test Steps

#### 1. Create Test Agent Directory
```bash
mkdir -p /tmp/test-deploy-agent
cat > /tmp/test-deploy-agent/template.yaml << 'EOF'
name: test-deploy
display_name: Test Deploy Agent
description: Testing local agent deployment
resources:
  cpu: "2"
  memory: "4g"
EOF

echo "# Test Deploy Agent" > /tmp/test-deploy-agent/CLAUDE.md
echo "TEST_API_KEY=test-value-123" > /tmp/test-deploy-agent/.env
```

#### 2. Package and Deploy via Claude Code

In Claude Code with Trinity MCP configured, ask:

```
Package and deploy my local agent at /tmp/test-deploy-agent to Trinity.

Steps:
1. Create a tar.gz archive of the directory (exclude .git, node_modules, .env)
2. Base64 encode the archive
3. Read the .env file for credentials
4. Call deploy_local_agent with the archive and credentials
```

**Expected**: Claude Code will:
1. Run `tar` command to create archive
2. Run `base64` to encode it
3. Parse .env file
4. Call the MCP tool with the data

**Verify**:
- Agent "test-deploy" created and running in Trinity
- Credential TEST_API_KEY imported

#### 3. Deploy Again (Versioning Test)
```
Deploy my local agent at /tmp/test-deploy-agent to Trinity again
```

**Expected**:
- New agent "test-deploy-2" created
- Previous "test-deploy" stopped

#### 4. Test Invalid Archive
```
Call deploy_local_agent with archive="not-valid-base64!"
```

**Expected**: Error "Invalid archive format"

#### 5. Test Missing Template
```bash
rm /tmp/test-deploy-agent/template.yaml
# Then try to deploy
```

**Expected**: Error "NOT_TRINITY_COMPATIBLE"

### Edge Cases
- [ ] Archive larger than 50MB -> ARCHIVE_TOO_LARGE
- [ ] More than 1000 files -> TOO_MANY_FILES
- [ ] Path traversal in archive -> INVALID_ARCHIVE
- [ ] Same credential with different value -> renamed with suffix

### Cleanup
```bash
rm -rf /tmp/test-deploy-agent
rm -f /tmp/agent-deploy.tar.gz /tmp/agent-deploy.b64
```

---

## Example: Full Deployment Script

For reference, here's a complete bash script a local agent might execute:

```bash
#!/bin/bash
# deploy-to-trinity.sh - Package and prepare for MCP deployment

AGENT_DIR="$1"
if [ -z "$AGENT_DIR" ]; then
  echo "Usage: deploy-to-trinity.sh /path/to/agent"
  exit 1
fi

# Validate template.yaml exists
if [ ! -f "$AGENT_DIR/template.yaml" ]; then
  echo "Error: Not Trinity-compatible - missing template.yaml"
  exit 1
fi

# Create archive
ARCHIVE="/tmp/trinity-deploy-$$.tar.gz"
tar -czf "$ARCHIVE" \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  --exclude='.env' \
  -C "$(dirname "$AGENT_DIR")" "$(basename "$AGENT_DIR")"

# Base64 encode
ARCHIVE_B64=$(base64 -i "$ARCHIVE" 2>/dev/null || base64 "$ARCHIVE")

# Read credentials from .env
CREDENTIALS="{}"
if [ -f "$AGENT_DIR/.env" ]; then
  CREDENTIALS=$(grep -v '^#' "$AGENT_DIR/.env" | grep '=' | \
    awk -F'=' '{gsub(/^[ \t]+|[ \t]+$/, "", $1); gsub(/^[ \t]+|[ \t]+$/, "", $2);
                printf "\"%s\": \"%s\", ", $1, $2}' | \
    sed 's/, $//' | sed 's/^/{/' | sed 's/$/}/')
fi

echo "Archive size: $(wc -c < "$ARCHIVE") bytes"
echo "Credentials: $CREDENTIALS"
echo "Ready for deploy_local_agent MCP call"

# Cleanup
rm -f "$ARCHIVE"
```

---

## Related Documentation

- [TRINITY_COMPATIBLE_AGENT_GUIDE.md](../../TRINITY_COMPATIBLE_AGENT_GUIDE.md) - Required template.yaml structure
- [credential-injection.md](credential-injection.md) - Credential management
- [agent-lifecycle.md](agent-lifecycle.md) - Agent creation flow

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-05 | **CRED-002**: Removed `credential_manager` parameter from deploy flow. Credentials now injected via `POST /api/agents/{name}/credentials/inject` endpoint directly. Updated line numbers for deployment flow steps 8-10. |
| 2026-01-23 | Verified all line numbers. Updated deploy.py references (now 437 lines). Added safe tar extraction details. Updated router line numbers (212-225). Added template validation location. |
| 2025-12-30 | Verified line numbers |
| 2025-12-27 | Service layer refactoring: Deploy logic moved to `services/agent_service/deploy.py` |
| 2025-12-24 | Changed from local path to archive-based deployment |
| 2025-12-21 | Initial implementation |

**Status**: Working
