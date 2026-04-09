from flask import Blueprint, request, jsonify
from app.services.finance_service import FinanceService
from app.services.fee_service import FeeService
from app.repositories.system_repository import SystemRepository
from app.repositories.finance_repository import FinanceRepository
from app.repositories.student_repository import StudentRepository
from app.utils.validators import is_valid_uuid
from app.validators.transaction_validators import TransactionFilterValidator
from app.builders.transaction_query_builder import TransactionQueryBuilder
from app.formatters.transaction_formatter import TransactionResponseFormatter
from flask_jwt_extended import jwt_required
from app.security import roles_required
import uuid

finance_bp = Blueprint('finance', __name__, url_prefix='/api/finance')


@finance_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """
    Endpoint to fetch filtered cashbook transactions with Omni-Search and Advanced Filters.
    
    Filters (all optional):
    - search: Broad omni-search across descriptions, references, accounts
    - type: INCOME or EXPENSE (case-insensitive)
    - date: Exact date in YYYY-MM-DD format
    - category: Vote head name or code
    - method: Payment method name
    - minAmount: Minimum transaction amount (numeric)
    """
    try:
        # 1. VALIDATE: Extract and normalize filters
        raw_filters = {
            'search': request.args.get('search'),
            'date': request.args.get('date'),
            'type': request.args.get('type'),
            'category': request.args.get('category'),
            'method': request.args.get('method'),
            'minAmount': request.args.get('minAmount')
        }
        
        # This will raise TransactionValidationError with clear messages if any filter is invalid
        validated_filters = TransactionFilterValidator.validate_filters(raw_filters)
        
        # 2. BUILD: Construct query with validated filters
        query_builder = TransactionQueryBuilder()
        transactions = (query_builder
            .build_base_query()
            .apply_all_filters(validated_filters)
            .order_by_newest()
            .execute()
        )
        
        # 3. FORMAT: Transform to validated API response with correct type labels
        response = TransactionResponseFormatter.format_api_response(transactions)
        
        return jsonify(response), 200
        
    except Exception as e:
        # Error handlers will catch and format appropriately
        raise


@finance_bp.route('/pay', methods=['POST'])
def receive_payment():
    """Record a student fee payment."""
    data = request.get_json() or {}
    payment_method = data.get('payment_method') or data.get('method')
    reference_no = data.get('reference_no') or data.get('reference')

    try:
        # Get system context (user and budget head)
        user_id = SystemRepository.get_or_create_system_user()
        vote_head_id = SystemRepository.get_or_create_default_fee_vote_head()
        
        # Record the transaction
        receipt = FinanceService.process_fee_payment(
            student_id=data.get('student_id'),
            amount=data.get('amount'),
            payment_method=payment_method,
            reference_no=reference_no,
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


@finance_bp.route('/vote-heads', methods=['POST'])
@jwt_required()
@roles_required('admin', 'principal')
def create_vote_head():
    """Create a new vote head."""
    data = request.get_json() or {}
    try:
        vote_head = FinanceService.create_vote_head(data)
        return jsonify({
            "status": "success",
            "message": "Vote head created successfully",
            "data": vote_head
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/vote-heads/<string:vote_head_id>', methods=['PUT'])
@jwt_required()
@roles_required('admin', 'principal')
def update_vote_head(vote_head_id):
    """Update an existing vote head."""
    data = request.get_json() or {}
    try:
        if not is_valid_uuid(vote_head_id):
            return jsonify({"status": "error", "message": "Invalid vote_head_id format"}), 400

        vote_head_uuid = uuid.UUID(vote_head_id)

        vote_head = FinanceService.update_vote_head(vote_head_uuid, data)
        return jsonify({
            "status": "success",
            "message": "Vote head updated successfully",
            "data": vote_head
        }), 200
    except ValueError as e:
        if str(e) == 'vote head not found':
            return jsonify({"status": "error", "message": str(e)}), 404
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/vote-heads/<string:vote_head_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin', 'principal')
def delete_vote_head(vote_head_id):
    """Delete an existing vote head."""
    try:
        if not is_valid_uuid(vote_head_id):
            return jsonify({"status": "error", "message": "Invalid vote_head_id format"}), 400

        vote_head_uuid = uuid.UUID(vote_head_id)

        FinanceService.delete_vote_head(vote_head_uuid)
        return jsonify({
            "status": "success",
            "message": "Vote head deleted successfully"
        }), 200
    except ValueError as e:
        if str(e) == 'vote head not found':
            return jsonify({"status": "error", "message": str(e)}), 404
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


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


@finance_bp.route('/student/<string:student_id>/ledger', methods=['GET'])
def get_student_ledger_compat(student_id):
    """Compatibility endpoint for frontend student ledger queries under /api/finance."""
    try:
        if not is_valid_uuid(student_id):
            return jsonify({"status": "error", "message": "Invalid student_id format"}), 400

        entries = StudentRepository.get_ledger_history(student_id)
        return jsonify({
            "status": "success",
            "data": [entry.to_dict() for entry in entries]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@finance_bp.route('/fee-structures/<int:structure_id>/invoice', methods=['POST'])
@finance_bp.route('/fee-structures/<int:structure_id>/invoice/', methods=['POST'])
def issue_fee_structure_invoices_compat(structure_id):
    """Compatibility endpoint for issuing cohort invoices via /api/finance."""
    try:
        result = FeeService.issue_cohort_invoices(structure_id)
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
