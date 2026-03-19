from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config

# 1. Initialize Extensions (Unbound)
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 2. Bind Extensions to the App instance
    db.init_app(app)
    jwt.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)

    # Restrict CORS to only allow requests from your future React frontend
    cors.init_app(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
                  

    # 3. Setup Developer Logging
    from app.utils.logger import setup_logger
    setup_logger(app)

    # 4. Global Error Catching (Protects the client UI from seeing raw code)
    @app.errorhandler(Exception)
    def handle_exception(e):
        # This writes the exact line number of the crash to logs/school_erp.log
        app.logger.exception(f"System Crash: {str(e)}")

        # This sends a clean, polite JSON response to the React frontend
        return jsonify({
            "status": "error",
            "code": "SYS-500",
            "message": "An internal system error occurred. Please quote code SYS-500 to support."
        }), 500

    # 5. Health Check Route (To prove the server is alive)
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "online", "message": "Smart School ERP Engine is running."}), 200

    # Register Blueprints (Controllers)
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

    return app
