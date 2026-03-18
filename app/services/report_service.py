from app.repositories.transaction_repository import TransactionRepository
from app.models.finance import VoteHead

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

      current_balance = TransactionRepository.get_vote_head_balance(vh.id)

      summary_data.append({
        "vote_head_name": vh.name,
        "code": vh.code,
        "allocation_budget": float(vh.annual_budget),
        "actual_balance": float(current_balance)
      })

      total_school_liquidity += current_balance

      # 3. Return the formatted report
      return{
        "report_title": "MoE Vote Head Liquidity Summary",
        "total_school_liquidity": float(total_school_liquidity),
        "breakdown": summary_data
      }, 200