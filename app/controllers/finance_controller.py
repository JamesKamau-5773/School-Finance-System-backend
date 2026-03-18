from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.fee_collection_service import FeeCollectionService

finance_bp = Blueprint('finance_bp' , __name__, url_prefix= '/api/finance')

@finance_bp.route('/collect', methods=['POST'])
@jwt_required()
def collect():
  data = request.get_json()

  #responsible for request validation and response formatting
  if not data.get('amount') or data.get ('amount') <= 0:
    return jsonify({"error": "invalid amount"}), 400

  collector_id = get_jwt_identity()
  result = FeeCollectionService.process_fee_payment(
    student_id=data.get('student_id'),
    total_amount=data.get('amount'),
    collector_id=collector_id
  )

  return jsonify(result), 201
