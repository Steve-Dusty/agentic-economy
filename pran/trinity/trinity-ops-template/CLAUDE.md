# Trinity Operations Agent

> **Purpose**: Manage and operate Trinity Deep Agent Platform instances.
> This is the master operator agent with knowledge of Trinity architecture and operations.

---

## Overview

Trinity is a **Deep Agent Orchestration Platform** for deploying, orchestrating, and governing autonomous AI systems. Each instance runs as a Docker-based deployment with:

- **Frontend** (Vue.js) - Web UI for agent management
- **Backend** (FastAPI) - REST API and WebSocket server
- **MCP Server** (FastMCP) - Model Context Protocol for external agent access
- **Scheduler** (Python/APScheduler) - Dedicated scheduled task execution service
- **Redis** - Credential and session storage, distributed locking
- **Vector** - Log aggregation
- **Agent Containers** - Isolated Docker containers running Claude Code

## Instance Management

### Instance Directory Structure

Each instance is managed in `instances/{name}/`:

```
instances/{name}/
├── CLAUDE.md           # Instance-specific operations guide
├── .env                # Credentials (never commit)
├── scripts/            # Helper scripts (tunnel, health-check)
└── state.md            # Current deployment state (optional)
```

### Working with an Instance

```bash
# Navigate to instance directory
cd instances/{name}

# Load credentials
source .env

# SSH to instance
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST

# Run remote command
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "command here"

# Run sudo command
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "echo '$SSH_PASSWORD' | sudo -S docker ps"
```

---

## Trinity Architecture

### Core Services

| Service | Default Port | Purpose |
|---------|--------------|---------|
| Frontend | 3000 | Vue.js Web UI |
| Backend | 8000 | FastAPI REST API |
| MCP Server | 8080/8180 | Model Context Protocol |
| Scheduler | 8001 | Scheduled task execution |
| Redis | 6379 | Sessions, credentials, distributed locks |
| Vector | 8686 | Log aggregation |
| OTEL Collector | 4317-4318 | Telemetry |

### Docker Containers

**Platform containers** (prefix `trinity-`):
- `trinity-backend` - FastAPI backend
- `trinity-frontend` - Vue.js frontend
- `trinity-mcp-server` - MCP protocol server
- `trinity-scheduler` - Scheduled task execution (prevents duplicate runs)
- `trinity-redis` - Redis instance (also used for scheduler locking)
- `trinity-vector` - Log aggregation
- `trinity-otel-collector` - OpenTelemetry

**Agent containers** (prefix `agent-`):
- `agent-{name}` - Each agent runs in isolation
- Labels: `trinity.platform=agent`, `trinity.agent-name={name}`

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `trinity_trinity-data` | SQLite database (`trinity.db`) |
| `trinity_redis-data` | Redis persistence |
| `trinity_agent-configs` | Agent templates |
| `agent-{name}-workspace` | Agent workspace (per agent) |

### Network

- `trinity-agent-network` - Isolated bridge network (172.28.0.0/16)
- Agents communicate via internal hostnames

---

## Standard Operations

### Health Checks

```bash
# Backend health
curl -s http://$HOST:$BACKEND_PORT/health

# Frontend accessible
curl -s -o /dev/null -w '%{http_code}' http://$HOST:$FRONTEND_PORT

# Redis ping
docker exec trinity-redis redis-cli ping

# MCP server health
curl -s http://$HOST:$MCP_PORT/health

# Scheduler health
curl -s http://$HOST:8001/health
```

### Service Management

```bash
# Check all containers
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'trinity|agent'

# Restart all services
cd ~/trinity && docker compose restart

# Restart specific service
docker restart trinity-backend

# View logs
docker logs trinity-backend --tail 50 -f

# Rebuild after code changes
cd ~/trinity && docker compose build --no-cache backend frontend mcp-server scheduler
docker compose up -d
```

### Agent Management

```bash
# List agents
docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep agent-

# Start agent
docker start agent-{name}

# Stop agent
docker stop agent-{name}

# View agent logs
docker logs agent-{name} --tail 50

# Execute in agent
docker exec agent-{name} ls -la /home/developer/workspace

# Check agent workspace
docker exec agent-{name} cat /home/developer/workspace/CLAUDE.md
```

### Git Operations (Trinity Codebase)

```bash
# Check version
cd ~/trinity && git log -1 --oneline

# Pull latest
cd ~/trinity && git pull origin main

# Stash, pull, apply (if local changes)
cd ~/trinity && git stash && git pull origin main && git stash pop
```

---

## API Reference

### Authentication

```bash
# Get access token (admin login)
TOKEN=$(curl -s -X POST http://$HOST:$BACKEND_PORT/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=admin&password=$ADMIN_PASSWORD" | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $TOKEN" http://$HOST:$BACKEND_PORT/api/agents
```

### Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/agents | List all agents |
| GET | /api/agents/{name} | Get agent details |
| POST | /api/agents | Create agent |
| DELETE | /api/agents/{name} | Delete agent |
| POST | /api/agents/{name}/start | Start agent |
| POST | /api/agents/{name}/stop | Stop agent |
| GET | /api/agents/{name}/logs | Get agent logs |
| GET | /api/agents/{name}/stats | Get live telemetry |
| POST | /api/agents/{name}/chat | Send chat message |
| GET | /api/agents/{name}/chat/history | Get chat history |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /api/auth/mode | Auth configuration |
| POST | /token | Get access token |
| GET | /api/templates | List templates |
| GET | /api/observability/metrics | OTel metrics |

### MCP Access

```bash
# List MCP tools
curl http://$HOST:$MCP_PORT/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Call MCP tool
curl http://$HOST:$MCP_PORT/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_agents","arguments":{}},"id":1}'
```

---

## Database Operations

### SQLite Access

```bash
# List tables
docker run --rm -v trinity_trinity-data:/data alpine sh -c \
  'apk add --quiet sqlite && sqlite3 /data/trinity.db ".tables"'

# Query agents
docker run --rm -v trinity_trinity-data:/data alpine sh -c \
  "apk add --quiet sqlite && sqlite3 /data/trinity.db 'SELECT * FROM agent_ownership'"

# Backup database
docker run --rm -v trinity_trinity-data:/data -v /tmp:/backup alpine \
  cp /data/trinity.db /backup/trinity.db.bak
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts |
| `agent_ownership` | Agent registry and owners |
| `agent_schedules` | Scheduled tasks |
| `agent_permissions` | Inter-agent permissions |
| `chat_sessions` | Conversation sessions |
| `chat_messages` | Chat history |
| `mcp_api_keys` | MCP API keys |
| `email_whitelist` | Allowed login emails |

---

## Troubleshooting

### Agent Container Won't Start

**Symptom**: `network xxx not found` error

**Cause**: Agent references old Docker network

**Fix**: Remove and recreate container:
```bash
# Remove old container (preserves workspace)
docker rm agent-{name}

# Recreate via API or restart backend
docker restart trinity-backend
# Then start agent via UI/API
```

### Backend Not Responding

```bash
# Check logs
docker logs trinity-backend --tail 100

# Restart
docker restart trinity-backend

# Verify health
sleep 5 && curl -s http://localhost:8000/health
```

### Redis Connection Issues

```bash
# Check Redis
docker logs trinity-redis --tail 50

# Restart Redis
docker restart trinity-redis

# Verify
docker exec trinity-redis redis-cli ping
```

### Database Locked

```bash
# Check for multiple writers
docker exec trinity-backend ps aux | grep uvicorn

# Restart backend (single writer)
docker restart trinity-backend
```

---

## Upgrade Procedure

```bash
# 1. Backup database
docker run --rm -v trinity_trinity-data:/data -v ~/backups:/backup alpine \
  cp /data/trinity.db /backup/trinity-$(date +%Y%m%d).db

# 2. Pull latest code
cd ~/trinity && git pull origin main

# 3. Rebuild and restart
docker compose build --no-cache backend frontend mcp-server scheduler
docker compose up -d

# 4. Verify health
sleep 10 && curl -s http://localhost:8000/health && curl -s http://localhost:8001/health
```

---

## Instance Credentials Pattern

Each instance `.env` should contain:

```bash
# Connection
SSH_HOST=your-server-ip          # Or Tailscale IP
SSH_HOST_LAN=your-lan-ip         # Optional: LAN IP for local access
SSH_USER=your-username
SSH_PASSWORD=your-password

# Trinity Access
TRINITY_PATH=/home/user/trinity
FRONTEND_PORT=3000
BACKEND_PORT=8000
MCP_PORT=8180

# Authentication
ADMIN_PASSWORD=your-admin-password
MCP_API_KEY=trinity_mcp_xxx

# API Keys (for agents)
ANTHROPIC_API_KEY=sk-ant-xxx

# Tunnel Ports (optional - for local access)
TUNNEL_FRONTEND=11030
TUNNEL_BACKEND=11080
TUNNEL_MCP=11085
```

---

## MCP Multi-Instance Access

Configure `.mcp.json` in this directory to access all instances:

```json
{
  "mcpServers": {
    "trinity-{instance}": {
      "type": "http",
      "url": "http://localhost:{tunneled_port}/mcp",
      "headers": {
        "Authorization": "Bearer ${INSTANCE_MCP_KEY}"
      }
    }
  }
}
```

Start tunnels before using MCP access.

---

## Adding a New Instance

1. Create directory: `mkdir -p instances/{name}/scripts`
2. Copy template from `instances/example/` or create new CLAUDE.md
3. Create `.env` with connection and authentication credentials
4. Copy helper scripts from `instances/example/scripts/`
5. Add to `.mcp.json` if MCP access needed
6. Test connection: `source .env && ssh $SSH_USER@$SSH_HOST`

### Instance Types

| Type | Example | Notes |
|------|---------|-------|
| **Local Server** | Home lab, workstation | Direct SSH, no firewall |
| **Cloud VM** | GCP, AWS, Azure | May need tunnels or VPN |
| **VPS** | Hetzner, DigitalOcean | Public IP, firewall rules |
| **Tailscale** | Any remote | Use Tailscale IP |

---

## Monitoring & Health Checks

### Built-in Trinity APIs

Trinity instances expose ops endpoints for monitoring:

```bash
# Get auth token first
TOKEN=$(curl -s -X POST http://$HOST:$BACKEND_PORT/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=admin&password=$ADMIN_PASSWORD" | jq -r '.access_token')

# Fleet status (all agents with context usage)
curl -s -H "Authorization: Bearer $TOKEN" http://$HOST:$BACKEND_PORT/api/ops/fleet/status | jq

# Fleet health (issues, warnings, healthy counts)
curl -s -H "Authorization: Bearer $TOKEN" http://$HOST:$BACKEND_PORT/api/ops/fleet/health | jq

# Cost metrics (if OTel enabled)
curl -s -H "Authorization: Bearer $TOKEN" http://$HOST:$BACKEND_PORT/api/ops/costs | jq

# OTel observability status
curl -s -H "Authorization: Bearer $TOKEN" http://$HOST:$BACKEND_PORT/api/observability/status | jq
```

### Health Check Endpoints

| Endpoint | Auth | What it checks |
|----------|------|----------------|
| `GET /health` | No | Backend alive |
| `GET /api/ops/fleet/status` | Yes | All agents + context |
| `GET /api/ops/fleet/health` | Yes | Health classification |
| `GET /api/ops/costs` | Yes | OTel cost metrics |
| `GET /api/observability/status` | Yes | OTel collector status |
| `GET /api/logs/health` | Yes | Log archival service |

### Log Analysis

Trinity uses Vector for centralized logging. Query logs via SSH:

```bash
# Platform errors (last hour)
ssh $SSH_USER@$SSH_HOST "sudo docker exec trinity-vector sh -c \"tail -10000 /data/logs/platform.json\" | jq 'select(.level == \"error\")'"

# Error count
ssh $SSH_USER@$SSH_HOST "sudo docker exec trinity-vector sh -c \"tail -10000 /data/logs/platform.json | grep -c '\"level\":\"error\"'\""

# Auth failures
ssh $SSH_USER@$SSH_HOST "sudo docker exec trinity-vector sh -c \"grep -i 'unauthorized\\|forbidden\\|auth' /data/logs/platform.json | tail -20\" | jq"

# Agent errors
ssh $SSH_USER@$SSH_HOST "sudo docker exec trinity-vector sh -c \"tail -5000 /data/logs/agents.json\" | jq 'select(.level == \"error\")'"

# Container restart issues
ssh $SSH_USER@$SSH_HOST "sudo docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -E 'Restarting|Exited'"
```

### Resource Monitoring

```bash
# Disk usage
ssh $SSH_USER@$SSH_HOST "df -h | grep -E '/$|/var'"

# Docker disk usage
ssh $SSH_USER@$SSH_HOST "sudo docker system df"

# Container memory/CPU
ssh $SSH_USER@$SSH_HOST "sudo docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep -E 'trinity|agent'"

# Log file sizes
ssh $SSH_USER@$SSH_HOST "sudo docker exec trinity-vector ls -lh /data/logs/"
```

### Key Metrics to Monitor

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Backend health | - | Not 200 | Restart backend |
| Agent context | >75% | >90% | Reset context |
| Disk space | >80% | >95% | Cleanup logs/docker |
| Error rate | >10/hr | >50/hr | Check logs |
| Container restarts | Any | Multiple | Check docker logs |
| Database size | >1GB | >5GB | Archive old data |

---

## Reference Documentation

For detailed Trinity internals, see the codebase:
- Architecture: `trinity/docs/memory/architecture.md`
- Requirements: `trinity/docs/memory/requirements.md`
- Feature flows: `trinity/docs/memory/feature-flows/`
- Deployment: `trinity/docs/DEPLOYMENT.md`

---

*Trinity Operations Agent - Manage your sovereign AI infrastructure*
