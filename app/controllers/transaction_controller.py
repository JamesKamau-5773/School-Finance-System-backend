from flask import Blueprint, jsonify, request
from app.services.transaction_service import TransactionService
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.security import roles_required, InputSanitizer, audit_log

# Create the Blueprint (Groups all /api/transactions routes together)
transaction_bp = Blueprint('transaction_bp', __name__, url_prefix='/api/transactions')

@transaction_bp.route('/', methods=['GET'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar')  # SRP: RBAC in decorator
def get_transactions():
    """
    Get all transactions (ledger entries).
    Access restricted to admin, principal, and bursar.
    """
    # Call the service layer
    data = TransactionService.get_all_transactions()
    
    # Audit log for transaction listing
    audit_log('READ', 'TRANSACTION_LIST', 'system', {})
    
    return jsonify({"status": "success", "data": data}), 200


@transaction_bp.route('/', methods=['POST'])
@jwt_required()
@roles_required('admin', 'bursar')  # SRP: RBAC - only admins and bursars can record transactions
def record_transaction():
    """
    Record a new transaction (debit/credit entry).
    Access restricted to admin and bursar.
    """
    data = request.get_json()
    current_user_id = get_jwt_identity()
    
    # Extract and validate inputs (SRP: Sanitization in handler)
    try:
        account = InputSanitizer.sanitize_text(
            data.get('account', ''),
            max_length=100
        )
        debit = InputSanitizer.sanitize_number(
            data.get('debit', 0),
            min_val=0,
            max_val=999999.99
        )
        credit = InputSanitizer.sanitize_number(
            data.get('credit', 0),
            min_val=0,
            max_val=999999.99
        )
        description = InputSanitizer.sanitize_text(
            data.get('description', ''),
            max_length=500
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    if not account:
        return jsonify({"error": "Account is required"}), 400
    
    if debit == 0 and credit == 0:
        return jsonify({"error": "Either debit or credit amount is required"}), 400
    
    # Delegate to service (SRP: Business logic)
    result, status_code = TransactionService.record_transaction(
        account=account,
        debit=float(debit),
        credit=float(credit),
        description=description,
        user_id=current_user_id
    )
    
    # Audit log for transaction creation
    if status_code == 201:
        audit_log('CREATE', 'TRANSACTION', account, {
            'debit': debit,
            'credit': credit,
            'description': description
        })
    
    return jsonify(result), status_code