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

    protected_tables = [
        table for table in ('students', 'users', 'inventory_items')
        if table in existing_tables
    ]

    # Truncate only the whitelisted finance/store history tables if they exist.
    # We intentionally do NOT truncate students, users, roles, or inventory_items.
    truncate_candidates = [
        'transactions',
        'ledger_entries',
        'expenses',
        'student_ledgers',
        'fee_master',
        'fee_structures',
        'stock_transactions',
        'store_transactions',
    ]
    tables_to_truncate = [table for table in truncate_candidates if table in existing_tables]

    # Defensive safeguard: if any protected table has an FK pointing to a table that
    # is about to be truncated, PostgreSQL TRUNCATE ... CASCADE could wipe protected data.
    # Abort the operation instead of risking data loss.
    if (
        db.engine.dialect.name == 'postgresql'
        and protected_tables
        and tables_to_truncate
    ):
        fk_risks = db.session.execute(
            text(
                """
                SELECT
                    dep.relname AS dependent_table,
                    ref.relname AS referenced_table,
                    c.conname AS constraint_name
                FROM pg_constraint c
                JOIN pg_class dep ON dep.oid = c.conrelid
                JOIN pg_namespace dep_ns ON dep_ns.oid = dep.relnamespace
                JOIN pg_class ref ON ref.oid = c.confrelid
                JOIN pg_namespace ref_ns ON ref_ns.oid = ref.relnamespace
                WHERE c.contype = 'f'
                  AND dep_ns.nspname = 'public'
                  AND ref_ns.nspname = 'public'
                  AND dep.relname = ANY(:protected_tables)
                  AND ref.relname = ANY(:truncate_tables)
                """
            ),
            {
                'protected_tables': protected_tables,
                'truncate_tables': tables_to_truncate,
            },
        ).mappings().all()

        if fk_risks:
            return jsonify({
                'status': 'error',
                'code': 'PROTECTED_TABLE_RISK',
                'message': 'Reset aborted: CASCADE dependency risk detected on protected tables.',
                'risks': [dict(row) for row in fk_risks],
            }), 409

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

    inventory_zero_columns = []
    if 'inventory_items' in existing_tables:
        inventory_columns = {column['name'] for column in inspector.get_columns('inventory_items')}
        inventory_zero_columns = [
            column for column in ('current_stock', 'avg_daily_consumption')
            if column in inventory_columns
        ]

    if not tables_to_truncate and not zero_columns and not inventory_zero_columns:
        return jsonify({
            'status': 'error',
            'code': 'NOTHING_TO_RESET',
            'message': 'No matching finance/store tables or balance columns were found.'
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

            if inventory_zero_columns:
                inventory_zero_clause = ', '.join(
                    f'{column} = 0' for column in inventory_zero_columns
                )
                db.session.execute(text(
                    f'UPDATE inventory_items SET {inventory_zero_clause}'
                ))

        actor_id = get_jwt_identity()
        audit_log('UPDATE', 'SYSTEM_RESET_FINANCES', 'system', {
            'actor_id': actor_id,
            'truncated_tables': tables_to_truncate,
            'zeroed_columns': zero_columns,
            'zeroed_inventory_columns': inventory_zero_columns,
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
            'protected_tables': protected_tables,
            'zeroed_columns': zero_columns,
            'zeroed_inventory_columns': inventory_zero_columns,
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