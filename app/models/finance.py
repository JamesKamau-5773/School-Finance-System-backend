import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app import db

class VoteHead(db.Model):
    __tablename__ = 'vote_heads'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = db.Column(db.String(20), unique=True, nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    fund_type = db.Column(db.String(20), nullable=False) # 'CAPITATION', 'FEES', 'PROJECT'
    annual_budget = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    current_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    
    transactions = db.relationship('Transaction', backref='vote_head', lazy=True)

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(150), nullable=False)
    kra_pin = db.Column(db.String(20), nullable=True) 
    phone_number = db.Column(db.String(20), nullable=True)
    
    transactions = db.relationship('Transaction', backref='supplier', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vote_head_id = db.Column(UUID(as_uuid=True), db.ForeignKey('vote_heads.id'), nullable=False)
    recorded_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    supplier_id = db.Column(UUID(as_uuid=True), db.ForeignKey('suppliers.id'), nullable=True)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=True)
    
    transaction_type = db.Column(db.String(10), nullable=False) # 'INCOME' or 'EXPENSE'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    reference_number = db.Column(db.String(100), nullable=True) 
    description = db.Column(db.Text, nullable=False)
    
    transaction_date = db.Column(db.DateTime, nullable=False)
    sync_status = db.Column(db.String(20), default='SYNCED') 
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    ledger_entries = db.relationship('LedgerEntry', backref='transaction', lazy=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "vote_head_id": str(self.vote_head_id) if self.vote_head_id else None,
            "recorded_by": str(self.recorded_by) if self.recorded_by else None,
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "student_id": str(self.student_id) if self.student_id else None,
            "transaction_type": self.transaction_type,
            "type": self.transaction_type,  # Alias for frontend compatibility
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "reference_number": self.reference_number,
            "description": self.description,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "sync_status": self.sync_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LedgerEntry(db.Model):
    __tablename__ = 'ledger_entries'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = db.Column(UUID(as_uuid=True), db.ForeignKey('transactions.id'), nullable=False)
    vote_head_id = db.Column(UUID(as_uuid=True), db.ForeignKey('vote_heads.id'), nullable=False)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=True)

    entry_type = db.Column(db.String(10), nullable=False)  # 'DEBIT' or 'CREDIT'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    reference_no = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)