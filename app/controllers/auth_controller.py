from flask import Blueprint, jsonify

# Create the Blueprint (Groups all /api/auth routes together)
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    # We will add JWT login logic here later
    return jsonify({"status": "success", "message": "Auth endpoint ready"}), 200