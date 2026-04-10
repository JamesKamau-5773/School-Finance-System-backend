#!/bin/bash

# PostgreSQL Database Backup Script
# Uses pg_dump for automated backups in school financial ERP system
# Runs via cron at 11:59 PM daily

set -e  # Exit on error

# Configuration
BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$BACKUP_DIR/backup.log"
RETENTION_DAYS=30
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-school_finance_db}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.sql"
BACKUP_FILE_COMPRESSED="$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================"
log "Starting PostgreSQL backup process"
log "Database: $DB_NAME"
log "Host: $DB_HOST:$DB_PORT"
log "Backup file: $BACKUP_FILE_COMPRESSED"

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    log "ERROR: pg_dump not found. Please install PostgreSQL client tools."
    exit 1
fi

# Check database connectivity
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" &> /dev/null; then
    log "ERROR: Cannot connect to database at $DB_HOST:$DB_PORT"
    exit 1
fi

# Create backup
log "Creating backup..."
if PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    > "$BACKUP_FILE" 2>> "$LOG_FILE"; then
    log "Dump created successfully: $BACKUP_FILE"
else
    log "ERROR: pg_dump failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Compress backup
log "Compressing backup..."
if gzip "$BACKUP_FILE"; then
    log "Backup compressed: $BACKUP_FILE_COMPRESSED"
    BACKUP_SIZE=$(du -h "$BACKUP_FILE_COMPRESSED" | cut -f1)
    log "Backup size: $BACKUP_SIZE"
else
    log "ERROR: Compression failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Clean up old backups (older than RETENTION_DAYS)
log "Cleaning up backups older than $RETENTION_DAYS days..."
DELETED_COUNT=0
while IFS= read -r OLD_FILE; do
    if rm -f "$OLD_FILE"; then
        DELETED_COUNT=$((DELETED_COUNT + 1))
        log "Deleted: $(basename "$OLD_FILE")"
    fi
done < <(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS)

log "Deleted $DELETED_COUNT old backup(s)"

# Verify backup integrity
log "Verifying backup integrity..."
if gzip -t "$BACKUP_FILE_COMPRESSED" 2>> "$LOG_FILE"; then
    log "Backup verification: PASSED"
else
    log "ERROR: Backup verification failed"
    exit 1
fi

# Summary
BACKUP_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.sql.gz" -type f | wc -l)
log "Total backups retained: $BACKUP_COUNT"
log "Backup process completed successfully!"
log "========================================"

exit 0
