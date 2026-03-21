from sqlalchemy import func
from app import db
from app.models.finance import Transaction, LedgerEntry, VoteHead
from app.utils.validators import is_valid_uuid
from datetime import datetime, timezone


class FinanceRepository:
    @staticmethod
    def _resolve_vote_head(identifier):
        if identifier is None:
            return None

        identifier_str = str(identifier)
        if is_valid_uuid(identifier_str):
            return VoteHead.query.filter_by(id=identifier_str).first()

        return (
            VoteHead.query.filter_by(code=identifier_str).first()
            or VoteHead.query.filter_by(name=identifier_str).first()
        )

    @staticmethod
    def create_transaction_with_ledger(transaction_data, ledger_lines):
        try:
            source_vote_head = FinanceRepository._resolve_vote_head(transaction_data.get('source_vote_head'))
            destination_vote_head = FinanceRepository._resolve_vote_head(transaction_data.get('destination_vote_head'))

            if not source_vote_head:
                raise ValueError('source_vote_head is invalid or not found')
            if not destination_vote_head:
                raise ValueError('destination_vote_head is invalid or not found')

            transaction = Transaction(
                vote_head_id=destination_vote_head.id,
                recorded_by=transaction_data.get('recorded_by'),
                student_id=transaction_data.get('student_id'),
                transaction_type=transaction_data.get('transaction_type', 'ADJUSTMENT'),
                amount=transaction_data.get('amount'),
                reference_number=transaction_data.get('reference_no'),
                description=transaction_data.get('description'),
                transaction_date=datetime.now(timezone.utc)
            )
            db.session.add(transaction)
            db.session.flush()

            for line in ledger_lines:
                account_name = str(line.get('account_name', ''))
                vote_head_identifier = account_name.replace('Income_VoteHead_', '', 1)
                vote_head = FinanceRepository._resolve_vote_head(vote_head_identifier)

                if not vote_head:
                    raise ValueError(f'Unable to resolve vote head for ledger line: {account_name}')

                ledger_entry = LedgerEntry(
                    transaction_id=transaction.id,
                    vote_head_id=vote_head.id,
                    student_id=transaction_data.get('student_id'),
                    entry_type=line.get('entry_type'),
                    amount=line.get('amount'),
                    payment_method=transaction_data.get('payment_method'),
                    reference_no=transaction_data.get('reference_no'),
                    description=transaction_data.get('description'),
                    created_by=transaction_data.get('recorded_by')
                )
                db.session.add(ledger_entry)

            db.session.commit()
            return transaction
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_dashboard_summary():
        """
        Calculates aggregate financial totals directly in PostgreSQL.
        """
        try:
            total_income = (
                db.session.query(func.sum(Transaction.amount))
                .filter(Transaction.transaction_type == 'INCOME')
                .scalar()
                or 0
            )

            total_expense = (
                db.session.query(func.sum(Transaction.amount))
                .filter(Transaction.transaction_type == 'EXPENSE')
                .scalar()
                or 0
            )

            return {
                "total_collections": float(total_income),
                "total_expenses": float(total_expense),
                "net_position": float(total_income - total_expense)
            }
        except Exception as e:
            raise e
