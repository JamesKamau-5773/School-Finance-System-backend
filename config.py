import os
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

class Config:
    # 1. Application Security
    # CRITICAL: Must be set via environment variable. No fallback for security.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "FATAL: SECRET_KEY environment variable is not set. "
            "Generate a secure key: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    
    # 2. Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///school_db.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    
    # 3. JWT (Role-Based Authentication Settings)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError(
            "FATAL: JWT_SECRET_KEY environment variable is not set. "
            "Generate a secure key: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    
    JWT_TOKEN_LOCATION = ['headers']  # Headers only, not cookies in production
    JWT_COOKIE_SECURE = True  # Force HTTPS for cookies
    JWT_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    JWT_COOKIE_CSRF_PROTECT = True  # CSRF protection enabled
    JWT_TOKEN_EXPIRES = 3600  # 1 hour token expiration
    JWT_ALGORITHM = 'HS256'
    
    # 4. Performance (Caching)
    CACHE_TYPE = 'SimpleCache' 
    CACHE_DEFAULT_TIMEOUT = 300
    
    # 5. Request Security
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max request size
    JSON_SORT_KEYS = False
    
    # 6. Database Security (SRP: Connection-specific)
    # Only require SSL for PostgreSQL (not for SQLite in tests)
    SQLALCHEMY_ENGINE_OPTIONS = {}
    if SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'sslmode': 'require'}  # Force SSL for PostgreSQL
        }
    
    # 7. Production Security Flags
    PROPAGATE_EXCEPTIONS = False  # Don't expose exceptions to client
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    PREFERRED_URL_SCHEME = 'https'  # Force HTTPS URLs