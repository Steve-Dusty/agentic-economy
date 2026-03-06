#!/bin/bash
# Backup Trinity SQLite database from GCP
#
# Usage: ./scripts/deploy/backup-database.sh [backup_dir]
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

BACKUP_DIR="${1:-${PROJECT_ROOT}/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="trinity_db_backup_${TIMESTAMP}.db"

echo "====================================="
echo "Trinity Database Backup"
echo "====================================="
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}"

echo "Step 1: Creating backup on remote server..."
gcloud compute ssh "${GCP_INSTANCE}" \
    --zone="${GCP_ZONE}" \
    --project="${GCP_PROJECT}" \
    --command="cp ~/trinity-data/trinity.db /tmp/trinity_backup.db && chmod 644 /tmp/trinity_backup.db"

echo ""
echo "Step 2: Downloading backup..."
gcloud compute scp \
    --zone="${GCP_ZONE}" \
    --project="${GCP_PROJECT}" \
    "${GCP_INSTANCE}:/tmp/trinity_backup.db" "${BACKUP_DIR}/${BACKUP_FILE}"

echo ""
echo "Step 3: Cleaning up remote..."
gcloud compute ssh "${GCP_INSTANCE}" \
    --zone="${GCP_ZONE}" \
    --project="${GCP_PROJECT}" \
    --command="rm -f /tmp/trinity_backup.db"

echo ""
echo "Step 4: Verifying backup..."
if command -v sqlite3 &> /dev/null; then
    sqlite3 "${BACKUP_DIR}/${BACKUP_FILE}" "SELECT COUNT(*) as users FROM users; SELECT COUNT(*) as api_keys FROM mcp_api_keys;"
else
    echo "   (sqlite3 not installed, skipping verification)"
fi

echo ""
echo "====================================="
echo "Backup Complete!"
echo "====================================="
echo ""
echo "Backup saved to: ${BACKUP_DIR}/${BACKUP_FILE}"
echo "Size: $(ls -lh "${BACKUP_DIR}/${BACKUP_FILE}" | awk '{print $5}')"
echo ""
echo "To restore: ./scripts/deploy/restore-database.sh ${BACKUP_DIR}/${BACKUP_FILE}"
