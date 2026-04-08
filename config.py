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
    
    # 5. CORS Configuration (Environment-aware origins & credentials)
    # For development: http://localhost:5173 (Vite default)
    # For production: use CORS_ORIGINS env var (comma-separated)
    _cors_origins_str = os.environ.get('CORS_ORIGINS', 'http://localhost:5173')
    CORS_ORIGINS = [origin.strip() for origin in _cors_origins_str.split(',')]
    CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'
    CORS_MAX_AGE = int(os.environ.get('CORS_MAX_AGE', '3600'))  # 1 hour
    
    # 6. Request Security
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max request size
    JSON_SORT_KEYS = False
    
    # 7. Database Security (SRP: Connection-specific)
    # Only require SSL for PostgreSQL (not for SQLite in tests)
    SQLALCHEMY_ENGINE_OPTIONS = {}
    if SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'sslmode': 'require'}  # Force SSL for PostgreSQL
        }
    
    # 8. Rate Limiting (SRP: Request throttling by endpoint category)
    # Configured per deployment - stricter on auth, moderate on writes, permissive on reads
    RATELIMIT_AUTH = os.environ.get('RATELIMIT_AUTH', '5/minute')
    RATELIMIT_WRITE = os.environ.get('RATELIMIT_WRITE', '30/minute')
    RATELIMIT_READ = os.environ.get('RATELIMIT_READ', '100/minute')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')  # In-memory by default; use redis:// for production
    
    # 9. Production Security Flags
    PROPAGATE_EXCEPTIONS = False  # Don't expose exceptions to client
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    PREFERRED_URL_SCHEME = 'https'  # Force HTTPS URLs
    ENFORCE_HTTPS = os.environ.get('ENFORCE_HTTPS', 'False').lower() == 'true'