"""
Integration tests for Finance Controller endpoints.
Tests the contract between frontend (financeApi.js) and backend (/api/finance/* routes).
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import create_access_token

from app import db
from app.models.auth import Role, User
from app.models.finance import VoteHead, Transaction, LedgerEntry


class TestFinanceTransactions:
    """Test suite for GET /api/finance/transactions endpoint."""
    
    def test_get_ledger_returns_empty_list(self, client):
        """GET /api/finance/transactions should return an empty array initially."""
        response = client.get('/api/finance/transactions')
        
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['count'] == 0
        assert response.json['data'] == []

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
        ids = [item['id'] for item in response.json['data']]
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


class TestFinanceSummarySplit:
    """Tests for school vs government collections summary."""

    def test_summary_splits_school_and_government_collections(self, client, app):
        with app.app_context():
            role = Role(name='summary_tester', permissions='read,write')
            db.session.add(role)
            db.session.flush()

            user = User(
                id=uuid.uuid4(),
                role_id=role.id,
                username='summary_user',
                full_name='Summary User',
                email='summary@test.com',
                password_hash='hashed',
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            fee_head = VoteHead(
                id=uuid.uuid4(),
                code='FEE-001',
                name='School Fees',
                fund_type='FEES',
                annual_budget=0.00,
                current_balance=0.00,
            )
            cap_head = VoteHead(
                id=uuid.uuid4(),
                code='CAP-001',
                name='Government Capitation',
                fund_type='CAPITATION',
                annual_budget=0.00,
                current_balance=0.00,
            )
            expense_head = VoteHead(
                id=uuid.uuid4(),
                code='EXP-001',
                name='Operating Expense',
                fund_type='FEES',
                annual_budget=0.00,
                current_balance=0.00,
            )
            db.session.add_all([fee_head, cap_head, expense_head])
            db.session.flush()

            db.session.add(Transaction(
                id=uuid.uuid4(),
                vote_head_id=fee_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=8000.00,
                reference_number='FEE-100',
                description='Student fee payment',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            ))
            db.session.add(Transaction(
                id=uuid.uuid4(),
                vote_head_id=cap_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=12000.00,
                reference_number='CAP-100',
                description='MoE capitation',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            ))
            db.session.add(Transaction(
                id=uuid.uuid4(),
                vote_head_id=expense_head.id,
                recorded_by=user.id,
                transaction_type='EXPENSE',
                amount=2500.00,
                reference_number='EXP-100',
                description='Cleaning supplies',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            ))
            db.session.commit()

        response = client.get('/api/finance/summary')

        assert response.status_code == 200
        assert response.json['school_collections'] == 8000.0
        assert response.json['government_collections'] == 12000.0
        assert response.json['total_collections'] == 20000.0
        assert response.json['total_expenses'] == 2500.0


class TestFinanceReportingEndpoints:
    """Regression tests for finance reporting endpoints."""

    def _seed_ledger_data(self, app):
        with app.app_context():
            role = Role.query.filter_by(name='reporter').first()
            if not role:
                role = Role(name='reporter', permissions='read,write')
                db.session.add(role)
                db.session.flush()

            user = User.query.filter_by(username='report_user').first()
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    role_id=role.id,
                    username='report_user',
                    full_name='Report User',
                    email='report_user@test.com',
                    password_hash='hashed',
                    is_active=True,
                )
                db.session.add(user)
                db.session.flush()

            vote_head = VoteHead.query.filter_by(code='TUIT').first()
            if not vote_head:
                vote_head = VoteHead(
                    id=uuid.uuid4(),
                    code='TUIT',
                    name='Tuition',
                    fund_type='CAPITATION',
                    annual_budget=1000000.00,
                    current_balance=0.00,
                )
                db.session.add(vote_head)
                db.session.flush()

            transaction = Transaction(
                id=uuid.uuid4(),
                vote_head_id=vote_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=1000.00,
                reference_number='REF-TRIAL-001',
                description='Trial balance seed transaction',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(transaction)
            db.session.flush()

            debit_entry = LedgerEntry(
                id=uuid.uuid4(),
                transaction_id=transaction.id,
                vote_head_id=vote_head.id,
                entry_type='DEBIT',
                amount=1000.00,
                payment_method='BANK',
                reference_no='REF-TRIAL-001',
                description='Debit seed',
                created_by=user.id,
            )

            credit_entry = LedgerEntry(
                id=uuid.uuid4(),
                transaction_id=transaction.id,
                vote_head_id=vote_head.id,
                entry_type='CREDIT',
                amount=1000.00,
                payment_method='BANK',
                reference_no='REF-TRIAL-001',
                description='Credit seed',
                created_by=user.id,
            )

            db.session.add(debit_entry)
            db.session.add(credit_entry)
            db.session.commit()

    def test_trial_balance_returns_200_and_balanced_totals(self, client, app):
        """GET /api/finance/reports/trial-balance should return balanced totals."""
        self._seed_ledger_data(app)

        response = client.get('/api/finance/reports/trial-balance')

        assert response.status_code == 200
        assert 'lines' in response.json
        assert 'totals' in response.json
        assert isinstance(response.json['lines'], list)
        assert response.json['totals']['is_balanced'] is True

    def test_account_ledger_returns_entries_for_vote_head_name(self, client, app):
        """GET /api/finance/ledger/<account_name> should return account history."""
        self._seed_ledger_data(app)

        response = client.get('/api/finance/ledger/Tuition')

        assert response.status_code == 200
        assert isinstance(response.json, list)
        assert len(response.json) >= 1
        first_row = response.json[0]
        assert 'account' in first_row
        assert first_row['account'] == 'Tuition'
        assert 'running_balance' in first_row
        assert 'reference_no' in first_row

    def test_account_ledger_returns_empty_list_for_unknown_account(self, client):
        """GET /api/finance/ledger/<account_name> should return [] for unknown account."""
        response = client.get('/api/finance/ledger/UnknownAccount')

        assert response.status_code == 200
        assert response.json == []


class TestVoteHeadCrudEndpoints:
    """Integration tests for vote head CRUD endpoints."""

    def test_create_vote_head_success_admin(self, client, admin_token):
        payload = {
            "code": "ADM01",
            "name": "Administration",
            "fund_type": "CAPITATION",
            "annual_budget": 250000,
            "current_balance": 50000
        }
        response = client.post(
            '/api/finance/vote-heads',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 201
        assert response.json['status'] == 'success'
        assert response.json['data']['code'] == 'ADM01'
        assert response.json['data']['name'] == 'Administration'

    def test_create_vote_head_requires_auth(self, client):
        payload = {
            "code": "TST01",
            "name": "Test Head",
            "fund_type": "CAPITATION"
        }
        response = client.post(
            '/api/finance/vote-heads',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 401

    def test_create_vote_head_forbidden_for_user_role(self, client, app):
        with app.app_context():
            user_token = create_access_token(identity=str(uuid.uuid4()), additional_claims={"role": "user"})

        payload = {
            "code": "TST02",
            "name": "Test Head",
            "fund_type": "CAPITATION"
        }
        response = client.post(
            '/api/finance/vote-heads',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'Authorization': f'Bearer {user_token}'}
        )

        assert response.status_code == 403

    def test_update_vote_head_success(self, client, app, admin_token):
        with app.app_context():
            vote_head = VoteHead(
                id=uuid.uuid4(),
                code='LIB01',
                name='Library',
                fund_type='FEES',
                annual_budget=100000.00,
                current_balance=10000.00,
            )
            db.session.add(vote_head)
            db.session.commit()
            vote_head_id = str(vote_head.id)

        payload = {
            "name": "Library Services",
            "annual_budget": 150000
        }
        response = client.put(
            f'/api/finance/vote-heads/{vote_head_id}',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['data']['name'] == 'Library Services'
        assert response.json['data']['annual_budget'] == 150000.0

    def test_update_vote_head_rejects_invalid_uuid(self, client, admin_token):
        payload = {"name": "Updated Name"}
        response = client.put(
            '/api/finance/vote-heads/not-a-uuid',
            data=json.dumps(payload),
            content_type='application/json',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 400
        assert response.json['status'] == 'error'

    def test_delete_vote_head_success(self, client, app, admin_token):
        with app.app_context():
            vote_head = VoteHead(
                id=uuid.uuid4(),
                code='LAB01',
                name='Laboratory',
                fund_type='PROJECT',
                annual_budget=200000.00,
                current_balance=5000.00,
            )
            db.session.add(vote_head)
            db.session.commit()
            vote_head_id = str(vote_head.id)

        response = client.delete(
            f'/api/finance/vote-heads/{vote_head_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 200
        assert response.json['status'] == 'success'

        with app.app_context():
            deleted = VoteHead.query.filter_by(id=uuid.UUID(vote_head_id)).first()
            assert deleted is None

    def test_delete_vote_head_returns_404_when_not_found(self, client, admin_token):
        missing_id = str(uuid.uuid4())
        response = client.delete(
            f'/api/finance/vote-heads/{missing_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert response.status_code == 404
        assert response.json['status'] == 'error'


class TestVoteHeadDistributionFiltering:
    """Tests for CAPITATION-only vote-head distribution behavior."""

    def test_get_vote_heads_excludes_non_capitation_vote_heads(self, client, app):
        with app.app_context():
            role = Role(name='finance_tester', permissions='read,write')
            db.session.add(role)
            db.session.flush()

            user = User(
                id=uuid.uuid4(),
                role_id=role.id,
                username='finance_distribution_user',
                full_name='Finance Distribution User',
                email='finance_distribution@test.com',
                password_hash='hashed',
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            cap_vote_head = VoteHead(
                id=uuid.uuid4(),
                code='CAP01',
                name='Capitation Tuition',
                fund_type='CAPITATION',
                annual_budget=100000.00,
                current_balance=0.00,
            )
            fee_vote_head = VoteHead(
                id=uuid.uuid4(),
                code='FEE01',
                name='Fee Revenue',
                fund_type='FEES',
                annual_budget=100000.00,
                current_balance=0.00,
            )
            db.session.add(cap_vote_head)
            db.session.add(fee_vote_head)
            db.session.flush()

            tx_cap = Transaction(
                id=uuid.uuid4(),
                vote_head_id=cap_vote_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=5000.00,
                reference_number='CAP-001',
                description='Capitation disbursement',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            tx_fee = Transaction(
                id=uuid.uuid4(),
                vote_head_id=fee_vote_head.id,
                recorded_by=user.id,
                transaction_type='INCOME',
                amount=9000.00,
                reference_number='FEE-001',
                description='Fee payment',
                transaction_date=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(tx_cap)
            db.session.add(tx_fee)
            db.session.flush()

            db.session.add(LedgerEntry(
                id=uuid.uuid4(),
                transaction_id=tx_cap.id,
                vote_head_id=cap_vote_head.id,
                entry_type='CREDIT',
                amount=5000.00,
                payment_method='BANK',
                reference_no='CAP-001',
                description='Capitation credit',
                created_by=user.id,
            ))
            db.session.add(LedgerEntry(
                id=uuid.uuid4(),
                transaction_id=tx_fee.id,
                vote_head_id=fee_vote_head.id,
                entry_type='CREDIT',
                amount=9000.00,
                payment_method='BANK',
                reference_no='FEE-001',
                description='Fee credit',
                created_by=user.id,
            ))
            db.session.commit()

        response = client.get('/api/finance/vote-heads')

        assert response.status_code == 200
        names = [row['name'] for row in response.json]
        assert 'Capitation Tuition' in names
        assert 'Fee Revenue' not in names

        cap_row = next(row for row in response.json if row['name'] == 'Capitation Tuition')
        assert cap_row['current_balance'] == 5000.0
