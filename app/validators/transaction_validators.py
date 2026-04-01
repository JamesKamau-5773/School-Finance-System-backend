"""
Input validation for financial transactions.
Responsibility: Validate and normalize filter/payment inputs BEFORE database operations.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
import re


class ValidationError(ValueError):
    """Custom exception for input validation failures with clear client messages."""
    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        self.message = f"Invalid {field}: {reason}"
        super().__init__(self.message)


class TransactionFilterValidator:
    """
    Single Responsibility: Validate and normalize transaction filter inputs.
    """

    VALID_TRANSACTION_TYPES = {'INCOME', 'EXPENSE', 'INCOME', 'CREDIT', 'DEBIT'}
    VALID_ENTRY_TYPES = {'CREDIT', 'DEBIT'}
    MIN_AMOUNT = Decimal('0.01')
    MAX_AMOUNT = Decimal('999999999.99')

    @staticmethod
    def validate_search_term(search: Optional[str]) -> Optional[str]:
        """Validate and normalize omni-search term."""
        if search is None:
            return None
        
        search = search.strip()
        if not search:
            return None
        
        if len(search) > 255:
            raise ValidationError('search', search, 'Search term exceeds 255 characters')
        
        # Allow alphanumeric, spaces, hyphens, underscores, @, ., /
        if not re.match(r'^[a-zA-Z0-9\s\-_@./]+$', search):
            raise ValidationError('search', search, 'Contains invalid characters')
        
        return search

    @staticmethod
    def validate_transaction_type(tx_type: Optional[str]) -> Optional[str]:
        """Validate and normalize transaction type filter."""
        if tx_type is None:
            return None
        
        normalized = tx_type.strip().upper()
        
        # Map common aliases to standard types
        type_mapping = {
            'INCOME': 'INCOME',
            'CREDIT': 'INCOME',
            'INV': 'INCOME',
            'PAYMENT': 'INCOME',
            'EXPENSE': 'EXPENSE',
            'DEBIT': 'EXPENSE',
            'EXP': 'EXPENSE',
        }
        
        if normalized not in type_mapping:
            raise ValidationError('type', tx_type, 
                f'Must be one of: {", ".join(sorted(set(type_mapping.values())))}')
        
        return type_mapping[normalized]

    @staticmethod
    def validate_date(date_str: Optional[str]) -> Optional[datetime]:
        """Validate and parse date filter (YYYY-MM-DD format)."""
        if date_str is None:
            return None
        
        try:
            parsed = datetime.strptime(date_str.strip(), '%Y-%m-%d')
            return parsed
        except ValueError:
            raise ValidationError('date', date_str, 'Expected format YYYY-MM-DD')

    @staticmethod
    def validate_min_amount(amount_str: Optional[str]) -> Optional[Decimal]:
        """Validate and parse minimum amount filter."""
        if amount_str is None:
            return None
        
        try:
            amount = Decimal(str(amount_str).strip())
        except:
            raise ValidationError('minAmount', amount_str, 'Must be a valid number')
        
        if amount < 0:
            raise ValidationError('minAmount', amount_str, 'Must be non-negative')
        
        if amount > TransactionFilterValidator.MAX_AMOUNT:
            raise ValidationError('minAmount', amount_str, f'Exceeds maximum {TransactionFilterValidator.MAX_AMOUNT}')
        
        return amount

    @staticmethod
    def validate_category(category: Optional[str]) -> Optional[str]:
        """Validate category filter."""
        if category is None:
            return None
        
        category = category.strip()
        if not category:
            return None
        
        if len(category) > 100:
            raise ValidationError('category', category, 'Category exceeds 100 characters')
        
        if not re.match(r'^[a-zA-Z0-9\s\-_()]+$', category):
            raise ValidationError('category', category, 'Contains invalid characters')
        
        return category

    @staticmethod
    def validate_method(method: Optional[str]) -> Optional[str]:
        """Validate payment method filter."""
        if method is None:
            return None
        
        method = method.strip()
        if not method:
            return None
        
        if len(method) > 50:
            raise ValidationError('method', method, 'Payment method exceeds 50 characters')
        
        if not re.match(r'^[a-zA-Z0-9\s\-_()]+$', method):
            raise ValidationError('method', method, 'Contains invalid characters')
        
        return method

    @staticmethod
    def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all filters at once.
        Returns normalized filter dictionary.
        """
        validated = {}
        
        try:
            if 'search' in filters:
                validated['search'] = TransactionFilterValidator.validate_search_term(filters['search'])
            
            if 'type' in filters:
                validated['type'] = TransactionFilterValidator.validate_transaction_type(filters['type'])
            
            if 'date' in filters:
                validated['date'] = TransactionFilterValidator.validate_date(filters['date'])
            
            if 'minAmount' in filters:
                validated['minAmount'] = TransactionFilterValidator.validate_min_amount(filters['minAmount'])
            
            if 'category' in filters:
                validated['category'] = TransactionFilterValidator.validate_category(filters['category'])
            
            if 'method' in filters:
                validated['method'] = TransactionFilterValidator.validate_method(filters['method'])
            
            # Remove None values
            return {k: v for k, v in validated.items() if v is not None}
        
        except ValidationError:
            raise


class PaymentValidator:
    """
    Single Responsibility: Validate fee payment inputs.
    """

    @staticmethod
    def validate_reference_no(reference_no: Optional[str]) -> str:
        """Validate payment reference number."""
        if not reference_no:
            raise ValidationError('reference_no', reference_no, 'Reference number is required')
        
        reference_no = str(reference_no).strip()
        if len(reference_no) > 100:
            raise ValidationError('reference_no', reference_no, 'Exceeds 100 characters')
        
        if not re.match(r'^[a-zA-Z0-9\-_.]+$', reference_no):
            raise ValidationError('reference_no', reference_no, 'Invalid characters (alphanumeric, dash, underscore, dot only)')
        
        return reference_no

    @staticmethod
    def validate_amount(amount: Optional[float]) -> Decimal:
        """Validate payment amount."""
        if amount is None:
            raise ValidationError('amount', amount, 'Amount is required')
        
        try:
            amount_dec = Decimal(str(amount))
        except:
            raise ValidationError('amount', amount, 'Must be a valid decimal number')
        
        if amount_dec <= 0:
            raise ValidationError('amount', amount, 'Must be greater than 0')
        
        if amount_dec > Decimal('999999.99'):
            raise ValidationError('amount', amount, 'Exceeds maximum 999999.99')
        
        return amount_dec

    @staticmethod
    def validate_payment_method(method: Optional[str]) -> str:
        """Validate payment method."""
        if not method:
            raise ValidationError('payment_method', method, 'Payment method is required')
        
        method = str(method).strip()
        if len(method) > 50:
            raise ValidationError('payment_method', method, 'Exceeds 50 characters')
        
        return method
