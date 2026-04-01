import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db


class InventoryItem(db.Model):
    """
    Core item profile for the school store.
    Tracks physical stock levels and reorder thresholds.
    """
    __tablename__ = 'inventory_items'

    # --- Identity & Categorization ---
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_code = db.Column(db.String(50), unique=True,
                          nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    unit_of_measure = db.Column(db.String(20), nullable=False)

    # --- Stock Metrics ---
    # Using Numeric for exact precision (crucial for partial units like KGs)
    current_stock = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    reorder_level = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    avg_daily_consumption = db.Column(db.Numeric(12, 2), default=0.00)

    # --- State & Auditing ---
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(
        timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # --- Relationships ---
    transactions = db.relationship(
        'StockTransaction', backref='item_profile', lazy=True, cascade='all, delete-orphan')
    store_transactions = db.relationship(
        'StoreTransaction', backref='item_profile', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_code": self.item_code,
            "name": self.name,
            "category": self.category,
            "unit_of_measure": self.unit_of_measure,
            # Pass raw floats to the frontend. Let React format the commas.
            "reorder_level": float(self.reorder_level) if self.reorder_level is not None else 0.0,
            "current_stock": float(self.current_stock) if self.current_stock is not None else 0.0,
            "is_active": self.is_active
        }


class StockTransaction(db.Model):
    """
    Audit ledger tracking every physical movement in or out of the store.
    """
    __tablename__ = 'stock_transactions'

    # --- Primary & Foreign Keys ---
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'inventory_items.id', ondelete='CASCADE'), nullable=False)
    recorded_by = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)

    # --- Transaction Details ---
    transaction_type = db.Column(
        db.String(20), nullable=False)  # 'IN' or 'OUT'
    quantity = db.Column(db.Numeric(12, 2), nullable=False)

    # --- Audit Trail ---
    party_name = db.Column(db.String(100), nullable=False)
    reference_no = db.Column(db.String(50), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(
        timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "transaction_type": self.transaction_type,
            "quantity": float(self.quantity) if self.quantity is not None else 0.0,
            "party_name": self.party_name,
            "reference_no": self.reference_no,
            "remarks": self.remarks,
            # Standard ISO format is easiest for JavaScript Date() objects to parse
            "date": self.created_at.isoformat(),
            "recorded_by": str(self.recorded_by) if self.recorded_by else None
        }


class StoreTransaction(db.Model):
    """Append-only inventory ledger optimized for filtered transaction queries."""
    __tablename__ = 'store_transactions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = db.Column(UUID(as_uuid=True), db.ForeignKey(
        'inventory_items.id', ondelete='CASCADE'), nullable=False, index=True)
    recorded_by = db.Column(
        UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True, index=True)

    action = db.Column(db.String(20), nullable=False, index=True)  # received | issued
    quantity = db.Column(db.Integer, nullable=False)  # Integer-only by design
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(
        timezone.utc), nullable=False, index=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "item_id": str(self.item_id),
            "recorded_by": str(self.recorded_by) if self.recorded_by else None,
            "action": self.action,
            "quantity": self.quantity,
            "created_at": self.created_at.isoformat(),
            "category": self.item_profile.category if self.item_profile else None,
            "item_name": self.item_profile.name if self.item_profile else None,
            "item_code": self.item_profile.item_code if self.item_profile else None
        }
