import json
from datetime import datetime, timezone


def test_get_inventory_transactions_returns_data(client, admin_token, inventory_item, json_headers):
    headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}

    add_payload = {
        'item_id': str(inventory_item.id),
        'quantity': 10,
        'supplier': 'Main Supplier',
        'remarks': 'Restock'
    }
    consume_payload = {
        'item_id': str(inventory_item.id),
        'quantity': 3,
        'remarks': 'Issue to kitchen'
    }

    add_response = client.post('/api/inventory/add-stock', data=json.dumps(add_payload), headers=headers)
    assert add_response.status_code == 201

    consume_response = client.post('/api/inventory/consume', data=json.dumps(consume_payload), headers=headers)
    assert consume_response.status_code == 201

    response = client.get('/api/inventory/transactions', headers=headers)
    assert response.status_code == 200

    payload = json.loads(response.data)
    assert payload['status'] == 'success'
    assert payload['count'] >= 2
    assert isinstance(payload['data'], list)
    assert 'recorded_by_user' in payload['data'][0]
    assert payload['data'][0]['recorded_by_user'] is not None
    assert 'full_name' in payload['data'][0]['recorded_by_user']


def test_get_inventory_transactions_filters_by_action_and_start_date(client, admin_token, inventory_item, json_headers):
    headers = {**json_headers, 'Authorization': f'Bearer {admin_token}'}

    add_payload = {
        'item_id': str(inventory_item.id),
        'quantity': 4,
        'supplier': 'Main Supplier',
        'remarks': 'Restock'
    }
    add_response = client.post('/api/inventory/add-stock', data=json.dumps(add_payload), headers=headers)
    assert add_response.status_code == 201

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    response = client.get(
        f'/api/inventory/transactions?action=received&start_date={today}',
        headers=headers
    )
    assert response.status_code == 200

    payload = json.loads(response.data)
    assert payload['status'] == 'success'
    assert all(tx['action'] == 'received' for tx in payload['data'])
