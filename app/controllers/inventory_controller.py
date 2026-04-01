from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.repositories.inventory_repository import InventoryRepository
from app.security import roles_required, InputSanitizer, audit_log
import traceback

inventory_bp = Blueprint('inventory_bp', __name__, url_prefix='/api/inventory')


@inventory_bp.route('/status', methods=['GET'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar', 'clerk', 'storekeeper')
def get_inventory_status():
    """
    Get real-time stock levels and catalog items for the dashboard.
    """
    try:
        items = InventoryRepository.get_all_items()
        return jsonify({
            "status": "success",
            "data": items
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Failed to fetch inventory status."}), 500


@inventory_bp.route('/transactions', methods=['GET'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar', 'clerk', 'storekeeper')
def get_inventory_transactions():
    """Get append-only store ledger transactions with DB-level filtering."""
    try:
        filters = {
            'category': request.args.get('category'),
            'action': request.args.get('action'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'item_id': request.args.get('item_id'),
            'recorded_by': request.args.get('recorded_by'),
            'limit': request.args.get('limit', 200),
            'offset': request.args.get('offset', 0)
        }
        transactions = InventoryRepository.get_filtered_transactions(filters)
        return jsonify({
            "status": "success",
            "data": transactions,
            "count": len(transactions)
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Failed to fetch inventory transactions."}), 500


@inventory_bp.route('/consume', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar', 'clerk', 'storekeeper')
def record_consumption():
    """
    Record daily consumption of food/supplies (OUT Transaction).
    """
    data = request.get_json()
    current_user_id = get_jwt_identity()

    try:
        # 1. Extract and Validate
        item_id = data.get('item_id')
        if not item_id:
            raise ValueError("Item ID is required.")

        quantity = InputSanitizer.sanitize_integer(
            data.get('quantity', 0), min_val=1, max_val=999999
        )
        remarks = InputSanitizer.sanitize_text(
            data.get('remarks', 'Daily consumption'), max_length=500
        )

        # 2. Map to Unified Transaction Engine (OUT)
        transaction_data = {
            'transaction_type': 'OUT',
            'quantity': quantity,
            'party_name': 'Internal Requisition',  # Default for internal use
            'remarks': remarks
        }

        # This will automatically throw a ValueError if stock drops below 0
        result = InventoryRepository.record_transaction(
            item_id, transaction_data, current_user_id)

        # 3. Security Audit Log
        audit_log('CREATE', 'CONSUMPTION_OUT', item_id, {
            'quantity': quantity,
            'remarks': remarks,
            'recorded_by': current_user_id
        })

        return jsonify({
            "status": "success",
            "message": "Consumption recorded successfully.",
            "data": result
        }), 201

    except ValueError as e:
        # Catches both InputSanitizer errors AND "Insufficient Stock" errors from the repository
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "System error processing consumption."}), 500


@inventory_bp.route('/add-stock', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar', 'storekeeper')
def add_stock():
    """
    Record new stock being added to inventory (IN Transaction).
    """
    data = request.get_json()
    current_user_id = get_jwt_identity()

    try:
        # 1. Extract and Validate
        item_id = data.get('item_id')
        if not item_id:
            raise ValueError("Item ID is required.")

        quantity = InputSanitizer.sanitize_integer(
            data.get('quantity', 0), min_val=1, max_val=999999
        )
        supplier = InputSanitizer.sanitize_text(
            data.get('supplier', 'General Supplier'), max_length=100
        )
        remarks = InputSanitizer.sanitize_text(
            data.get('remarks', 'Stock delivery'), max_length=500
        )

        # 2. Map to Unified Transaction Engine (IN)
        transaction_data = {
            'transaction_type': 'IN',
            'quantity': quantity,
            'party_name': supplier,
            'reference_no': data.get('reference_no', ''),
            'remarks': remarks
        }

        result = InventoryRepository.record_transaction(
            item_id, transaction_data, current_user_id)

        # 3. Security Audit Log
        audit_log('CREATE', 'STOCK_IN', item_id, {
            'quantity': quantity,
            'supplier': supplier,
            'recorded_by': current_user_id
        })

        return jsonify({
            "status": "success",
            "message": "Stock added successfully.",
            "data": result
        }), 201

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "System error processing stock addition."}), 500


@inventory_bp.route('/items', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar', 'storekeeper')
def create_inventory_item():
    """Register a completely new item category in the store."""
    data = request.get_json() or {}
    try:
        if 'reorder_level' in data:
            data['reorder_level'] = InputSanitizer.sanitize_integer(
                data.get('reorder_level', 0), min_val=0, max_val=999999
            )
        item = InventoryRepository.create_item(data)
        audit_log('CREATE', 'INVENTORY_ITEM', item['id'], {
                  'item_code': item['item_code']})
        return jsonify({"status": "success", "message": "Item cataloged successfully.", "data": item}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@inventory_bp.route('/items/<uuid:item_id>', methods=['PUT'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar', 'storekeeper')
def edit_inventory_item(item_id):
    """Update item details like name or reorder threshold."""
    data = request.get_json() or {}
    try:
        if 'reorder_level' in data:
            data['reorder_level'] = InputSanitizer.sanitize_integer(
                data.get('reorder_level', 0), min_val=0, max_val=999999
            )
        item = InventoryRepository.update_item(item_id, data)
        audit_log('UPDATE', 'INVENTORY_ITEM', item_id, data)
        return jsonify({"status": "success", "message": "Item updated successfully.", "data": item}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@inventory_bp.route('/items/<uuid:item_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin', 'principal')  # Stricter RBAC for deletions
def remove_inventory_item(item_id):
    """Soft-delete an inventory item."""
    try:
        InventoryRepository.deactivate_item(item_id)
        audit_log('DELETE', 'INVENTORY_ITEM', item_id, {})
        return jsonify({"status": "success", "message": "Item deactivated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
