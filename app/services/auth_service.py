from app.models.auth import User
from flask_jwt_extended import create_access_token
from flask import request
import bcrypt
from app.security import LoginAttemptTracker, audit_log


class AuthService:
    """Responsibility: Authenticate users and issue JWT tokens."""
    
    @staticmethod
    def login_user(username, password):
        """
        Authenticate user and return JWT token.
        
        Args:
            username: Unique username (NOT full_name for security)
            password: Plain text password
            
        Returns:
            Tuple: (result_dict, status_code)
        """
        ip_address = request.remote_addr if request else "UNKNOWN"
        
        # 1. Check if account is locked due to failed attempts
        if LoginAttemptTracker.is_locked_out(username, ip_address):
            audit_log('AUTHENTICATE_FAILED_LOCKED', 'USER', username, 
                     {'reason': 'account_locked', 'ip': ip_address})
            return {
                "error": "Account temporarily locked",
                "message": f"Too many login attempts. Try again in {LoginAttemptTracker.LOCKOUT_MINUTES} minutes."
            }, 429
        
        # 2. Find user by username (not full_name)
        user = User.query.filter_by(username=username).first()
        
        if not user:
            # Record failed attempt (generic message to prevent user enumeration)
            LoginAttemptTracker.record_attempt(username, ip_address)
            audit_log('AUTHENTICATE_FAILED_NOTFOUND', 'USER', username, 
                     {'ip': ip_address})
            return {"error": "Invalid credentials"}, 401
        
        if not user.is_active:
            audit_log('AUTHENTICATE_FAILED_INACTIVE', 'USER', username, 
                     {'ip': ip_address})
            return {"error": "Account is inactive"}, 403
        
        # 3. Verify password
        try:
            if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                LoginAttemptTracker.record_attempt(username, ip_address)
                audit_log('AUTHENTICATE_FAILED_PASSWORD', 'USER', username, 
                         {'ip': ip_address})
                return {"error": "Invalid credentials"}, 401
        except Exception as e:
            audit_log('AUTHENTICATE_ERROR', 'USER', username, 
                     {'error': str(e), 'ip': ip_address})
            return {"error": "Authentication error"}, 500
        
        # 4. Reset failed attempts on successful login
        LoginAttemptTracker.reset_attempts(username, ip_address)
        
        # 5. Create JWT token with role claim
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role.name}
        )
        
        # 6. Update last login timestamp
        user.last_login = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        from app import db
        db.session.commit()
        
        audit_log('AUTHENTICATE_SUCCESS', 'USER', str(user.id), 
                 {'username': username, 'role': user.role.name, 'ip': ip_address})
        
        return {
            "message": "Login successful",
            "access_token": access_token,
            "role": user.role.name,
            "user_id": str(user.id)
        }, 200
