# Vector Logging Migration Plan

> **Purpose**: Replace unreliable audit-logger with Vector for centralized, reliable log aggregation.
> **Created**: 2025-12-31
> **Status**: Ready for implementation

---

## Executive Summary

Remove the current audit-logger service (fire-and-forget HTTP calls, silently drops events) and replace with Vector - a battle-tested log aggregator that captures ALL container stdout/stderr automatically via Docker socket.

### Benefits
- **Reliable**: Never drops logs - captures everything Docker sees
- **Complete**: ALL containers automatically (no manual call sites)
- **Zero code maintenance**: No application changes needed after migration
- **Queryable**: JSON files searchable with grep/jq
- **Production-proven**: Used by Datadog, AWS, and thousands of companies

---

## Current State Analysis

### Audit Logger Problems
| Issue | Impact |
|-------|--------|
| Fire-and-forget with 2s timeout | Events silently dropped |
| 173+ manual call sites | Incomplete coverage, maintenance burden |
| Silent failures | No way to detect audit logging problems |
| No retry/fallback | Single failure = event lost forever |
| Thread pool contention | Terminal usage causes timeouts |

### Files to Remove

**Services (delete entirely):**
```
src/audit-logger/audit_logger.py     # Audit logger service
docker/audit-logger/Dockerfile        # Audit logger Docker build
src/backend/services/audit_service.py # Backend audit client
```

**Backend files with log_audit_event calls (173+ calls across 23 files):**
```
src/backend/routers/agents.py         # 11 calls
src/backend/routers/credentials.py    # 19 calls
src/backend/routers/settings.py       # 24 calls
src/backend/routers/auth.py           # 12 calls
src/backend/routers/mcp_keys.py       # 11 calls
src/backend/routers/ops.py            # 9 calls
src/backend/routers/chat.py           # 8 calls
src/backend/routers/system_agent.py   # 8 calls
src/backend/routers/schedules.py      # 7 calls
src/backend/routers/public_links.py   # 7 calls
src/backend/routers/public.py         # 7 calls
src/backend/routers/systems.py        # 6 calls
src/backend/routers/sharing.py        # 5 calls
src/backend/routers/git.py            # 5 calls
src/backend/routers/setup.py          # 3 calls
src/backend/services/agent_service/files.py        # 11 calls
src/backend/services/agent_service/permissions.py  # 4 calls
src/backend/services/agent_service/crud.py         # 3 calls
src/backend/services/agent_service/queue.py        # 3 calls
src/backend/services/agent_service/terminal.py     # 3 calls
src/backend/services/agent_service/deploy.py       # 3 calls
src/backend/services/agent_service/folders.py      # 2 calls
src/backend/services/agent_service/api_key.py      # 2 calls
src/backend/dependencies.py           # 3 calls
src/backend/services/__init__.py      # 2 calls (import)
src/backend/main.py                   # /api/audit/logs endpoint
src/backend/config.py                 # AUDIT_URL config
```

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Trinity Platform                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │ Backend  │  │ Frontend │  │   MCP    │  │  Redis   │                │
│  │          │  │          │  │  Server  │  │          │                │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                │
│       │             │             │             │                        │
│       └─────────────┴─────────────┴─────────────┘                        │
│                           │                                              │
│                    stdout/stderr                                         │
│                           │                                              │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Docker Engine                                │   │
│  │  (Captures ALL container output automatically)                    │   │
│  └──────────────────────────────────┬───────────────────────────────┘   │
│                                     │                                    │
│                              Docker Socket                               │
│                                     │                                    │
│                                     ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        Vector                                     │   │
│  │  - Connects to /var/run/docker.sock                              │   │
│  │  - Streams logs from ALL containers                              │   │
│  │  - Enriches with metadata (container_name, labels)               │   │
│  │  - Writes to JSON files with rotation                            │   │
│  └──────────────────────────────────┬───────────────────────────────┘   │
│                                     │                                    │
│                                     ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  /data/logs/                                                      │   │
│  │  ├── platform.json    # backend, frontend, mcp-server, redis     │   │
│  │  ├── agents.json      # all agent-* containers                   │   │
│  │  └── (auto-rotated, compressed)                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Add Vector (30 minutes)

#### 1.1 Create Vector Configuration

**File**: `config/vector.yaml`

```yaml
# Vector Configuration for Trinity
# Collects logs from all Docker containers and writes to JSON files
# Version: Vector 0.43.1 (latest stable as of Dec 2025)

api:
  enabled: true
  address: 0.0.0.0:8686

# Sources - collect from Docker
sources:
  docker_logs:
    type: docker_logs
    # Automatically discovers all containers
    # Uses Docker socket to stream logs in real-time

# Transforms - enrich and route logs
transforms:
  enrich:
    type: remap
    inputs:
      - docker_logs
    source: |
      # Add useful metadata
      .service = .container_name
      .is_agent = starts_with(string!(.container_name), "agent-")
      .is_platform = !.is_agent && starts_with(string!(.container_name), "trinity-")

      # Parse JSON logs if present (Python/Node often log JSON)
      if is_string(.message) {
        parsed, err = parse_json(.message)
        if err == null {
          .parsed = parsed
        }
      }

      # Extract log level if present
      if exists(.parsed.level) {
        .level = .parsed.level
      } else if exists(.parsed.levelname) {
        .level = .parsed.levelname
      } else if match(string!(.message), r'(?i)\b(error|err)\b') {
        .level = "error"
      } else if match(string!(.message), r'(?i)\b(warn|warning)\b') {
        .level = "warning"
      } else {
        .level = "info"
      }

  # Route platform services
  route_platform:
    type: filter
    inputs:
      - enrich
    condition:
      type: vrl
      source: '.is_platform == true'

  # Route agent containers
  route_agents:
    type: filter
    inputs:
      - enrich
    condition:
      type: vrl
      source: '.is_agent == true'

# Sinks - write to files
sinks:
  # Platform services log file
  platform_logs:
    type: file
    inputs:
      - route_platform
    path: /data/logs/platform.json
    encoding:
      codec: json
    compression: none
    # Rotation: 50MB per file, keep 10 files (500MB total)
    # Files rotate to platform.json.1, platform.json.2, etc.

  # Agent containers log file
  agent_logs:
    type: file
    inputs:
      - route_agents
    path: /data/logs/agents.json
    encoding:
      codec: json
    compression: none

  # Console output for debugging (optional, remove in production)
  # console:
  #   type: console
  #   inputs:
  #     - enrich
  #   encoding:
  #     codec: json
```

#### 1.2 Update docker-compose.yml

Add Vector service:

```yaml
  vector:
    image: timberio/vector:0.43.1-alpine
    container_name: trinity-vector
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/vector.yaml:/etc/vector/vector.yaml:ro
      - trinity-logs:/data/logs
    ports:
      - "8686:8686"  # Vector API (optional, for health checks)
    networks:
      - trinity-network
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:8686/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Add volume:

```yaml
volumes:
  # ... existing volumes ...
  trinity-logs:  # Vector log storage
```

#### 1.3 Update docker-compose.prod.yml

Same changes as above, but:
- Consider adding log rotation settings
- Ensure volume is on persistent storage

---

### Phase 2: Remove Audit Logger Service (15 minutes)

#### 2.1 Delete Files

```bash
# Delete audit logger service
rm -rf src/audit-logger/
rm -rf docker/audit-logger/

# Delete audit service client
rm src/backend/services/audit_service.py
```

#### 2.2 Update docker-compose.yml

Remove:
```yaml
  audit-logger:
    build:
      context: .
      dockerfile: docker/audit-logger/Dockerfile
    container_name: trinity-audit-logger
    # ... entire service block
```

Remove from backend `depends_on`:
```yaml
    depends_on:
      - redis
      # - audit-logger  # REMOVE THIS LINE
```

Remove volumes:
```yaml
volumes:
  # audit-data:   # REMOVE
  # audit-logs:   # REMOVE
```

Remove from backend volumes:
```yaml
    volumes:
      # - audit-logs:/logs  # REMOVE THIS LINE
```

#### 2.3 Update docker-compose.prod.yml

Same removals as above.

---

### Phase 3: Remove Backend Audit Code (2-3 hours)

#### 3.1 Remove Config

**File**: `src/backend/config.py`

Remove line:
```python
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit-logger:8001")
```

#### 3.2 Remove Audit Endpoint

**File**: `src/backend/main.py`

Remove the entire `/api/audit/logs` endpoint (lines ~323-354):
```python
# DELETE THIS ENTIRE BLOCK
@app.get("/api/audit/logs")
async def get_audit_logs(...):
    ...
```

Also remove any AUDIT_URL import.

#### 3.3 Remove All log_audit_event Calls

For each file listed above, remove:
1. The import: `from services.audit_service import log_audit_event`
2. All `await log_audit_event(...)` calls

**Strategy**: Since these are fire-and-forget calls that don't affect control flow, they can be safely deleted without changing any logic.

**Example transformation**:

Before:
```python
from services.audit_service import log_audit_event

async def create_agent(...):
    # ... create agent logic ...

    await log_audit_event(
        event_type="agent_management",
        action="create",
        agent_name=name,
        user_id=current_user.id,
        result="success"
    )

    return agent
```

After:
```python
async def create_agent(...):
    # ... create agent logic ...

    return agent
```

#### 3.4 Remove services/__init__.py Export

**File**: `src/backend/services/__init__.py`

Remove audit_service from exports.

---

### Phase 4: Add Structured Logging (Optional Enhancement)

Since Vector captures stdout/stderr, improve what gets logged:

#### 4.1 Create Logging Configuration

**File**: `src/backend/logging_config.py`

```python
"""
Structured logging configuration for Trinity.
Logs go to stdout and are captured by Vector.
"""
import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing by Vector."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "event_type"):
            log_entry["event_type"] = record.event_type
        if hasattr(record, "agent_name"):
            log_entry["agent_name"] = record.agent_name
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "action"):
            log_entry["action"] = record.action

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

def setup_logging():
    """Configure structured JSON logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Specific loggers
    logging.getLogger("trinity").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
```

#### 4.2 Use Structured Logging

Instead of `log_audit_event`, use standard logging:

```python
import logging

logger = logging.getLogger("trinity.agents")

async def create_agent(...):
    # ... create agent logic ...

    logger.info(
        "Agent created",
        extra={
            "event_type": "agent_management",
            "action": "create",
            "agent_name": name,
            "user_id": current_user.id
        }
    )

    return agent
```

---

### Phase 5: Update Documentation (30 minutes)

#### 5.1 Update Files

- `docs/DEPLOYMENT.md` - Remove audit-logger references, add Vector
- `docs/memory/architecture.md` - Update architecture diagram
- `docs/memory/requirements.md` - Update audit logging requirement
- `docs/memory/feature-flows/*.md` - Remove audit_service references
- `CLAUDE.md` - Update service list

#### 5.2 Add Log Query Guide

**File**: `docs/QUERYING_LOGS.md`

```markdown
# Querying Trinity Logs

Trinity uses Vector to aggregate all container logs into JSON files.

## Log Locations

| File | Contents |
|------|----------|
| `/data/logs/platform.json` | Backend, frontend, MCP server, Redis |
| `/data/logs/agents.json` | All agent containers |

## Query Examples

### Find Errors
```bash
# All errors in last hour
jq 'select(.level == "error")' /data/logs/platform.json | tail -100

# Errors for specific agent
grep '"container_name":"agent-ruby"' /data/logs/agents.json | jq 'select(.level == "error")'
```

### Agent Activity
```bash
# What did agent-ruby do?
grep 'agent-ruby' /data/logs/agents.json | jq -r '.message' | tail -50

# All agent starts/stops
grep -E 'started|stopped' /data/logs/platform.json
```

### Authentication Events
```bash
# Login attempts
grep -i 'login\|auth' /data/logs/platform.json | jq .
```

### Performance Issues
```bash
# Slow requests (if logged)
jq 'select(.duration_ms > 1000)' /data/logs/platform.json
```

## Live Tail
```bash
# Follow platform logs
tail -f /data/logs/platform.json | jq .

# Follow agent logs
tail -f /data/logs/agents.json | jq .
```

## Vector Health
```bash
# Check Vector status
curl http://localhost:8686/health
```
```

---

## Testing Plan

### Pre-Migration Verification
- [ ] Backup current audit database (if needed for historical data)
- [ ] Document current audit log count for comparison

### Post-Migration Verification
- [ ] Vector container running: `docker ps | grep vector`
- [ ] Log files created: `ls -la /data/logs/`
- [ ] Platform logs capturing: `tail /data/logs/platform.json`
- [ ] Agent logs capturing: Start an agent, verify logs appear
- [ ] Log rotation working: Check file sizes don't grow unbounded
- [ ] No audit-logger references: `grep -r "audit" src/backend/`
- [ ] Backend starts without audit-logger dependency
- [ ] All existing functionality works (agents, chat, etc.)

### Query Testing
- [ ] Can find errors: `jq 'select(.level == "error")' /data/logs/platform.json`
- [ ] Can filter by container: `grep 'trinity-backend' /data/logs/platform.json`
- [ ] Can follow logs: `tail -f /data/logs/agents.json | jq .`

---

## Rollback Plan

If issues occur:

1. **Revert docker-compose changes**
   ```bash
   git checkout docker-compose.yml docker-compose.prod.yml
   ```

2. **Restore audit-logger**
   ```bash
   git checkout src/audit-logger/ docker/audit-logger/
   ```

3. **Restore backend audit code** (if already removed)
   ```bash
   git checkout src/backend/services/audit_service.py
   # Revert individual file changes
   ```

4. **Restart services**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

## Timeline

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Add Vector configuration and service | 30 min |
| 2 | Remove audit-logger service | 15 min |
| 3 | Remove backend audit code (173+ calls) | 2-3 hours |
| 4 | Add structured logging (optional) | 1 hour |
| 5 | Update documentation | 30 min |
| - | Testing | 30 min |
| **Total** | | **4-5 hours** |

---

## References

- [Vector Documentation](https://vector.dev/docs/)
- [Vector Docker Logs Source](https://vector.dev/docs/reference/configuration/sources/docker_logs/)
- [Vector File Sink](https://vector.dev/docs/reference/configuration/sinks/file/)
- [Docker Logging Best Practices](https://docs.docker.com/engine/logging/)
- [Vector GitHub Releases](https://github.com/vectordotdev/vector/releases)

---

## Approval

- [ ] Plan reviewed
- [ ] Ready for implementation
