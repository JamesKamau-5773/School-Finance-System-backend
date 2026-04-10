# PostgreSQL Database Backup System
**School Financial ERP - Automated Backup Solution**

## Overview
This directory contains automated backup scripts that protect the school financial database from catastrophic data loss. Backups are compressed, timestamped, and scheduled to run automatically every night at **11:59 PM**.

## Files

### `db_backup.sh`
Main backup script that uses PostgreSQL's `pg_dump` utility.

**Features:**
- Creates compressed SQL dumps of the entire database
- Automatic cleanup of backups older than 30 days (configurable)
- Integrity verification for all backups
- Comprehensive logging with timestamps
- Error handling and database connectivity checks
- Verbose output for troubleshooting

**Configuration via Environment Variables:**
- `DB_HOST` - Database hostname (default: localhost)
- `DB_PORT` - Database port (default: 5432)
- `DB_USER` - Database username (default: postgres)
- `DB_NAME` - Database name (default: school_finance_db)
- `DB_PASSWORD` - Database password (optional)

### `cron_backup.sh`
Wrapper script called by cron that:
- Sources `.env` file for environment variables
- Sets sensible defaults for database connection
- Calls the main backup script

### `backup.log`
Timestamped log file recording all backup operations and any errors.

### `cron.log`
Output log from cron job execution (stdout and stderr).

## Backup Files
Backups are stored in this directory with naming format: `backup_YYYYMMDD_HHMMSS.sql.gz`

Example: `backup_20260410_235900.sql.gz`

Each backup is:
- Compressed with gzip (typically reduces size by 80-90%)
- Verified for integrity after creation
- Automatically deleted after 30 days
- Timestamped for easy identification

## Scheduled Execution

✅ **Currently scheduled to run:** Every night at **23:59 (11:59 PM)**

View the cron job:
```bash
crontab -l | grep "db_backup\|cron_backup"
```

## Manual Testing

### Test 1: Quick Syntax Check
```bash
bash -n /home/james/projects/school-financial-system/backend/backups/db_backup.sh
```

### Test 2: Dry Run with Debug Output
```bash
cd /home/james/projects/school-financial-system/backend
bash -x ./backups/db_backup.sh
```

### Test 3: Manual Backup (Requires Database Running)
```bash
cd /home/james/projects/school-financial-system/backend

# With Docker Compose
docker-compose up -d db
sleep 5

# Run backup with environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=school
export DB_NAME=school_finance
export DB_PASSWORD=school

./backups/db_backup.sh

# Check result
ls -lh ./backups/backup_*.sql.gz
cat ./backups/backup.log
```

### Test 4: Verify Database Connectivity
```bash
pg_isready -h localhost -p 5432 -U school -d school_finance
```

## Monitoring Backups

### View Recent Backups
```bash
ls -lh /home/james/projects/school-financial-system/backend/backups/backup_*.sql.gz
```

### Check Backup Logs
```bash
tail -50 /home/james/projects/school-financial-system/backend/backups/backup.log
```

### Check Cron Execution Logs
```bash
tail -50 /home/james/projects/school-financial-system/backend/backups/cron.log
```

### View Backup Size and Count
```bash
du -sh /home/james/projects/school-financial-system/backend/backups/
find /home/james/projects/school-financial-system/backend/backups/ -name "backup_*.sql.gz" | wc -l
```

## Restoring from Backup

### Extract Backup
```bash
cd /home/james/projects/school-financial-system/backend/backups
gunzip -c backup_20260410_235900.sql.gz | psql -h localhost -U school -d school_finance
```

### Restore to Different Database
```bash
gunzip -c backup_20260410_235900.sql.gz | psql -h localhost -U school -d school_finance_restored
```

### Verify Restored Data
```bash
psql -h localhost -U school -d school_finance -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

## Troubleshooting

### Backup Not Running?
1. Verify cron job exists:
   ```bash
   crontab -l | grep cron_backup
   ```

2. Check that backups/cron_backup.sh is executable:
   ```bash
   ls -l /home/james/projects/school-financial-system/backend/backups/cron_backup.sh
   ```
   If not executable, run:
   ```bash
   chmod +x /home/james/projects/school-financial-system/backend/backups/cron_backup.sh
   ```

3. Check cron logs for errors:
   ```bash
   tail -100 /home/james/projects/school-financial-system/backend/backups/cron.log
   tail -100 /home/james/projects/school-financial-system/backend/backups/backup.log
   ```

4. Verify database is running and accessible:
   ```bash
   pg_isready -h localhost -p 5432
   ```

### Connection Errors?
Ensure environment variables are set correctly:
```bash
echo $DB_HOST $DB_PORT $DB_USER $DB_NAME
```

Or check the `.env` file is readable:
```bash
ls -l /home/james/projects/school-financial-system/backend/.env
```

### Disk Space Issues?
Adjust retention period in `db_backup.sh` (default 30 days):
```bash
# Line: RETENTION_DAYS=30
sed -i 's/RETENTION_DAYS=30/RETENTION_DAYS=14/g' db_backup.sh
```

## Security Considerations

⚠️ **Important:**
- Database password should be stored in `.env` or environment, NOT in scripts
- Backup files contain sensitive data - secure access appropriately
- Consider encrypting backups for additional protection
- Store backups in multiple locations (local + cloud)
- Regularly test restore procedures

## Backup Policy

**Current Configuration:**
- **Frequency:** Daily at 11:59 PM
- **Retention:** 30 days (automatically cleaned)
- **Compression:** Gzip (space efficient)
- **Location:** `./backups/` directory
- **Logging:** All operations logged with timestamps

**Recommended Enhancements:**
1. Upload backups to cloud storage (AWS S3, Azure Blob, etc.)
2. Implement email alerts on backup failure
3. Create incremental/differential backups for large databases
4. Add backup size tracking and alerts
5. Implement rsync to remote backup server
6. Test restore procedures monthly

## Example: Cloud Backup Integration

To upload backups to AWS S3:
```bash
# After backup completes, add to db_backup.sh:
aws s3 cp "$BACKUP_FILE_COMPRESSED" \
    "s3://your-backup-bucket/school-finance/$(basename $BACKUP_FILE_COMPRESSED)"
```

## Additional Resources

- PostgreSQL pg_dump documentation: https://www.postgresql.org/docs/current/app-pgdump.html
- Cron schedule reference: https://crontab.guru/
- Bash scripting best practices: https://mywiki.wooledge.org/BashGuide

---
**Last Updated:** 2026-04-10  
**System:** School Financial ERP Backend  
**Database:** PostgreSQL
