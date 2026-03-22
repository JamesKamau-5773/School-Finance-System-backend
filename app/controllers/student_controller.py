from flask import Blueprint, request, jsonify
from app.repositories.student_repository import StudentRepository
import traceback

student_bp = Blueprint('student', __name__, url_prefix='/api/students')


@student_bp.route('/directory', methods=['GET'])
def get_directory():
    search_term = request.args.get('search')
    only_defaulters = request.args.get('defaulters', 'false').lower()

    try:
        students = StudentRepository.get_students_with_balances(
            search_term, only_defaulters)
        return jsonify({"status": "success", "data": students}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


@student_bp.route('/', methods=['POST'])
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
    """Endpoint to update student details."""
    data = request.get_json()
    try:
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
