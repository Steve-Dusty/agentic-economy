# Example Trinity Instance

> **Host**: Your Server Name
> **Purpose**: Description of this instance's purpose

---

## Quick Reference

| Property | Value |
|----------|-------|
| **Host (Primary)** | your-server-ip |
| **Host (LAN)** | your-lan-ip (optional) |
| **SSH User** | your-username |
| **Trinity Path** | /home/username/trinity |
| **Frontend** | Port 3000 |
| **Backend** | Port 8000 |
| **MCP Server** | Port 8180 |

**Credentials**: Load from `.env` before operations:
```bash
source .env
```

---

## Connection

### SSH Access

```bash
# Load credentials first
source .env

# Connect
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST

# Run command directly
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "command"

# Run sudo command
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "echo '$SSH_PASSWORD' | sudo -S docker ps"
```

### SSH Tunnel (Access from Local Machine)

Start tunnel to access services locally:

```bash
./scripts/tunnel.sh &
```

**Tunnel Port Mappings** (customize in .env):
| Local Port | Remote Port | Service |
|------------|-------------|---------|
| 11030 | 3000 | Frontend |
| 11080 | 8000 | Backend API |
| 11085 | 8180 | MCP Server |

After tunnel: `http://localhost:11030` opens Trinity UI.

---

## Service Management

### Check Status

```bash
source .env

# All containers
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'trinity|agent'"

# Health check
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$BACKEND_PORT/health"
```

### Restart Services

```bash
source .env

# Restart all Trinity services
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && echo '$SSH_PASSWORD' | sudo -S docker compose restart"

# Restart specific service
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker restart trinity-backend"
```

### View Logs

```bash
source .env

# Backend logs
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker logs trinity-backend --tail 50"

# Agent logs
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker logs agent-{name} --tail 50"
```

---

## Agent Management

### List Agents

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep agent-"
```

### Start/Stop Agent

```bash
source .env

# Start
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker start agent-{name}"

# Stop
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker stop agent-{name}"
```

### Execute in Agent

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec agent-{name} ls -la /home/developer/workspace"
```

---

## API Access

### Get Token

```bash
source .env

TOKEN=$(curl -s -X POST http://localhost:$TUNNEL_BACKEND/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=admin&password=$ADMIN_PASSWORD" | jq -r '.access_token')

echo $TOKEN
```

### API Calls (via tunnel)

```bash
source .env

# List agents
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:$TUNNEL_BACKEND/api/agents | jq

# Agent details
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:$TUNNEL_BACKEND/api/agents/{name} | jq
```

### MCP Access (via tunnel)

```bash
source .env

# List tools
curl -s http://localhost:$TUNNEL_MCP/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | jq

# List agents via MCP
curl -s http://localhost:$TUNNEL_MCP/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_agents","arguments":{}},"id":1}' | jq
```

---

## Git Operations

### Check Version

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git log -1 --oneline"
```

### Pull Latest

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git pull origin main"
```

### Pull with Stash (if local changes)

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git stash && git pull origin main && git stash pop"
```

### Rebuild After Pull

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && echo '$SSH_PASSWORD' | sudo -S docker compose build --no-cache backend frontend mcp-server && echo '$SSH_PASSWORD' | sudo -S docker compose up -d"
```

---

## Database Operations

### List Tables

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker run --rm -v trinity_trinity-data:/data alpine sh -c 'apk add --quiet sqlite && sqlite3 /data/trinity.db \".tables\"'"
```

### Query Agents

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker run --rm -v trinity_trinity-data:/data alpine sh -c \"apk add --quiet sqlite && sqlite3 /data/trinity.db 'SELECT agent_name, owner_id FROM agent_ownership'\""
```

### Backup Database

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker run --rm -v trinity_trinity-data:/data -v /tmp:/backup alpine cp /data/trinity.db /backup/trinity.db.bak"
```

---

## Current State

### Deployed Agents

| Agent | Type | Status |
|-------|------|--------|
| trinity-system | System orchestrator | Running |
| (add your agents here) | | |

### Version

```
(run ./scripts/status.sh to see current version)
```

---

## Troubleshooting

### Agent Network Error

If agent fails with "network not found":

```bash
source .env

# Remove old container
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker rm agent-{name}"

# Restart backend (recreates agents properly)
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker restart trinity-backend"
```

### Backend Not Responding

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker restart trinity-backend && sleep 5 && curl -s http://localhost:$BACKEND_PORT/health"
```

---

## Files Reference

| Path | Purpose |
|------|---------|
| `$TRINITY_PATH/` | Trinity installation root |
| `$TRINITY_PATH/.env` | Environment configuration |
| `$TRINITY_PATH/docker-compose.yml` | Docker Compose config |
| `$TRINITY_PATH/config/agent-templates/` | Agent templates |
| `$TRINITY_PATH/src/backend/` | Backend source |
| `$TRINITY_PATH/src/frontend/` | Frontend source |

---

*Example Trinity Instance - Last updated: 2026-01-14*
