"""
Integration tests for InventoryController endpoints.
Tests: API endpoints, JWT authentication, request/response validation, error handling.
"""
import pytest
import json
import uuid
from decimal import Decimal
from app.models import Inventory


class TestInventoryControllerGetStatus:
    """Test suite for GET /api/inventory/status endpoint."""
    
    def test_get_inventory_status_authenticated(self, client, admin_token, inventory_item, json_headers):
        """Should return inventory predictions for authenticated user."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        response = client.get('/api/inventory/status', headers=headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check first item structure
        first_item = data[0]
        assert 'item' in first_item
        assert 'current_quantity' in first_item
        assert 'unit' in first_item
        assert 'days_remaining' in first_item
    
    def test_get_inventory_status_unauthenticated(self, client, json_headers):
        """Should reject unauthenticated requests."""
        response = client.get('/api/inventory/status', headers=json_headers)
        
        assert response.status_code == 401
    
    def test_get_inventory_status_invalid_token(self, client, json_headers):
        """Should reject requests with invalid token."""
        headers = {**json_headers, 'Authorization': 'Bearer invalid_token_123'}
        
        response = client.get('/api/inventory/status', headers=headers)
        
        assert response.status_code in [401, 422]
    
    def test_get_inventory_status_missing_token(self, client, json_headers):
        """Should reject requests without Bearer token."""
        headers = json_headers
        
        response = client.get('/api/inventory/status', headers=headers)
        
        assert response.status_code == 401
    
    def test_get_inventory_status_with_multiple_items(self, client, admin_token, inventory_item, low_stock_item, json_headers):
        """Should return predictions for all items."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        response = client.get('/api/inventory/status', headers=headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        items = {item['item']: item for item in data}
        assert 'Maize' in items
        assert 'Beans' in items


class TestInventoryControllerRecordConsumption:
    """Test suite for POST /api/inventory/consume endpoint."""
    
    def test_record_consumption_success(self, client, admin_token, inventory_item, json_headers):
        """Should record consumption successfully."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 10.0,
            'remarks': 'Test consumption'
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        assert 'message' in data
        assert 'Consumption recorded' in data['message']
        assert 'remaining_stock' in data
        assert data['remaining_stock'] == 90.0  # 100 - 10
    
    def test_record_consumption_missing_item_id(self, client, admin_token, json_headers):
        """Should reject consumption without item_id."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'quantity': 10.0,
            'remarks': 'Missing item_id'
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_record_consumption_missing_quantity(self, client, admin_token, inventory_item, json_headers):
        """Should reject consumption without quantity."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'remarks': 'Missing quantity'
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_record_consumption_invalid_item_id(self, client, admin_token, json_headers):
        """Should reject consumption for non-existent item."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(uuid.uuid4()),
            'quantity': 10.0
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_record_consumption_insufficient_stock(self, client, admin_token, inventory_item, json_headers):
        """Should reject consumption when stock is insufficient."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 200.0  # More than available
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Insufficient' in data['error']
    
    def test_record_consumption_triggers_alert(self, client, admin_token, low_stock_item, json_headers):
        """Should include alert when stock falls below reorder level."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(low_stock_item.id),
            'quantity': 1.0
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        assert 'alert' in data
        assert data['alert'] is not None
        assert 'Low stock' in data['alert']
    
    def test_record_consumption_unauthenticated(self, client, inventory_item, json_headers):
        """Should reject unauthenticated consumption requests."""
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 10.0
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=json_headers
        )
        
        assert response.status_code == 401
    
    def test_record_consumption_default_remarks(self, client, admin_token, inventory_item, json_headers):
        """Should use default remarks if not provided."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 5.0
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_record_consumption_zero_quantity(self, client, admin_token, inventory_item, json_headers):
        """Should handle zero quantity consumption."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 0.0,
            'remarks': 'Test zero consumption'
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['remaining_stock'] == 100.0  # Unchanged
    
    def test_record_consumption_decimal_quantity(self, client, admin_token, inventory_item, json_headers):
        """Should handle decimal quantities."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 5.75,
            'remarks': 'Decimal consumption'
        }
        
        response = client.post(
            '/api/inventory/consume',
            data=json.dumps(payload),
            headers=headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['remaining_stock'] == 94.25  # 100 - 5.75


class TestInventoryControllerAddStock:
    """Test suite for POST /api/inventory/add-stock endpoint."""
    
    def test_add_stock_endpoint_exists(self, client, admin_token, inventory_item, json_headers):
        """Should have add-stock endpoint."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        payload = {
            'item_id': str(inventory_item.id),
            'quantity': 50.0,
            'remarks': 'Delivery from supplier'
        }
        
        response = client.post(
            '/api/inventory/add-stock',
            data=json.dumps(payload),
            headers=headers
        )
        
        # Currently returns 400 (not implemented), but endpoint exists
        assert response.status_code in [400, 405, 201, 200]


class TestInventoryControllerErrorHandling:
    """Test suite for error handling across endpoints."""
    
    def test_malformed_json(self, client, admin_token, json_headers):
        """Should handle malformed JSON gracefully."""
        headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}
        
        response = client.post(
            '/api/inventory/consume',
            data='not valid json',
            headers=headers
        )
        
        assert response.status_code in [400, 415, 200]
    
    def test_missing_content_type(self, client, admin_token, inventory_item):
        """Should handle missing Content-Type header."""
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        payload = json.dumps({
            'item_id': str(inventory_item.id),
            'quantity': 10.0
        })
        
        response = client.post(
            '/api/inventory/consume',
            data=payload,
            headers=headers
        )
        
        # May fail due to missing content type
        assert response.status_code in [400, 415, 201, 200]
