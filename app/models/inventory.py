import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app import db


class Inventory(db.Model):
    """
    Table to track current stock levels of items (food, fuel, etc.).
    """
    __tablename__ = 'inventory'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_name = db.Column(db.String(100), nullable=False)
    unit_of_measure = db.Column(db.String(20), nullable=False)
    current_quantity = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    reorder_level = db.Column(db.Numeric(12, 2), nullable=False)
    average_daily_consumption = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    logs = db.relationship('InventoryLog', backref='inventory', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Inventory {self.item_name} ({self.current_quantity} {self.unit_of_measure})>'


class InventoryLog(db.Model):
    """
    Audit log table tracking every stock transaction.
    """
    __tablename__ = 'inventory_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = db.Column(UUID(as_uuid=True), db.ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    recorded_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<InventoryLog {self.transaction_type} {self.quantity} on {self.created_at}>'
