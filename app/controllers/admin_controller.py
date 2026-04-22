from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import inspect, text

from app import db
from app.security import roles_required, audit_log


admin_bp = Blueprint('admin_bp', __name__, url_prefix='/api/admin')

CONFIRMATION_CODE = 'I_CONFIRM_FINANCIAL_WIPE'


@admin_bp.route('/system/reset-finances', methods=['POST'])
@jwt_required()
@roles_required('admin')
def reset_finances():
    """
    Soft factory reset for finance data only.

    Safety controls:
    - Requires JWT auth plus admin RBAC.
    - Requires an exact confirmation code in the request body.
    - Executes all changes in a single atomic transaction.
    - Rolls back on any error to prevent partial corruption.
    - Preserves students and users while clearing financial history.
    """
    payload = request.get_json(silent=True) or {}

    if payload.get('confirmation_code') != CONFIRMATION_CODE:
        return jsonify({
            'status': 'error',
            'code': 'INVALID_CONFIRMATION',
            'message': 'Invalid confirmation code.'
        }), 400

    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    # Truncate only the whitelisted financial tables if they exist in this schema.
    truncate_candidates = [
        'transactions',
        'expenses',
        'student_ledgers',
        'fee_master',
        'fee_structures',
    ]
    tables_to_truncate = [table for table in truncate_candidates if table in existing_tables]

    if 'students' not in existing_tables:
        return jsonify({
            'status': 'error',
            'code': 'MISSING_TABLE',
            'message': 'students table was not found in the database schema.'
        }), 500

    student_columns = {column['name'] for column in inspector.get_columns('students')}
    zero_columns = [
        column for column in ('current_balance', 'fees_arrears')
        if column in student_columns
    ]

    if not tables_to_truncate and not zero_columns:
        return jsonify({
            'status': 'error',
            'code': 'NOTHING_TO_RESET',
            'message': 'No matching finance tables or balance columns were found.'
        }), 404

    try:
        with db.session.begin():
            for table_name in tables_to_truncate:
                db.session.execute(text(
                    f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'
                ))

            if zero_columns:
                zero_clause = ', '.join(f'{column} = 0' for column in zero_columns)
                db.session.execute(text(
                    f'UPDATE students SET {zero_clause}'
                ))

        actor_id = get_jwt_identity()
        audit_log('UPDATE', 'SYSTEM_RESET_FINANCES', 'system', {
            'actor_id': actor_id,
            'truncated_tables': tables_to_truncate,
            'zeroed_columns': zero_columns,
        })

        current_app.logger.warning(
            'Financial reset completed by user %s. Tables truncated: %s. Columns zeroed: %s',
            actor_id,
            tables_to_truncate,
            zero_columns,
        )

        return jsonify({
            'status': 'success',
            'message': 'Financial reset completed successfully.',
            'truncated_tables': tables_to_truncate,
            'zeroed_columns': zero_columns,
        }), 200

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Financial reset failed; transaction rolled back.')
        return jsonify({
            'status': 'error',
            'code': 'RESET_FAILED',
            'message': 'Financial reset failed and was rolled back.',
            'error': str(exc),
        }), 500