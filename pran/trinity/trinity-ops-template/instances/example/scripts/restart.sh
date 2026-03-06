#!/bin/bash
# Restart Trinity services
# Usage: ./restart.sh [service]
# Examples:
#   ./restart.sh           # Restart all
#   ./restart.sh backend   # Restart backend only

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

SERVICE=${1:-all}

echo "Restarting Trinity on $SSH_HOST..."

if [ "$SERVICE" == "all" ]; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
      "cd ~/trinity && echo '$SSH_PASSWORD' | sudo -S docker compose restart"
else
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
      "echo '$SSH_PASSWORD' | sudo -S docker restart trinity-$SERVICE"
fi

echo ""
echo "Waiting for services to come up..."
sleep 5

# Health check
BACKEND_HEALTH=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST \
  "curl -s http://localhost:$BACKEND_PORT/health" 2>/dev/null)

echo "Backend health: $BACKEND_HEALTH"
