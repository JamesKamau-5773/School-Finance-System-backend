#!/bin/bash

# Migration Runner: Update Student Balances
# This script safely applies balance adjustments to students
# It creates an audit trail via ledger entries (no data deletion)

set -e

echo "=================================================="
echo "Student Balance Update Migration"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "run.py" ]; then
    echo "❌ Error: run.py not found. Are you in the backend directory?"
    exit 1
fi

# Confirm before running against production
echo ""
echo "⚠️  THIS WILL UPDATE STUDENT BALANCES IN PRODUCTION"
echo ""
read -p "Continue? (type 'yes' to proceed): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Migration cancelled."
    exit 0
fi

# Run the migration
python << 'EOF'
import sys
import os
from migrations.update_student_balances import migrate

try:
    result = migrate()
    sys.exit(0 if result['success'] else 1)
except Exception as e:
    print(f"Migration failed: {e}")
    sys.exit(1)
EOF

echo ""
echo "✅ Migration complete!"
