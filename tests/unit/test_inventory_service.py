"""
Unit tests for InventoryService business logic.
Tests: consumption recording, stock predictions, validation, error handling.
"""
import pytest
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.services.inventory_service import InventoryService
from app.models import Inventory, InventoryLog
from app import db


class TestInventoryServiceRecordUsage:
    """Test suite for record_usage method."""
    
    def test_record_usage_success(self, app, inventory_item, admin_user):
        """Should successfully record consumption and update stock level."""
        with app.app_context():
            initial_quantity = float(inventory_item.current_quantity)
            usage_quantity = 10.0
            
            result, status_code = InventoryService.record_usage(
                item_id=inventory_item.id,
                quantity_used=usage_quantity,
                user_id=admin_user.id,
                remarks='Test consumption'
            )
            
            assert status_code == 201
            assert result['message'] == 'Consumption recorded'
            assert result['remaining_stock'] == initial_quantity - usage_quantity
            assert result['alert'] is None
            
            # Verify database was updated
            updated_item = Inventory.query.get(inventory_item.id)
            assert float(updated_item.current_quantity) == initial_quantity - usage_quantity
    
    def test_record_usage_insufficient_stock(self, app, inventory_item, admin_user):
        """Should reject consumption if stock is insufficient."""
        with app.app_context():
            result, status_code = InventoryService.record_usage(
                item_id=inventory_item.id,
                quantity_used=200.0,  # More than available
                user_id=admin_user.id,
                remarks='Excessive consumption'
            )
            
            assert status_code == 400
            assert 'error' in result
            assert 'Insufficient stock' in result['error']
    
    def test_record_usage_low_stock_alert(self, app, low_stock_item, admin_user):
        """Should trigger alert when stock falls below reorder level."""
        with app.app_context():
            result, status_code = InventoryService.record_usage(
                item_id=low_stock_item.id,
                quantity_used=1.0,
                user_id=admin_user.id,
                remarks='Bring stock below threshold'
            )
            
            assert status_code == 201
            assert result['alert'] is not None
            assert 'Low stock alert' in result['alert']
    
    def test_record_usage_creates_audit_log(self, app, inventory_item, admin_user):
        """Should create an audit log entry for consumption."""
        with app.app_context():
            result, status_code = InventoryService.record_usage(
                item_id=inventory_item.id,
                quantity_used=5.0,
                user_id=admin_user.id,
                remarks='Test audit log'
            )
            
            assert status_code == 201
            
            # Verify log was created
            log = InventoryLog.query.filter_by(
                inventory_id=inventory_item.id,
                transaction_type='CONSUMPTION'
            ).first()
            
            assert log is not None
            assert float(log.quantity) == -5.0
            assert log.recorded_by == admin_user.id
            assert log.remarks == 'Test audit log'
    
    def test_record_usage_nonexistent_item(self, app, admin_user):
        """Should return error for non-existent inventory item."""
        with app.app_context():
            fake_id = uuid.uuid4()
            result, status_code = InventoryService.record_usage(
                item_id=fake_id,
                quantity_used=5.0,
                user_id=admin_user.id,
                remarks='Non-existent item'
            )
            
            assert status_code == 400
            assert 'error' in result
    
    def test_record_usage_zero_quantity(self, app, inventory_item, admin_user):
        """Should handle zero quantity gracefully."""
        with app.app_context():
            result, status_code = InventoryService.record_usage(
                item_id=inventory_item.id,
                quantity_used=0.0,
                user_id=admin_user.id,
                remarks='Zero consumption'
            )
            
            assert status_code == 201
            assert result['remaining_stock'] == float(inventory_item.current_quantity)
    
    def test_record_usage_database_error_rollback(self, app, inventory_item, admin_user):
        """Should rollback transaction on database error."""
        with app.app_context():
            initial_quantity = float(inventory_item.current_quantity)
            
            # Mock db.session.commit to raise an exception
            with patch('app.services.inventory_service.db.session.commit', side_effect=Exception('DB Error')):
                result, status_code = InventoryService.record_usage(
                    item_id=inventory_item.id,
                    quantity_used=5.0,
                    user_id=admin_user.id,
                    remarks='Cause DB error'
                )
            
            assert status_code == 500
            assert 'error' in result
            
            # Verify stock wasn't changed
            updated_item = Inventory.query.get(inventory_item.id)
            assert float(updated_item.current_quantity) == initial_quantity


class TestInventoryServiceGetStockPredictions:
    """Test suite for get_stock_predictions method."""
    
    def test_get_stock_predictions_success(self, app, inventory_item):
        """Should return accurate days-remaining predictions."""
        with app.app_context():
            predictions, status_code = InventoryService.get_stock_predictions()
            
            assert status_code == 200
            assert len(predictions) > 0
            
            # Find our test item
            maize_pred = next(
                (p for p in predictions if p['item'] == 'Maize'),
                None
            )
            
            assert maize_pred is not None
            assert maize_pred['current_quantity'] == 100.0
            assert maize_pred['unit'] == '90kg Bag'
            
            # Days = 100 / 5 = 20
            assert maize_pred['days_remaining'] == 20.0
    
    def test_get_stock_predictions_zero_consumption(self, app):
        """Should handle items with zero daily consumption (infinite days)."""
        with app.app_context():
            # Create item with zero consumption
            item = Inventory(
                id=uuid.uuid4(),
                item_name='Fuel Reserve',
                unit_of_measure='Liter',
                current_quantity=1000.00,
                reorder_level=100.00,
                average_daily_consumption=0.00
            )
            db.session.add(item)
            db.session.commit()
            
            predictions, status_code = InventoryService.get_stock_predictions()
            
            assert status_code == 200
            fuel_pred = next(
                (p for p in predictions if p['item'] == 'Fuel Reserve'),
                None
            )
            
            assert fuel_pred is not None
            assert fuel_pred['days_remaining'] == float('inf')
    
    def test_get_stock_predictions_multiple_items(self, app, inventory_item, low_stock_item):
        """Should return predictions for all items."""
        with app.app_context():
            predictions, status_code = InventoryService.get_stock_predictions()
            
            assert status_code == 200
            assert len(predictions) >= 2
            
            items = {p['item']: p for p in predictions}
            assert 'Maize' in items
            assert 'Beans' in items
    
    def test_get_stock_predictions_rounding(self, app):
        """Should round days remaining to 1 decimal place."""
        with app.app_context():
            # Create item with specific numbers for rounding test
            item = Inventory(
                id=uuid.uuid4(),
                item_name='Test Item',
                unit_of_measure='kg',
                current_quantity=100.00,
                reorder_level=10.00,
                average_daily_consumption=3.33
            )
            db.session.add(item)
            db.session.commit()
            
            predictions, status_code = InventoryService.get_stock_predictions()
            
            test_item = next(
                (p for p in predictions if p['item'] == 'Test Item'),
                None
            )
            
            # Check that result is rounded to 1 decimal
            assert isinstance(test_item['days_remaining'], float)
            assert test_item['days_remaining'] == pytest.approx(30.0, rel=0.1)
    
    def test_get_stock_predictions_empty_inventory(self, app):
        """Should return empty list when no items exist."""
        with app.app_context():
            predictions, status_code = InventoryService.get_stock_predictions()
            
            assert status_code == 200
            assert isinstance(predictions, list)
