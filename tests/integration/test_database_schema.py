"""
Database schema smoke tests.
Ensures critical finance tables exist after model metadata initialization.
"""
from sqlalchemy import inspect
from app import db


def test_finance_tables_exist_in_test_database(app):
    """Critical finance tables should exist in the active test database."""
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())

    assert 'transactions' in table_names
    assert 'ledger_entries' in table_names
