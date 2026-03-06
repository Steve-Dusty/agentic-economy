#!/bin/bash
# Update Trinity Instance
# - Backs up database
# - Pulls latest code
# - Rebuilds images
# - Restarts services (preserves agents)
# - Verifies health

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Auto-detect host (LAN or primary)
if [ -n "$SSH_HOST_LAN" ] && ping -c 1 -W 1 $SSH_HOST_LAN &>/dev/null 2>&1; then
    HOST=$SSH_HOST_LAN
    echo -e "${BLUE}Using local network: $HOST${NC}"
else
    HOST=$SSH_HOST
    echo -e "${BLUE}Using primary host: $HOST${NC}"
fi

# SSH helper
ssh_cmd() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$HOST "$@"
}

ssh_sudo() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$HOST "echo '$SSH_PASSWORD' | sudo -S $*"
}

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           Trinity Update${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"

# Step 1: Pre-flight checks
echo ""
echo -e "${YELLOW}[1/7] Pre-flight checks...${NC}"

CURRENT_VERSION=$(ssh_cmd "cd ~/trinity && git log -1 --format='%h'")
echo "  Current version: $CURRENT_VERSION"

# Check for uncommitted changes
LOCAL_CHANGES=$(ssh_cmd "cd ~/trinity && git status --porcelain" | wc -l | tr -d ' ')
if [ "$LOCAL_CHANGES" -gt 0 ]; then
    echo -e "  ${YELLOW}Warning: $LOCAL_CHANGES uncommitted changes detected${NC}"
    echo "  Will stash before pull"
    NEEDS_STASH=true
else
    echo "  No local changes"
    NEEDS_STASH=false
fi

# Check if remote has updates
ssh_cmd "cd ~/trinity && git fetch origin main" 2>/dev/null
BEHIND=$(ssh_cmd "cd ~/trinity && git rev-list HEAD..origin/main --count")
if [ "$BEHIND" -eq 0 ]; then
    echo -e "  ${GREEN}Already up to date${NC}"
    read -p "  Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
else
    echo "  $BEHIND commits behind origin/main"
fi

# Step 2: Backup database
echo ""
echo -e "${YELLOW}[2/7] Backing up database...${NC}"

BACKUP_NAME="trinity-$(date +%Y%m%d-%H%M%S).db"
ssh_sudo "docker run --rm -v trinity_trinity-data:/data -v /home/$SSH_USER/backups:/backup alpine cp /data/trinity.db /backup/$BACKUP_NAME" 2>/dev/null

if ssh_cmd "ls ~/backups/$BACKUP_NAME" &>/dev/null; then
    BACKUP_SIZE=$(ssh_cmd "ls -lh ~/backups/$BACKUP_NAME | awk '{print \$5}'")
    echo -e "  ${GREEN}Backup created: ~/backups/$BACKUP_NAME ($BACKUP_SIZE)${NC}"
else
    echo -e "  ${RED}Backup failed!${NC}"
    read -p "  Continue without backup? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Step 3: Pull latest code
echo ""
echo -e "${YELLOW}[3/7] Pulling latest code...${NC}"

if [ "$NEEDS_STASH" = true ]; then
    echo "  Stashing local changes..."
    ssh_cmd "cd ~/trinity && git stash"
fi

PULL_OUTPUT=$(ssh_cmd "cd ~/trinity && git pull origin main 2>&1")
echo "$PULL_OUTPUT" | head -5

if [ "$NEEDS_STASH" = true ]; then
    echo "  Restoring stashed changes..."
    ssh_cmd "cd ~/trinity && git stash pop" 2>/dev/null || echo "  (no stash to pop or conflict)"
fi

NEW_VERSION=$(ssh_cmd "cd ~/trinity && git log -1 --format='%h'")
echo -e "  ${GREEN}Updated: $CURRENT_VERSION → $NEW_VERSION${NC}"

# Step 4: Rebuild images
echo ""
echo -e "${YELLOW}[4/7] Rebuilding Docker images...${NC}"
echo "  (This may take a few minutes)"

# Only rebuild platform services, not base image
BUILD_OUTPUT=$(ssh_sudo "cd /home/$SSH_USER/trinity && docker compose build --no-cache backend frontend mcp-server 2>&1")
BUILD_STATUS=$?

# Show summary
echo "$BUILD_OUTPUT" | grep -E "(DONE|Built|error|Error|SUCCESS)" | tail -10

if [ $BUILD_STATUS -ne 0 ]; then
    echo -e "  ${RED}Build failed! Check logs above.${NC}"
    exit 1
fi
echo -e "  ${GREEN}Build complete${NC}"

# Step 5: Restart services (graceful)
echo ""
echo -e "${YELLOW}[5/7] Restarting services...${NC}"

# Restart platform services only (preserves agent containers)
ssh_sudo "docker restart trinity-backend trinity-frontend trinity-mcp-server 2>/dev/null" || true

echo "  Waiting for services to start..."
sleep 5

# Step 6: Verify health
echo ""
echo -e "${YELLOW}[6/7] Verifying health...${NC}"

# Backend
BACKEND_HEALTH=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$BACKEND_PORT/health" 2>/dev/null)
if [ "$BACKEND_HEALTH" = "200" ]; then
    echo -e "  Backend:  ${GREEN}✓ healthy${NC}"
else
    echo -e "  Backend:  ${RED}✗ unhealthy ($BACKEND_HEALTH)${NC}"
    echo "  Checking logs..."
    ssh_sudo "docker logs trinity-backend --tail 20 2>&1" | tail -10
fi

# Frontend
FRONTEND_HEALTH=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$FRONTEND_PORT" 2>/dev/null)
if [ "$FRONTEND_HEALTH" = "200" ]; then
    echo -e "  Frontend: ${GREEN}✓ healthy${NC}"
else
    echo -e "  Frontend: ${RED}✗ unhealthy ($FRONTEND_HEALTH)${NC}"
fi

# MCP Server
MCP_HEALTH=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$MCP_PORT/health" 2>/dev/null)
if [ "$MCP_HEALTH" = "200" ]; then
    echo -e "  MCP:      ${GREEN}✓ healthy${NC}"
else
    echo -e "  MCP:      ${YELLOW}○ not responding ($MCP_HEALTH)${NC}"
fi

# Redis
REDIS_HEALTH=$(ssh_sudo "docker exec trinity-redis redis-cli ping 2>/dev/null")
if [ "$REDIS_HEALTH" = "PONG" ]; then
    echo -e "  Redis:    ${GREEN}✓ healthy${NC}"
else
    echo -e "  Redis:    ${RED}✗ unhealthy${NC}"
fi

# Step 7: Show agent status
echo ""
echo -e "${YELLOW}[7/7] Agent status...${NC}"

ssh_sudo "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | grep agent-" || echo "  No agents running"

# Summary
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Update complete!${NC}"
echo ""
echo "  Version: $(ssh_cmd "cd ~/trinity && git log -1 --format='%h %s'")"
echo "  Backup:  ~/backups/$BACKUP_NAME"
echo ""
echo "  Rollback command:"
echo "    ./rollback.sh $BACKUP_NAME $CURRENT_VERSION"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
