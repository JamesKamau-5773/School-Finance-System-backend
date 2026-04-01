"""
Transaction Query Builder - Separates filter application logic from DB operations.
Responsibility: Build SQLAlchemy queries from validated filter parameters.
"""
from sqlalchemy import or_, func
from app import db
from app.models.finance import Transaction, LedgerEntry, VoteHead
from typing import Optional, Dict, Any, List


class TransactionQueryBuilder:
    """
    Single Responsibility: Build Transaction queries with filters applied sequentially.
    Decouples query building from validation and response formatting.
    """

    def __init__(self):
        self.query = None

    def build_base_query(self):
        """Initialize the base query with necessary joins."""
        self.query = db.session.query(Transaction).outerjoin(
            LedgerEntry, Transaction.id == LedgerEntry.transaction_id
        ).outerjoin(
            VoteHead, LedgerEntry.vote_head_id == VoteHead.id
        )
        return self

    def apply_omni_search(self, search_term: Optional[str]):
        """Apply broad omni-search filter."""
        if not search_term:
            return self
        
        search_upper = search_term.upper().strip()
        search_pattern = f"%{search_term}%"
        
        # Keywords that match transaction types
        is_income_search = search_upper in ('INCOME', 'CREDIT', 'INV', 'PAYMENT')
        is_expense_search = search_upper in ('EXPENSE', 'DEBIT', 'EXP')
        
        conditions = [
            Transaction.description.ilike(search_pattern),
            Transaction.reference_number.ilike(search_pattern),
            VoteHead.name.ilike(search_pattern),
            VoteHead.code.ilike(search_pattern),
            LedgerEntry.reference_no.ilike(search_pattern),
            LedgerEntry.description.ilike(search_pattern)
        ]
        
        if is_income_search:
            conditions.append(Transaction.transaction_type == 'INCOME')
        if is_expense_search:
            conditions.append(Transaction.transaction_type == 'EXPENSE')
        
        self.query = self.query.filter(or_(*conditions))
        return self

    def apply_type_filter(self, tx_type: Optional[str]):
        """Apply transaction type filter."""
        if not tx_type:
            return self
        
        # tx_type should already be normalized by TransactionFilterValidator
        self.query = self.query.filter(Transaction.transaction_type == tx_type)
        return self

    def apply_date_filter(self, date_obj: Optional[Any]):
        """Apply exact date filter."""
        if not date_obj:
            return self
        
        self.query = self.query.filter(func.date(Transaction.created_at) == date_obj)
        return self

    def apply_category_filter(self, category: Optional[str]):
        """Apply category/vote head filter."""
        if not category:
            return self
        
        category_pattern = f"%{category}%"
        self.query = self.query.filter(
            or_(
                VoteHead.name.ilike(category_pattern),
                VoteHead.code.ilike(category_pattern),
                LedgerEntry.description.ilike(category_pattern)
            )
        )
        return self

    def apply_method_filter(self, method: Optional[str]):
        """Apply payment method filter."""
        if not method:
            return self
        
        method_pattern = f"%{method}%"
        self.query = self.query.filter(
            or_(
                LedgerEntry.payment_method.ilike(method_pattern),
                Transaction.description.ilike(method_pattern),
                LedgerEntry.description.ilike(method_pattern)
            )
        )
        return self

    def apply_amount_filter(self, min_amount: Optional[Any]):
        """Apply minimum amount filter."""
        if min_amount is None:
            return self
        
        self.query = self.query.filter(Transaction.amount >= float(min_amount))
        return self

    def apply_all_filters(self, filters: Dict[str, Any]):
        """Apply all filters from a normalized filter dictionary."""
        self.apply_omni_search(filters.get('search'))
        self.apply_type_filter(filters.get('type'))
        self.apply_date_filter(filters.get('date'))
        self.apply_category_filter(filters.get('category'))
        self.apply_method_filter(filters.get('method'))
        self.apply_amount_filter(filters.get('minAmount'))
        return self

    def order_by_newest(self):
        """Order results by most recent first."""
        self.query = self.query.distinct().order_by(Transaction.created_at.desc())
        return self

    def execute(self) -> List[Transaction]:
        """Execute the built query and return Transaction objects."""
        if self.query is None:
            raise RuntimeError("Query not built. Call build_base_query() first.")
        
        return self.query.all()
