#!/bin/bash
# Trinity Instance Health Check
# Comprehensive health check for a Trinity instance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Auto-detect host (try LAN first if defined)
if [ -n "$SSH_HOST_LAN" ] && ping -c 1 -W 1 $SSH_HOST_LAN &>/dev/null 2>&1; then
    HOST=$SSH_HOST_LAN
else
    HOST=$SSH_HOST
fi

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           Trinity Health Check${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo "Host: $HOST"
echo ""

ISSUES=0
WARNINGS=0

# Helper function
ssh_cmd() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 $SSH_USER@$HOST "$@" 2>/dev/null
}

ssh_sudo() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 $SSH_USER@$HOST "echo '$SSH_PASSWORD' | sudo -S $* 2>/dev/null"
}

check_result() {
    local name="$1"
    local status="$2"
    local detail="$3"

    if [ "$status" = "ok" ]; then
        echo -e "  ${GREEN}✓${NC} $name: $detail"
    elif [ "$status" = "warn" ]; then
        echo -e "  ${YELLOW}⚠${NC} $name: $detail"
        ((WARNINGS++))
    else
        echo -e "  ${RED}✗${NC} $name: $detail"
        ((ISSUES++))
    fi
}

# ==================== Service Health ====================
echo -e "${YELLOW}[1/5] Service Health${NC}"

# Backend
BACKEND=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$BACKEND_PORT/health")
if [ "$BACKEND" = "200" ]; then
    check_result "Backend" "ok" "healthy"
else
    check_result "Backend" "fail" "HTTP $BACKEND"
fi

# Frontend
FRONTEND=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$FRONTEND_PORT")
if [ "$FRONTEND" = "200" ]; then
    check_result "Frontend" "ok" "accessible"
else
    check_result "Frontend" "fail" "HTTP $FRONTEND"
fi

# Redis
REDIS=$(ssh_sudo "docker exec trinity-redis redis-cli ping 2>/dev/null" | tr -d '\r')
if [ "$REDIS" = "PONG" ]; then
    check_result "Redis" "ok" "responding"
else
    check_result "Redis" "fail" "not responding"
fi

# MCP Server
MCP=$(ssh_cmd "curl -s -o /dev/null -w '%{http_code}' http://localhost:$MCP_PORT/health")
if [ "$MCP" = "200" ]; then
    check_result "MCP Server" "ok" "healthy"
elif [ "$MCP" = "000" ]; then
    check_result "MCP Server" "warn" "not responding (may be disabled)"
else
    check_result "MCP Server" "warn" "HTTP $MCP"
fi

# Vector
VECTOR=$(ssh_sudo "docker exec trinity-vector wget -q -O - http://localhost:8686/health 2>/dev/null" | head -c 20)
if [ -n "$VECTOR" ]; then
    check_result "Vector" "ok" "capturing logs"
else
    check_result "Vector" "warn" "not responding"
fi

# ==================== Container Status ====================
echo ""
echo -e "${YELLOW}[2/5] Container Status${NC}"

# Platform containers
PLATFORM_CONTAINERS=$(ssh_sudo "docker ps --format '{{.Names}}:{{.Status}}' | grep trinity-")
for line in $PLATFORM_CONTAINERS; do
    NAME=$(echo $line | cut -d: -f1)
    STATUS=$(echo $line | cut -d: -f2-)
    if echo "$STATUS" | grep -q "Up"; then
        check_result "$NAME" "ok" "$STATUS"
    elif echo "$STATUS" | grep -q "Restarting"; then
        check_result "$NAME" "fail" "restarting"
    else
        check_result "$NAME" "fail" "$STATUS"
    fi
done

# Agent containers
AGENT_COUNT=$(ssh_sudo "docker ps --format '{{.Names}}' | grep -c agent- || echo 0")
AGENT_RUNNING=$(ssh_sudo "docker ps --format '{{.Names}}:{{.Status}}' | grep agent- | grep -c 'Up' || echo 0")
if [ "$AGENT_COUNT" -eq "0" ]; then
    check_result "Agents" "ok" "none deployed"
elif [ "$AGENT_RUNNING" -eq "$AGENT_COUNT" ]; then
    check_result "Agents" "ok" "$AGENT_RUNNING/$AGENT_COUNT running"
else
    check_result "Agents" "warn" "$AGENT_RUNNING/$AGENT_COUNT running"
fi

# ==================== Resource Usage ====================
echo ""
echo -e "${YELLOW}[3/5] Resource Usage${NC}"

# Disk space
DISK_USAGE=$(ssh_cmd "df -h / | tail -1 | awk '{print \$5}'" | tr -d '%')
if [ -n "$DISK_USAGE" ]; then
    if [ "$DISK_USAGE" -gt 95 ]; then
        check_result "Disk" "fail" "${DISK_USAGE}% used (critical)"
    elif [ "$DISK_USAGE" -gt 80 ]; then
        check_result "Disk" "warn" "${DISK_USAGE}% used"
    else
        check_result "Disk" "ok" "${DISK_USAGE}% used"
    fi
fi

# Docker disk
DOCKER_DISK=$(ssh_sudo "docker system df --format '{{.Size}}' | head -1")
check_result "Docker images" "ok" "$DOCKER_DISK"

# Log file sizes
LOG_SIZE=$(ssh_sudo "docker exec trinity-vector du -sh /data/logs/ 2>/dev/null | cut -f1")
if [ -n "$LOG_SIZE" ]; then
    check_result "Log files" "ok" "$LOG_SIZE"
fi

# ==================== Error Analysis ====================
echo ""
echo -e "${YELLOW}[4/5] Error Analysis (last 1000 lines)${NC}"

# Platform errors
PLATFORM_ERRORS=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -1000 /data/logs/platform.json 2>/dev/null | grep -c '\"level\":\"error\"' || echo 0\"" | tr -d '\r')
if [ "$PLATFORM_ERRORS" -gt 50 ]; then
    check_result "Platform errors" "fail" "$PLATFORM_ERRORS errors"
elif [ "$PLATFORM_ERRORS" -gt 10 ]; then
    check_result "Platform errors" "warn" "$PLATFORM_ERRORS errors"
else
    check_result "Platform errors" "ok" "$PLATFORM_ERRORS errors"
fi

# Agent errors
AGENT_ERRORS=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -1000 /data/logs/agents.json 2>/dev/null | grep -c '\"level\":\"error\"' || echo 0\"" | tr -d '\r')
if [ "$AGENT_ERRORS" -gt 50 ]; then
    check_result "Agent errors" "fail" "$AGENT_ERRORS errors"
elif [ "$AGENT_ERRORS" -gt 10 ]; then
    check_result "Agent errors" "warn" "$AGENT_ERRORS errors"
else
    check_result "Agent errors" "ok" "$AGENT_ERRORS errors"
fi

# ==================== Fleet Health ====================
echo ""
echo -e "${YELLOW}[5/5] Fleet Health (via API)${NC}"

# Get token and fleet health
TOKEN=$(ssh_cmd "curl -s -X POST http://localhost:$BACKEND_PORT/token -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=admin&password=$ADMIN_PASSWORD'" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    FLEET_HEALTH=$(ssh_cmd "curl -s -H 'Authorization: Bearer $TOKEN' http://localhost:$BACKEND_PORT/api/ops/fleet/health")

    HEALTHY=$(echo "$FLEET_HEALTH" | grep -o '"healthy_count":[0-9]*' | cut -d: -f2)
    WARNINGS_COUNT=$(echo "$FLEET_HEALTH" | grep -o '"warning_count":[0-9]*' | cut -d: -f2)
    CRITICAL=$(echo "$FLEET_HEALTH" | grep -o '"critical_count":[0-9]*' | cut -d: -f2)

    if [ -n "$HEALTHY" ]; then
        if [ "$CRITICAL" -gt 0 ]; then
            check_result "Fleet health" "fail" "$CRITICAL critical, $WARNINGS_COUNT warnings, $HEALTHY healthy"
        elif [ "$WARNINGS_COUNT" -gt 0 ]; then
            check_result "Fleet health" "warn" "$WARNINGS_COUNT warnings, $HEALTHY healthy"
        else
            check_result "Fleet health" "ok" "$HEALTHY healthy agents"
        fi
    else
        check_result "Fleet health" "warn" "Could not parse response"
    fi
else
    check_result "Fleet health" "warn" "Could not authenticate"
fi

# ==================== Summary ====================
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"

if [ $ISSUES -gt 0 ]; then
    echo -e "${RED}Health Check: $ISSUES issues, $WARNINGS warnings${NC}"
    echo -e "${RED}Action required!${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Health Check: $WARNINGS warnings${NC}"
    echo -e "${YELLOW}Review warnings above${NC}"
    exit 0
else
    echo -e "${GREEN}Health Check: All systems healthy${NC}"
    exit 0
fi
