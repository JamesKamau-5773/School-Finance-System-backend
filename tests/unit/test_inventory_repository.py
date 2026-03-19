"""
Unit tests for InventoryRepository data access layer.
Tests: CRUD operations, stock updates, log creation, query filters.
"""
import pytest
import uuid
from datetime import datetime, timezone
from app.repositories.inventory_repository import InventoryRepository
from app.models import Inventory, InventoryLog
from app import db


class TestInventoryRepositoryGetOperations:
    """Test suite for get_all_items and get_item_by_id."""
    
    def test_get_all_items_returns_list(self, app, inventory_item):
        """Should return a list of all inventory items."""
        with app.app_context():
            items = InventoryRepository.get_all_items()
            
            assert isinstance(items, list)
            assert len(items) > 0
    
    def test_get_all_items_empty(self, app):
        """Should return empty list when no items exist."""
        with app.app_context():
            items = InventoryRepository.get_all_items()
            assert items == []
    
    def test_get_item_by_id_success(self, app, inventory_item):
        """Should retrieve item by ID."""
        with app.app_context():
            result = InventoryRepository.get_item_by_id(inventory_item.id)
            
            assert result is not None
            assert result.id == inventory_item.id
            assert result.item_name == 'Maize'
            assert float(result.current_quantity) == 100.0
    
    def test_get_item_by_id_not_found(self, app):
        """Should return None for non-existent item."""
        with app.app_context():
            fake_id = uuid.uuid4()
            result = InventoryRepository.get_item_by_id(fake_id)
            
            assert result is None
    
    def test_get_item_by_id_type(self, app, inventory_item):
        """Should return Inventory model instance."""
        with app.app_context():
            result = InventoryRepository.get_item_by_id(inventory_item.id)
            
            assert isinstance(result, Inventory)


class TestInventoryRepositoryStockUpdates:
    """Test suite for update_stock_level."""
    
    def test_update_stock_level_positive(self, app, inventory_item):
        """Should increase stock level for positive quantity."""
        with app.app_context():
            initial = float(inventory_item.current_quantity)
            
            updated = InventoryRepository.update_stock_level(inventory_item.id, 25.0)
            
            assert updated is not None
            assert float(updated.current_quantity) == initial + 25.0
            
            # Verify persistence
            db.session.commit()
            item = InventoryRepository.get_item_by_id(inventory_item.id)
            assert float(item.current_quantity) == initial + 25.0
    
    def test_update_stock_level_negative(self, app, inventory_item):
        """Should decrease stock level for negative quantity."""
        with app.app_context():
            initial = float(inventory_item.current_quantity)
            
            updated = InventoryRepository.update_stock_level(inventory_item.id, -10.0)
            
            assert updated is not None
            assert float(updated.current_quantity) == initial - 10.0
    
    def test_update_stock_level_zero(self, app, inventory_item):
        """Should handle zero quantity update."""
        with app.app_context():
            initial = float(inventory_item.current_quantity)
            
            updated = InventoryRepository.update_stock_level(inventory_item.id, 0)
            
            assert float(updated.current_quantity) == initial
    
    def test_update_stock_level_nonexistent_item(self, app):
        """Should return None for non-existent item."""
        with app.app_context():
            fake_id = uuid.uuid4()
            result = InventoryRepository.update_stock_level(fake_id, 10.0)
            
            assert result is None
    
    def test_update_stock_level_decimal_precision(self, app, inventory_item):
        """Should maintain decimal precision for stock quantities."""
        with app.app_context():
            InventoryRepository.update_stock_level(inventory_item.id, 12.75)
            
            item = InventoryRepository.get_item_by_id(inventory_item.id)
            # Should be 100 + 12.75 = 112.75
            assert float(item.current_quantity) == 112.75


class TestInventoryRepositoryLogs:
    """Test suite for add_log."""
    
    def test_add_log_success(self, app, inventory_item, admin_user):
        """Should create a new log entry."""
        with app.app_context():
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': -5.00,
                'transaction_type': 'CONSUMPTION',
                'recorded_by': admin_user.id,
                'remarks': 'Daily use'
            }
            
            log = InventoryRepository.add_log(log_data)
            
            assert log is not None
            assert isinstance(log, InventoryLog)
            assert log.inventory_id == inventory_item.id
            assert float(log.quantity) == -5.0
            assert log.transaction_type == 'CONSUMPTION'
    
    def test_add_log_stock_in(self, app, inventory_item, admin_user):
        """Should create log entry for stock-in transaction."""
        with app.app_context():
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': 50.00,
                'transaction_type': 'STOCK_IN',
                'recorded_by': admin_user.id,
                'remarks': 'Delivery from supplier'
            }
            
            log = InventoryRepository.add_log(log_data)
            
            assert log.transaction_type == 'STOCK_IN'
            assert float(log.quantity) == 50.0
    
    def test_add_log_adjustment(self, app, inventory_item, admin_user):
        """Should create log entry for inventory adjustment."""
        with app.app_context():
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': -3.00,
                'transaction_type': 'ADJUSTMENT',
                'recorded_by': admin_user.id,
                'remarks': 'Stock level correction'
            }
            
            log = InventoryRepository.add_log(log_data)
            
            assert log.transaction_type == 'ADJUSTMENT'
    
    def test_add_log_without_user(self, app, inventory_item):
        """Should allow log entry without user reference."""
        with app.app_context():
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': 10.00,
                'transaction_type': 'STOCK_IN',
                'recorded_by': None,
                'remarks': 'System-generated log'
            }
            
            log = InventoryRepository.add_log(log_data)
            
            assert log.recorded_by is None
    
    def test_add_log_without_remarks(self, app, inventory_item, admin_user):
        """Should allow log entry without remarks."""
        with app.app_context():
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': 5.00,
                'transaction_type': 'CONSUMPTION',
                'recorded_by': admin_user.id,
                'remarks': None
            }
            
            log = InventoryRepository.add_log(log_data)
            
            assert log.remarks is None
    
    def test_add_log_timestamp(self, app, inventory_item, admin_user):
        """Should automatically set created_at timestamp."""
        with app.app_context():
            before = datetime.now(timezone.utc)
            
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': 5.00,
                'transaction_type': 'CONSUMPTION',
                'recorded_by': admin_user.id,
            }
            
            log = InventoryRepository.add_log(log_data)
            after = datetime.now(timezone.utc)
            
            assert log.created_at is not None
            assert before <= log.created_at <= after
    
    def test_add_log_with_empty_remarks(self, app, inventory_item, admin_user):
        """Should handle empty string remarks."""
        with app.app_context():
            log_data = {
                'inventory_id': inventory_item.id,
                'quantity': 2.50,
                'transaction_type': 'CONSUMPTION',
                'recorded_by': admin_user.id,
                'remarks': ''
            }
            
            log = InventoryRepository.add_log(log_data)
            
            assert log.remarks == ''
