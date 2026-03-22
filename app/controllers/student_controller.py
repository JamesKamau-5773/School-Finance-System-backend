from flask import Blueprint, request, jsonify
from app.repositories.student_repository import StudentRepository
from app.utils.validators import is_valid_uuid
import traceback

student_bp = Blueprint('student', __name__, url_prefix='/api/students')


def _get_directory_payload():
    search_term = request.args.get('search')
    only_defaulters = request.args.get('defaulters', 'false').lower()

    students = StudentRepository.get_students_with_balances(
        search_term, only_defaulters)
    return jsonify({"status": "success", "data": students}), 200


@student_bp.route('/directory', methods=['GET'])
def get_directory():
    try:
        return _get_directory_payload()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('', methods=['GET'])
@student_bp.route('/', methods=['GET'])
def get_students():
    try:
        return _get_directory_payload()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('/', methods=['POST'])
@student_bp.route('/directory', methods=['POST'])
@student_bp.route('/directory/', methods=['POST'])
def register_student():
    """Endpoint to add a new student."""
    data = request.get_json()
    try:
        student = StudentRepository.create_student(data)
        return jsonify({"status": "success", "message": "Student registered successfully.", "data": student}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Failed to register student. Check if Admission Number is unique."}), 400


@student_bp.route('/<int:student_id>', methods=['PUT'])
def edit_student(student_id):
    
    data = request.get_json()
    try:
        student = StudentRepository.update_student(student_id, data)
        return jsonify({"status": "success", "message": "Student updated successfully.", "data": student}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('/<string:student_id>', methods=['PUT'])
@student_bp.route('/<string:student_id>/', methods=['PUT'])
@student_bp.route('/directory/<string:student_id>', methods=['PUT'])
@student_bp.route('/directory/<string:student_id>/', methods=['PUT'])
def edit_student_uuid(student_id):
    """Compatibility endpoint to update student details using UUID routes."""
    data = request.get_json()
    try:
        if not is_valid_uuid(student_id):
            return jsonify({"status": "error", "message": "Invalid student_id format"}), 400

        student = StudentRepository.update_student(student_id, data)
        return jsonify({"status": "success", "message": "Student updated successfully.", "data": student}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('/<int:student_id>', methods=['DELETE'])
def remove_student(student_id):
    """Endpoint to soft-delete a student."""
    try:
        StudentRepository.deactivate_student(student_id)
        return jsonify({"status": "success", "message": "Student deactivated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('/<string:student_id>', methods=['DELETE'])
@student_bp.route('/<string:student_id>/', methods=['DELETE'])
@student_bp.route('/directory/<string:student_id>', methods=['DELETE'])
@student_bp.route('/directory/<string:student_id>/', methods=['DELETE'])
def remove_student_uuid(student_id):
    """Compatibility endpoint to soft-delete student details using UUID routes."""
    try:
        if not is_valid_uuid(student_id):
            return jsonify({"status": "error", "message": "Invalid student_id format"}), 400

        StudentRepository.deactivate_student(student_id)
        return jsonify({"status": "success", "message": "Student deactivated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('/<string:student_id>/ledger', methods=['GET'])
def get_student_ledger(student_id):
    """Fetches a specific student's invoice/payment ledger history."""
    try:
        if not is_valid_uuid(student_id):
            return jsonify({"status": "error", "message": "Invalid student_id format"}), 400

        entries = StudentRepository.get_ledger_history(student_id)
        return jsonify({
            "status": "success",
            "data": [entry.to_dict() for entry in entries]
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400
