# Querying Trinity Logs

Trinity uses Vector to aggregate all container logs into daily-rotated JSON files.

## Log Locations

| Pattern | Contents |
|---------|----------|
| `/data/logs/platform-YYYY-MM-DD.json` | Backend, frontend, MCP server, Redis, Vector |
| `/data/logs/agents-YYYY-MM-DD.json` | All agent containers |

Files rotate automatically at midnight UTC.

## Accessing Logs

Logs are stored in the `trinity-logs` Docker volume. To access them:

```bash
# Set today's date for convenience
TODAY=$(date +%Y-%m-%d)

# Find the volume location
docker volume inspect trinity-logs

# List all log files
docker exec trinity-vector ls -la /data/logs/

# Or exec into a container that has access (today's logs)
docker exec trinity-vector cat /data/logs/platform-$TODAY.json | tail -100

# Or mount the volume to a temporary container
docker run --rm -v trinity-logs:/logs alpine cat /logs/platform-$TODAY.json | tail -100
```

## Query Examples

### Find Errors

```bash
TODAY=$(date +%Y-%m-%d)

# All errors in last 100 lines (today)
docker exec trinity-vector sh -c "cat /data/logs/platform-$TODAY.json | tail -100" | jq 'select(.level == "error")'

# Errors for specific agent (today)
docker exec trinity-vector sh -c "grep 'agent-ruby' /data/logs/agents-$TODAY.json | tail -50" | jq 'select(.level == "error")'

# Errors across all platform log files
docker exec trinity-vector sh -c "cat /data/logs/platform-*.json" | jq 'select(.level == "error")' | tail -50
```

### Agent Activity

```bash
TODAY=$(date +%Y-%m-%d)

# What did agent-ruby log today?
docker exec trinity-vector sh -c "grep 'agent-ruby' /data/logs/agents-$TODAY.json | tail -50" | jq -r '.message'

# All agent container logs (today)
docker exec trinity-vector sh -c "cat /data/logs/agents-$TODAY.json | tail -100" | jq -r '.container_name + ": " + .message'
```

### Authentication Events

```bash
TODAY=$(date +%Y-%m-%d)

# Login attempts (today)
docker exec trinity-vector sh -c "grep -i 'login\|auth' /data/logs/platform-$TODAY.json | tail -50" | jq .

# Login attempts (all files)
docker exec trinity-vector sh -c "cat /data/logs/platform-*.json" | grep -i 'login\|auth' | tail -50 | jq .
```

### Backend Requests

```bash
TODAY=$(date +%Y-%m-%d)

# Recent backend logs (today)
docker exec trinity-vector sh -c "grep 'trinity-backend' /data/logs/platform-$TODAY.json | tail -50" | jq .
```

### Historical Logs

```bash
# Logs from a specific date
docker exec trinity-vector cat /data/logs/platform-2026-01-20.json | tail -100 | jq .

# Logs from the past week
docker exec trinity-vector sh -c "cat /data/logs/platform-2026-01-1*.json" | tail -500 | jq .
```

## Live Tail

```bash
TODAY=$(date +%Y-%m-%d)

# Follow platform logs (today's file)
docker exec trinity-vector sh -c "tail -f /data/logs/platform-$TODAY.json" | jq .

# Follow agent logs (today's file)
docker exec trinity-vector sh -c "tail -f /data/logs/agents-$TODAY.json" | jq .
```

## Log Structure

Each log entry contains:

```json
{
  "timestamp": "2026-01-23T12:00:00.000Z",
  "container_name": "trinity-backend",
  "container_id": "abc123...",
  "message": "The log message",
  "level": "info",
  "is_agent": false,
  "is_platform": true,
  "service": "trinity-backend"
}
```

For JSON-formatted log messages (from Python's structured logging), Vector parses them:

```json
{
  "timestamp": "2026-01-23T12:00:00.000Z",
  "container_name": "trinity-backend",
  "message": "{\"level\": \"INFO\", ...}",
  "parsed": {
    "level": "INFO",
    "logger": "trinity.agents",
    "message": "Agent created",
    "agent_name": "test-agent"
  }
}
```

## Vector Health

```bash
# Check Vector status
curl http://localhost:8686/health

# Vector API (if enabled)
curl http://localhost:8686/api/v1/topology
```

## Known Limitations

### Historical Logs Not Captured

Vector's `docker_logs` source only captures logs from **after** it starts watching a container. This means:

| Scenario | Impact |
|----------|--------|
| Container started before Vector | No logs until container restarts |
| Vector restart | Logs during downtime lost |
| Pre-existing agents | Startup logs not captured |

**Mitigation**: Backend depends on Vector being healthy before starting, so newly created agents will always have logs captured.

**For pre-existing containers**, restart them to begin capturing logs:

```bash
# Restart an agent to start capturing its logs
docker restart agent-my-agent

# Restart all agents
docker ps --filter "label=trinity.platform=agent" -q | xargs -r docker restart
```

See [GitHub issue #7358](https://github.com/vectordotdev/vector/issues/7358) for upstream tracking.

## Troubleshooting

### Logs Not Appearing

1. Check Vector is running:
   ```bash
   docker ps | grep vector
   ```

2. Check Vector logs:
   ```bash
   docker logs trinity-vector --tail 50
   ```

3. Verify Docker socket access:
   ```bash
   docker exec trinity-vector ls -la /var/run/docker.sock
   ```

### Large Log Files

Vector rotates logs daily via date-stamped filenames. Old logs are automatically archived by the backend after the retention period (default: 90 days).

Monitor log file sizes:

```bash
docker exec trinity-vector ls -lh /data/logs/
```

To check log statistics via API:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/stats
```

To manually clear today's logs (if needed):

```bash
TODAY=$(date +%Y-%m-%d)
docker exec trinity-vector sh -c "echo '' > /data/logs/platform-$TODAY.json"
docker exec trinity-vector sh -c "echo '' > /data/logs/agents-$TODAY.json"
```

## Log Archival

Old logs are automatically compressed and archived. Admin endpoints for management:

```bash
# Get log statistics
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/stats

# Get retention config
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/retention

# Manually trigger archival
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/logs/archive
```

See `docs/memory/feature-flows/vector-logging.md` for full archival documentation.
