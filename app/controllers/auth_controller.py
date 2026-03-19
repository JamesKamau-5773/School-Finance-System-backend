from flask import Blueprint, jsonify, request
from app.services.auth_service import AuthService
from app.security import PasswordValidator, InputSanitizer

# Blueprint: Groups all /api/auth routes together
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and issue JWT token.
    
    Request body:
        {
            "username": "unique_username",
            "password": "SecurePassword123!"
        }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    
    # 1. Extract and sanitize inputs
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # 2. Validate required fields
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    
    # 3. Basic input validation (prevent injection)
    try:
        username = InputSanitizer.sanitize_text(username, max_length=50)
    except Exception as e:
        return jsonify({"error": f"Invalid username format: {str(e)}"}), 400
    
    # 4. Delegate to service layer
    result, status_code = AuthService.login_user(username, password)
    
    return jsonify(result), status_code


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (admin-only endpoint in production).
    """
    from flask_jwt_extended import jwt_required, get_jwt
    from app.security import roles_required
    from app import db
    from app.models import User, Role
    
    @jwt_required()
    @roles_required('admin')
    def _register():
        data = request.get_json()
        
        # 1. Validate inputs
        username = data.get('username', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        role_name = data.get('role', 'user').strip()
        
        if not all([username, password, full_name]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # 2. Check password strength
        is_valid, error = PasswordValidator.validate(password)
        if not is_valid:
            return jsonify({
                "error": error,
                "requirements": PasswordValidator.get_requirements()
            }), 400
        
        # 3. Validate username format (alphanumeric + underscore)
        if not all(c.isalnum() or c == '_' for c in username):
            return jsonify({"error": "Username can only contain letters, numbers, and underscores"}), 400
        
        # 4. Check if user exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            return jsonify({"error": "Username already exists"}), 409
        
        # 5. Get role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return jsonify({"error": f"Role '{role_name}' does not exist"}), 400
        
        # 6. Create user
        try:
            user = User(
                username=username,
                full_name=full_name,
                email=email if email else None,
                role_id=role.id
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            return jsonify({
                "message": "User created successfully",
                "user_id": str(user.id),
                "username": user.username
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Registration failed: {str(e)}"}), 500
    
    return _register()


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password (JWT required)."""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from app import db
    from app.models import User
    
    @jwt_required()
    def _change_password():
        data = request.get_json()
        
        user_id = get_jwt_identity()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return jsonify({"error": "Missing old or new password"}), 400
        
        # 1. Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # 2. Verify old password
        if not user.check_password(old_password):
            return jsonify({"error": "Old password is incorrect"}), 401
        
        # 3. Validate new password
        is_valid, error = PasswordValidator.validate(new_password)
        if not is_valid:
            return jsonify({
                "error": error,
                "requirements": PasswordValidator.get_requirements()
            }), 400
        
        # 4. Prevent reuse of old password
        if user.check_password(new_password):
            return jsonify({"error": "New password must be different from current password"}), 400
        
        # 5. Update password
        try:
            user.set_password(new_password)
            db.session.commit()
            
            return jsonify({
                "message": "Password changed successfully"
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to change password: {str(e)}"}), 500
    
    return _change_password()