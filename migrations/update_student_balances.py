"""
Migration Script: Update Student Balances Safely
Purpose: Adjust student ledger balances to match provided target values
Approach: Creates adjustment entries (no data deletion - preserves audit trail)

Usage:
  python -c "from migrations.update_student_balances import migrate; migrate()"
  
Or manually:
  python run.py
  Then in Python shell:
  >>> from migrations.update_student_balances import migrate
  >>> migrate()
"""

from app import db, create_app
from app.models.student import Student
from app.models.student_ledger import StudentLedger
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, case
import json

# Target balances provided by user
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


def get_student_balance(student_id):
    """Calculate current balance for a student from ledger entries."""
    result = db.session.query(
        func.sum(
            case(
                (StudentLedger.entry_type == 'DEBIT', StudentLedger.amount),
                (StudentLedger.entry_type == 'CREDIT', -StudentLedger.amount),
                else_=0
            )
        )
    ).filter(StudentLedger.student_id == student_id).scalar()
    
    return Decimal(result or 0)


def create_adjustment_entry(student_id, adjustment_amount, description, reference_no):
    """Create an adjustment ledger entry."""
    entry_type = 'DEBIT' if adjustment_amount > 0 else 'CREDIT'
    amount = abs(adjustment_amount)
    
    ledger_entry = StudentLedger(
        student_id=student_id,
        entry_type=entry_type,
        amount=amount,
        description=description,
        reference_no=reference_no
    )
    db.session.add(ledger_entry)
    return ledger_entry


def migrate():
    """Execute the migration: update student balances safely."""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("STUDENT BALANCE UPDATE MIGRATION")
        print("="*80)
        
        # Start transaction
        transaction = db.session.begin()
        
        try:
            changes = []
            not_found = []
            timestamp = datetime.utcnow().isoformat()
            
            print("\n[1/3] Analyzing balance adjustments...")
            print("-" * 80)
            
            for target in TARGET_BALANCES:
                adm_number = str(target['adm'])
                desired_balance = Decimal(str(target['balance']))
                
                # Find student by admission number
                student = Student.query.filter_by(
                    admission_number=adm_number
                ).first()
                
                if not student:
                    not_found.append(adm_number)
                    print(f"❌ ADM {adm_number}: NOT FOUND")
                    continue
                
                # Calculate current balance
                current_balance = get_student_balance(student.id)
                adjustment = desired_balance - current_balance
                
                if adjustment == 0:
                    print(f"✓ ADM {adm_number}: {current_balance} ➜ {desired_balance} (no change)")
                else:
                    direction = "+" if adjustment > 0 else ""
                    print(f"▶ ADM {adm_number}: {current_balance} ➜ {desired_balance} ({direction}{adjustment})")
                    
                    # Create adjustment entry
                    reference = f"BALANCE_ADJ_{adm_number}_{timestamp.replace(':', '').replace('-', '')}"
                    desc = f"Balance adjustment to {desired_balance}"
                    
                    create_adjustment_entry(
                        student_id=student.id,
                        adjustment_amount=adjustment,
                        description=desc,
                        reference_no=reference
                    )
                    
                    changes.append({
                        "admission_number": adm_number,
                        "student_id": str(student.id),
                        "current_balance": float(current_balance),
                        "desired_balance": float(desired_balance),
                        "adjustment": float(adjustment),
                        "reference": reference
                    })
            
            print("\n[2/3] Committing changes to database...")
            print("-" * 80)
            
            if changes:
                db.session.commit()
                print(f"✅ Successfully applied {len(changes)} balance adjustments")
            else:
                print("ℹ️  No adjustments needed")
            
            print("\n[3/3] Verification...")
            print("-" * 80)
            
            # Verify updates
            verified = 0
            for change in changes:
                student = Student.query.filter_by(
                    admission_number=change['admission_number']
                ).first()
                if student:
                    verified_balance = get_student_balance(student.id)
                    desired = Decimal(str(change['desired_balance']))
                    
                    if verified_balance == desired:
                        print(f"✓ ADM {change['admission_number']}: Verified ✓ (balance = {verified_balance})")
                        verified += 1
                    else:
                        print(f"❌ ADM {change['admission_number']}: MISMATCH! Expected {desired}, got {verified_balance}")
            
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
            
            return {
                "success": True,
                "processed": len(TARGET_BALANCES),
                "adjustments": len(changes),
                "verified": verified,
                "not_found": not_found,
                "changes": changes
            }
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            transaction.rollback()
            print("Transaction rolled back. No changes applied.")
            raise


if __name__ == "__main__":
    migrate()
