from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.fee_collection_service import FeeCollectionService
from app.services.finance_service import FinanceService
from app.security import roles_required, InputSanitizer, audit_log

finance_bp = Blueprint('finance_bp', __name__, url_prefix='/api/finance')


@finance_bp.route('/pay', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar')  # SRP: Authorization delegated to decorator
def process_payment():
    """
    Process student fee payment.
    Only: admin, principal, bursar can process payments.
    """
    # 1. Extract and sanitize data (SRP: Input validation)
    data = request.get_json()
    
    try:
        student_id = data.get('student_id')
        amount = InputSanitizer.sanitize_number(data.get('amount', 0), min_val=0.01, max_val=999999.99)
        payment_method = InputSanitizer.sanitize_text(data.get('payment_method', ''), max_length=50)
        reference_no = InputSanitizer.sanitize_text(data.get('reference_no', ''), max_length=100)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # 2. Validate required fields
    if not all([student_id, amount, payment_method, reference_no]):
        return jsonify({"error": "Missing required payment fields"}), 400
    
    # 3. Get authenticated user
    current_user_id = get_jwt_identity()
    
    # 4. Process payment (SRP: Business logic in service)
    result, status_code = FinanceService.process_fee_payment(
        student_id=student_id,
        amount=amount,
        payment_method=payment_method,
        reference_no=reference_no,
        user_id=current_user_id
    )
    
    # 5. Audit log for financial transaction
    if status_code == 201:
        audit_log('CREATE', 'PAYMENT', student_id, {
            'amount': amount,
            'method': payment_method,
            'reference': reference_no
        })
    
    return jsonify(result), status_code


@finance_bp.route('/collect', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal', 'collector')  # SRP: Role check in decorator
def collect():
    """
    Collect fee payment (delegated collection).
    """
    data = request.get_json()
    
    # Input validation
    try:
        amount = InputSanitizer.sanitize_number(data.get('amount', 0), min_val=0.01, max_val=999999.99)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400
    
    collector_id = get_jwt_identity()
    result = FeeCollectionService.process_fee_payment(
        student_id=data.get('student_id'),
        total_amount=amount,
        collector_id=collector_id
    )
    
    audit_log('CREATE', 'COLLECTION', data.get('student_id'), {
        'amount': amount,
        'collector_id': collector_id
    })
    
    return jsonify(result), 201


@finance_bp.route('/expense', methods=['POST'])
@jwt_required()
@roles_required('admin', 'bursar')  # Only admin/bursar can record expenses
def record_expense():
    """
    Record school expense (requires bursar role).
    """
    data = request.get_json()
    
    # Extract and validate inputs (SRP: Validation in sanitizer)
    try:
        vote_head_id = data.get('vote_head_id')
        amount = InputSanitizer.sanitize_number(data.get('amount', 0), min_val=0.01, max_val=999999.99)
        payment_method = InputSanitizer.sanitize_text(data.get('payment_method', ''), max_length=50)
        reference_no = InputSanitizer.sanitize_text(data.get('reference_no', ''), max_length=100)
        description = InputSanitizer.sanitize_text(data.get('description', ''), max_length=500)
        etims_receipt_no = InputSanitizer.sanitize_text(data.get('etims_receipt_no', ''), max_length=100)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # Validate required fields
    if not all([vote_head_id, amount, payment_method, etims_receipt_no]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["vote_head_id", "amount", "payment_method", "etims_receipt_no"]
        }), 400
    
    # Get authenticated user
    current_user_id = get_jwt_identity()
    
    # Process expense (SRP: Business logic delegated)
    result, status_code = FinanceService.record_expense(
        vote_head_id=vote_head_id,
        amount=amount,
        payment_method=payment_method,
        reference_no=reference_no,
        etims_receipt_no=etims_receipt_no,
        description=description,
        user_id=current_user_id
    )
    
    # Audit log for expense
    if status_code == 201:
        audit_log('CREATE', 'EXPENSE', vote_head_id, {
            'amount': amount,
            'payment_method': payment_method,
            'etims_receipt': etims_receipt_no
        })
    
    return jsonify(result), status_code
