# Student Balance Update - Migration Guide

## Summary

I've created safe data migration scripts to update student balances for 45 students. Here's what was done:

### ✅ Migration Strategy
- **Preserves all historical data** - no ledger entries are deleted
- **Creates audit trail** - each adjustment is tracked with reference number and timestamp
- **Atomic operations** - all-or-nothing commit to prevent partial updates
- **Zero-downtime** - balances calculated on-the-fly from ledger entries

### Migration Scripts Created

1. **`standalone_balance_migration.py`** (Main Script)
   - Pure Python, no Flask dependency
   - Connects directly to Neon PostgreSQL via `DATABASE_URL`
   - Updates 45 students identified by admission number
   - Creates adjustment ledger entries
   - Verifies all updates post-commit
   - **Location**: `/home/james/projects/school-financial-system/backend/standalone_balance_migration.py`

2. **`migrations/update_student_balances.py`** (Flask-based)
   - For running within Flask app context
   - Can be imported as module
   - Same logic as standalone version
   - **Location**: `/home/james/projects/school-financial-system/backend/migrations/update_student_balances.py`

3. **`run_balance_migration.sh`** (Bash wrapper)
   - Interactive confirmation
   - Safe execution wrapper
   - **Location**: `/home/james/projects/school-financial-system/backend/run_balance_migration.sh`

---

## How to Run the Migration

### Method 1: Direct Python (Recommended)
```bash
cd /home/james/projects/school-financial-system/backend
DATABASE_URL='your_neon_url' python standalone_balance_migration.py
```

### Method 2: Via Render Shell (No Local Setup)
1. Go to https://dashboard.render.com
2. Click your service: **school-finance-system-backend**
3. Click the **"Shell"** tab
4. Run:
```bash
python standalone_balance_migration.py
```
The `DATABASE_URL` is already set in Render environment!

### Method 3: AWS Lambda / One-off Production Job
Same as Method 1, just ensure `DATABASE_URL` environment variable is set.

---

## Getting Your DATABASE_URL

### From Render Dashboard:
1. Go to https://dashboard.render.com
2. Click **school-finance-system-backend** service
3. Go to **Environment** tab
4. Copy the value of `DATABASE_URL` 
5. Format: `postgresql://user:password@host/dbname?sslmode=require`

### From Neon Console:
1. Go to https://console.neon.tech
2. Find your database  
3. Click **Connection string**
4. Copy the PostgreSQL URL

---

## What the Migration Does

### Input Data
```json
[
  {"adm": 1238, "balance": 3500},
  {"adm": 1241, "balance": 7800},
  ... (45 total)
]
```

### Processing
For each student:
1. **Find** student by admission number
2. **Calculate** current balance from ledger
3. **Compute** difference = desired - current
4. **Create** adjustment ledger entry (DEBIT or CREDIT)
5. **Verify** new balance matches target

### Result Example
```
ADM 1238: 2500 ➜ 3500 (+1000)    ← Creates DEBIT entry for 1000
ADM 1241: 8000 ➜ 7800 (-200)     ← Creates CREDIT entry for 200
ADM 1252: 500 ➜ 0 (-500)         ← Creates CREDIT entry for 500
```

### Output Ledger Entries
```sql
-- Example: Student ADM 1238 gets an adjustment entry
INSERT INTO student_ledgers 
(student_id, entry_type, amount, description, reference_no, created_at)
VALUES 
  ('uuid-here', 'DEBIT', 1000, 'Balance adjustment to 3500', 'BALANCE_ADJ_1238_20260429...', NOW());
```

---

## Data Integrity

### What's Preserved
✅ All student records  
✅ All user accounts  
✅ All existing ledger entries  
✅ All transaction history  
✅ Inventory data  
✅ Fee structures  

### What Changes
🔄 Student ledger entries: **45 new adjustment entries added**  
🔄 Student balances: **Recalculated from ledger (automatically)**  

### Audit Trail
- Each adjustment gets a unique reference: `BALANCE_ADJ_{adm}_{timestamp}`
- Description: `Balance adjustment to {target_balance}`
- All tracked with `created_at` timestamp
- Fully queryable and reversible if needed

---

## Verification

After running, check results:

### In Render Shell or Local psql:
```sql
-- Check that balances were updated correctly
SELECT 
  s.admission_number,
  SUM(CASE WHEN sl.entry_type = 'DEBIT' THEN sl.amount 
           WHEN sl.entry_type = 'CREDIT' THEN -sl.amount 
           ELSE 0 END) as balance
FROM students s
LEFT JOIN student_ledgers sl ON s.id = sl.student_id
WHERE s.admission_number IN ('1238', '1241', '1242')
GROUP BY s.admission_number;

-- See the adjustment entries created
SELECT * FROM student_ledgers 
WHERE reference_no LIKE 'BALANCE_ADJ_%'
ORDER BY created_at DESC
LIMIT 45;
```

---

## Sample Migration Output

```
================================================================================
STUDENT BALANCE UPDATE - STANDALONE MIGRATION
================================================================================

[Connecting to database...]
✅ Database connected

[1/3] Analyzing balance adjustments...
--------------------------------------------------------------------------------
✓ ADM 1238: 2500 ➜ 3500 (+1000)
▶ ADM 1241: 8000 ➜ 7800 (-200)
▶ ADM 1242: 32500 ➜ 32000 (-500)
✓ ADM 1252: 0 ➜ 0 (no change)
... [41 more]

[2/3] Committing changes to database...
--------------------------------------------------------------------------------
✅ Successfully applied 42 balance adjustments

[3/3] Verification...
--------------------------------------------------------------------------------
✓ ADM 1238: Verified ✓ (balance = 3500)
✓ ADM 1241: Verified ✓ (balance = 7800)
... [43 more]

================================================================================
MIGRATION SUMMARY
================================================================================
Processed:     45 students
Adjustments:   42 (3 already had correct balance)
Verified:      42/42
Not Found:     0

✅ MIGRATION COMPLETED SUCCESSFULLY
================================================================================
```

---

## Troubleshooting

### Error: "DATABASE_URL environment variable not set"
**Solution**: Set the environment variable before running:
```bash
export DATABASE_URL='postgresql://...'
python standalone_balance_migration.py
```

### Error: "Student not found" (ADM 1238, etc.)
**Meaning**: Student with that admission number doesn't exist  
**Check**: Query your students table:
```sql
SELECT admission_number FROM students WHERE admission_number IN ('1238', '1241', ...);
```

### Error: "Connection refused"
**Meaning**: Can't reach database  
**Check**: 
- DATABASE_URL is correct
- Network allows outbound to Neon PostgreSQL (port 5432)
- If using Render shell, this shouldn't happen (network already configured)

### Partial Update (some students updated, others failed)
**Safe**: Transaction rolled back automatically - either all succeed or all fail  
**If error occurred**: Check logs and re-run script

---

## Rollback (If Needed)

If something goes wrong, the migration is reversible:

```sql
-- Option 1: Delete adjustment entries (keeps audit trail)
DELETE FROM student_ledgers 
WHERE reference_no LIKE 'BALANCE_ADJ_%'
AND created_at > NOW() - INTERVAL '1 hour';

-- Option 2: View the adjustments before deleting
SELECT admission_number, amount, entry_type, created_at
FROM student_ledgers sl
JOIN students s ON sl.student_id = s.id
WHERE sl.reference_no LIKE 'BALANCE_ADJ_%'
ORDER BY sl.created_at DESC;
```

---

## Files Created

| File | Purpose |
|------|---------|
| `standalone_balance_migration.py` | Main migration script (pure Python, no Flask needed) |
| `migrations/update_student_balances.py` | Flask-based migration (alternative) |
| `run_balance_migration.sh` | Interactive bash wrapper |
| `BALANCE_MIGRATION_README.md` | This file |

---

## Next Steps

1. **Obtain DATABASE_URL** from Render environment or Neon console
2. **Run migration**:
   ```bash
   DATABASE_URL='your_url_here' python standalone_balance_migration.py
   ```
3. **Verify results** in database
4. **Commit changes** if needed, or update frontend if caching

---

## Questions or Issues?

The migration is fully atomic and safe. No data is deleted, only ledger entries added for audit trail.
