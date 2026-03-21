from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config

# 1. Initialize Extensions (Unbound)
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 2. Bind Extensions to the App instance
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)

    # 3. CORS Configuration (SRP: Environment-aware frontend origins with credentials)
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['http://localhost:5173']),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "X-Total-Count"],
            "supports_credentials": app.config.get('CORS_ALLOW_CREDENTIALS', True),
            "max_age": app.config.get('CORS_MAX_AGE', 3600)
        }
    })

    # 4. Security Headers Middleware (SRP: Add security headers to all responses)
    from app.security import add_security_headers
    
    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    # 5. HTTPS Enforcement (SRP: Redirect HTTP to HTTPS only when explicitly enabled)
    if app.config.get('ENFORCE_HTTPS', False):
        @app.before_request
        def enforce_https():
            from flask import request, redirect
            if request.method == 'OPTIONS':
                return None
            if request.endpoint and request.endpoint != 'health_check':
                if not request.is_secure and not app.config.get('TESTING'):
                    url = request.url.replace('http://', 'https://', 1)
                    return redirect(url, code=301)

    # 6. Setup Developer Logging (SRP: Logging utility)
    from app.utils.logger import setup_logger
    setup_logger(app)

    # 7. Global Error Handler (SRP: Exception handling - no stack traces to client)
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception(f"Unhandled exception: {str(e)}")
        
        # Don't expose stack traces in production
        if app.debug:
            raise e
        
        return jsonify({
            "status": "error",
            "code": "SYS-500",
            "message": "An internal error occurred. Please contact support."
        }), 500
    
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({
            "status": "error",
            "code": "NOT-FOUND",
            "message": "Endpoint not found"
        }), 404
    
    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({
            "status": "error",
            "code": "METHOD-NOT-ALLOWED",
            "message": "HTTP method not allowed"
        }), 405

    # 8. Health Check Route (SRP: Simple liveness probe)
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "message": "Smart School ERP is running"}), 200

    # 9. Register API Blueprints (SRP: Route organization)
    from app.controllers.auth_controller import auth_bp
    from app.controllers.transaction_controller import transaction_bp
    from app.controllers.finance_controller import finance_bp
    from app.controllers.report_controller import report_bp
    from app.controllers.inventory_controller import inventory_bp
    
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(inventory_bp)
    

    return app
