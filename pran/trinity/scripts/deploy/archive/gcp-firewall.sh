#!/bin/bash
# GCP Firewall Setup for Trinity Agent Platform
#
# Creates firewall rules for Trinity services
# Requires deploy.config to be set up

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${PROJECT_ROOT}/deploy.config"

# Check for config file
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Error: deploy.config not found!"
    echo "Run: cp deploy.config.example deploy.config"
    exit 1
fi

source "${CONFIG_FILE}"

# Validate
if [ -z "${GCP_PROJECT}" ] || [ "${GCP_PROJECT}" = "your-gcp-project-id" ]; then
    echo "Error: GCP_PROJECT not configured"
    exit 1
fi

echo "====================================="
echo "Trinity Platform - GCP Firewall Setup"
echo "====================================="
echo ""
echo "Project: ${GCP_PROJECT}"
echo ""

# Check gcloud auth
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -n1 > /dev/null; then
    echo "Error: Not authenticated. Run 'gcloud auth login' first."
    exit 1
fi

# Set project
gcloud config set project "${GCP_PROJECT}" 2>/dev/null

# Get network tag from instance (or use instance name)
NETWORK_TAG="${GCP_INSTANCE}"

echo "Creating firewall rules..."
echo ""

# Platform services firewall rule
PLATFORM_PORTS="${FRONTEND_PORT:-80},${BACKEND_PORT:-8000},${MCP_PORT:-8080}"
echo "1. Creating trinity-platform rule (ports ${PLATFORM_PORTS})..."

if gcloud compute firewall-rules describe trinity-platform --project="${GCP_PROJECT}" &>/dev/null; then
    echo "   Rule exists. Updating..."
    gcloud compute firewall-rules update trinity-platform \
        --allow=tcp:${FRONTEND_PORT:-80},tcp:${BACKEND_PORT:-8000},tcp:${MCP_PORT:-8080} \
        --project="${GCP_PROJECT}"
else
    gcloud compute firewall-rules create trinity-platform \
        --allow=tcp:${FRONTEND_PORT:-80},tcp:${BACKEND_PORT:-8000},tcp:${MCP_PORT:-8080} \
        --target-tags="${NETWORK_TAG}" \
        --description="Trinity Agent Platform - Core services" \
        --project="${GCP_PROJECT}"
fi
echo "   Done."
echo ""

# Agent SSH ports firewall rule
SSH_START="${AGENT_SSH_PORT_START:-2222}"
SSH_END=$((SSH_START + 19))
echo "2. Creating trinity-agents rule (SSH ports ${SSH_START}-${SSH_END})..."

if gcloud compute firewall-rules describe trinity-agents --project="${GCP_PROJECT}" &>/dev/null; then
    echo "   Rule exists. Updating..."
    gcloud compute firewall-rules update trinity-agents \
        --allow=tcp:${SSH_START}-${SSH_END} \
        --project="${GCP_PROJECT}"
else
    gcloud compute firewall-rules create trinity-agents \
        --allow=tcp:${SSH_START}-${SSH_END} \
        --target-tags="${NETWORK_TAG}" \
        --description="Trinity Agent Platform - Agent SSH ports" \
        --project="${GCP_PROJECT}"
fi
echo "   Done."
echo ""

echo "====================================="
echo "Firewall Setup Complete"
echo "====================================="
echo ""
echo "Rules created:"
echo "  - trinity-platform: tcp:${PLATFORM_PORTS}"
echo "  - trinity-agents:   tcp:${SSH_START}-${SSH_END}"
echo ""
echo "To verify:"
echo "  gcloud compute firewall-rules list --project=${GCP_PROJECT} --filter='name~trinity'"
