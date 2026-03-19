"""
Tests for Inventory and InventoryLog database models.
Tests: model creation, relationships, constraints, default values.
"""
import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from app.models import Inventory, InventoryLog
from app import db


class TestInventoryModel:
    """Test suite for Inventory model."""
    
    def test_inventory_creation(self, app):
        """Should successfully create an Inventory instance."""
        with app.app_context():
            item = Inventory(
                item_name='Rice',
                unit_of_measure='50kg Bag',
                current_quantity=50.0,
                reorder_level=10.0,
                average_daily_consumption=2.5
            )
            
            db.session.add(item)
            db.session.commit()
            
            assert item.id is not None
            assert item.item_name == 'Rice'
            assert float(item.current_quantity) == 50.0
    
    def test_inventory_uuid_auto_generation(self, app):
        """Should auto-generate UUID for primary key."""
        with app.app_context():
            item = Inventory(
                item_name='Sugar',
                unit_of_measure='kg',
                current_quantity=100.0,
                reorder_level=20.0,
                average_daily_consumption=5.0
            )
            
            # ID should be None before commit
            assert item.id is None
            
            db.session.add(item)
            db.session.commit()
            
            # ID should be generated after commit
            assert item.id is not None
            assert isinstance(item.id, uuid.UUID)
    
    def test_inventory_default_timestamps(self, app):
        """Should set updated_at timestamp automatically."""
        with app.app_context():
            before = datetime.now(timezone.utc)
            
            item = Inventory(
                item_name='Oil',
                unit_of_measure='Liter',
                current_quantity=500.0,
                reorder_level=100.0,
                average_daily_consumption=10.0
            )
            
            db.session.add(item)
            db.session.commit()
            
            after = datetime.now(timezone.utc)
            
            assert item.updated_at is not None
            assert before <= item.updated_at <= after
    
    def test_inventory_required_fields(self, app):
        """Should enforce required fields."""
        with app.app_context():
            # Missing item_name
            item = Inventory(
                unit_of_measure='kg',
                current_quantity=100.0,
                reorder_level=20.0
            )
            
            db.session.add(item)
            
            with pytest.raises(Exception):  # SQLAlchemy constraint error
                db.session.commit()
    
    def test_inventory_decimal_precision(self, app):
        """Should maintain precision for decimal quantities."""
        with app.app_context():
            item = Inventory(
                item_name='Flour',
                unit_of_measure='kg',
                current_quantity=Decimal('123.45'),
                reorder_level=Decimal('25.50'),
                average_daily_consumption=Decimal('3.75')
            )
            
            db.session.add(item)
            db.session.commit()
            
            retrieved = Inventory.query.get(item.id)
            assert float(retrieved.current_quantity) == 123.45
            assert float(retrieved.reorder_level) == 25.50
            assert float(retrieved.average_daily_consumption) == 3.75
    
    def test_inventory_default_quantities(self, app):
        """Should use default values for optional quantity fields."""
        with app.app_context():
            item = Inventory(
                item_name='Salt',
                unit_of_measure='kg',
                reorder_level=5.0
            )
            
            db.session.add(item)
            db.session.commit()
            
            retrieved = Inventory.query.get(item.id)
            assert float(retrieved.current_quantity) == 0.0
            assert float(retrieved.average_daily_consumption) == 0.0
    
    def test_inventory_relationship_with_logs(self, app, inventory_item):
        """Should maintain relationship to InventoryLog entries."""
        with app.app_context():
            item = Inventory.query.get(inventory_item.id)
            
            # Logs relationship should exist
            assert hasattr(item, 'logs')
            assert isinstance(item.logs, list)
    
    def test_inventory_repr(self, app):
        """Should have meaningful string representation."""
        with app.app_context():
            item = Inventory(
                item_name='Maize',
                unit_of_measure='90kg Bag',
                current_quantity=50.0,
                reorder_level=10.0
            )
            
            repr_str = repr(item)
            assert 'Inventory' in repr_str
            assert 'Maize' in repr_str


class TestInventoryLogModel:
    """Test suite for InventoryLog model."""
    
    def test_inventory_log_creation(self, app, inventory_item, admin_user):
        """Should successfully create an InventoryLog instance."""
        with app.app_context():
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=-10.0,
                transaction_type='CONSUMPTION',
                recorded_by=admin_user.id,
                remarks='Daily consumption'
            )
            
            db.session.add(log)
            db.session.commit()
            
            assert log.id is not None
            assert float(log.quantity) == -10.0
            assert log.transaction_type == 'CONSUMPTION'
    
    def test_inventory_log_uuid_generation(self, app, inventory_item, admin_user):
        """Should auto-generate UUID for log entries."""
        with app.app_context():
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=5.0,
                transaction_type='STOCK_IN',
                recorded_by=admin_user.id
            )
            
            db.session.add(log)
            db.session.commit()
            
            assert isinstance(log.id, uuid.UUID)
    
    def test_inventory_log_timestamp(self, app, inventory_item, admin_user):
        """Should auto-set created_at timestamp."""
        with app.app_context():
            before = datetime.now(timezone.utc)
            
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=5.0,
                transaction_type='STOCK_IN',
                recorded_by=admin_user.id
            )
            
            db.session.add(log)
            db.session.commit()
            
            after = datetime.now(timezone.utc)
            
            assert log.created_at is not None
            assert before <= log.created_at <= after
    
    def test_inventory_log_transaction_types(self, app, inventory_item, admin_user):
        """Should support all valid transaction types."""
        with app.app_context():
            transaction_types = ['STOCK_IN', 'CONSUMPTION', 'ADJUSTMENT']
            
            for trans_type in transaction_types:
                log = InventoryLog(
                    inventory_id=inventory_item.id,
                    quantity=1.0,
                    transaction_type=trans_type,
                    recorded_by=admin_user.id
                )
                
                db.session.add(log)
                db.session.commit()
                
                assert log.transaction_type == trans_type
    
    def test_inventory_log_foreign_key_constraint(self, app, admin_user):
        """Should enforce foreign key constraint with inventory."""
        with app.app_context():
            fake_inventory_id = uuid.uuid4()
            
            log = InventoryLog(
                inventory_id=fake_inventory_id,
                quantity=5.0,
                transaction_type='STOCK_IN',
                recorded_by=admin_user.id
            )
            
            db.session.add(log)
            
            # Should fail on commit due to foreign key
            with pytest.raises(Exception):
                db.session.commit()
    
    def test_inventory_log_cascade_delete(self, app, inventory_item, admin_user):
        """Should delete logs when inventory item is deleted."""
        with app.app_context():
            # Create a log
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=10.0,
                transaction_type='CONSUMPTION',
                recorded_by=admin_user.id
            )
            db.session.add(log)
            db.session.commit()
            
            log_id = log.id
            
            # Delete the inventory item
            db.session.delete(inventory_item)
            db.session.commit()
            
            # Log should be deleted (cascade)
            deleted_log = InventoryLog.query.get(log_id)
            assert deleted_log is None
    
    def test_inventory_log_optional_fields(self, app, inventory_item):
        """Should allow optional user and remarks fields."""
        with app.app_context():
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=5.0,
                transaction_type='ADJUSTMENT',
                recorded_by=None,
                remarks=None
            )
            
            db.session.add(log)
            db.session.commit()
            
            retrieved = InventoryLog.query.get(log.id)
            assert retrieved.recorded_by is None
            assert retrieved.remarks is None
    
    def test_inventory_log_repr(self, app, inventory_item, admin_user):
        """Should have meaningful string representation."""
        with app.app_context():
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=-5.0,
                transaction_type='CONSUMPTION',
                recorded_by=admin_user.id
            )
            
            repr_str = repr(log)
            assert 'InventoryLog' in repr_str
            assert 'CONSUMPTION' in repr_str
    
    def test_inventory_log_decimal_precision(self, app, inventory_item, admin_user):
        """Should maintain precision for decimal quantities."""
        with app.app_context():
            log = InventoryLog(
                inventory_id=inventory_item.id,
                quantity=Decimal('-12.75'),
                transaction_type='CONSUMPTION',
                recorded_by=admin_user.id
            )
            
            db.session.add(log)
            db.session.commit()
            
            retrieved = InventoryLog.query.get(log.id)
            assert float(retrieved.quantity) == -12.75
