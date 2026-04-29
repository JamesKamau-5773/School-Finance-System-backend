#!/usr/bin/env bash

# QUICK START: Student Balance Migration
# Copy-paste the command below with your DATABASE_URL

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║         STUDENT BALANCE MIGRATION - QUICK START                            ║
╚════════════════════════════════════════════════════════════════════════════╝

📋 WHAT'S HAPPENING:
   • 45 students will get balance adjustments
   • All historical data is PRESERVED (no deletions)
   • Audit trail created for each change (reference: BALANCE_ADJ_*)
   • Zero downtime - can run anytime

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 OPTION 1: Via Render Shell (EASIEST - NO SETUP NEEDED)
   
   1. Open Render Dashboard: https://dashboard.render.com
   2. Click: school-finance-system-backend
   3. Click: "Shell" tab
   4. Paste:
   
      python standalone_balance_migration.py
   
   ✓ DATABASE_URL already set in Render environment
   ✓ Run immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 OPTION 2: From Your Local Terminal

   1. Get DATABASE_URL from Render:
      • Go to https://dashboard.render.com
      • Click: school-finance-system-backend  
      • Go to: Environment tab
      • Copy: DATABASE_URL value
   
   2. Run:
   
      cd /home/james/projects/school-financial-system/backend
      DATABASE_URL='postgresql://user:pass@host/db?sslmode=require' \
        python standalone_balance_migration.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 EXPECTED OUTPUT:

   ================================================================================
   STUDENT BALANCE UPDATE - STANDALONE MIGRATION
   ================================================================================
   
   [Connecting to database...]
   ✅ Database connected
   
   [1/3] Analyzing balance adjustments...
   ────────────────────────────────────────────────────────────────────────────
   ✓ ADM 1238: 2500 ➜ 3500 (+1000)
   ▶ ADM 1241: 8000 ➜ 7800 (-200)
   ▶ ADM 1242: 32500 ➜ 32000 (-500)
   [... 42 more adjustments ...]
   
   [2/3] Committing changes to database...
   ────────────────────────────────────────────────────────────────────────────
   ✅ Successfully applied 42 balance adjustments
   
   [3/3] Verification...
   ────────────────────────────────────────────────────────────────────────────
   ✓ ADM 1238: Verified ✓ (balance = 3500)
   ✓ ADM 1241: Verified ✓ (balance = 7800)
   [... 40 more verified ...]
   
   ================================================================================
   MIGRATION SUMMARY
   ================================================================================
   Processed:     45 students
   Adjustments:   42
   Verified:      42/42
   Not Found:     0
   
   ✅ MIGRATION COMPLETED SUCCESSFULLY
   ================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SAFETY FEATURES:

   ✓ No data deletion - audit trail preserved  
   ✓ Atomic transaction - all or nothing
   ✓ Automatic verification - confirms each update
   ✓ Detailed reporting - shows exactly what changed
   ✓ Reversible - can query and delete adjustment entries if needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ NEED HELP?

   • Check DATABASE_URL format: postgresql://user:pass@host/db?sslmode=require
   • See full docs: MIGRATION_COMPLETE.md
   • View migration code: standalone_balance_migration.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
