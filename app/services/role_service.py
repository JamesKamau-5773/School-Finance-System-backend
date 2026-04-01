from sqlalchemy import func

from app import db
from app.models import Role


class RoleService:
    """Role domain logic: normalization, validation, and provisioning."""

    DEFAULT_ROLE_PERMISSIONS = {
        'admin': 'read,write,delete',
        'principal': 'read,write,approve',
        'bursar': 'read,write',
        'clerk': 'read,write',
        'storekeeper': 'read,write',
        'user': 'read',
        'system': 'all'
    }

    @staticmethod
    def normalize_role(role_name):
        if role_name is None:
            return ''
        return str(role_name).strip().lower()

    @classmethod
    def supported_roles(cls):
        return tuple(sorted(cls.DEFAULT_ROLE_PERMISSIONS.keys()))

    @classmethod
    def resolve_or_create_supported_role(cls, role_name):
        normalized_role_name = cls.normalize_role(role_name or 'user')

        if not normalized_role_name:
            normalized_role_name = 'user'

        if normalized_role_name not in cls.DEFAULT_ROLE_PERMISSIONS:
            supported_roles = ', '.join(cls.supported_roles())
            return None, f"Unsupported role '{normalized_role_name}'. Supported roles: {supported_roles}"

        role = Role.query.filter(func.lower(Role.name) == normalized_role_name).first()
        if role:
            return role, None

        role = Role(
            name=normalized_role_name,
            permissions=cls.DEFAULT_ROLE_PERMISSIONS[normalized_role_name]
        )
        db.session.add(role)
        db.session.flush()
        return role, None

    @classmethod
    def ensure_default_roles(cls):
        for role_name, permissions in cls.DEFAULT_ROLE_PERMISSIONS.items():
            role = Role.query.filter(func.lower(Role.name) == role_name).first()
            if not role:
                db.session.add(Role(name=role_name, permissions=permissions))

        db.session.commit()
