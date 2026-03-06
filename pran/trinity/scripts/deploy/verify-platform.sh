#!/bin/bash

# Trinity Platform - Verification Script
# Checks that all core services are running and healthy

set -e

echo "====================================="
echo "Trinity Platform - Health Check"
echo "====================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "1. Checking Docker..."
if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check core services
echo "2. Checking core services..."

services=("trinity-backend" "trinity-redis" "trinity-frontend" "trinity-audit-logger")
all_running=true

for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --format "{{.Names}}" | grep -q "$service"; then
        status=$(docker ps --filter "name=$service" --format "{{.Status}}")
        echo -e "${GREEN}✓ $service${NC} - $status"
    else
        echo -e "${RED}✗ $service is not running${NC}"
        all_running=false
    fi
done
echo ""

# Check health endpoints
echo "3. Checking health endpoints..."

# Backend health
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend health endpoint${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    all_running=false
fi

# Audit logger health
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Audit logger health endpoint${NC}"
else
    echo -e "${RED}✗ Audit logger health check failed${NC}"
    all_running=false
fi

# Frontend
if curl -s http://localhost:3000 | grep -q "Claude Agent Manager"; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${RED}✗ Frontend is not accessible${NC}"
    all_running=false
fi
echo ""

# Check base image
echo "4. Checking base agent image..."
if docker images | grep -q "trinity-agent-base"; then
    echo -e "${GREEN}✓ trinity-agent-base:latest exists${NC}"
else
    echo -e "${YELLOW}⚠ trinity-agent-base image not found${NC}"
    echo "  Run: ./scripts/deploy/build-base-image.sh"
fi
echo ""

# Check .env file
echo "5. Checking configuration..."
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
else
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "  Run: cp .env.example .env"
fi
echo ""

# Summary
echo "====================================="
if [ "$all_running" = true ]; then
    echo -e "${GREEN}✓ Platform is healthy!${NC}"
    echo ""
    echo "Access points:"
    echo "  - Web UI:       http://localhost:3000"
    echo "  - Backend API:  http://localhost:8000/docs"
    echo "  - Audit Logger: http://localhost:8001/docs"
    echo ""
    echo "Default login: admin / admin"
else
    echo -e "${RED}✗ Some services are not running${NC}"
    echo ""
    echo "Try:"
    echo "  docker-compose up -d"
    exit 1
fi
echo "====================================="
