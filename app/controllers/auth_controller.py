from flask import Blueprint, jsonify, request
from app.services.auth_service import AuthService

# Create the Blueprint (Groups all /api/auth routes together)
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    full_name = data.get('full_name')
    password = data.get('password')

    if not full_name or not password:
        return jsonify({"error": "Missing credentials"}), 400

    result, status_code = AuthService.login_user(full_name, password)
    return jsonify(result), status_code