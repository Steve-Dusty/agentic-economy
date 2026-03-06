#!/bin/bash
# Trinity Log Analysis
# Analyze logs from a Trinity instance

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Auto-detect host
if [ -n "$SSH_HOST_LAN" ] && ping -c 1 -W 1 $SSH_HOST_LAN &>/dev/null 2>&1; then
    HOST=$SSH_HOST_LAN
else
    HOST=$SSH_HOST
fi

# Parse arguments
MODE=${1:-summary}
LINES=${2:-1000}

ssh_sudo() {
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$HOST "echo '$SSH_PASSWORD' | sudo -S $* 2>/dev/null"
}

usage() {
    echo "Usage: $0 [mode] [lines]"
    echo ""
    echo "Modes:"
    echo "  summary     - Overview of log activity (default)"
    echo "  errors      - Show recent errors"
    echo "  warnings    - Show recent warnings"
    echo "  auth        - Authentication events"
    echo "  agents      - Agent-specific logs"
    echo "  timeline    - Timeline of events"
    echo "  containers  - Container restart/failure logs"
    echo ""
    echo "Lines: Number of log lines to analyze (default: 1000)"
    echo ""
    echo "Examples:"
    echo "  $0 summary"
    echo "  $0 errors 5000"
    echo "  $0 auth"
    exit 1
}

case "$MODE" in
    summary)
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}           Log Summary (last $LINES lines)${NC}"
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo ""

        echo -e "${YELLOW}Platform Logs:${NC}"
        TOTAL=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | wc -l\"")
        ERRORS=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | grep -c '\"level\":\"error\"' || echo 0\"")
        WARNINGS=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | grep -c '\"level\":\"warning\"' || echo 0\"")
        echo "  Total:    $TOTAL"
        echo -e "  Errors:   ${RED}$ERRORS${NC}"
        echo -e "  Warnings: ${YELLOW}$WARNINGS${NC}"

        echo ""
        echo -e "${YELLOW}Agent Logs:${NC}"
        AGENT_TOTAL=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/agents.json | wc -l\"")
        AGENT_ERRORS=$(ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/agents.json | grep -c '\"level\":\"error\"' || echo 0\"")
        echo "  Total:  $AGENT_TOTAL"
        echo -e "  Errors: ${RED}$AGENT_ERRORS${NC}"

        echo ""
        echo -e "${YELLOW}Top Services by Log Volume:${NC}"
        ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | grep -o '\"service\":\"[^\"]*\"' | sort | uniq -c | sort -rn | head -5\""

        echo ""
        echo -e "${YELLOW}Log File Sizes:${NC}"
        ssh_sudo "docker exec trinity-vector ls -lh /data/logs/"
        ;;

    errors)
        echo -e "${RED}══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}           Recent Errors (last $LINES lines)${NC}"
        echo -e "${RED}══════════════════════════════════════════════════════════${NC}"
        echo ""

        echo -e "${YELLOW}Platform Errors:${NC}"
        ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | grep '\"level\":\"error\"' | tail -20\"" | while read line; do
            TS=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -c 19)
            SVC=$(echo "$line" | grep -o '"service":"[^"]*"' | cut -d'"' -f4)
            MSG=$(echo "$line" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 80)
            echo -e "${CYAN}$TS${NC} [$SVC] $MSG"
        done

        echo ""
        echo -e "${YELLOW}Agent Errors:${NC}"
        ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/agents.json | grep '\"level\":\"error\"' | tail -10\"" | while read line; do
            TS=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -c 19)
            SVC=$(echo "$line" | grep -o '"service":"[^"]*"' | cut -d'"' -f4)
            MSG=$(echo "$line" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 80)
            echo -e "${CYAN}$TS${NC} [$SVC] $MSG"
        done
        ;;

    warnings)
        echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}           Recent Warnings (last $LINES lines)${NC}"
        echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
        echo ""

        ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | grep '\"level\":\"warning\"' | tail -30\"" | while read line; do
            TS=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -c 19)
            SVC=$(echo "$line" | grep -o '"service":"[^"]*"' | cut -d'"' -f4)
            MSG=$(echo "$line" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 80)
            echo -e "${CYAN}$TS${NC} [$SVC] $MSG"
        done
        ;;

    auth)
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}           Authentication Events${NC}"
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo ""

        echo -e "${YELLOW}Login Attempts:${NC}"
        ssh_sudo "docker exec trinity-vector sh -c \"grep -iE 'login|auth|token|unauthorized|forbidden' /data/logs/platform.json | tail -30\"" | while read line; do
            TS=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -c 19)
            LVL=$(echo "$line" | grep -o '"level":"[^"]*"' | cut -d'"' -f4)
            MSG=$(echo "$line" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 60)

            if [ "$LVL" = "error" ]; then
                echo -e "${CYAN}$TS${NC} ${RED}[$LVL]${NC} $MSG"
            elif [ "$LVL" = "warning" ]; then
                echo -e "${CYAN}$TS${NC} ${YELLOW}[$LVL]${NC} $MSG"
            else
                echo -e "${CYAN}$TS${NC} ${GREEN}[$LVL]${NC} $MSG"
            fi
        done
        ;;

    agents)
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}           Agent Logs${NC}"
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo ""

        echo -e "${YELLOW}Active Agents:${NC}"
        ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/agents.json | grep -o '\"service\":\"[^\"]*\"' | sort | uniq -c | sort -rn\""

        echo ""
        echo -e "${YELLOW}Recent Agent Activity:${NC}"
        ssh_sudo "docker exec trinity-vector sh -c \"tail -50 /data/logs/agents.json\"" | while read line; do
            TS=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -c 19)
            SVC=$(echo "$line" | grep -o '"service":"[^"]*"' | cut -d'"' -f4)
            MSG=$(echo "$line" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 60)
            echo -e "${CYAN}$TS${NC} [$SVC] $MSG"
        done
        ;;

    timeline)
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}           Event Timeline (last 50 events)${NC}"
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo ""

        ssh_sudo "docker exec trinity-vector sh -c \"tail -$LINES /data/logs/platform.json | tail -50\"" | while read line; do
            TS=$(echo "$line" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -c 19)
            LVL=$(echo "$line" | grep -o '"level":"[^"]*"' | cut -d'"' -f4)
            SVC=$(echo "$line" | grep -o '"service":"[^"]*"' | cut -d'"' -f4)
            MSG=$(echo "$line" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 50)

            if [ "$LVL" = "error" ]; then
                echo -e "${CYAN}$TS${NC} ${RED}ERR${NC} [$SVC] $MSG"
            elif [ "$LVL" = "warning" ]; then
                echo -e "${CYAN}$TS${NC} ${YELLOW}WRN${NC} [$SVC] $MSG"
            else
                echo -e "${CYAN}$TS${NC} ${GREEN}INF${NC} [$SVC] $MSG"
            fi
        done
        ;;

    containers)
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}           Container Status${NC}"
        echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
        echo ""

        echo -e "${YELLOW}All Containers:${NC}"
        ssh_sudo "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}' | grep -E 'trinity|agent'"

        echo ""
        echo -e "${YELLOW}Exited/Restarting Containers:${NC}"
        PROBLEM=$(ssh_sudo "docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -E 'Exited|Restarting'")
        if [ -n "$PROBLEM" ]; then
            echo "$PROBLEM"
        else
            echo "  None - all containers healthy"
        fi
        ;;

    *)
        usage
        ;;
esac

echo ""
