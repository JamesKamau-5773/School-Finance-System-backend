"""
Response schema validation for API contracts.
Responsibility: Ensure API responses conform to expected schema before sending to client.
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime


class ResponseValidationError(Exception):
    """Raised when response schema validation fails."""
    def __init__(self, message: str, expected: str, actual: str):
        self.message = message
        self.expected = expected
        self.actual = actual
        super().__init__(f"{message} | Expected: {expected}, Got: {actual}")


class TransactionResponseSchema:
    """
    Single Responsibility: Validate transaction response structure and field values.
    Ensures type labels are correct (INCOME/EXPENSE not Income/Expense).
    """

    REQUIRED_FIELDS = {'id', 'date', 'reference_no', 'description', 'type', 'amount', 'transaction_type'}
    VALID_TYPES = {'INCOME', 'EXPENSE', 'ADJUSTMENT'}

    @staticmethod
    def validate_single_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single transaction object."""
        
        # Check required fields exist
        missing_fields = TransactionResponseSchema.REQUIRED_FIELDS - set(tx.keys())
        if missing_fields:
            raise ResponseValidationError(
                f'Missing required fields',
                f'{TransactionResponseSchema.REQUIRED_FIELDS}',
                f'{set(tx.keys())}'
            )
        
        # Validate type field (must be uppercase INCOME/EXPENSE)
        tx_type = tx.get('type')
        if tx_type not in TransactionResponseSchema.VALID_TYPES:
            raise ResponseValidationError(
                f'Invalid transaction type value',
                f'{TransactionResponseSchema.VALID_TYPES}',
                f'{tx_type}'
            )
        
        # Ensure transaction_type matches type
        if tx.get('transaction_type') != tx_type:
            raise ResponseValidationError(
                f'type and transaction_type mismatch',
                f'Both should be {tx_type}',
                f'type={tx_type}, transaction_type={tx.get("transaction_type")}'
            )
        
        # Validate amount is numeric
        try:
            amount = float(tx.get('amount', 0))
            if amount < 0:
                raise ResponseValidationError(
                    'Amount cannot be negative',
                    'amount >= 0',
                    f'amount={amount}'
                )
        except (TypeError, ValueError):
            raise ResponseValidationError(
                'Amount must be numeric',
                'float',
                f'{type(tx.get("amount"))}'
            )
        
        # Validate date format
        date_str = tx.get('date')
        if not isinstance(date_str, str) or not date_str:
            raise ResponseValidationError(
                'Date must be non-empty string',
                'str (YYYY-MM-DD HH:MM:SS)',
                f'{type(date_str)}'
            )
        
        return tx

    @staticmethod
    def validate_transaction_list(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate a list of transaction responses."""
        if not isinstance(transactions, list):
            raise ResponseValidationError(
                'Transactions must be a list',
                'list',
                f'{type(transactions)}'
            )
        
        validated = []
        for idx, tx in enumerate(transactions):
            try:
                validated.append(TransactionResponseSchema.validate_single_transaction(tx))
            except ResponseValidationError as e:
                raise ResponseValidationError(
                    f'Transaction at index {idx}: {e.message}',
                    e.expected,
                    e.actual
                )
        
        return validated


class PaymentResponseSchema:
    """
    Single Responsibility: Validate payment response structure.
    """

    REQUIRED_FIELDS = {'status', 'message', 'data'}

    @staticmethod
    def validate_payment_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payment API response."""
        
        missing_fields = PaymentResponseSchema.REQUIRED_FIELDS - set(response.keys())
        if missing_fields:
            raise ResponseValidationError(
                'Missing required fields in payment response',
                f'{PaymentResponseSchema.REQUIRED_FIELDS}',
                f'{set(response.keys())}'
            )
        
        # Validate status
        if response.get('status') not in ('success', 'error'):
            raise ResponseValidationError(
                'Invalid status value',
                '"success" or "error"',
                f'{response.get("status")}'
            )
        
        # Validate message is string
        if not isinstance(response.get('message'), str):
            raise ResponseValidationError(
                'Message must be string',
                'str',
                f'{type(response.get("message"))}'
            )
        
        return response
