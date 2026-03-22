from app import db
from app.models.fee_structure import FeeStructure
from app.models.student import Student
from app.models.student_ledger import StudentLedger
from app.models.finance import Transaction, LedgerEntry, VoteHead
from app.models.auth import User

class FeeRepository:
    @staticmethod
    def create_fee_structure(data):
        """Saves a new BOM-approved levy to the database."""
        try:
            new_fee = FeeStructure(**data)
            db.session.add(new_fee)
            db.session.commit()
            return new_fee
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_all_active_fees(academic_year=None, term=None):
        """Fetches active levies, optionally filtered by year and term."""
        try:
            query = FeeStructure.query.filter_by(is_active=True)
            
            if academic_year:
                query = query.filter_by(academic_year=academic_year)
            if term:
                query = query.filter_by(term=term)
                
            # Order by newest first
            return query.order_by(FeeStructure.created_at.desc()).all()
        except Exception as e:
            raise e

    @staticmethod
    def get_fee_structure_by_id(fee_structure_id):
        return FeeStructure.query.get(fee_structure_id)

    @staticmethod
    def get_active_students_for_cohort(target_cohort):
        if target_cohort == "All Students":
            return Student.query.filter_by(is_active=True).all()
        return Student.query.filter_by(grade_level=target_cohort, is_active=True).all()

    @staticmethod
    def invoice_exists(student_id, fee_structure_id):
        return StudentLedger.query.filter_by(
            student_id=student_id,
            fee_structure_id=fee_structure_id,
            entry_type='DEBIT'
        ).first() is not None

    @staticmethod
    def add_student_invoice(student_id, fee_structure_id, amount, description, reference_no):
        invoice = StudentLedger(
            student_id=student_id,
            fee_structure_id=fee_structure_id,
            entry_type='DEBIT',
            amount=amount,
            description=description,
            reference_no=reference_no
        )
        db.session.add(invoice)
        return invoice

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.filter_by(id=user_id).first()

    @staticmethod
    def get_user_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_vote_head_by_code(code):
        return VoteHead.query.filter_by(code=code).first()

    @staticmethod
    def create_vote_head(code, name, fund_type='FEES', annual_budget=0, current_balance=0):
        vote_head = VoteHead(
            code=code,
            name=name,
            fund_type=fund_type,
            annual_budget=annual_budget,
            current_balance=current_balance
        )
        db.session.add(vote_head)
        return vote_head

    @staticmethod
    def add_student_credit(student_id, amount, payment_method, reference_no):
        entry = StudentLedger(
            student_id=student_id,
            entry_type='CREDIT',
            amount=amount,
            description=f"Term Fee Payment via {payment_method}",
            reference_no=reference_no
        )
        db.session.add(entry)
        return entry

    @staticmethod
    def add_transaction(vote_head_id, recorded_by, student_id, transaction_type, amount, reference_number, description, transaction_date):
        transaction = Transaction(
            vote_head_id=vote_head_id,
            recorded_by=recorded_by,
            student_id=student_id,
            transaction_type=transaction_type,
            amount=amount,
            reference_number=reference_number,
            description=description,
            transaction_date=transaction_date
        )
        db.session.add(transaction)
        return transaction

    @staticmethod
    def add_ledger_entry(transaction_id, vote_head_id, student_id, entry_type, amount, payment_method, reference_no, description, created_by):
        ledger_entry = LedgerEntry(
            transaction_id=transaction_id,
            vote_head_id=vote_head_id,
            student_id=student_id,
            entry_type=entry_type,
            amount=amount,
            payment_method=payment_method,
            reference_no=reference_no,
            description=description,
            created_by=created_by
        )
        db.session.add(ledger_entry)
        return ledger_entry

    @staticmethod
    def flush():
        db.session.flush()

    @staticmethod
    def commit():
        db.session.commit()

    @staticmethod
    def rollback():
        db.session.rollback()