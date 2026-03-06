#!/bin/bash
# Rollback Trinity Instance
# Usage: ./rollback.sh <backup-file> <git-commit>
# Example: ./rollback.sh trinity-20260108-143022.db f6bb57f

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

BACKUP_FILE=${1:-}
GIT_COMMIT=${2:-}

if [ -z "$BACKUP_FILE" ] || [ -z "$GIT_COMMIT" ]; then
    echo "Usage: $0 <backup-file> <git-commit>"
    echo ""
    echo "Available backups:"
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "ls -la ~/backups/*.db 2>/dev/null | tail -10" || echo "  No backups found"
    echo ""
    echo "Recent commits:"
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "cd ~/trinity && git log --oneline -10"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Auto-detect host
if [ -n "$SSH_HOST_LAN" ] && ping -c 1 -W 1 $SSH_HOST_LAN &>/dev/null 2>&1; then
    HOST=$SSH_HOST_LAN
else
    HOST=$SSH_HOST
fi

ssh_cmd() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$HOST "$@"
}

ssh_sudo() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$HOST "echo '$SSH_PASSWORD' | sudo -S $*"
}

echo ""
echo -e "${RED}══════════════════════════════════════════════════════════${NC}"
echo -e "${RED}           Trinity ROLLBACK${NC}"
echo -e "${RED}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Backup file: $BACKUP_FILE"
echo "  Git commit:  $GIT_COMMIT"
echo ""
read -p "Are you sure you want to rollback? (yes/no) " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Step 1: Verify backup exists
echo ""
echo -e "${YELLOW}[1/5] Verifying backup...${NC}"

if ssh_cmd "ls ~/backups/$BACKUP_FILE" &>/dev/null; then
    BACKUP_SIZE=$(ssh_cmd "ls -lh ~/backups/$BACKUP_FILE | awk '{print \$5}'")
    echo -e "  ${GREEN}Found: ~/backups/$BACKUP_FILE ($BACKUP_SIZE)${NC}"
else
    echo -e "  ${RED}Backup not found: ~/backups/$BACKUP_FILE${NC}"
    exit 1
fi

# Step 2: Stop services
echo ""
echo -e "${YELLOW}[2/5] Stopping services...${NC}"

ssh_sudo "docker stop trinity-backend trinity-frontend trinity-mcp-server 2>/dev/null" || true
echo "  Services stopped"

# Step 3: Restore database
echo ""
echo -e "${YELLOW}[3/5] Restoring database...${NC}"

# Backup current before restoring
CURRENT_BACKUP="trinity-pre-rollback-$(date +%Y%m%d-%H%M%S).db"
ssh_sudo "docker run --rm -v trinity_trinity-data:/data -v /home/$SSH_USER/backups:/backup alpine cp /data/trinity.db /backup/$CURRENT_BACKUP" 2>/dev/null
echo "  Current state saved: ~/backups/$CURRENT_BACKUP"

# Restore
ssh_sudo "docker run --rm -v trinity_trinity-data:/data -v /home/$SSH_USER/backups:/backup alpine cp /backup/$BACKUP_FILE /data/trinity.db" 2>/dev/null
echo -e "  ${GREEN}Database restored from $BACKUP_FILE${NC}"

# Step 4: Checkout git commit
echo ""
echo -e "${YELLOW}[4/5] Checking out git commit...${NC}"

ssh_cmd "cd ~/trinity && git checkout $GIT_COMMIT"
echo "  Checked out: $GIT_COMMIT"

# Rebuild
echo "  Rebuilding images..."
ssh_sudo "cd /home/$SSH_USER/trinity && docker compose build --no-cache backend frontend mcp-server 2>&1" | grep -E "(DONE|Built)" | tail -5

# Step 5: Restart services
echo ""
echo -e "${YELLOW}[5/5] Restarting services...${NC}"

ssh_sudo "docker start trinity-backend trinity-frontend trinity-mcp-server 2>/dev/null" || true
sleep 5

# Verify
BACKEND_HEALTH=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$BACKEND_PORT/health" 2>/dev/null)
if [ "$BACKEND_HEALTH" = "200" ]; then
    echo -e "  ${GREEN}Backend healthy${NC}"
else
    echo -e "  ${RED}Backend unhealthy - check logs${NC}"
fi

echo ""
echo -e "${GREEN}Rollback complete!${NC}"
echo ""
echo "  Version: $(ssh_cmd "cd ~/trinity && git log -1 --format='%h %s'")"
echo ""
echo "  To return to main branch:"
echo "    ssh to server and run: cd ~/trinity && git checkout main"
