#!/bin/bash

# Cron Wrapper for PostgreSQL Backup
# This script is called by cron and sets up the environment before running the backup

# Source environment variables if .env exists
if [ -f /home/james/projects/school-financial-system/backend/.env ]; then
    set -a
    source /home/james/projects/school-financial-system/backend/.env
    set +a
fi

# Set backup defaults if not already set
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_USER="${DB_USER:-school}"
export DB_NAME="${DB_NAME:-school_finance}"
export DB_PASSWORD="${DB_PASSWORD:-school}"

# Run the backup script
/home/james/projects/school-financial-system/backend/backups/db_backup.sh
