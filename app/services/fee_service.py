import uuid
from datetime import datetime, timezone

from app import db
from app.repositories.fee_repository import FeeRepository
from app.utils.validators import is_valid_uuid


class FeeService:
    @staticmethod
    def create_levy(name, amount, academic_year, term, target_cohort, created_by):
        """
        Prepares the payload for a new fee structure.
        """
        data = {
            "name": name,
            "amount": amount,
            "academic_year": academic_year,
            "term": term,
            "target_cohort": target_cohort,
            "created_by": created_by
        }

        fee = FeeRepository.create_fee_structure(data)
        return fee.to_dict()

    @staticmethod
    def get_levies(academic_year=None, term=None):
        """
        Retrieves and formats active fee structures for the frontend.
        """
        fees = FeeRepository.get_all_active_fees(academic_year, term)
        return [fee.to_dict() for fee in fees]

    @staticmethod
    def issue_cohort_invoices(fee_structure_id):
        """
        Locates the target cohort and generates an invoice for every active student.
        Includes safeguards against double-billing.
        """
        try:
            # 1. Retrieve the Levy Rules
            fee = FeeRepository.get_fee_structure_by_id(fee_structure_id)
            if not fee:
                raise ValueError("Fee structure not found.")

            # 2. Identify the Target Cohort
            students = FeeRepository.get_active_students_for_cohort(fee.target_cohort)

            if not students:
                return {"count": 0, "message": f"No active students found in cohort: {fee.target_cohort}"}

            invoices_created = 0

            # 3. Generate Invoices with Double-Billing Protection
            for student in students:
                # Check if this exact student has already been billed for this exact fee structure
                if not FeeRepository.invoice_exists(student.id, fee.id):
                    # Generate a unique invoice reference
                    inv_ref = f"INV-{fee.term.replace(' ', '')}-{fee.academic_year}-{student.admission_number}-{uuid.uuid4().hex[:6].upper()}"

                    FeeRepository.add_student_invoice(
                        student_id=student.id,
                        fee_structure_id=fee.id,
                        amount=fee.amount,
                        description=f"{fee.term} {fee.name} ({fee.academic_year})",
                        reference_no=inv_ref
                    )
                    invoices_created += 1

            FeeRepository.commit()

            return {
                "count": invoices_created,
                "total_value": float(fee.amount * invoices_created),
                "message": f"Successfully issued {invoices_created} new invoices."
            }

        except Exception as e:
            FeeRepository.rollback()
            raise e

    @staticmethod
    def process_student_payment(student_id, amount, payment_method, reference_no, received_by):
        """
        Processes a lump-sum term fee payment.
        1. Credits the student's personal ledger (lowers debt).
        2. Debits the school's main cashbook account and credits fee income.
        """
        if not student_id:
            raise ValueError("student_id is required")
        if amount is None:
            raise ValueError("amount is required")
        if not payment_method:
            raise ValueError("payment_method is required")
        if not reference_no:
            raise ValueError("reference_no is required")

        amount_value = float(amount)
        if amount_value <= 0:
            raise ValueError("amount must be greater than 0")

        valid_student_id = student_id if is_valid_uuid(student_id) else None
        if not valid_student_id:
            raise ValueError("student_id must be a valid UUID")

        if received_by and is_valid_uuid(received_by):
            received_by_user = FeeRepository.get_user_by_id(received_by)
            if not received_by_user:
                raise ValueError("received_by user not found")
            recorded_by = received_by_user.id
        else:
            system_user = FeeRepository.get_user_by_username('system')
            if not system_user:
                raise ValueError("received_by must be a valid user UUID")
            recorded_by = system_user.id

        cash_vote_head = FeeRepository.get_vote_head_by_code('BANK-MAIN')
        if not cash_vote_head:
            cash_vote_head = FeeRepository.create_vote_head(
                code='BANK-MAIN',
                name='Asset Bank Main Account',
                fund_type='FEES',
                annual_budget=0,
                current_balance=0
            )

        revenue_vote_head = FeeRepository.get_vote_head_by_code('FEE-DEFAULT')
        if not revenue_vote_head:
            revenue_vote_head = FeeRepository.create_vote_head(
                code='FEE-DEFAULT',
                name='Default Fee Collection',
                fund_type='FEES',
                annual_budget=0,
                current_balance=0
            )

        try:
            with db.session.begin():
                FeeRepository.flush()

                student_credit = FeeRepository.add_student_credit(
                    student_id=valid_student_id,
                    amount=amount_value,
                    payment_method=payment_method,
                    reference_no=reference_no
                )

                school_tx = FeeRepository.add_transaction(
                    vote_head_id=revenue_vote_head.id,
                    recorded_by=recorded_by,
                    student_id=valid_student_id,
                    transaction_type='INCOME',
                    amount=amount_value,
                    reference_number=reference_no,
                    description=f"Fee Collection - Student ID: {valid_student_id}",
                    transaction_date=datetime.now(timezone.utc)
                )
                FeeRepository.flush()

                FeeRepository.add_ledger_entry(
                    transaction_id=school_tx.id,
                    vote_head_id=cash_vote_head.id,
                    student_id=valid_student_id,
                    entry_type='DEBIT',
                    amount=amount_value,
                    payment_method=payment_method,
                    reference_no=reference_no,
                    description=f"Cashbook inflow - {payment_method}",
                    created_by=recorded_by
                )

                FeeRepository.add_ledger_entry(
                    transaction_id=school_tx.id,
                    vote_head_id=revenue_vote_head.id,
                    student_id=valid_student_id,
                    entry_type='CREDIT',
                    amount=amount_value,
                    payment_method=payment_method,
                    reference_no=reference_no,
                    description="Fee collection revenue",
                    created_by=recorded_by
                )

            return student_credit.to_dict()

        except Exception as e:
            FeeRepository.rollback()
            raise e
