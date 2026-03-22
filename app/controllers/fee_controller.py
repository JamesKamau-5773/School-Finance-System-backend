from flask import Blueprint, request, jsonify
from app.services.fee_service import FeeService
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
