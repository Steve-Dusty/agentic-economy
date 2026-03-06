#!/bin/bash
# Trinity SSH Tunnel
# Creates tunnels to access Trinity services locally

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

echo "Starting SSH tunnels to $SSH_HOST..."

# Kill existing tunnels
pkill -f "ssh.*$SSH_HOST.*-L" 2>/dev/null

# Create tunnels
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -N \
  -L $TUNNEL_FRONTEND:localhost:$FRONTEND_PORT \
  -L $TUNNEL_BACKEND:localhost:$BACKEND_PORT \
  -L $TUNNEL_MCP:localhost:$MCP_PORT \
  $SSH_USER@$SSH_HOST &

TUNNEL_PID=$!

echo ""
echo "Tunnels established (PID: $TUNNEL_PID):"
echo "  Frontend: http://localhost:$TUNNEL_FRONTEND"
echo "  Backend:  http://localhost:$TUNNEL_BACKEND"
echo "  MCP:      http://localhost:$TUNNEL_MCP"
echo ""
echo "Press Ctrl+C to stop tunnels"

# Wait for tunnel process
wait $TUNNEL_PID
