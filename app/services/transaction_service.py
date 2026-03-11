from app.repositories.transaction_repository import TransactionRepository


class TransactionService:
    @staticmethod
    def get_all_transactions():
        # We will add MoE budget validation and calculation logic here later
        transactions = TransactionRepository.get_all()
        # Returning a placeholder list for now
        return [t.id for t in transactions]
