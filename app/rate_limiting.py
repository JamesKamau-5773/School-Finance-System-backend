"""
Rate limiting module (SRP: Centralized rate limit application)

Applies rate limits to API endpoints based on their sensitivity level.
Limits are configured in config.py and applied here without cluttering controllers.
"""

from flask import Flask
from .extensions import limiter


def apply_rate_limits(app: Flask):
    """
    Register rate limit decorators on all API routes based on category.
    
    Categories:
    - AUTH: Sensitive authentication endpoints (5 req/min per IP)
    - WRITE: State-modifying endpoints (30 req/min per IP)
    - READ: Query endpoints (100 req/min per IP)
    """
    
    # Extract rate limit config
    auth_limit = app.config.get('RATELIMIT_AUTH', "5/minute")
    write_limit = app.config.get('RATELIMIT_WRITE', "30/minute")
    read_limit = app.config.get('RATELIMIT_READ', "100/minute")
    
    # AUTH routes - login, register, password reset (most restrictive)
    auth_routes = {
        'auth_bp.login': auth_limit,
        'auth_bp.register': auth_limit,
        'auth_bp.change_password': auth_limit,
        'auth_bp.reset_password': auth_limit,
    }
    
    # WRITE routes - create, update, delete (medium restrictive)
    write_routes = {
        # Finance
        'finance.expense': write_limit,
        'finance.pay': write_limit,
        'finance.reallocate': write_limit,
        'finance.capitation': write_limit,
        # Fees
        'fee.pay': write_limit,
        # Inventory
        'inventory_bp.consume': write_limit,
        'inventory_bp.add_stock': write_limit,
        'inventory_bp.create_item': write_limit,
        'inventory_bp.update_item': write_limit,
        'inventory_bp.delete_item': write_limit,
        # Students
        'student.create': write_limit,
        'student.update': write_limit,
        'student.delete': write_limit,
        # Transactions
        'transaction_bp.create': write_limit,
    }
    
    # READ routes - fetch operations (most permissive)
    read_routes = {
        # Finance
        'finance.transactions': read_limit,
        'finance.summary': read_limit,
        'finance.vote_heads': read_limit,
        'finance.trial_balance': read_limit,
        'finance.ledger': read_limit,
        'finance.student_ledger': read_limit,
        # Fees
        'fee.structures': read_limit,
        'fee.student_ledger': read_limit,
        # Inventory
        'inventory_bp.status': read_limit,
        'inventory_bp.transactions': read_limit,
        # Students
        'student.directory': read_limit,
        'student.list': read_limit,
        'student.ledger': read_limit,
        # Transactions
        'transaction_bp.list': read_limit,
        # Reports
        'report_bp.vote_head': read_limit,
        'report_bp.trial_balance': read_limit,
        # Auth
        'auth_bp.users': read_limit,
    }
    
    # Apply decorators
    for endpoint, limit in auth_routes.items():
        view_func = app.view_functions.get(endpoint)
        if view_func:
            app.view_functions[endpoint] = limiter.limit(limit)(view_func)
    
    for endpoint, limit in write_routes.items():
        view_func = app.view_functions.get(endpoint)
        if view_func:
            app.view_functions[endpoint] = limiter.limit(limit)(view_func)
    
    for endpoint, limit in read_routes.items():
        view_func = app.view_functions.get(endpoint)
        if view_func:
            app.view_functions[endpoint] = limiter.limit(limit)(view_func)
