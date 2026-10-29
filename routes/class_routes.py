from flask import Blueprint, request, jsonify
from database.repositories import ClassroomRepository, StudentRepository

class_bp = Blueprint("classes", __name__)

@class_bp.route("/api/classes", methods=["GET"])
def get_classes():
    classes = ClassroomRepository.get_all()
    return jsonify({"success": True, "data": classes})

@class_bp.route("/api/classes", methods=["POST"])
def create_class():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    code = data.get("code")
    subject = data.get("subject", "")
    department = data.get("department", "")

    if not name or not code:
        return jsonify({"success": False, "error": "Both 'name' and 'code' are required."}), 400

    try:
        class_id = ClassroomRepository.create(name, code, subject, department)
        return jsonify({"success": True, "class_id": class_id, "message": "Classroom created successfully."}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@class_bp.route("/api/classes/<int:class_id>", methods=["GET"])
def get_class_details(class_id):
    cls = ClassroomRepository.get_by_id(class_id)
    if not cls:
        return jsonify({"success": False, "error": "Classroom not found."}), 404
    students = StudentRepository.get_by_classroom(class_id)
    return jsonify({"success": True, "data": cls, "students": students})

@class_bp.route("/api/classes/<int:class_id>/students", methods=["GET"])
def get_students(class_id):
    students = StudentRepository.get_by_classroom(class_id)
    return jsonify({"success": True, "data": students})

@class_bp.route("/api/classes/<int:class_id>/students", methods=["POST"])
def add_student(class_id):
    data = request.get_json(silent=True) or {}
    student_id_number = data.get("student_id_number")
    name = data.get("name")
    email = data.get("email", "")

    if not student_id_number or not name:
        return jsonify({"success": False, "error": "'student_id_number' and 'name' are required."}), 400

    try:
        student_id = StudentRepository.create(class_id, student_id_number, name, email)
        return jsonify({"success": True, "student_id": student_id, "message": "Student registered."}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
