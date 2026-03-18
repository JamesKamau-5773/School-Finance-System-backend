from app.repositories.transaction_repository import TransactionRepository
from app.repositories.student_repository import StudentRepository
from app.models.finance import VoteHead
from app import db


class FinanceService:
    @staticmethod
    def process_fee_payment(student_id, amount, payment_method, reference_no, user_id):
        # 1. Verify the student exists
        student = StudentRepository.get_by_id(student_id)
        if not student:
            return {"error": "Student not found"}, 404

        # 2. Fetch active Vote Heads directly
        vote_heads = VoteHead.query.all()
        if not vote_heads:
            return {"error": "System configuration error: No Vote Heads found"}, 500

        # 3. Calculate the total budget weight for proportional splitting
        total_budget = sum(vh.annual_budget for vh in vote_heads)

        try:
            # 4. Distribute the money into the separate buckets
            for vh in vote_heads:
                # Calculate the exact share for this specific bucket
                split_amount = round(
                    (vh.annual_budget / total_budget) * amount, 2)

                # Record the ledger entry using our Repository
                TransactionRepository.create_ledger_entry({
                    'student_id': student_id,
                    'vote_head_id': vh.id,
                    'amount': split_amount,
                    'transaction_type': 'CREDIT',
                    'payment_method': payment_method,
                    'reference_no': reference_no,
                    'description': f"Automated split allocation to {vh.name}",
                    'created_by': user_id
                })

            # 5. Update the student's master balance (reducing their debt)
            StudentRepository.update_balance(student_id, -amount)

            db.session.commit()
            return {
                "message": "Payment successfully processed and split",
                "total_recorded": amount,
                "new_balance": float(student.balance)
            }, 201

        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.student_repository import StudentRepository
from app.models.finance import VoteHead
from app import db


class FinanceService:
    @staticmethod
    def process_fee_payment(student_id, amount, payment_method, reference_no, user_id):
        # 1. Verify the student exists
        student = StudentRepository.get_by_id(student_id)
        if not student:
            return {"error": "Student not found"}, 404

        # 2. Fetch active Vote Heads directly
        vote_heads = VoteHead.query.all()
        if not vote_heads:
            return {"error": "System configuration error: No Vote Heads found"}, 500

        # 3. Calculate the total budget weight for proportional splitting
        total_budget = sum(vh.annual_budget for vh in vote_heads)

        try:
            # 4. Distribute the money into the separate buckets
            for vh in vote_heads:
                # Calculate the exact share for this specific bucket
                split_amount = round(
                    (vh.annual_budget / total_budget) * amount, 2)

                # Record the ledger entry using our Repository
                TransactionRepository.create_ledger_entry({
                    'student_id': student_id,
                    'vote_head_id': vh.id,
                    'amount': split_amount,
                    'transaction_type': 'CREDIT',
                    'payment_method': payment_method,
                    'reference_no': reference_no,
                    'description': f"Automated split allocation to {vh.name}",
                    'created_by': user_id
                })

            # 5. Update the student's master balance (reducing their debt)
            StudentRepository.update_balance(student_id, -amount)

            db.session.commit()
            return {
                "message": "Payment successfully processed and split",
                "total_recorded": amount,
                "new_balance": float(student.balance)
            }, 201

        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500
