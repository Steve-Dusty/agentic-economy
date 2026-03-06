# Credential System Refactor - Encrypted Files in Git

> **Requirement ID**: CRED-002
> **Priority**: HIGH
> **Status**: ⏳ Not Started
> **Created**: 2026-02-04
> **Updated**: 2026-02-05
> **Author**: Claude + Eugene

---

## Summary

Replace Trinity's complex Redis-based credential system with **encrypted credential files stored in git**. Credentials become portable, version-controlled, and simple.

| Current System | New System |
|----------------|------------|
| Redis store + assignments | Encrypted file in git |
| Template substitution (`.mcp.json.template`) | Direct file storage |
| Global `/credentials` page | Per-agent only |
| Complex: create → assign → apply | Simple: decrypt → inject |

---

## How It Works

### Storage

```
/home/developer/
├── .credentials.enc      # Encrypted credential files (committed to git)
├── .env                  # Decrypted at runtime (gitignored)
├── .mcp.json             # Decrypted at runtime (gitignored)
└── config/
    └── gcp-sa.json       # Decrypted at runtime (gitignored)
```

### Encrypted File Format

```json
{
  "version": 1,
  "algorithm": "AES-256-GCM",
  "key_id": "platform-2026",
  "nonce": "base64...",
  "ciphertext": "base64...",
  "tag": "base64..."
}
```

### Decrypted Payload

```json
{
  "files": {
    ".env": "HEYGEN_API_KEY=sk-xxx\nOPENAI_API_KEY=sk-yyy",
    ".mcp.json": "{ \"mcpServers\": { ... } }",
    "config/gcp-sa.json": "{ \"type\": \"service_account\", ... }"
  },
  "metadata": {
    "exported_at": "2026-02-05T15:30:00Z",
    "exported_by": "eugene@ability.ai"
  }
}
```

### Flow

**Export (UI → Git):**
1. User clicks "Export Credentials" in agent's Credentials tab
2. Backend reads credential files from running agent
3. Encrypts with platform key
4. Writes `.credentials.enc` to workspace
5. User commits to git

**Import (Git → Agent):**
1. On agent start, `startup.sh` checks for `.credentials.enc`
2. If found and platform key available, decrypts
3. Writes files to workspace (`.env`, `.mcp.json`, etc.)
4. Agent starts with credentials ready

**Hot Reload:**
1. User pastes credentials in UI (like today)
2. Files written to agent
3. Optionally re-export to update `.credentials.enc`

---

## Platform Key

```bash
# Generate key
openssl rand -base64 32

# Store in .env (gitignored)
CREDENTIAL_ENCRYPTION_KEY=Ks7Jm2Qp4Rt8Wv3Xy6Za9Bc1Df5Gh0Ij=
```

- Never committed to git
- Required to decrypt `.credentials.enc`
- Same key across Trinity instance enables portable deployments

---

## API Endpoints

### New

```
POST /api/agents/{name}/credentials/export
  → Reads files from agent, encrypts, writes .credentials.enc
  Auth: Owner or Admin

POST /api/agents/{name}/credentials/import
  → Decrypts .credentials.enc, writes files to agent
  Auth: Owner or Admin

POST /api/agents/{name}/credentials/inject
  → Writes credential files directly (hot-reload replacement)
  Body: { "files": { ".env": "...", ".mcp.json": "..." } }
  Auth: Owner or Admin
```

### Remove

```
# Global credential store - REMOVE ALL
GET    /api/credentials
POST   /api/credentials
DELETE /api/credentials/{id}
POST   /api/credentials/bulk

# Assignment model - REMOVE ALL
GET    /api/agents/{name}/credentials/assignments
POST   /api/agents/{name}/credentials/assign
DELETE /api/agents/{name}/credentials/assign/{id}
POST   /api/agents/{name}/credentials/apply

# Template-based - REMOVE
GET    /api/agents/{name}/credentials  (returns template requirements)

# Old hot-reload - REPLACE with /inject
POST   /api/agents/{name}/credentials/hot-reload
POST   /api/agents/{name}/credentials/reload
```

### Keep (Modified)

```
GET /api/agents/{name}/credentials/status
  → Returns what credential files exist in agent workspace
```

---

## MCP Tools

### New

```typescript
inject_credentials(agent_name: string, files: Record<string, string>): Result
  // Write credential files to agent workspace

export_credentials(agent_name: string): Result
  // Export to .credentials.enc

import_credentials(agent_name: string): Result
  // Import from .credentials.enc
```

### Remove

```typescript
reload_credentials  // Replaced by inject_credentials
get_credential_status  // Keep but simplify
```

---

## Frontend Changes

### Remove

- `src/frontend/src/views/Credentials.vue` - Delete entire page
- NavBar link to `/credentials` - Remove
- Global credential store UI - Remove

### Modify: CredentialsPanel.vue

```
┌─────────────────────────────────────────────────────────────┐
│ Credentials                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Credential Files                                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ .env              exists    [View] [Edit]              │ │
│  │ .mcp.json         exists    [View] [Edit]              │ │
│  │ config/gcp.json   missing   [Add]                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  [Export to Git]  [Import from Git]                         │
│                                                              │
│  Quick Inject (.env format)                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ HEYGEN_API_KEY=sk-xxx                                  │ │
│  │ OPENAI_API_KEY=sk-yyy                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  [Inject]                                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Backend Changes

### Delete

```
src/backend/credentials.py                    # Entire file (~677 lines)
```

### New

```
src/backend/services/credential_encryption.py  # ~150 lines
```

```python
class CredentialEncryptionService:
    def encrypt(self, files: dict[str, str]) -> str:
        """Encrypt credential files to .credentials.enc content"""

    def decrypt(self, encrypted: str) -> dict[str, str]:
        """Decrypt .credentials.enc content to files dict"""

    def export_to_agent(self, agent_name: str) -> None:
        """Read files from agent, encrypt, write .credentials.enc"""

    def import_to_agent(self, agent_name: str) -> None:
        """Read .credentials.enc, decrypt, write files to agent"""
```

### Modify

```
src/backend/routers/credentials.py
  - Remove: ~500 lines (store, assign, apply)
  - Add: ~100 lines (inject, export, import)

src/backend/services/agent_service/crud.py
  - Remove: credential injection during creation
  - Agent starts, checks for .credentials.enc, imports if found

src/backend/services/template_service.py
  - Remove: extract_credentials_from_template_yaml()
  - Remove: extract_env_vars_from_mcp_json()
  - Remove: generate_credential_files()
```

---

## Agent Server Changes

### Modify: startup.sh

```bash
# Add after git clone/pull:
if [ -f "/home/developer/.credentials.enc" ] && [ ! -f "/home/developer/.env" ]; then
    echo "Found encrypted credentials, requesting decryption..."
    curl -X POST "http://backend:8000/api/internal/decrypt-credentials" \
         -H "Content-Type: application/json" \
         -d "{\"agent_name\": \"$AGENT_NAME\"}"
fi
```

### Remove from agent_server

```
agent_server/routers/credentials.py
  - Remove: Template substitution logic (~50 lines)
  - Keep: File writing endpoint (simplified)
```

---

## Redis Changes

### Remove Keys

```
credentials:{id}:metadata
credentials:{id}:secret
user:{user_id}:credentials
agent:{agent_name}:credentials
agent:{agent_name}:mcp:{server}:credential_id
```

### No New Keys

Credentials live in git, not Redis. Injection history optional (defer to SEC-001 audit system).

---

## Implementation Order

### Phase 1: Build New (keep old working)

1. Create `credential_encryption.py` service
2. Add `/inject`, `/export`, `/import` endpoints
3. Add MCP tools
4. Update CredentialsPanel.vue with new UI
5. Modify startup.sh for auto-import

### Phase 2: Remove Old

1. Delete `credentials.py`
2. Delete `Credentials.vue`
3. Remove old endpoints from router
4. Remove template substitution
5. Remove NavBar link
6. Clean up imports

### Phase 3: Verify

1. Test fresh agent creation (no credentials → inject → export → git push)
2. Test git clone deployment (git pull → auto-import → agent works)
3. Test hot-reload (paste → inject)
4. Verify old endpoints return 404

---

## Security

- Platform key in env var only (never in git, never in Redis)
- `.credentials.enc` safe to commit (encrypted)
- `.env`, `.mcp.json` always gitignored
- File permissions: 600 for credential files
- Path validation: no `..`, must be under `/home/developer/`

---

## Testing Checklist

- [ ] Inject credentials via UI
- [ ] Export creates `.credentials.enc`
- [ ] Import decrypts and writes files
- [ ] Startup auto-import works
- [ ] Git clone + start works with encrypted credentials
- [ ] Old endpoints return 404
- [ ] No Redis credential keys remain
- [ ] MCP inject_credentials works

---

## Success Criteria

1. ✅ Agent credentials managed through git (encrypted)
2. ✅ No global credential store
3. ✅ No assignment model
4. ✅ Deploy agent to new instance via git clone
5. ✅ ~500 lines of code removed
