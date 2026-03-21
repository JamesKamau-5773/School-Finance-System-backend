"""System repository for getting/creating system entities (users, vote heads)."""
import uuid
from app import db
from app.models.auth import User, Role
from app.models.finance import VoteHead


class SystemRepository:
    """Handles retrieval/creation of system-level entities."""

    @staticmethod
    def get_or_create_system_role():
        """Get or create the system role.
        
        Returns:
            UUID: The role's ID
        """
        role = Role.query.filter_by(name='system').first()
        if not role:
            role = Role(
                id=uuid.uuid4(),
                name='system',
                permissions='all'
            )
            db.session.add(role)
            db.session.commit()
        return role.id

    @staticmethod
    def get_or_create_system_user():
        """Get or create the system user for transaction recording.
        
        Returns:
            UUID: The system user's ID
        """
        user = User.query.filter_by(username='system').first()
        if not user:
            role_id = SystemRepository.get_or_create_system_role()
            user = User(
                id=uuid.uuid4(),
                role_id=role_id,
                username='system',
                email='system@erp.local',
                full_name='System',
                password_hash='',
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
        return user.id

    @staticmethod
    def get_or_create_default_fee_vote_head():
        """Get or create the default FEES vote head.
        
        Returns:
            UUID: The vote head's ID
        """
        vh = VoteHead.query.filter_by(fund_type='FEES').first()
        if not vh:
            vh = VoteHead(
                id=uuid.uuid4(),
                code='FEE-DEFAULT',
                name='Default Fee Collection',
                fund_type='FEES',
                annual_budget=0.00,
                current_balance=0.00
            )
            db.session.add(vh)
            db.session.commit()
        return vh.id
