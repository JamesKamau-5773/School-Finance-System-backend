"""
Integration tests for Finance Controller endpoints.
Tests the contract between frontend (financeApi.js) and backend (/api/finance/* routes).
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta, timezone

from app import db
from app.models.auth import Role, User
from app.models.finance import VoteHead, Transaction


class TestFinanceTransactions:
    """Test suite for GET /api/finance/transactions endpoint."""
    
    def test_get_ledger_returns_empty_list(self, client):
        """GET /api/finance/transactions should return an empty array initially."""
        response = client.get('/api/finance/transactions')
        
        assert response.status_code == 200
        assert response.json == []

    def test_get_ledger_returns_latest_transactions_first(self, client, app):
        """GET /api/finance/transactions should return newest transactions first."""
        with app.app_context():
            role = Role(name='bursar', permissions='read,write')
            db.session.add(role)
            db.session.flush()

            user = User(
                id=uuid.uuid4(),
                role_id=role.id,
                username='ledger_user',
                full_name='Ledger User',
                email='ledger_user@test.com',
                password_hash='hashed',
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            vote_head = VoteHead(
                id=uuid.uuid4(),
                code='VH-TST',
                name='Test Vote Head',
                fund_type='FEES',
                annual_budget=100000.00,
                current_balance=100000.00,
            )
            db.session.add(vote_head)
            db.session.flush()

            older_tx = Transaction(
                id=uuid.uuid4(),
                vote_head_id=vote_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=1000.00,
                reference_number='REF-OLD',
                description='Older transaction',
                transaction_date=datetime.now(timezone.utc) - timedelta(days=1),
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
            )

            newer_tx = Transaction(
                id=uuid.uuid4(),
                vote_head_id=vote_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=2000.00,
                reference_number='REF-NEW',
                description='Newer transaction',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )

            db.session.add(older_tx)
            db.session.add(newer_tx)
            db.session.commit()

            older_id = str(older_tx.id)
            newer_id = str(newer_tx.id)

        response = client.get('/api/finance/transactions')

        assert response.status_code == 200
        ids = [item['id'] for item in response.json]
        assert newer_id in ids
        assert older_id in ids
        assert ids.index(newer_id) < ids.index(older_id)


class TestFinancePayment:
    """Test suite for POST /api/finance/pay endpoint."""
    
    def test_pay_success_with_valid_payload(self, client):
        """POST /api/finance/pay should accept valid payment payload and return success."""
        payload = {
            "student_id": None,
            "amount": 15000.00,
            "payment_method": "mpesa",
            "reference_no": "MPM123456789"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['status'] == 'success'
        assert response.json['message'] == 'Payment recorded successfully'
        # Validate Transaction object structure
        data = response.json['data']
        assert data['transaction_type'] == 'INCOME'
        assert data['amount'] == payload['amount']
        assert data['reference_number'] == payload['reference_no']
        assert 'id' in data
        assert 'created_at' in data
        assert 'recorded_by' in data
        assert 'vote_head_id' in data
    
    def test_pay_accepts_missing_student_id(self, client):
        """POST /api/finance/pay should accept request without student_id (now optional)."""
        payload = {
            "amount": 15000.00,
            "payment_method": "mpesa",
            "reference_no": "MPM123456789"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['status'] == 'success'
        assert response.json['data']['student_id'] is None
    
    def test_pay_fails_without_amount(self, client):
        """POST /api/finance/pay should fail if amount is missing."""
        payload = {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "payment_method": "mpesa",
            "reference_no": "MPM123456789"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'amount' in response.json['message']
    
    def test_pay_fails_without_payment_method(self, client):
        """POST /api/finance/pay should fail if payment_method is missing."""
        payload = {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "amount": 15000.00,
            "reference_no": "MPM123456789"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'payment_method' in response.json['message']
    
    def test_pay_fails_with_zero_amount(self, client):
        """POST /api/finance/pay should fail if amount is zero or negative."""
        payload = {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "amount": 0,
            "payment_method": "mpesa",
            "reference_no": "MPM123456789"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'greater than 0' in response.json['message']
    
    def test_pay_fails_with_negative_amount(self, client):
        """POST /api/finance/pay should fail if amount is negative."""
        payload = {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "amount": -5000.00,
            "payment_method": "mpesa",
            "reference_no": "MPM123456789"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'greater than 0' in response.json['message']
    
    def test_pay_accepts_decimal_amount(self, client):
        """POST /api/finance/pay should accept decimal amounts."""
        payload = {
            "student_id": None,
            "amount": 12500.50,
            "payment_method": "bank",
            "reference_no": "BANK987654321"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['data']['amount'] == 12500.50


class TestFinanceExpense:
    """Test suite for POST /api/finance/expense endpoint."""
    
    def test_expense_success_with_valid_payload(self, client):
        """POST /api/finance/expense should accept valid expense payload and return success."""
        payload = {
            "description": "Purchase of classroom chalk",
            "amount": 5000.00,
            "category": "supplies",
            "payment_method": "bank",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['status'] == 'success'
        assert response.json['message'] == 'Expense recorded successfully'
        # Validate Transaction object structure
        data = response.json['data']
        assert data['transaction_type'] == 'EXPENSE'
        assert data['description'] == payload['description']
        assert data['amount'] == payload['amount']
        assert data['reference_number'] == payload['reference_no']
        assert 'id' in data
        assert 'created_at' in data
        assert 'recorded_by' in data
        assert 'vote_head_id' in data
    
    def test_expense_fails_without_description(self, client):
        """POST /api/finance/expense should fail if description is missing."""
        payload = {
            "amount": 5000.00,
            "category": "supplies",
            "payment_method": "bank",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'description' in response.json['message']
    
    def test_expense_fails_without_amount(self, client):
        """POST /api/finance/expense should fail if amount is missing."""
        payload = {
            "description": "Purchase of classroom chalk",
            "category": "supplies",
            "payment_method": "bank",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'amount' in response.json['message']
    
    def test_expense_fails_without_category(self, client):
        """POST /api/finance/expense should fail if category is missing."""
        payload = {
            "description": "Purchase of classroom chalk",
            "amount": 5000.00,
            "payment_method": "bank",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'category' in response.json['message']
    
    def test_expense_fails_without_payment_method(self, client):
        """POST /api/finance/expense should fail if payment_method is missing."""
        payload = {
            "description": "Purchase of classroom chalk",
            "amount": 5000.00,
            "category": "supplies",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'payment_method' in response.json['message']
    
    def test_expense_fails_with_zero_amount(self, client):
        """POST /api/finance/expense should fail if amount is zero or negative."""
        payload = {
            "description": "Purchase of classroom chalk",
            "amount": 0,
            "category": "supplies",
            "payment_method": "bank",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'greater than 0' in response.json['message']
    
    def test_expense_fails_with_negative_amount(self, client):
        """POST /api/finance/expense should fail if amount is negative."""
        payload = {
            "description": "Purchase of classroom chalk",
            "amount": -3000.00,
            "category": "supplies",
            "payment_method": "bank",
            "reference_no": "BANK123456789"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert response.json['status'] == 'error'
        assert 'greater than 0' in response.json['message']
    
    def test_expense_accepts_decimal_amount(self, client):
        """POST /api/finance/expense should accept decimal amounts."""
        payload = {
            "description": "Purchase of cleaning supplies",
            "amount": 2750.25,
            "category": "maintenance",
            "payment_method": "mpesa",
            "reference_no": "MPM555666777"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        assert response.json['data']['amount'] == 2750.25


class TestFinanceContractCompliance:
    """Test suite to ensure the API contract matches financeApi.js expectations."""
    
    def test_payment_response_structure(self, client):
        """Verify payment response has the expected Transaction structure."""
        payload = {
            "student_id": None,
            "amount": 20000.00,
            "payment_method": "cash",
            "reference_no": "CASH111222333"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.json
        assert 'status' in data
        assert 'message' in data
        assert 'data' in data
        assert isinstance(data['data'], dict)
        # Validate Transaction object fields
        assert 'id' in data['data']
        assert 'transaction_type' in data['data']
        assert data['data']['transaction_type'] == 'INCOME'
        assert 'amount' in data['data']
        assert 'reference_number' in data['data']
        assert 'created_at' in data['data']
        assert 'recorded_by' in data['data']
    
    def test_expense_response_structure(self, client):
        """Verify expense response has the expected Transaction structure."""
        payload = {
            "description": "Maintenance of school fence",
            "amount": 50000.00,
            "category": "maintenance",
            "payment_method": "bank",
            "reference_no": "BANK777888999"
        }
        
        response = client.post(
            '/api/finance/expense',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.json
        assert 'status' in data
        assert 'message' in data
        assert 'data' in data
        assert isinstance(data['data'], dict)
        # Validate Transaction object fields
        assert 'id' in data['data']
        assert 'transaction_type' in data['data']
        assert data['data']['transaction_type'] == 'EXPENSE'
        assert 'description' in data['data']
        assert 'amount' in data['data']
        assert 'reference_number' in data['data']
        assert 'created_at' in data['data']
        assert 'recorded_by' in data['data']
    
    def test_error_response_structure(self, client):
        """Verify error response has the expected structure."""
        payload = {
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "amount": -1000.00,
            "payment_method": "mpesa",
            "reference_no": "TEST1"
        }
        
        response = client.post(
            '/api/finance/pay',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json
        assert 'status' in data
        assert data['status'] == 'error'
        assert 'message' in data
