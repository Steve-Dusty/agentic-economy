# Playbook: Monitoring Trinity Instances

## Overview

This playbook documents how to monitor the health of Trinity instances, analyze logs, and respond to issues.

## Quick Health Check (Automated)

```bash
cd instances/{name}
./scripts/health-check.sh
```

Returns exit code 0 (healthy), 0 with warnings, or 1 (issues found).

## Quick Log Analysis (Automated)

```bash
cd instances/{name}

# Summary
./scripts/analyze-logs.sh summary

# Recent errors
./scripts/analyze-logs.sh errors

# Auth events
./scripts/analyze-logs.sh auth

# Agent activity
./scripts/analyze-logs.sh agents
```

---

## Manual Monitoring Procedures

### 1. Service Health Checks

```bash
source .env

# Backend (most important)
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$BACKEND_PORT/health"
# Expected: {"status":"healthy",...}

# Frontend
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s -o /dev/null -w '%{http_code}' http://localhost:$FRONTEND_PORT"
# Expected: 200

# Redis
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-redis redis-cli ping"
# Expected: PONG

# MCP Server
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$MCP_PORT/health"
# Expected: {"status":"ok"}

# Vector (log aggregation)
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector wget -q -O - http://localhost:8686/health"
```

### 2. Fleet Status (via API)

```bash
source .env

# Get token
TOKEN=$(sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s -X POST http://localhost:$BACKEND_PORT/token \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d 'username=admin&password=$ADMIN_PASSWORD'" | jq -r '.access_token')

# Fleet status (all agents with context usage)
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s -H 'Authorization: Bearer $TOKEN' http://localhost:$BACKEND_PORT/api/ops/fleet/status" | jq

# Fleet health (issues, warnings, healthy counts)
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s -H 'Authorization: Bearer $TOKEN' http://localhost:$BACKEND_PORT/api/ops/fleet/health" | jq
```

### 3. Container Status

```bash
source .env

# All Trinity containers
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'trinity|agent'"

# Problem containers (exited/restarting)
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -E 'Exited|Restarting'"

# Container resource usage
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}' | grep -E 'trinity|agent'"
```

### 4. Resource Usage

```bash
source .env

# Disk space
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST "df -h / /var"

# Docker disk usage
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker system df"

# Log file sizes
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector ls -lh /data/logs/"

# Database size
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker run --rm -v trinity_trinity-data:/data alpine ls -lh /data/trinity.db"
```

### 5. Log Analysis

```bash
source .env

# Platform error count
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector sh -c \"tail -10000 /data/logs/platform.json | grep -c '\"level\":\"error\"'\""

# Recent platform errors
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector sh -c \"tail -10000 /data/logs/platform.json\" | jq 'select(.level == \"error\")' | tail -50"

# Auth failures
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector sh -c \"grep -iE 'unauthorized|forbidden|auth.*fail' /data/logs/platform.json | tail -20\""

# Agent errors
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector sh -c \"tail -5000 /data/logs/agents.json\" | jq 'select(.level == \"error\")'"
```

---

## Health Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Backend health | - | Not 200 | Restart backend |
| Agent context | >75% | >90% | Reset context via UI or restart |
| Disk space | >80% | >95% | Cleanup logs, docker prune |
| Error rate | >10/hr | >50/hr | Investigate logs |
| Container restarts | Any | Multiple | Check docker logs |
| Database size | >1GB | >5GB | Archive/cleanup old data |
| Log file size | >5GB | >10GB | Trigger archival |

---

## Common Issues & Resolution

### Backend Not Responding

```bash
# Check logs
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker logs trinity-backend --tail 100"

# Restart
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker restart trinity-backend"

# Verify
sleep 5
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$BACKEND_PORT/health"
```

### Agent Stuck (High Context)

```bash
# Check context usage via API
# If >90%, restart the agent:
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker restart agent-{name}"
```

### Disk Space Critical

```bash
# Docker cleanup
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker system prune -f"

# Rotate logs
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-vector sh -c 'echo > /data/logs/platform.json; echo > /data/logs/agents.json'"
```

### Container Restarting

```bash
# Check why it's restarting
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker logs trinity-{service} --tail 200"

# Common causes:
# - OOM: Increase memory limit
# - Config error: Check .env or docker-compose
# - Network: Check Docker network exists
```

---

## Scheduled Monitoring

### Recommended Schedule

| Check | Frequency | Method |
|-------|-----------|--------|
| Service health | Every 5 min | Automated check |
| Container status | Every 5 min | Automated check |
| Disk space | Every hour | Automated check |
| Log analysis | Every hour | Automated summary |
| Full health check | Every 4 hours | `health-check.sh` |
| Cost review | Daily | OTel dashboard or API |

### Setting Up Automated Checks

You can set up a cron job on your local machine:

```bash
# crontab -e
# Run health check every 4 hours, alert on failure
0 */4 * * * cd /path/to/trinity-ops/instances/my-server && ./scripts/health-check.sh || echo "Trinity health check failed" | mail -s "Trinity Alert" admin@example.com
```

Or use the instance's own system agent for self-monitoring.

---

## MCP-Based Monitoring

If you have MCP access configured, you can monitor programmatically:

```bash
# In claude session with MCP configured
# Use trinity-{instance} MCP server tools:

# List agents
mcp__trinity-myserver__list_agents

# Get specific agent
mcp__trinity-myserver__get_agent name="agent-name"

# Get logs
mcp__trinity-myserver__get_agent_logs agent_name="agent-name" lines=50
```

---

## Alerting (Future)

Consider integrating with:
- **Slack webhook**: Send alerts to a channel
- **PagerDuty**: For on-call escalation
- **Email**: For daily summaries
- **Prometheus/Grafana**: If OTel is enabled

---

*Last updated: 2026-01-14*
