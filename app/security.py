"""
Security utilities: decorators, validators, and helpers.
Implements RBAC, rate limiting, password validation, input sanitization.
"""
import functools
import re
from datetime import datetime, timedelta
from flask import jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request


# ==================== RATE LIMITING FOR LOGIN ====================

class LoginAttemptTracker:
    """Track failed login attempts per IP/user to prevent brute force."""
    
    _attempts = {}  # {ip:{user: [timestamps]}}
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    
    @classmethod
    def record_attempt(cls, user_id, ip_address):
        """Record a failed login attempt."""
        if ip_address not in cls._attempts:
            cls._attempts[ip_address] = {}
        
        if user_id not in cls._attempts[ip_address]:
            cls._attempts[ip_address][user_id] = []
        
        now = datetime.utcnow()
        # Clean old attempts (older than lockout window)
        cls._attempts[ip_address][user_id] = [
            ts for ts in cls._attempts[ip_address][user_id]
            if (now - ts).total_seconds() < (cls.LOCKOUT_MINUTES * 60)
        ]
        
        cls._attempts[ip_address][user_id].append(now)
    
    @classmethod
    def is_locked_out(cls, user_id, ip_address):
        """Check if account is temporarily locked."""
        if ip_address not in cls._attempts:
            return False
        
        if user_id not in cls._attempts[ip_address]:
            return False
        
        attempts = cls._attempts[ip_address][user_id]
        now = datetime.utcnow()
        
        # Clean old attempts
        attempts = [
            ts for ts in attempts
            if (now - ts).total_seconds() < (cls.LOCKOUT_MINUTES * 60)
        ]
        cls._attempts[ip_address][user_id] = attempts
        
        if len(attempts) >= cls.MAX_ATTEMPTS:
            # Account is locked
            oldest = min(attempts)
            lockout_end = oldest + timedelta(minutes=cls.LOCKOUT_MINUTES)
            return lockout_end > now
        
        return False
    
    @classmethod
    def reset_attempts(cls, user_id, ip_address):
        """Clear attempts after successful login."""
        if ip_address in cls._attempts:
            if user_id in cls._attempts[ip_address]:
                del cls._attempts[ip_address][user_id]


# ==================== ROLE-BASED ACCESS CONTROL ====================

def roles_required(*allowed_roles):
    """
    Decorator to enforce role-based access control.
    
    Usage:
        @app.route('/api/admin/users')
        @roles_required('admin', 'principal')
        def admin_endpoint():
            return {"message": "Admin only"}
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role')
            
            if user_role not in allowed_roles:
                return jsonify({
                    "error": "Insufficient permissions",
                    "message": f"This endpoint requires one of: {', '.join(allowed_roles)}"
                }), 403
            
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator


# ==================== PASSWORD VALIDATION ====================

class PasswordValidator:
    """Validate password strength and security."""
    
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    
    @classmethod
    def validate(cls, password):
        """
        Validate password complexity.
        Returns: (is_valid: bool, error_message: str)
        """
        if not password:
            return False, "Password cannot be empty"
        
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if cls.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        if cls.REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "Password must contain at least one special character (!@#$%^&*)"
        
        return True, None
    
    @classmethod
    def get_requirements(cls):
        """Return password requirements as list."""
        req = [f"Minimum {cls.MIN_LENGTH} characters"]
        if cls.REQUIRE_UPPERCASE:
            req.append("At least one uppercase letter")
        if cls.REQUIRE_DIGITS:
            req.append("At least one digit")
        if cls.REQUIRE_SPECIAL:
            req.append("At least one special character")
        return req


# ==================== INPUT SANITIZATION ====================

class InputSanitizer:
    """Sanitize and validate user inputs."""
    
    # Patterns for common attack vectors
    SQL_INJECTION_PATTERN = re.compile(
        r"(\bOR\b|\bAND\b|\bUNION\b|\bDROP\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|'|\"|-{2,}|/\*|\*/)",
        re.IGNORECASE
    )
    
    XSS_PATTERN = re.compile(
        r"(<script|javascript:|onerror=|onload=|onclick=|<iframe|<embed|<object)",
        re.IGNORECASE
    )
    
    @classmethod
    def sanitize_text(cls, text, max_length=1000):
        """Sanitize text input (remove XSS vectors)."""
        if not isinstance(text, str):
            return str(text)[:max_length]
        
        # Remove common XSS patterns
        cleaned = cls.XSS_PATTERN.sub('', text)
        
        # Strip HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Limit length
        return cleaned[:max_length].strip()
    
    @classmethod
    def sanitize_number(cls, value, min_val=0, max_val=999999999.99):
        """Sanitize numeric input."""
        try:
            num = float(value)
            if num < min_val or num > max_val:
                raise ValueError(f"Number must be between {min_val} and {max_val}")
            return num
        except (ValueError, TypeError):
            raise ValueError(f"Invalid number: {value}")
    
    @classmethod
    def sanitize_phone(cls, phone):
        """Sanitize and validate Kenyan phone number."""
        if not phone:
            return None
        
        # Remove all non-digits except +
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # Must be 10-15 digits (international format)
        if not re.match(r'^(\+)?[\d]{9,15}$', cleaned):
            raise ValueError("Invalid phone number format")
        
        return cleaned
    
    @classmethod
    def sanitize_json(cls, data, allowed_keys=None):
        """Validate JSON structure."""
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")
        
        if allowed_keys:
            for key in data.keys():
                if key not in allowed_keys:
                    raise ValueError(f"Unexpected field: {key}")
        
        return data


# ==================== AUDIT LOGGING ====================

def audit_log(action, resource_type, resource_id, details=None):
    """
    Log security-relevant actions for audit trail.
    
    Args:
        action: 'CREATE', 'READ', 'UPDATE', 'DELETE', 'AUTHENTICATE', 'AUTHORIZE_FAIL'
        resource_type: 'TRANSACTION', 'USER', 'STUDENT', 'PAYMENT', etc.
        resource_id: UUID or identifier of resource
        details: Additional context
    """
    from flask import current_app
    from flask_jwt_extended import get_jwt_identity
    
    try:
        user_id = get_jwt_identity()
    except:
        user_id = "UNKNOWN"
    
    ip_address = request.remote_addr if request else "UNKNOWN"
    timestamp = datetime.utcnow().isoformat()
    
    audit_entry = {
        "timestamp": timestamp,
        "user_id": user_id,
        "ip_address": ip_address,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details
    }
    
    # Log to audit logger
    if current_app:
        current_app.logger.info(f"AUDIT: {audit_entry}")


# ==================== SECURITY HEADERS ====================

def add_security_headers(response):
    """
    Add security headers to HTTP response.
    Called after each request via after_request hook.
    """
    # Prevent XSS attacks
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy (CSP)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    
    # HTTPS enforcement
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Disable MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response
