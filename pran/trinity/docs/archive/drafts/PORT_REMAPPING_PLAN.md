# Port Remapping Plan

> **Goal**: Simplify port configuration with web interface on port 80
> **Status**: Planning (not yet implemented)
> **Created**: 2026-01-09

## Target Configuration

| Service | Development | Production | Notes |
|---------|-------------|------------|-------|
| **Web UI** | 3000 | **80** | Standard HTTP, no port in URLs |
| **Backend API** | 8000 | 8000 | Proxied via `/api` on port 80 |
| **MCP Server** | 8080 | 8080 | Claude Code clients connect here |
| **Agent SSH** | 2222+ | 2222+ | Sequential allocation |
| **Vector (logs)** | 8686 | 8686 | Internal health checks |
| **Redis** | 6379 | 6379 | Internal only, never exposed |

### Architecture (Production)

```
Internet
    │
    ▼
Port 80 (nginx)
    ├── /              → Frontend static files
    ├── /api/*         → Backend :8000 (reverse proxy)
    └── /ws            → Backend :8000 (WebSocket proxy)

Port 8080 (MCP Server)
    └── /mcp           → Claude Code clients
```

---

## Files to Modify

### 1. Docker Compose Files

#### `docker-compose.yml` (Development)
| Line | Current | Change To | Notes |
|------|---------|-----------|-------|
| 8 | `"8000:8000"` | Keep as-is | Backend stays on 8000 |
| 75 | `"3000:3000"` | Keep as-is | Dev frontend stays on 3000 |
| 121 | `"8080:8080"` | Keep as-is | MCP already on 8080 |

**No changes needed for development.**

#### `docker-compose.prod.yml` (Production)
| Line | Current | Change To | Notes |
|------|---------|-----------|-------|
| 17 | `"8005:8005"` | `"8000:8000"` | Backend on 8000 |
| 62 | `http://localhost:8005/health` | `http://localhost:8000/health` | Health check URL |
| 73 | `VITE_API_URL=...8005` | `VITE_API_URL=http://localhost:8000` | Frontend API URL |
| 81 | `"3005:80"` | `"80:80"` | Frontend on port 80 |
| 151 | `"8007:8080"` | `"8080:8080"` | MCP on 8080 |
| 155 | `http://backend:8005` | `http://backend:8000` | MCP → Backend URL |

---

### 2. Configuration Files

#### `deploy.config.example`
| Line | Current | Change To |
|------|---------|-----------|
| 36 | `BACKEND_PORT="8005"` | `BACKEND_PORT="8000"` |
| 37 | `FRONTEND_PORT="3005"` | `FRONTEND_PORT="80"` |
| 39 | `MCP_PORT="8007"` | `MCP_PORT="8080"` |
| 42 | `AGENT_SSH_PORT_START="2223"` | `AGENT_SSH_PORT_START="2222"` |

#### `.env.example`
| Line | Current | Change To |
|------|---------|-----------|
| 83 | `BACKEND_URL=http://localhost:8000` | Keep as-is |

**No changes needed.**

#### `.env.prod`
| Line | Current | Change To |
|------|---------|-----------|
| 46 | `http://audit-logger:8002` | Remove or update if audit logger is removed |

---

### 3. Backend Code

#### `src/backend/config.py`
| Line | Current | Change To |
|------|---------|-----------|
| 40 | `BACKEND_URL = "http://localhost:8000"` | Keep as-is |
| 41 | `FRONTEND_URL = "http://localhost:3000"` | Keep as-is (dev default) |

**No changes needed** - these are development defaults.

#### `src/backend/services/docker_service.py`
| Line | Current | Change To | Notes |
|------|---------|-----------|-------|
| 120 | `max(existing_ports or {2289}) + 1` | `max(existing_ports or {2221}) + 1` | Start SSH at 2222 |

#### `src/backend/services/agent_service/lifecycle.py`
| Line | Current | Change To |
|------|---------|-----------|
| 125 | `ssh_port = int(labels.get("trinity.ssh-port", 2222))` | Keep as-is |

**No changes needed.**

#### `src/backend/routers/agents.py`
| Line | Current | Change To |
|------|---------|-----------|
| 974 | `ssh_port = int(labels.get("trinity.ssh-port", "2222"))` | Keep as-is |

**No changes needed.**

---

### 4. Frontend Code

#### `src/frontend/nginx.conf`
| Line | Current | Change To |
|------|---------|-----------|
| 22 | `proxy_pass http://trinity-backend:8005/api/;` | `proxy_pass http://trinity-backend:8000/api/;` |
| 36 | `proxy_pass http://trinity-backend:8005/ws;` | `proxy_pass http://trinity-backend:8000/ws;` |

#### `src/frontend/vite.config.js`
**No changes needed** - already uses 8000 for dev proxy.

#### `src/frontend/src/views/ApiKeys.vue`
| Line | Current | Change To |
|------|---------|-----------|
| 347 | `return 'http://localhost:8080/mcp'` | Keep as-is (MCP stays on 8080) |

**No changes needed.**

---

### 5. MCP Server Code

#### `src/mcp-server/Dockerfile`
**No changes needed** - already exposes 8080.

#### `src/mcp-server/src/server.ts`
**No changes needed** - already defaults to 8080.

---

### 6. Docker Files

#### `docker/backend/Dockerfile`
**No changes needed** - already exposes 8000.

#### `docker/frontend/Dockerfile`
**No changes needed** - nginx listens on 80 internally.

---

### 7. Scripts

#### `scripts/deploy/start.sh`
| Line | Current | Change To |
|------|---------|-----------|
| 32 | `http://localhost:3000` | Keep as-is (dev script) |
| 33 | `http://localhost:8000/docs` | Keep as-is |

**No changes needed** - this is for development.

#### `scripts/deploy/gcp-deploy.sh`
| Line | Current | Change To |
|------|---------|-----------|
| 161 | `BACKEND_PORT=${BACKEND_PORT:-8005}` | `BACKEND_PORT=${BACKEND_PORT:-8000}` |
| 162 | `FRONTEND_PORT=${FRONTEND_PORT:-3005}` | `FRONTEND_PORT=${FRONTEND_PORT:-80}` |

Update display URLs accordingly.

#### `scripts/deploy/gcp-firewall.sh`
| Line | Current | Change To |
|------|---------|-----------|
| 51 | `...3005...8007...` | `...80...8080...` |

Update firewall rule port list.

#### `scripts/deploy/verify-platform.sh`
**No changes needed** - uses localhost ports for local verification.

---

### 8. Documentation

#### `CLAUDE.md`
| Section | Current | Change To |
|---------|---------|-----------|
| Local URLs | 3000, 8000/docs, 8080/mcp | Keep as-is (dev) |
| Production Ports table | 3005, 8005, 8007 | 80, 8000, 8080 |

#### `CLAUDE.local.md.example`
| Line | Current | Change To |
|------|---------|-----------|
| 28-32 | Port table (3005, 8005, 8007) | Port table (80, 8000, 8080) |

#### `docs/DEPLOYMENT.md`
Update production port references throughout.

#### `docs/memory/architecture.md`
| Section | Current | Change To |
|---------|---------|-----------|
| Port Allocation (Production) | 3005, 8005, 8007 | 80, 8000, 8080 |

#### `README.md`
| Lines | Current | Change To |
|-------|---------|-----------|
| 80-92 | Dev environment ports | Keep as-is (dev) |

---

## Summary of Changes

### Files Requiring Modification

| Category | File | Changes |
|----------|------|---------|
| **Docker Compose** | `docker-compose.prod.yml` | 6 line changes |
| **Config** | `deploy.config.example` | 4 line changes |
| **Frontend** | `src/frontend/nginx.conf` | 2 line changes |
| **Backend** | `src/backend/services/docker_service.py` | 1 line change |
| **Scripts** | `scripts/deploy/gcp-deploy.sh` | 2 line changes |
| **Scripts** | `scripts/deploy/gcp-firewall.sh` | 1 line change |
| **Docs** | `CLAUDE.md` | Update port table |
| **Docs** | `CLAUDE.local.md.example` | Update port table |
| **Docs** | `docs/DEPLOYMENT.md` | Update port references |
| **Docs** | `docs/memory/architecture.md` | Update port table |

### Files NOT Requiring Changes

- `docker-compose.yml` - Development stays on 3000/8000/8080
- `src/backend/config.py` - Already uses 8000 as default
- `src/backend/services/agent_service/*.py` - Uses internal Docker networking
- `src/mcp-server/*` - Already on 8080
- `src/frontend/vite.config.js` - Already proxies to 8000
- All agent-internal communication (uses port 8000 on Docker network)

---

## Port Considerations

### Why These Ports?

| Port | Rationale |
|------|-----------|
| **80** | Standard HTTP - users don't need to type port |
| **8000** | De facto Python API standard, easy to remember |
| **8080** | Common alternative HTTP, intuitive for MCP |
| **2222** | Non-privileged SSH, memorable sequence |

### Port 80 Requirements

Running on port 80 requires either:
1. **nginx as reverse proxy** (recommended) - nginx runs as root briefly to bind port 80
2. **Docker port mapping** - Container runs non-root, Docker maps 80 externally
3. **setcap on binary** - Not recommended for containers

The current architecture uses Docker port mapping, which is secure.

### Firewall Considerations

Production firewall needs to allow:
- **80/tcp** - Web UI (was 3005)
- **8080/tcp** - MCP Server (was 8007)
- **2222-2262/tcp** - Agent SSH range

---

## Implementation Order

1. Update `docker-compose.prod.yml`
2. Update `deploy.config.example`
3. Update `src/frontend/nginx.conf`
4. Update `src/backend/services/docker_service.py` (SSH port start)
5. Update deployment scripts
6. Update documentation
7. Test locally with production compose
8. Deploy to production

---

## Rollback Plan

If issues arise:
1. Revert `docker-compose.prod.yml` to previous ports
2. Update firewall rules back to 3005, 8005, 8007
3. Restart services

No data migration required - this is purely a port mapping change.
