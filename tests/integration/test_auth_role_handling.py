import uuid

import pytest
from flask_jwt_extended import create_access_token

from app import db
from app.models import User
from app.services.role_service import RoleService


@pytest.fixture
def admin_auth_headers(app):
    with app.app_context():
        admin_role, error = RoleService.resolve_or_create_supported_role('admin')
        assert error is None

        user = User(
            id=uuid.uuid4(),
            role_id=admin_role.id,
            username=f"admin_{uuid.uuid4().hex[:8]}",
            full_name='Admin Test User',
            email=f"admin_{uuid.uuid4().hex[:8]}@test.com",
            password_hash='hashed',
            is_active=True,
        )
        user.set_password('AdminPass123!')
        db.session.add(user)
        db.session.commit()

        token = create_access_token(
            identity=str(user.id),
            additional_claims={'role': 'ADMIN'}
        )

        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


class TestAuthRoleHandling:
    def test_register_accepts_mixed_case_supported_role(self, client, app, admin_auth_headers):
        payload = {
            'username': f"principal_{uuid.uuid4().hex[:8]}",
            'password': 'StrongPass123!',
            'full_name': 'Principal Mixed Case',
            'email': None,
            'role': 'Principal',
        }

        response = client.post('/api/auth/register', json=payload, headers=admin_auth_headers)

        assert response.status_code == 201
        assert response.json['message'] == 'User created successfully'

        with app.app_context():
            user = User.query.filter_by(username=payload['username']).first()
            assert user is not None
            assert user.role is not None
            assert user.role.name == 'principal'

    def test_register_rejects_unsupported_role(self, client, admin_auth_headers):
        payload = {
            'username': f"badrole_{uuid.uuid4().hex[:8]}",
            'password': 'StrongPass123!',
            'full_name': 'Bad Role User',
            'email': None,
            'role': 'NopeRole',
        }

        response = client.post('/api/auth/register', json=payload, headers=admin_auth_headers)

        assert response.status_code == 400
        assert 'Unsupported role' in response.json['error']

    def test_roles_required_allows_uppercase_admin_claim(self, client, admin_auth_headers):
        response = client.get('/api/inventory/status', headers=admin_auth_headers)

        assert response.status_code != 403
