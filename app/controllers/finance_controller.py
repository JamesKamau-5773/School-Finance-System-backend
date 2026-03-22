from flask import Blueprint, request, jsonify
from app.services.finance_service import FinanceService
from app.repositories.system_repository import SystemRepository
from app.repositories.finance_repository import FinanceRepository

finance_bp = Blueprint('finance', __name__, url_prefix='/api/finance')


@finance_bp.route('/transactions', methods=['GET'])
def get_ledger():
    try:
        data = FinanceService.get_recent_transactions(limit=50)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@finance_bp.route('/pay', methods=['POST'])
def receive_payment():
    """Record a student fee payment."""
    data = request.get_json() or {}

    try:
        # Get system context (user and budget head)
        user_id = SystemRepository.get_or_create_system_user()
        vote_head_id = SystemRepository.get_or_create_default_fee_vote_head()
        
        # Record the transaction
        receipt = FinanceService.process_fee_payment(
            student_id=data.get('student_id'),
            amount=data.get('amount'),
            payment_method=data.get('payment_method'),
            reference_no=data.get('reference_no'),
            user_id=user_id,
            vote_head_id=vote_head_id
        )
        return jsonify({
            "status": "success",
            "message": "Payment recorded successfully",
            "data": receipt
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/expense', methods=['POST'])
def record_expense():
    """Record an expense transaction."""
    data = request.get_json() or {}

    try:
        # Get system context (user and budget head)
        user_id = SystemRepository.get_or_create_system_user()
        vote_head_id = SystemRepository.get_or_create_default_fee_vote_head()
        
        # Record the transaction
        expense = FinanceService.process_expense(
            description=data.get('description'),
            amount=data.get('amount'),
            category=data.get('category'),
            payment_method=data.get('payment_method'),
            reference_no=data.get('reference_no'),
            user_id=user_id,
            vote_head_id=vote_head_id
        )
        return jsonify({
            "status": "success",
            "message": "Expense recorded successfully",
            "data": expense
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/summary', methods=['GET'])
def get_dashboard_summary():
    try:
        summary_data = FinanceRepository.get_dashboard_summary()
        return jsonify(summary_data), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@finance_bp.route('/vote-heads', methods=['GET'])
def get_vote_heads():
    try:
        vote_heads = FinanceService.get_all_vote_heads()
        return jsonify(vote_heads), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@finance_bp.route('/reallocate', methods=['POST'])
def reallocate_funds():
    """Catches the payload for internal Vote Head adjustments."""
    data = request.get_json() or {}
    try:
        adjustment = FinanceService.reallocate_funds(
            source_vote_head=data.get('source_vote_head'),
            destination_vote_head=data.get('destination_vote_head'),
            amount=data.get('amount'),
            authorized_by=data.get('authorized_by', 'PRINCIPAL-01'),
            reason=data.get('reason')
        )
        return jsonify({
            "status": "success",
            "message": "Funds reallocated successfully",
            "data": adjustment
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@finance_bp.route('/capitation', methods=['POST'])
def receive_capitation():
    """Catches the payload for massive MoE block grants."""
    data = request.get_json() or {}
    try:
        # Pass the React payload to the Capitation Splitter
        receipt = FinanceService.process_capitation_disbursement(
            total_amount=data.get('amount'),
            term_identifier=data.get('term', 'Term 1'),
            reference_no=data.get('reference_no')
        )
        return jsonify({
            "status": "success", 
            "message": "FDSE Capitation securely distributed", 
            "data": receipt
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@finance_bp.route('/reports/trial-balance', methods=['GET'])
def get_trial_balance_report():
    """Fetches the Trial Balance for MoE compliance reporting."""
    try:
        tb_data = FinanceRepository.get_trial_balance()
        return jsonify(tb_data), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400 


@finance_bp.route('/ledger/<account_name>', methods=['GET'])
def get_specific_ledger(account_name):
    """Fetches the chronological transaction history for a specific account."""
    try:
        ledger_history = FinanceRepository.get_account_ledger(account_name)
        return jsonify(ledger_history), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400
