#!/bin/bash

# Interactive Student Balance Migration
# Prompts for DATABASE_URL and runs migration safely

set -e

echo "=================================================="
echo "Student Balance Update Migration"
echo "====================================================="
echo ""
echo "This script will:"
echo "  • Connect to your Neon PostgreSQL database"
echo "  • Create adjustment ledger entries for each student"
echo "  • Preserve all existing transaction history"
echo "  • Update 45 student balances"
echo ""

# Get DATABASE_URL
echo "Enter your DATABASE_URL from Render/Neon:"
echo "(Format: postgresql://user:password@host/database?sslmode=require)"
echo ""
read -p "DATABASE_URL: " DATABASE_URL

if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL cannot be empty"
    exit 1
fi

# Confirm
echo ""
echo "⚠️  CONFIRM OPERATION"
echo "Database: ${DATABASE_URL:0:40}..."
echo ""
read -p "Type 'yes' to proceed: " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Migration cancelled"
    exit 0
fi

# Run migration
export DATABASE_URL="$DATABASE_URL"

python3 << 'EOFMIG'
import sys
sys.path.insert(0, '/home/james/projects/school-financial-system/backend')
exec(open('/home/james/projects/school-financial-system/backend/standalone_balance_migration.py').read())
EOFMIG
