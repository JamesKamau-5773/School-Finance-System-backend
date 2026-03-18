from flask import Blueprint, jsonify
from Flask_jwt_extended import jwt_required
from app.services.report_service import ReportService

report_bp = Blueprint('report_bp', __name__, url_prefix='/api/reports')

@report_bp.route('/vote_head', methods=['GET'])
@jwt_required()
def get_vote_head_summary():

  #Route the request and return JSON
  result,status_code = ReportService.generate_vote_head_summary()
  return jsonify(result), status_code
