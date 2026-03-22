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
