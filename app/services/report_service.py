from app.repositories.transaction_repository import TransactionRepository
from app.models.finance import VoteHead
from sqlalchemy import func
from app import db


class ReportService:
    @staticmethod
    def generate_vote_head_summary():

        # 1. Fetch all MoE budget categories
        vote_heads = VoteHead.query.all()

        if not vote_heads:
            return {"error": "No Vote Heads Configured in the system"}, 404

        summary_data = []
        total_school_liquidity = 0

        # 2. Calculate the exact balance for each bucket using the ledger
        for vh in vote_heads:

            current_balance = TransactionRepository.get_vote_head_balance(
                vh.id)

            summary_data.append({
                "vote_head_name": vh.name,
                "code": vh.code,
                "allocation_budget": float(vh.annual_budget),
                "actual_balance": float(current_balance)
            })

            total_school_liquidity += current_balance

            # 3. Return the formatted report
            return {
                "report_title": "MoE Vote Head Liquidity Summary",
                "total_school_liquidity": float(total_school_liquidity),
                "breakdown": summary_data
            }, 200

    @staticmethod
    def generate_trial_balance():
        """
        Generates a professional Trial Balance by summarizing 
        debits and credits for every Vote Head.
        """
        vote_heads = VoteHead.query.all()
        trial_balance_rows = []
        total_debits = 0
        total_credits = 0

        for vh in vote_heads:
            # Fetching raw sums from the Repository
            summary = db.session.query(
                func.sum(db.case((Transaction.transaction_type ==
                         'DEBIT', Transaction.amount), else_=0)).label('debit'),
                func.sum(db.case((Transaction.transaction_type ==
                         'CREDIT', Transaction.amount), else_=0)).label('credit')
            ).filter(Transaction.vote_head_id == vh.id).first()

            debit = float(summary.debit or 0)
            credit = float(summary.credit or 0)

            trial_balance_rows.append({
                "account_name": vh.name,
                "code": vh.code,
                "debit": debit,
                "credit": credit
            })

            total_debits += debit
            total_credits += credit

        # The mathematical proof of Double-Entry integrity:
        # Total Debits must equal Total Credits
        is_balanced = round(total_debits, 2) == round(total_credits, 2)

        return {
            "report_name": "Trial Balance",
            "is_balanced": is_balanced,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "accounts": trial_balance_rows
        }, 200
