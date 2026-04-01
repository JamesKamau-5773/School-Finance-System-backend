"""
Transaction Response Formatter - Converts domain objects to validated API responses.
Responsibility: Transform Transaction objects into JSON with correct type labels.
"""
from typing import List, Dict, Any
from app.models.finance import Transaction
from app.validators.response_validators import TransactionResponseSchema


class TransactionResponseFormatter:
    """
    Single Responsibility: Format Transaction objects into validated response DTOs.
    Ensures type labels are always INCOME/EXPENSE (never Income/Expense).
    """

    @staticmethod
    def format_single_transaction(tx: Transaction) -> Dict[str, Any]:
        """
        Format a single Transaction into response DTO.
        Ensures correct UPPERCASE type labels.
        """
        if not tx:
            raise ValueError("Transaction object cannot be None")
        
        # Ensure transaction_type is uppercase (INCOME, EXPENSE, or ADJUSTMENT)
        transaction_type = str(tx.transaction_type).upper() if tx.transaction_type else 'UNKNOWN'
        
        if transaction_type not in ('INCOME', 'EXPENSE', 'ADJUSTMENT'):
            raise ValueError(f'Invalid transaction type in database: {tx.transaction_type}')
        
        formatted = {
            "id": str(tx.id),
            "date": tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "reference_no": tx.reference_number,
            "reference_number": tx.reference_number,
            "description": tx.description,
            "account_name": tx.vote_head.name if tx.vote_head else None,
            "type": transaction_type,  # INCOME or EXPENSE (uppercase)
            "transaction_type": transaction_type,
            "amount": float(tx.amount) if tx.amount is not None else 0.0
        }
        
        # Validate before returning
        return TransactionResponseSchema.validate_single_transaction(formatted)

    @staticmethod
    def format_transaction_list(transactions: List[Transaction]) -> List[Dict[str, Any]]:
        """
        Format a list of Transaction objects into validated response list.
        """
        if not isinstance(transactions, list):
            raise ValueError("Transactions must be a list")
        
        formatted_list = []
        for tx in transactions:
            formatted_list.append(TransactionResponseFormatter.format_single_transaction(tx))
        
        # Validate entire list
        return TransactionResponseSchema.validate_transaction_list(formatted_list)

    @staticmethod
    def format_api_response(transactions: List[Transaction], count: int = None) -> Dict[str, Any]:
        """
        Format complete API response with proper structure.
        """
        formatted_transactions = TransactionResponseFormatter.format_transaction_list(transactions)
        
        return {
            "status": "success",
            "data": formatted_transactions,
            "count": count or len(formatted_transactions)
        }
