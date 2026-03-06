#!/bin/bash
# Trinity Instance Status Check

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

echo "=== Trinity Instance Status ==="
echo ""

echo "Host: $SSH_HOST"
echo ""

echo "--- Docker Containers ---"
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | grep -E 'trinity|agent'"

echo ""
echo "--- Health Checks ---"

# Backend
BACKEND_HEALTH=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
  "curl -s -o /dev/null -w '%{http_code}' http://localhost:$BACKEND_PORT/health" 2>/dev/null)
echo "Backend:  $BACKEND_HEALTH"

# Frontend
FRONTEND_HEALTH=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
  "curl -s -o /dev/null -w '%{http_code}' http://localhost:$FRONTEND_PORT" 2>/dev/null)
echo "Frontend: $FRONTEND_HEALTH"

# Redis
REDIS_HEALTH=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
  "echo '$SSH_PASSWORD' | sudo -S docker exec trinity-redis redis-cli ping 2>/dev/null")
echo "Redis:    $REDIS_HEALTH"

echo ""
echo "--- Git Version ---"
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
  "cd ~/trinity && git log -1 --oneline"
