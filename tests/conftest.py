"""
Pytest configuration and shared fixtures for the test suite.
Provides Flask app, database, JWT tokens, and test data.
"""
import pytest
import uuid
from datetime import datetime, timezone
from flask_jwt_extended import create_access_token
from app import db, create_app
from app.models import User, Role, Inventory, InventoryLog
from config import Config


class TestConfig(Config):
    """Test environment configuration."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    JWT_SECRET_KEY = 'test-secret-key'
    PROPAGATE_EXCEPTIONS = True


@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app instance for testing."""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_db(app):
    """Reset database before each test."""
    with app.app_context():
        db.session.rollback()
        db.session.remove()
        yield
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        admin_role = Role.query.filter_by(role_name='admin').first()
        if not admin_role:
            admin_role = Role(role_name='admin', permissions='read,write,delete')
            db.session.add(admin_role)
        
        user = User(
            id=uuid.uuid4(),
            username='admin',
            email='admin@test.com',
            role_id=admin_role.id,
            is_active=True
        )
        user.set_password('adminpass123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def regular_user(app):
    """Create a regular user for testing."""
    with app.app_context():
        user_role = Role.query.filter_by(role_name='user').first()
        if not user_role:
            user_role = Role(role_name='user', permissions='read')
            db.session.add(user_role)
        
        user = User(
            id=uuid.uuid4(),
            username='testuser',
            email='user@test.com',
            role_id=user_role.id,
            is_active=True
        )
        user.set_password('userpass123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_token(app, admin_user):
    """Generate a valid JWT token for admin user."""
    with app.app_context():
        return create_access_token(identity=str(admin_user.id))


@pytest.fixture
def user_token(app, regular_user):
    """Generate a valid JWT token for regular user."""
    with app.app_context():
        return create_access_token(identity=str(regular_user.id))


@pytest.fixture
def inventory_item(app, admin_user):
    """Create a sample inventory item."""
    with app.app_context():
        item = Inventory(
            id=uuid.uuid4(),
            item_name='Maize',
            unit_of_measure='90kg Bag',
            current_quantity=100.00,
            reorder_level=20.00,
            average_daily_consumption=5.00,
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(item)
        db.session.commit()
        return item


@pytest.fixture
def low_stock_item(app, admin_user):
    """Create an inventory item with low stock."""
    with app.app_context():
        item = Inventory(
            id=uuid.uuid4(),
            item_name='Beans',
            unit_of_measure='50kg Bag',
            current_quantity=15.00,
            reorder_level=20.00,
            average_daily_consumption=3.00,
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(item)
        db.session.commit()
        return item


@pytest.fixture
def inventory_log(app, inventory_item, admin_user):
    """Create a sample inventory log entry."""
    with app.app_context():
        log = InventoryLog(
            id=uuid.uuid4(),
            inventory_id=inventory_item.id,
            quantity=-5.00,
            transaction_type='CONSUMPTION',
            recorded_by=admin_user.id,
            remarks='Daily consumption',
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(log)
        db.session.commit()
        return log


@pytest.fixture
def auth_headers(admin_token):
    """Create authorization headers with JWT token."""
    return {'Authorization': f'Bearer {admin_token}'}


@pytest.fixture
def json_headers():
    """Create JSON content-type headers."""
    return {'Content-Type': 'application/json'}
