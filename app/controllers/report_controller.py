from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.services.report_service import ReportService
from app.security import roles_required, audit_log

report_bp = Blueprint('report_bp', __name__, url_prefix='/api/reports')

@report_bp.route('/vote_head', methods=['GET'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar')  # SRP: RBAC in decorator
def get_vote_head_summary():
    """
    Get financial summary by vote head (budget categories).
    Access restricted to admin, principal, and bursar.
    """
    # Controller acts as the traffic cop, delegating to the service
    result, status_code = ReportService.generate_vote_head_summary()
    
    # Audit log for report access
    if status_code == 200:
        audit_log('READ', 'REPORT_VOTE_HEAD', 'system', {})
    
    return jsonify(result), status_code

@report_bp.route('/trial-balance', methods=['GET'])
@jwt_required()
@roles_required('admin', 'principal', 'bursar')  # SRP: RBAC in decorator
def get_trial_balance():
    """
    Get trial balance (debit/credit verification).
    Access restricted to admin, principal, and bursar.
    """
    # Controller acts as the traffic cop, delegating to the service
    result, status_code = ReportService.generate_trial_balance()
    
    # Audit log for report access
    if status_code == 200:
        audit_log('READ', 'REPORT_TRIAL_BALANCE', 'system', {})
    
    return jsonify(result), status_code