import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app import db

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), unique=True, nullable=False) 
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = db.Column(UUID(as_uuid=True), db.ForeignKey('roles.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    transactions = db.relationship('Transaction', backref='author', lazy=True)