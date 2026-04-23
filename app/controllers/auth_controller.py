from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
import bcrypt
from app.models import User
from app.security import PasswordValidator, InputSanitizer
from app.services.role_service import RoleService
import traceback

# Blueprint: Groups all /api/auth routes together
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')


def _as_clean_string(value):
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ''
    return str(value).strip()


def _serialize_user(user):
    role_name = RoleService.normalize_role(user.role.name if user.role else 'user')
    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": role_name or "user",
        "is_active": bool(user.is_active),
    }


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticates a user and issues a JWT token.
    
    Request body:
        {
            "identifier": "username_or_email",
            "password": "password"
        }
    
    Returns:
        {
            "status": "success",
            "access_token": "eyJhbGc...",
            "user": {
                "id": "uuid",
                "username": "username",
                "role": "role_name",
                "full_name": "Full Name"
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "Missing request body"}), 400
        
        identifier = _as_clean_string(data.get('identifier'))
        password = data.get('password', '')

        if not identifier or not password:
            return jsonify({"status": "error", "message": "Missing credentials"}), 400

        # Query the database (username or email as identifier)
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        # Verify existence and bcrypt password hash
        if not user:
            return jsonify({"status": "error", "message": "Invalid credentials. Access denied"}), 401
        
        # Use bcrypt to verify password (stored as bcrypt hash)
        try:
            password_valid = bcrypt.checkpw(
                password.encode('utf-8'),
                user.password_hash.encode('utf-8')
            )
        except Exception:
            password_valid = False
        
        if not password_valid:
            return jsonify({"status": "error", "message": "Invalid credentials. Access denied"}), 401

        # Check if account is active
        if not getattr(user, 'is_active', True):
            return jsonify({"status": "error", "message": "Account has been deactivated"}), 403

        # Mint the JWT Token with role claim for RBAC
        normalized_role = RoleService.normalize_role(user.role.name if user.role else 'user') or 'user'
        additional_claims = {"role": normalized_role}
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims
        )

        # Return the token and safe user data to the React frontend
        return jsonify({
            "status": "success",
            "access_token": access_token,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": normalized_role,
                "full_name": getattr(user, 'full_name', user.username)
            }
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "System authentication error"}), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (admin-only endpoint in production).
    """
    from flask_jwt_extended import jwt_required, get_jwt
    from app.security import roles_required
    from app import db
    from app.models import User
    
    @jwt_required()
    @roles_required('admin')
    def _register():
        data = request.get_json() or {}
        
        # 1. Validate inputs
        username = _as_clean_string(data.get('username'))
        password = data.get('password', '')
        full_name = _as_clean_string(data.get('full_name'))
        email = _as_clean_string(data.get('email'))
        role_name = _as_clean_string(data.get('role') or 'user')
        
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
        
        # 5. Resolve/create supported role
        role, role_error = RoleService.resolve_or_create_supported_role(role_name)
        if role_error:
            return jsonify({"error": role_error}), 400
        
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


@auth_bp.route('/users', methods=['GET'])
def list_users():
    """List users (admin only)."""
    from flask_jwt_extended import jwt_required
    from app.security import roles_required
    from app.models import User

    @jwt_required()
    @roles_required('admin')
    def _list_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify({
            "status": "success",
            "users": [_serialize_user(user) for user in users]
        }), 200

    return _list_users()


@auth_bp.route('/users/<user_id>', methods=['PATCH'])
def update_user(user_id):
    """Update user profile and role (admin only)."""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from app.security import roles_required
    from app import db
    from app.models import User

    @jwt_required()
    @roles_required('admin')
    def _update_user():
        data = request.get_json() or {}

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        username = data.get('username')
        full_name = data.get('full_name')
        email = data.get('email')
        role_name = data.get('role')
        password = data.get('password', None)

        if username is not None:
            username = username.strip()
            if not username:
                return jsonify({"error": "Username cannot be empty"}), 400
            if not all(c.isalnum() or c == '_' for c in username):
                return jsonify({"error": "Username can only contain letters, numbers, and underscores"}), 400

            existing = User.query.filter(User.username == username, User.id != user.id).first()
            if existing:
                return jsonify({"error": "Username already exists"}), 409
            user.username = username

        if full_name is not None:
            full_name = full_name.strip()
            if not full_name:
                return jsonify({"error": "Full name cannot be empty"}), 400
            user.full_name = full_name

        if email is not None:
            normalized_email = email.strip() if email else None
            if normalized_email:
                existing_email = User.query.filter(User.email == normalized_email, User.id != user.id).first()
                if existing_email:
                    return jsonify({"error": "Email already exists"}), 409
            user.email = normalized_email

        if role_name is not None:
            role, role_error = RoleService.resolve_or_create_supported_role(role_name)
            if role_error:
                return jsonify({"error": role_error}), 400
            user.role_id = role.id

        # Password changes from the Edit User modal must be hashed server-side.
        # Blank strings are ignored so the frontend can submit the form without
        # changing the password unless the field is intentionally filled.
        if password is not None:
            password = str(password).strip()
            if password:
                is_valid, error = PasswordValidator.validate(password)
                if not is_valid:
                    return jsonify({
                        "error": error,
                        "requirements": PasswordValidator.get_requirements()
                    }), 400

                if user.check_password(password):
                    return jsonify({"error": "New password must be different from current password"}), 400

                user.set_password(password)

        if 'is_active' in data:
            is_active = bool(data.get('is_active'))
            current_user_id = get_jwt_identity()
            if str(user.id) == str(current_user_id) and not is_active:
                return jsonify({"error": "You cannot deactivate your own account"}), 400
            user.is_active = is_active

        try:
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "User updated successfully",
                "user": _serialize_user(user)
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to update user: {str(e)}"}), 500

    return _update_user()


@auth_bp.route('/users/<user_id>/status', methods=['PATCH'])
def update_user_status(user_id):
    """Activate/deactivate user account (admin only)."""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from app.security import roles_required
    from app import db
    from app.models import User

    @jwt_required()
    @roles_required('admin')
    def _update_user_status():
        data = request.get_json() or {}
        if 'is_active' not in data:
            return jsonify({"error": "Missing 'is_active' field"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        is_active = bool(data.get('is_active'))
        current_user_id = get_jwt_identity()
        if str(user.id) == str(current_user_id) and not is_active:
            return jsonify({"error": "You cannot deactivate your own account"}), 400

        try:
            user.is_active = is_active
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "User status updated successfully",
                "user": _serialize_user(user)
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to update user status: {str(e)}"}), 500

    return _update_user_status()


@auth_bp.route('/users/<user_id>/reset-password', methods=['POST'])
def reset_user_password(user_id):
    """Reset another user's password (admin only)."""
    from flask_jwt_extended import jwt_required
    from app.security import roles_required
    from app import db
    from app.models import User

    @jwt_required()
    @roles_required('admin')
    def _reset_user_password():
        data = request.get_json() or {}
        new_password = data.get('new_password', '')

        if not new_password:
            return jsonify({"error": "Missing new_password"}), 400

        is_valid, error = PasswordValidator.validate(new_password)
        if not is_valid:
            return jsonify({
                "error": error,
                "requirements": PasswordValidator.get_requirements()
            }), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            user.set_password(new_password)
            db.session.commit()
            return jsonify({"message": "Password reset successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to reset password: {str(e)}"}), 500

    return _reset_user_password()


@auth_bp.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user account (admin only)."""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from app.security import roles_required
    from app import db
    from app.models import User

    @jwt_required()
    @roles_required('admin')
    def _delete_user():
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        current_user_id = get_jwt_identity()
        if str(user.id) == str(current_user_id):
            return jsonify({"error": "You cannot delete your own account"}), 400

        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": "User deleted successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500

    return _delete_user()