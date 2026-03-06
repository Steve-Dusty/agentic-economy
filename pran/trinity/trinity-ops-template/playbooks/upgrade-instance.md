# Playbook: Upgrade Trinity Instance

## Overview

This playbook documents the complete procedure for updating a Trinity instance to the latest version, including backup, update, verification, and rollback procedures.

## Quick Update (Automated)

For routine updates, use the automated script:

```bash
cd instances/{name}
./scripts/update.sh
```

The script handles:
1. Pre-flight checks (version, local changes)
2. Database backup
3. Git pull with stash handling
4. Docker image rebuild
5. Service restart (preserves agents)
6. Health verification
7. Rollback instructions

---

## Manual Update Procedure

### Prerequisites

- [ ] SSH access to instance
- [ ] Credentials loaded (`source .env`)
- [ ] No critical scheduled tasks running
- [ ] Backup storage available (`~/backups/` on host)

### Step 1: Pre-flight Checks

```bash
source .env

# Check current version
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git log -1 --oneline"

# Check for local changes
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git status --porcelain"

# Check how far behind
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git fetch origin main && git rev-list HEAD..origin/main --count"
```

### Step 2: Backup Database

**CRITICAL: Always backup before updating**

```bash
source .env

BACKUP_NAME="trinity-$(date +%Y%m%d-%H%M%S).db"

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker run --rm \
    -v trinity_trinity-data:/data \
    -v ~/backups:/backup \
    alpine cp /data/trinity.db /backup/$BACKUP_NAME"

# Verify backup
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "ls -lh ~/backups/$BACKUP_NAME"
```

### Step 3: Pull Latest Code

```bash
source .env

# If no local changes:
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git pull origin main"

# If local changes exist:
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git stash && git pull origin main && git stash pop"
```

### Step 4: Rebuild Docker Images

Only rebuild platform services (backend, frontend, mcp-server), not the base agent image:

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && echo '$SSH_PASSWORD' | sudo -S \
    docker compose build --no-cache backend frontend mcp-server"
```

**Note:** Full rebuild takes 3-5 minutes. For faster updates when only code changed (no dependency changes), omit `--no-cache`.

### Step 5: Restart Services

**Important:** Use `restart`, not `down/up`, to preserve agent containers.

```bash
source .env

# Restart platform services only
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S \
    docker restart trinity-backend trinity-frontend trinity-mcp-server"

# Wait for startup
sleep 5
```

### Step 6: Verify Health

```bash
source .env

# Backend
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$BACKEND_PORT/health"

# Frontend
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s -o /dev/null -w '%{http_code}' http://localhost:$FRONTEND_PORT"

# Redis
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-redis redis-cli ping"

# MCP Server
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$MCP_PORT/health"
```

### Step 7: Verify Agents

```bash
source .env

# List agent containers
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker ps --format 'table {{.Names}}\t{{.Status}}' | grep agent-"

# Check agent connectivity via API (if tunnel is running)
TOKEN=$(curl -s -X POST http://localhost:$TUNNEL_BACKEND/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=admin&password=$ADMIN_PASSWORD" | jq -r '.access_token')

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:$TUNNEL_BACKEND/api/agents | jq '.[].name'
```

### Step 8: Post-Update Verification

- [ ] Web UI loads at `http://localhost:{tunnel_port}`
- [ ] Can login with admin credentials
- [ ] Agent list shows expected agents
- [ ] Can start/stop an agent
- [ ] System agent is running
- [ ] Scheduled tasks still configured

---

## Rollback Procedure

### Quick Rollback (Automated)

```bash
cd instances/{name}
./scripts/rollback.sh <backup-file> <git-commit>

# Example:
./scripts/rollback.sh trinity-20260108-143022.db f6bb57f
```

### Manual Rollback

#### Step 1: Stop Services

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker stop trinity-backend trinity-frontend trinity-mcp-server"
```

#### Step 2: Restore Database

```bash
source .env

# List available backups
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "ls -la ~/backups/*.db"

# Restore specific backup
BACKUP_FILE="trinity-YYYYMMDD-HHMMSS.db"

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker run --rm \
    -v trinity_trinity-data:/data \
    -v ~/backups:/backup \
    alpine cp /backup/$BACKUP_FILE /data/trinity.db"
```

#### Step 3: Checkout Previous Version

```bash
source .env

# List recent commits
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git log --oneline -10"

# Checkout specific commit
GIT_COMMIT="abc1234"

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git checkout $GIT_COMMIT"
```

#### Step 4: Rebuild and Restart

```bash
source .env

sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && echo '$SSH_PASSWORD' | sudo -S \
    docker compose build --no-cache backend frontend mcp-server && \
    echo '$SSH_PASSWORD' | sudo -S docker start trinity-backend trinity-frontend trinity-mcp-server"
```

#### Step 5: Return to Main Branch (After Fixing Issues)

```bash
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git checkout main"
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker logs trinity-backend --tail 100"

# Common issues:
# - Database migration needed: Check for alembic errors
# - Missing env vars: Check .env file
# - Port conflict: Check if port 8000 is in use
```

### Database Migration Errors

If the update includes schema changes:

```bash
# The backend auto-runs migrations on startup
# Check logs for migration errors
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker logs trinity-backend 2>&1 | grep -i migration"
```

### Agent Containers Orphaned

If `docker compose down` was run accidentally:

```bash
# Agents still exist but may reference old network
# Restart backend - it will recreate agents on start via labels
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker restart trinity-backend"
```

### Network Issues

```bash
# Recreate agent network
sshpass -p "$SSH_PASSWORD" ssh $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker network create trinity-agent-network 2>/dev/null || true"
```

---

## Best Practices

1. **Always backup before updating** - Database backups are cheap, downtime is expensive
2. **Use restart, not down/up** - Preserves agent containers and their networks
3. **Test on staging first** - If you have multiple instances
4. **Check changelog** - Review what changed before updating
5. **Schedule updates** - Avoid updating during scheduled agent tasks
6. **Keep backups** - Retain at least 7 days of database backups

---

## Automation

### Cron Job for Backups

Add to host crontab:

```bash
# Daily backup at 2 AM
0 2 * * * docker run --rm -v trinity_trinity-data:/data -v ~/backups:/backup alpine cp /data/trinity.db /backup/trinity-$(date +\%Y\%m\%d).db

# Cleanup backups older than 14 days
0 3 * * * find ~/backups -name "trinity-*.db" -mtime +14 -delete
```

### CI/CD Integration

For automated deployments, trigger update via SSH:

```bash
ssh user@host "cd ~/trinity && git pull && docker compose build --no-cache backend frontend mcp-server && docker restart trinity-backend trinity-frontend trinity-mcp-server"
```

---

*Last updated: 2026-01-14*
