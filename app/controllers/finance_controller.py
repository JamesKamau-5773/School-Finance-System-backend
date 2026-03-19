from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.fee_collection_service import FeeCollectionService
from app.services.finance_service import FinanceService

finance_bp = Blueprint('finance_bp', __name__, url_prefix='/api/finance')


@finance_bp.route('/pay', methods=['POST'])
@jwt_required()
def process_payment():

    # 1. Extract Data (Controller's sole responsibility: handling HTTP input)
    data = request.get_json()
    student_id = data.get('student_id')
    amount = data.get('amount')
    payment_method = data.get('payment_method')
    reference_no = data.get('reference_no')

    # 2. Basic Input Validation (Ensuring the payload is structurally valid)
    if not all([student_id, amount, payment_method, reference_no]):
        return jsonify({"error": "Missing required payment fields"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount format"}), 400

    # 3. Identify the user making the request via JWT
    current_user_id = get_jwt_identity()

    # 4. Delegate to the Service Layer (SRP: Business logic happens elsewhere)
    result, status_code = FinanceService.process_fee_payment(
        student_id=student_id,
        amount=amount,
        payment_method=payment_method,
        reference_no=reference_no,
        user_id=current_user_id
    )

    # 5. Return the HTTP Response
    return jsonify(result), status_code


@finance_bp.route('/collect', methods=['POST'])
@jwt_required()
def collect():
    data = request.get_json()

    # responsible for request validation and response formatting
    if not data.get('amount') or data.get('amount') <= 0:
        return jsonify({"error": "invalid amount"}), 400

    collector_id = get_jwt_identity()
    result = FeeCollectionService.process_fee_payment(
        student_id=data.get('student_id'),
        total_amount=data.get('amount'),
        collector_id=collector_id
    )

    return jsonify(result), 201


@finance_bp.route('/expense', methods=['POST'])
@jwt_required()
def record_expense():
    data = request.get_json()

    # 1. Extract Data
    vote_head_id = data.get('vote_head_id')
    amount = data.get('amount')
    payment_method = data.get('payment_method')
    reference_no = data.get('reference_no')
    etims_receipt_no = data.get('etims_receipt_no')
    description = data.get('description')

    # 2. Basic Controller Validation
    if not all([vote_head_id, amount, payment_method, etims_receipt_no]):
        return jsonify({"error": "Missing required fields. Ensure eTIMS and Vote Head are provided."}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Expense amount must be greater than zero"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount format"}), 400

    # 3. Get the Bursar's ID
    current_user_id = get_jwt_identity()

    # 4. Delegate to the Service Layer
    result, status_code = FinanceService.record_expense(
        vote_head_id=vote_head_id,
        amount=amount,
        payment_method=payment_method,
        reference_no=reference_no,
        etims_receipt_no=etims_receipt_no,
        description=description,
        user_id=current_user_id
    )

    return jsonify(result), status_code
