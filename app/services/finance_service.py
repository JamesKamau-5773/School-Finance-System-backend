from datetime import datetime, timezone
from decimal import Decimal
import uuid
from app import db
from app.models.finance import Transaction
from app.models.auth import User
from app.repositories.finance_repository import FinanceRepository
from app.repositories.system_repository import SystemRepository
from app.utils.validators import is_valid_uuid


class FinanceService:
    """Handles business logic for financial transactions (income/expense recording).
    
    Single Responsibility: Create and persist Transaction records to database.
    Does NOT handle user/vote head lookup (delegated to SystemRepository).
    """

    FDSE_CAPITATION_RATIOS = {
        'Tuition': Decimal('0.45'),
        'RMI': Decimal('0.20'),
        'Activity': Decimal('0.10'),
        'Admin': Decimal('0.15'),
        'SMASSE': Decimal('0.05'),
        'Medical': Decimal('0.05')
    }

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

        # Create and persist transaction
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

        transaction_data = {
            'reference_no': reference_no,
            'student_id': None,
            'recorded_by': SystemRepository.get_or_create_system_user(),
            'source_vote_head': 'Cash In Bank Capitation',
            'destination_vote_head': 'Tuition',
            'amount': amount_dec,
            'transaction_type': 'INCOME',
            'payment_method': 'BANK',
            'description': f"FDSE Govt Capitation Disbursement - {term_identifier}"
        }

        ledger_lines = [
            {
                'account_name': 'Cash In Bank Capitation',
                'amount': amount_dec,
                'entry_type': 'DEBIT'
            }
        ]

        for vote_head, percentage in FinanceService.FDSE_CAPITATION_RATIOS.items():
            allocated_amount = round(amount_dec * percentage, 2)
            ledger_lines.append({
                'account_name': f"Income_VoteHead_{vote_head}",
                'amount': allocated_amount,
                'entry_type': 'CREDIT'
            })

        total_credits = sum(
            line['amount'] for line in ledger_lines
            if line['entry_type'] == 'CREDIT'
        )
        if total_credits != amount_dec:
            difference = amount_dec - total_credits
            ledger_lines[1]['amount'] += difference

        transaction = FinanceRepository.create_transaction_with_ledger(
            transaction_data,
            ledger_lines
        )
        return transaction.to_dict()
