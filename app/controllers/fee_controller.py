from flask import Blueprint, request, jsonify
from app.services.fee_service import FeeService
from app.models.student_ledger import StudentLedger
from app.utils.validators import is_valid_uuid
import traceback

# Create a dedicated blueprint for student billing
fee_bp = Blueprint('fee', __name__, url_prefix='/api/fees')


@fee_bp.route('/structures', methods=['POST'])
def create_fee_structure():
    """Endpoint for the Principal to define a new BOM levy."""
    data = request.get_json()
    try:

        fee = FeeService.create_levy(
            name=data.get('name'),
            amount=data.get('amount'),
            academic_year=data.get('academic_year'),
            term=data.get('term'),
            target_cohort=data.get('target_cohort'),
            created_by=data.get('created_by', 'PRINCIPAL-01')
        )
        return jsonify({
            "status": "success",
            "message": "Fee structure created successfully.",
            "data": fee
        }), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


@fee_bp.route('/structures', methods=['GET'])
def get_fee_structures():
    """Endpoint to fetch the catalog of active fees."""
    academic_year = request.args.get('academic_year')
    term = request.args.get('term')

    try:
        fees = FeeService.get_levies(academic_year, term)
        return jsonify({"status": "success", "data": fees}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


@fee_bp.route('/pay', methods=['POST'])
@fee_bp.route('/pay/', methods=['POST'])
def receive_student_payment():
    """Endpoint to process a parent's lump-sum fee payment."""
    data = request.get_json() or {}
    payment_method = data.get('method') or data.get('payment_method')
    reference_no = data.get('reference') or data.get('reference_no')

    try:
        # Require strict validation to prevent ghost money
        if not data.get('student_id') or data.get('amount') is None or not payment_method or not reference_no:
            return jsonify({"status": "error", "message": "Missing required payment fields"}), 400

        result = FeeService.process_student_payment(
            student_id=data['student_id'],
            amount=float(data['amount']),
            payment_method=payment_method,
            reference_no=reference_no,
            received_by=data.get('received_by')
        )

        return jsonify({
            "status": "success",
            "message": "Payment recorded and synced to Cashbook.",
            "data": result
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


@fee_bp.route('/student/<string:student_id>/ledger', methods=['GET'])
def get_student_ledger(student_id):
    """Fetches the specific invoice and payment history for the modal."""
    try:
        if not is_valid_uuid(student_id):
            return jsonify({"status": "error", "message": "Invalid student_id format"}), 400

        entries = (
            StudentLedger.query
            .filter_by(student_id=student_id)
            .order_by(StudentLedger.created_at.desc())
            .all()
        )
        return jsonify({
            "status": "success",
            "data": [entry.to_dict() for entry in entries]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@fee_bp.route('/structures/<int:structure_id>/invoice', methods=['POST'])
def trigger_cohort_invoicing(structure_id):
    """Endpoint to trigger mass billing for a specific fee structure."""
    try:
        result = FeeService.issue_cohort_invoices(structure_id)

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400
