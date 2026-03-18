from app.repositories.vote_head_repository import VoteHeadRepository
from app.repositories.transaction_repository import TransactionRepository


class FeeCollectionService:
    @staticmethod
    def process_fee_payment(student_id, total_amount, collector_id):
        # 1. Fetch Vote Heads
        vote_heads = VoteHeadRepository.get_all_active()

        # 2. Logic: Splitting the amount 
        
        split_amount = total_amount / len(vote_heads)

        for vh in vote_heads:
            # 3. Update the budget bucket
            VoteHeadRepository.update_balance(vh.id, split_amount)

            # 4. Record the specific ledger entry
            TransactionRepository.create_ledger_entry(
                student_id=student_id,
                vote_head_id=vh.id,
                amount=split_amount,
                user_id=collector_id
            )

        return {"status": "success", "amount_processed": total_amount}
