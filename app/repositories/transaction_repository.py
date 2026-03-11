from app.models.finance import Transaction
from app import db

class TransactionRepository:
    @staticmethod
    def get_all():
        # Retrieves all transactions from the PostgreSQL database
        return Transaction.query.all()
    
    # We will add create, update, and delete queries here later