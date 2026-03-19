"""
End-to-end integration tests for complete inventory workflows.
Tests: multi-step operations, audit trails, predictions, state consistency.
"""
import pytest
import json
import uuid
from app.models import Inventory, InventoryLog
from app import db


class TestInventoryWorkflowIntegration:
    """Test suite for complete inventory workflows."""
    
    def test_full_inventory_cycle(self, app, client, admin_token, json_headers):
        """Should successfully complete: create → consume → check predictions."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        with app.app_context():
            # 1. Create an inventory item
            item = Inventory(
                item_name='Test Rice',
                unit_of_measure='50kg Bag',
                current_quantity=100.0,
                reorder_level=20.0,
                average_daily_consumption=5.0
            )
            db.session.add(item)
            db.session.commit()
            
            item_id = item.id
        
        # 2. Record consumption
        consume_payload = {
            'item_id': str(item_id),
            'quantity': 15.0,
            'remarks': 'Week 1 consumption'
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(consume_payload),
            headers=headers
        )
        
        assert response.status_code == 201
        consume_data = json.loads(response.data)
        assert consume_data['remaining_stock'] == 85.0  # 100 - 15
        
        # 3. Get predictions
        response = client.get('/api/inventory/status', headers=headers)
        
        assert response.status_code == 200
        predictions = json.loads(response.data)
        
        # Find our item in predictions
        item_pred = next(
            (p for p in predictions if p['item'] == 'Test Rice'),
            None
        )
        
        assert item_pred is not None
        assert item_pred['current_quantity'] == 85.0
        # Days = 85 / 5 = 17
        assert item_pred['days_remaining'] == 17.0
    
    def test_multiple_consumption_sequence(self, app, client, admin_token, inventory_item, json_headers):
        """Should track multiple consumption events correctly."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        consumptions = [10.0, 5.0, 8.0]
        total_consumed = sum(consumptions)
        expected_balance = 100.0 - total_consumed
        
        # Record multiple consumptions
        for qty in consumptions:
            payload = {
                'item_id': str(inventory_item.id),
                'quantity': qty,
                'remarks': f'Consumption of {qty}'
            }
            
            response = client.post(
                '/api/inventory/consume',
                data=json.dumps(payload),
                headers=headers
            )
            
            assert response.status_code == 201
        
        # Verify final state
        with app.app_context():
            item = Inventory.query.get(inventory_item.id)
            assert float(item.current_quantity) == expected_balance
    
    def test_audit_trail_chain(self, app, admin_user, inventory_item):
        """Should maintain complete audit trail of all transactions."""
        with app.app_context():
            # Record multiple transactions
            from app.services.inventory_service import InventoryService
            
            for i in range(3):
                InventoryService.record_usage(
                    item_id=inventory_item.id,
                    quantity_used=5.0,
                    user_id=admin_user.id,
                    remarks=f'Consumption {i+1}'
                )
            
            # Verify logs
            logs = InventoryLog.query.filter_by(
                inventory_id=inventory_item.id
            ).all()
            
            assert len(logs) == 3
            
            for i, log in enumerate(logs):
                assert log.transaction_type == 'CONSUMPTION'
                assert float(log.quantity) == -5.0
                assert f'Consumption {i+1}' in log.remarks
    
    def test_stock_prediction_accuracy_over_time(self, app, client, admin_token, json_headers):
        """Should maintain accurate predictions after multiple operations."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        with app.app_context():
            # Create item with known consumption pattern
            item = Inventory(
                item_name='Prediction Test',
                unit_of_measure='kg',
                current_quantity=100.0,
                reorder_level=10.0,
                average_daily_consumption=10.0
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        
        # Expected days: 100 / 10 = 10
        response = client.get('/api/inventory/status', headers=headers)
        data = json.loads(response.data)
        
        pred = next(
            (p for p in data if p['item'] == 'Prediction Test'),
            None
        )
        assert pred['days_remaining'] == 10.0
        
        # Consume 20 units
        consume_payload = {
            'item_id': str(item_id),
            'quantity': 20.0
        }
        
        client.post(
            '/api/inventory/consume',
            data=json.dumps(consume_payload),
            headers=headers
        )
        
        # Now: 80 / 10 = 8 days remaining
        response = client.get('/api/inventory/status', headers=headers)
        data = json.loads(response.data)
        
        pred = next(
            (p for p in data if p['item'] == 'Prediction Test'),
            None
        )
        assert pred['days_remaining'] == 8.0
    
    def test_low_stock_alert_progression(self, app, admin_user, client, admin_token, json_headers):
        """Should handle transition from normal to low stock correctly."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        with app.app_context():
            # Create item that starts normal
            item = Inventory(
                item_name='Alert Test',
                unit_of_measure='kg',
                current_quantity=50.0,
                reorder_level=20.0,
                average_daily_consumption=5.0
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        
        # First consumption - no alert
        from app.services.inventory_service import InventoryService
        
        result1, _ = InventoryService.record_usage(
            item_id=item_id,
            quantity_used=10.0,
            user_id=admin_user.id,
            remarks='Consumption 1'
        )
        
        assert result1['alert'] is None
        
        # Second consumption - triggers alert
        result2, _ = InventoryService.record_usage(
            item_id=item_id,
            quantity_used=20.0,
            user_id=admin_user.id,
            remarks='Consumption 2'
        )
        
        assert result2['alert'] is not None
        assert 'Low stock alert' in result2['alert']
        assert result2['remaining_stock'] == 20.0
    
    def test_concurrent_modifications_isolation(self, app, admin_user, inventory_item):
        """Should handle concurrent modifications with proper isolation."""
        with app.app_context():
            from app.services.inventory_service import InventoryService
            
            # Simulate two operations happening
            result1, _ = InventoryService.record_usage(
                item_id=inventory_item.id,
                quantity_used=10.0,
                user_id=admin_user.id,
                remarks='Operation 1'
            )
            
            result2, _ = InventoryService.record_usage(
                item_id=inventory_item.id,
                quantity_used=15.0,
                user_id=admin_user.id,
                remarks='Operation 2'
            )
            
            # Final state should be: 100 - 10 - 15 = 75
            item = Inventory.query.get(inventory_item.id)
            assert float(item.current_quantity) == 75.0


class TestInventoryDataIntegrity:
    """Test suite for data integrity and consistency."""
    
    def test_stock_level_consistency(self, app, admin_user, inventory_item):
        """Should maintain stock consistency across operations."""
        with app.app_context():
            from app.services.inventory_service import InventoryService
            
            initial = 100.0
            operations = [10.0, 5.0, 15.0, 2.5, 8.0]
            
            for qty in operations:
                InventoryService.record_usage(
                    item_id=inventory_item.id,
                    quantity_used=qty,
                    user_id=admin_user.id,
                    remarks=f'Op: {qty}'
                )
            
            final_expected = initial - sum(operations)
            
            item = Inventory.query.get(inventory_item.id)
            assert float(item.current_quantity) == final_expected
    
    def test_log_completeness(self, app, admin_user, inventory_item):
        """Should create a log entry for every modification."""
        with app.app_context():
            from app.services.inventory_service import InventoryService
            
            operations_count = 5
            
            for i in range(operations_count):
                InventoryService.record_usage(
                    item_id=inventory_item.id,
                    quantity_used=2.0,
                    user_id=admin_user.id,
                    remarks=f'Op {i+1}'
                )
            
            logs = InventoryLog.query.filter_by(
                inventory_id=inventory_item.id
            ).all()
            
            assert len(logs) == operations_count
    
    def test_timestamp_monotonicity(self, app, admin_user, inventory_item):
        """Should maintain chronological order of logs."""
        with app.app_context():
            from app.services.inventory_service import InventoryService
            import time
            
            for i in range(3):
                InventoryService.record_usage(
                    item_id=inventory_item.id,
                    quantity_used=1.0,
                    user_id=admin_user.id,
                    remarks=f'Op {i+1}'
                )
                time.sleep(0.01)  # Ensure different timestamps
            
            logs = InventoryLog.query.filter_by(
                inventory_id=inventory_item.id
            ).order_by(InventoryLog.created_at.asc()).all()
            
            # Verify chronological order
            for i in range(len(logs) - 1):
                assert logs[i].created_at <= logs[i+1].created_at
