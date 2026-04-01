"""
Error handling middleware for graceful error responses.
Responsibility: Convert internal errors into clear, client-friendly JSON responses.
"""
from flask import jsonify, current_app
from app.validators.transaction_validators import ValidationError as TransactionValidationError
from app.validators.response_validators import ResponseValidationError
import traceback


def register_error_handlers(app):
    """Register all error handlers with the Flask app."""
    
    @app.errorhandler(TransactionValidationError)
    def handle_validation_error(error):
        """Handle input validation errors."""
        current_app.logger.warning(f'Validation error: {error.field} = {error.value} | Reason: {error.reason}')
        
        return jsonify({
            "status": "error",
            "code": "VALIDATION_ERROR",
            "field": error.field,
            "message": error.message,
            "hint": f"Invalid {error.field}. {error.reason}"
        }), 400

    @app.errorhandler(ResponseValidationError)
    def handle_response_validation_error(error):
        """Handle response schema validation errors (internal error - should not reach client)."""
        current_app.logger.error(f'CRITICAL: Response validation failed: {error.message}')
        current_app.logger.error(f'Expected: {error.expected}, Got: {error.actual}')
        traceback.print_exc()
        
        # Return generic error without exposing schema details
        return jsonify({
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An internal error occurred processing your request. Please try again."
        }), 500

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        """Handle general ValueError."""
        error_msg = str(error)
        current_app.logger.warning(f'ValueError: {error_msg}')
        
        return jsonify({
            "status": "error",
            "code": "INVALID_REQUEST",
            "message": error_msg
        }), 400

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle unexpected exceptions."""
        current_app.logger.error(f'EXCEPTION: {type(error).__name__}: {str(error)}')
        traceback.print_exc()
        
        # Check for specific database errors
        error_str = str(error).lower()
        
        if 'unique' in error_str and 'reference_no' in error_str:
            return jsonify({
                "status": "error",
                "code": "DUPLICATE_REFERENCE",
                "message": "This reference number has already been used. Please use a different reference.",
                "hint": "Reference numbers must be unique. Try adding a timestamp or suffix."
            }), 409
        
        if 'unique' in error_str:
            return jsonify({
                "status": "error",
                "code": "DUPLICATE_ENTRY",
                "message": "This entry already exists. Please check your data and try again."
            }), 409
        
        if 'foreign key' in error_str:
            return jsonify({
                "status": "error",
                "code": "INVALID_REFERENCE",
                "message": "Referenced resource not found. Please verify IDs and try again."
            }), 400
        
        # Generic internal error
        return jsonify({
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact support."
        }), 500

    app.logger.info("Error handlers registered successfully")
