#!/bin/bash

set -e

cd "$(dirname "$0")/../.."

echo "====================================="
echo "Trinity Agent Platform - Stopping"
echo "====================================="
echo ""

docker compose down

echo ""
echo "✅ All services stopped"
echo ""

