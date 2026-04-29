"""
Quick Start: Run this command in your terminal to update all balances

OPTION 1: If you have DATABASE_URL in environment:
    cd /home/james/projects/school-financial-system/backend
    python standalone_balance_migration.py

OPTION 2: Direct inline (replace YOUR_DATABASE_URL):
    cd /home/james/projects/school-financial-system/backend
    DATABASE_URL='YOUR_DATABASE_URL' python standalone_balance_migration.py

OPTION 3: Get DATABASE_URL from Render console, then:
    1. Go to: https://dashboard.render.com
    2. Click your backend service: "school-finance-system-backend"
    3. Go to "Environment" tab  
    4. Copy the DATABASE_URL value
    5. Paste it into the command below and run:

    DATABASE_URL='postgresql://postgres:YOUR_PASSWORD@YOUR_HOST/YOUR_DB?sslmode=require' python standalone_balance_migration.py
    
OPTION 4: Use Render shell directly:
    1. Go to Render dashboard
    2. Click your backend service
    3. Click "Shell" tab
    4. cd /home/james/projects/school-financial-system/backend
    5. python standalone_balance_migration.py
    
The script will:
✓ Connect to your Neon database
✓ Create adjustment ledger entries (no deletions)
✓ Update 45 students' balances
✓ Verify all changes
✓ Show detailed report

No data is deleted - audit trail preserved!
"""

# Quick reference for DATABASE_URL format:
# postgresql://user:password@host:5432/database?sslmode=require

print(__doc__)
