from flask import Blueprint, jsonify
from app.services.transaction_service import TransactionService

# Create the Blueprint (Groups all /api/transactions routes together)
transaction_bp = Blueprint('transaction_bp', __name__, url_prefix='/api/transactions')

@transaction_bp.route('/', methods=['GET'])
def get_transactions():
    # Call the service layer
    data = TransactionService.get_all_transactions()
    return jsonify({"status": "success", "data": data}), 200