import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app import db
import bcrypt


class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), unique=True, nullable=False) 
    permissions = db.Column(db.String(500), nullable=True)  # Comma-separated perms
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    users = db.relationship('User', backref='role', lazy=True)


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = db.Column(UUID(as_uuid=True), db.ForeignKey('roles.id'), nullable=False)
    
    # Authentication
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Security
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    last_password_change = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    transactions = db.relationship('Transaction', backref='author', lazy=True)
    
    def set_password(self, password):
        """Hash and set password securely."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
        self.last_password_change = datetime.now(timezone.utc)
    
    def check_password(self, password):
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def __repr__(self):
        return f'<User {self.username} ({self.full_name})>'