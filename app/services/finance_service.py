from datetime import datetime, timezone
from decimal import Decimal
import uuid
from app import db
from app.models.finance import Transaction, VoteHead
from app.models.student_ledger import StudentLedger
from app.models.auth import User
from app.repositories.finance_repository import FinanceRepository
from app.repositories.vote_head_repository import VoteHeadRepository
from app.repositories.system_repository import SystemRepository
from app.utils.validators import is_valid_uuid


class FinanceService:
    """Handles business logic for financial transactions (income/expense recording).
    
    Single Responsibility: Create and persist Transaction records to database.
    Does NOT handle user/vote head lookup (delegated to SystemRepository).
    """

    @staticmethod
    def get_recent_transactions(limit=50):
        """Fetch most recent transactions for the finance ledger."""
        transactions = (
            Transaction.query
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )
        return [transaction.to_dict() for transaction in transactions]

    @staticmethod
    def get_all_vote_heads():
        """Fetch all vote heads with their current balances."""
        return FinanceRepository.get_all_vote_heads()

    @staticmethod
    def create_vote_head(data):
        """Create a new vote head."""
        return VoteHeadRepository.create(data)

    @staticmethod
    def update_vote_head(vote_head_id, data):
        """Update an existing vote head."""
        return VoteHeadRepository.update(vote_head_id, data)

    @staticmethod
    def delete_vote_head(vote_head_id):
        """Delete an existing vote head."""
        return VoteHeadRepository.delete(vote_head_id)

    @staticmethod
    def _build_unique_student_ledger_reference(reference_no):
        base_reference = str(reference_no or '').strip()
        if not base_reference:
            base_reference = 'REF'

        if not StudentLedger.query.filter_by(reference_no=base_reference).first():
            return base_reference

        suffix = 1
        while True:
            candidate = f"{base_reference}-{suffix}"
            if not StudentLedger.query.filter_by(reference_no=candidate).first():
                return candidate
            suffix += 1

    @staticmethod
    def process_fee_payment(student_id, amount, payment_method, reference_no, user_id, vote_head_id):
        """Record a fee payment (income transaction).
        
        Args:
            student_id: Student making the payment (optional)
            amount: Payment amount
            payment_method: Method of payment (CASH, CARD, etc.)
            reference_no: Transaction reference number
            user_id: User recording the transaction
            vote_head_id: Vote head (budget bucket) for this transaction
            
        Returns:
            dict: Serialized Transaction object
            
        Raises:
            ValueError: If validation fails
        """
        # Input validation
        if amount is None:
            raise ValueError("amount is required")
        if not payment_method:
            raise ValueError("payment_method is required")

        amount_value = float(amount)
        if amount_value <= 0:
            raise ValueError("amount must be greater than 0")

        # Create and persist transaction (+ student ledger credit when student is known)
        try:
            description_base = f"Payment received via {payment_method}"
            
            # Validate and use student_id only if it's a valid UUID
            valid_student_id = None
            if student_id and is_valid_uuid(student_id):
                valid_student_id = student_id
            elif student_id and not is_valid_uuid(student_id):
                # Log invalid UUID but don't fail - just exclude the student_id
                description_base += f" from student ID {student_id}"
            
            transaction = Transaction(
                vote_head_id=vote_head_id,
                recorded_by=user_id,
                student_id=valid_student_id,  # Only set if valid UUID
                transaction_type='INCOME',
                amount=amount_value,
                reference_number=reference_no,
                description=description_base,
                transaction_date=datetime.now(timezone.utc)
            )
            db.session.add(transaction)

            if valid_student_id:
                safe_reference_no = FinanceService._build_unique_student_ledger_reference(reference_no)
                student_ledger_entry = StudentLedger(
                    student_id=valid_student_id,
                    entry_type='CREDIT',
                    amount=amount_value,
                    description=f"Payment received via {payment_method}",
                    reference_no=safe_reference_no
                )
                db.session.add(student_ledger_entry)

            db.session.commit()
            return transaction.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def process_expense(description, amount, category, payment_method, reference_no, user_id, vote_head_id):
        """Record an expense (expense transaction).
        
        Args:
            description: Expense description
            amount: Expense amount
            category: Expense category
            payment_method: Method of payment (CASH, CARD, etc.)
            reference_no: Transaction reference number
            user_id: User recording the transaction
            vote_head_id: Vote head (budget bucket) for this transaction
            
        Returns:
            dict: Serialized Transaction object
            
        Raises:
            ValueError: If validation fails
        """
        # Input validation
        if not description:
            raise ValueError("description is required")
        if amount is None:
            raise ValueError("amount is required")
        if not category:
            raise ValueError("category is required")
        if not payment_method:
            raise ValueError("payment_method is required")

        amount_value = float(amount)
        if amount_value <= 0:
            raise ValueError("amount must be greater than 0")

        # Create and persist transaction
        try:
            transaction = Transaction(
                vote_head_id=vote_head_id,
                recorded_by=user_id,
                transaction_type='EXPENSE',
                amount=amount_value,
                reference_number=reference_no,
                description=description,
                transaction_date=datetime.now(timezone.utc)
            )
            db.session.add(transaction)
            db.session.commit()
            return transaction.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def reallocate_funds(source_vote_head, destination_vote_head, amount, authorized_by, reason):
        """
        Moves funds from one MoE Vote Head to another based on Principal authorization.
        """
        if not source_vote_head:
            raise ValueError('source_vote_head is required')
        if not destination_vote_head:
            raise ValueError('destination_vote_head is required')
        if amount is None:
            raise ValueError('amount is required')
        if not reason:
            raise ValueError('reason is required')

        amount_dec = Decimal(str(amount))
        if amount_dec <= 0:
            raise ValueError('amount must be greater than 0')

        recorded_by = SystemRepository.get_or_create_system_user()
        if authorized_by and is_valid_uuid(authorized_by):
            authorized_user = User.query.filter_by(id=authorized_by).first()
            if authorized_user:
                recorded_by = authorized_user.id

        student_id = authorized_by if (authorized_by and is_valid_uuid(authorized_by)) else None

        transaction_data = {
            'reference_no': f"ADJ-{str(uuid.uuid4())[:8].upper()}",
            'student_id': student_id,
            'recorded_by': recorded_by,
            'source_vote_head': source_vote_head,
            'destination_vote_head': destination_vote_head,
            'amount': amount_dec,
            'transaction_type': 'ADJUSTMENT',
            'payment_method': 'INTERNAL',
            'description': f"Reallocation: {reason} (authorized_by={authorized_by})"
        }

        ledger_lines = [
            {
                'account_name': f"Income_VoteHead_{source_vote_head}",
                'amount': amount_dec,
                'entry_type': 'DEBIT'
            },
            {
                'account_name': f"Income_VoteHead_{destination_vote_head}",
                'amount': amount_dec,
                'entry_type': 'CREDIT'
            }
        ]

        transaction = FinanceRepository.create_transaction_with_ledger(transaction_data, ledger_lines)
        return transaction.to_dict()

    @staticmethod
    def process_capitation_disbursement(total_amount, term_identifier, reference_no):
        """
        Ingests a lump-sum MoE capitation grant and instantly shatters it
        into ring-fenced statutory Vote Heads.
        """
        amount_dec = Decimal(str(total_amount))
        if amount_dec <= 0:
            raise ValueError('total_amount must be greater than 0')
        if not term_identifier:
            raise ValueError('term_identifier is required')
        if not reference_no:
            raise ValueError('reference_no is required')

        # Dynamic vote-head allocation: no hardcoded vote-head names.
        # 1) Prefer CAPITATION vote heads configured by admins.
        # 2) Fallback to all vote heads.
        # 3) If still empty, create one dynamically based on the term.
        target_vote_heads = VoteHead.query.filter_by(fund_type='CAPITATION').all()
        if not target_vote_heads:
            target_vote_heads = VoteHead.query.all()

        if not target_vote_heads:
            dynamic_vote_head = VoteHeadRepository.create({
                'code': f"VH-{str(uuid.uuid4())[:8].upper()}",
                'name': str(term_identifier).strip(),
                'fund_type': 'CAPITATION',
                'annual_budget': 0,
                'current_balance': 0,
            })
            dynamic_vote_head_obj = VoteHead.query.filter_by(code=dynamic_vote_head['code']).first()
            target_vote_heads = [dynamic_vote_head_obj]

        # Weighted allocation by annual_budget when present; otherwise equal split.
        total_budget = sum(Decimal(str(vh.annual_budget or 0)) for vh in target_vote_heads)

        credits = []
        if total_budget > 0:
            for vote_head in target_vote_heads:
                ratio = Decimal(str(vote_head.annual_budget or 0)) / total_budget
                credits.append((vote_head, (amount_dec * ratio).quantize(Decimal('0.01'))))
        else:
            equal_share = (amount_dec / Decimal(len(target_vote_heads))).quantize(Decimal('0.01'))
            credits = [(vote_head, equal_share) for vote_head in target_vote_heads]

        credited_total = sum(amount for _, amount in credits)
        rounding_difference = amount_dec - credited_total
        if credits and rounding_difference != 0:
            first_vote_head, first_amount = credits[0]
            credits[0] = (first_vote_head, first_amount + rounding_difference)

        settlement_vote_head_name = target_vote_heads[0].name

        transaction_data = {
            'reference_no': reference_no,
            'student_id': None,
            'recorded_by': SystemRepository.get_or_create_system_user(),
            'source_vote_head': settlement_vote_head_name,
            'destination_vote_head': settlement_vote_head_name,
            'amount': amount_dec,
            'transaction_type': 'INCOME',
            'payment_method': 'BANK',
            'description': f"FDSE Govt Capitation Disbursement - {term_identifier}"
        }

        ledger_lines = [
            {
                'account_name': f"Income_VoteHead_{settlement_vote_head_name}",
                'amount': amount_dec,
                'entry_type': 'DEBIT'
            }
        ]

        for vote_head, allocated_amount in credits:
            ledger_lines.append({
                'account_name': f"Income_VoteHead_{vote_head.name}",
                'amount': allocated_amount,
                'entry_type': 'CREDIT'
            })

        transaction = FinanceRepository.create_transaction_with_ledger(
            transaction_data,
            ledger_lines
        )
        return transaction.to_dict()
