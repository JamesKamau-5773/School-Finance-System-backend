import uuid

from app.models import Role
from app.services.role_service import RoleService


class TestRoleService:
    def test_normalize_role_handles_none_and_case(self):
        assert RoleService.normalize_role(None) == ''
        assert RoleService.normalize_role(' Principal ') == 'principal'
        assert RoleService.normalize_role('STOREKEEPER') == 'storekeeper'

    def test_resolve_or_create_supported_role_creates_role(self, app):
        with app.app_context():
            role = Role.query.filter_by(name='clerk').first()
            if role:
                Role.query.filter_by(id=role.id).delete()

            role, error = RoleService.resolve_or_create_supported_role('ClErK')

            assert error is None
            assert role is not None
            assert role.name == 'clerk'

            fetched = Role.query.filter_by(name='clerk').first()
            assert fetched is not None

    def test_resolve_or_create_supported_role_rejects_unknown_role(self, app):
        with app.app_context():
            role, error = RoleService.resolve_or_create_supported_role('unknown_role')

            assert role is None
            assert error is not None
            assert 'Unsupported role' in error

    def test_ensure_default_roles_seeds_all_supported_roles(self, app):
        with app.app_context():
            Role.query.delete()

            RoleService.ensure_default_roles()

            existing = {role.name for role in Role.query.all()}
            assert set(RoleService.supported_roles()).issubset(existing)
