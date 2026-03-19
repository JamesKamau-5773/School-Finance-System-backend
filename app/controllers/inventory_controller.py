from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.inventory_service import InventoryService

inventory_bp = Blueprint('inventory_bp', __name__, url_prefix='/api/inventory')


@inventory_bp.route('/status', methods=['GET'])
@jwt_required()
def get_inventory_status():
    """
    Provides the Principal with the real-time stock levels 
    and 'Days Remaining' predictions.
    """
    predictions, status_code = InventoryService.get_stock_predictions()
    return jsonify(predictions), status_code


@inventory_bp.route('/consume', methods=['POST'])
@jwt_required()
def record_consumption():
    """
    Records the daily usage of food or fuel.
    """
    data = request.get_json()
    item_id = data.get('item_id')
    quantity = data.get('quantity')
    remarks = data.get('remarks', 'Daily consumption')

    if not item_id or not quantity:
        return jsonify({"error": "Item ID and Quantity are required"}), 400

    current_user_id = get_jwt_identity()
    result, status_code = InventoryService.record_usage(
        item_id=item_id,
        quantity_used=float(quantity),
        user_id=current_user_id,
        remarks=remarks
    )
    return jsonify(result), status_code


@inventory_bp.route('/add-stock', methods=['POST'])
@jwt_required()
def add_stock():
    """
    Records new supplies entering the store (e.g., a delivery of beans).
    """
    # Logic similar to consume, but increasing the count in the Repository
    # This ensures a paper trail for every bag delivered to the school.
    pass
