#!/usr/bin/env python3
"""
Standalone Student Balance Migration Runner
Connects directly to Neon PostgreSQL and updates balances
Run this on Render via a one-off dyno or SSH terminal
"""

import os
import sys
import json
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine, func, case, text
from sqlalchemy.orm import sessionmaker

# Database connection using Render/Neon environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    print("Set it in Render environment variables or .env file")
    sys.exit(1)

TARGET_BALANCES = [
    {"adm": 1238, "balance": 3500},
    {"adm": 1241, "balance": 7800},
    {"adm": 1242, "balance": 32000},
    {"adm": 1243, "balance": 2750},
    {"adm": 1245, "balance": 3000},
    {"adm": 1246, "balance": 7000},
    {"adm": 1248, "balance": 7000},
    {"adm": 1251, "balance": 3000},
    {"adm": 1252, "balance": 0},
    {"adm": 1254, "balance": 4000},
    {"adm": 1255, "balance": 20500},
    {"adm": 1256, "balance": 4000},
    {"adm": 1257, "balance": 9800},
    {"adm": 1258, "balance": 8000},
    {"adm": 1261, "balance": 3250},
    {"adm": 1264, "balance": 32000},
    {"adm": 1267, "balance": 7000},
    {"adm": 1268, "balance": 8000},
    {"adm": 1272, "balance": 8000},
    {"adm": 1273, "balance": 3500},
    {"adm": 1277, "balance": 4000},
    {"adm": 1278, "balance": 14800},
    {"adm": 1282, "balance": 8750},
    {"adm": 1285, "balance": 27900},
    {"adm": 1286, "balance": 6000},
    {"adm": 1287, "balance": 19200},
    {"adm": 1288, "balance": 4350},
    {"adm": 1292, "balance": 500},
    {"adm": 1294, "balance": 9500},
    {"adm": 1298, "balance": 700},
    {"adm": 1301, "balance": 14000},
    {"adm": 1302, "balance": 7000},
    {"adm": 1308, "balance": 21500},
    {"adm": 1313, "balance": 9500},
    {"adm": 1314, "balance": 1500},
    {"adm": 1315, "balance": 39000},
    {"adm": 1316, "balance": 39000},
    {"adm": 1321, "balance": 20000},
    {"adm": 1322, "balance": 50},
    {"adm": 1324, "balance": 1600},
    {"adm": 1325, "balance": 22000},
    {"adm": 1326, "balance": 19950},
    {"adm": 1327, "balance": 29000},
    {"adm": 1328, "balance": 30356},
    {"adm": 1329, "balance": 32800}
]


def main():
    """Execute the standalone migration."""
    
    print("\n" + "="*80)
    print("STUDENT BALANCE UPDATE - STANDALONE MIGRATION")
    print("="*80)
    
    try:
        # Connect to database
        print("\n[Connecting to database...]")
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("✅ Database connected")
        
        # Start transaction
        print("\n[1/3] Analyzing balance adjustments...")
        print("-" * 80)
        
        changes = []
        not_found = []
        timestamp = datetime.utcnow().isoformat().replace(':', '').replace('-', '').split('.')[0]
        
        for target in TARGET_BALANCES:
            adm_number = str(target['adm'])
            desired_balance = Decimal(str(target['balance']))
            
            # Query student
            student = session.execute(
                text("SELECT id FROM students WHERE admission_number = :adm"),
                {"adm": adm_number}
            ).fetchone()
            
            if not student:
                not_found.append(adm_number)
                print(f"❌ ADM {adm_number}: NOT FOUND")
                continue
            
            student_id = student[0]
            
            # Get current balance (sum DEBIT - sum CREDIT)
            balance_result = session.execute(
                text("""
                    SELECT COALESCE(SUM(CASE 
                        WHEN entry_type = 'DEBIT' THEN amount
                        WHEN entry_type = 'CREDIT' THEN -amount
                        ELSE 0
                    END), 0) as balance
                    FROM student_ledgers
                    WHERE student_id = :student_id
                """),
                {"student_id": student_id}
            ).fetchone()
            
            current_balance = Decimal(str(balance_result[0] or 0))
            adjustment = desired_balance - current_balance
            
            if adjustment == 0:
                print(f"✓ ADM {adm_number}: {current_balance} ➜ {desired_balance} (no change)")
            else:
                direction = "+" if adjustment > 0 else ""
                print(f"▶ ADM {adm_number}: {current_balance} ➜ {desired_balance} ({direction}{adjustment})")
                
                # Create adjustment entry
                entry_type = 'DEBIT' if adjustment > 0 else 'CREDIT'
                amount = abs(adjustment)
                reference = f"BALANCE_ADJ_{adm_number}_{timestamp}"
                description = f"Balance adjustment to {desired_balance}"
                
                session.execute(
                    text("""
                        INSERT INTO student_ledgers 
                        (student_id, entry_type, amount, description, reference_no, created_at)
                        VALUES (:student_id, :entry_type, :amount, :description, :reference_no, :created_at)
                    """),
                    {
                        "student_id": student_id,
                        "entry_type": entry_type,
                        "amount": float(amount),
                        "description": description,
                        "reference_no": reference,
                        "created_at": datetime.utcnow()
                    }
                )
                
                changes.append({
                    "admission_number": adm_number,
                    "student_id": str(student_id),
                    "current_balance": float(current_balance),
                    "desired_balance": float(desired_balance),
                    "adjustment": float(adjustment),
                    "reference": reference
                })
        
        print("\n[2/3] Committing changes to database...")
        print("-" * 80)
        
        if changes:
            session.commit()
            print(f"✅ Successfully applied {len(changes)} balance adjustments")
        else:
            print("ℹ️  No adjustments needed")
        
        print("\n[3/3] Verification...")
        print("-" * 80)
        
        # Verify updates
        verified = 0
        for change in changes:
            # Get updated balance
            balance_result = session.execute(
                text("""
                    SELECT id FROM students WHERE admission_number = :adm
                """),
                {"adm": change['admission_number']}
            ).fetchone()
            
            if balance_result:
                student_id = balance_result[0]
                balance_check = session.execute(
                    text("""
                        SELECT COALESCE(SUM(CASE 
                            WHEN entry_type = 'DEBIT' THEN amount
                            WHEN entry_type = 'CREDIT' THEN -amount
                            ELSE 0
                        END), 0) as balance
                        FROM student_ledgers
                        WHERE student_id = :student_id
                    """),
                    {"student_id": student_id}
                ).fetchone()
                
                verified_balance = Decimal(str(balance_check[0] or 0))
                desired = Decimal(str(change['desired_balance']))
                
                if verified_balance == desired:
                    print(f"✓ ADM {change['admission_number']}: Verified ✓ (balance = {verified_balance})")
                    verified += 1
                else:
                    print(f"❌ ADM {change['admission_number']}: MISMATCH! Expected {desired}, got {verified_balance}")
        
        session.close()
        
        print("\n" + "="*80)
        print("MIGRATION SUMMARY")
        print("="*80)
        print(f"Processed:     {len(TARGET_BALANCES)} students")
        print(f"Adjustments:   {len(changes)}")
        print(f"Verified:      {verified}/{len(changes)}")
        print(f"Not Found:     {len(not_found)}")
        
        if not_found:
            print(f"\nMissing Students (ADM): {', '.join(not_found)}")
        
        print("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
