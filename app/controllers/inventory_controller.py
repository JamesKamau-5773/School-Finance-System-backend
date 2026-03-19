from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.inventory_service import InventoryService
from app.security import roles_required, InputSanitizer, audit_log

inventory_bp = Blueprint('inventory_bp', __name__, url_prefix='/api/inventory')


@inventory_bp.route('/status', methods=['GET'])
@jwt_required()
@roles_required('admin', 'principal', 'clerk')  # SRP: RBAC in decorator
def get_inventory_status():
    """
    Get real-time stock levels and days remaining predictions.
    """
    predictions, status_code = InventoryService.get_stock_predictions()
    return jsonify(predictions), status_code


@inventory_bp.route('/consume', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'clerk')  # SRP: RBAC in decorator
def record_consumption():
    """
    Record daily consumption of food/fuel.
    """
    data = request.get_json()
    
    # Extract and validate inputs (SRP: Sanitization in handler)
    try:
        item_id = data.get('item_id')
        quantity = InputSanitizer.sanitize_number(
            data.get('quantity', 0),
            min_val=0.01,
            max_val=999999.99
        )
        remarks = InputSanitizer.sanitize_text(
            data.get('remarks', 'Daily consumption'),
            max_length=500
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    if not item_id or not quantity:
        return jsonify({"error": "Item ID and Quantity are required"}), 400
    
    current_user_id = get_jwt_identity()
    
    # Delegate to service (SRP: Business logic)
    result, status_code = InventoryService.record_usage(
        item_id=item_id,
        quantity_used=float(quantity),
        user_id=current_user_id,
        remarks=remarks
    )
    
    # Audit log for consumption
    if status_code == 201:
        audit_log('CREATE', 'CONSUMPTION', item_id, {
            'quantity': quantity,
            'remarks': remarks
        })
    
    return jsonify(result), status_code


@inventory_bp.route('/add-stock', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar')  # Only admin/bursar can add stock
def add_stock():
    """
    Record new stock being added to inventory (deliveries, purchases).
    """
    data = request.get_json()
    
    # Extract and validate inputs
    try:
        item_id = data.get('item_id')
        quantity = InputSanitizer.sanitize_number(
            data.get('quantity', 0),
            min_val=0.01,
            max_val=999999.99
        )
        supplier = InputSanitizer.sanitize_text(
            data.get('supplier', ''),
            max_length=100
        )
        remarks = InputSanitizer.sanitize_text(
            data.get('remarks', 'Stock delivery'),
            max_length=500
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    if not item_id or not quantity:
        return jsonify({"error": "Item ID and Quantity are required"}), 400
    
    current_user_id = get_jwt_identity()
    
    # Delegate to service
    result, status_code = InventoryService.record_stock_in(
        item_id=item_id,
        quantity_added=float(quantity),
        supplier=supplier,
        user_id=current_user_id,
        remarks=remarks
    )
    
    # Audit log for stock-in
    if status_code == 201:
        audit_log('CREATE', 'STOCK_IN', item_id, {
            'quantity': quantity,
            'supplier': supplier
        })
    
    return jsonify(result), status_code
