from flask import Blueprint, request, jsonify
from database.repositories import AttendanceRepository

attendance_bp = Blueprint("attendance", __name__)

@attendance_bp.route("/api/sessions/<int:session_id>/attendance", methods=["GET"])
def get_session_attendance(session_id):
    records = AttendanceRepository.get_by_session(session_id)
    return jsonify({"success": True, "data": records, "count": len(records)})

@attendance_bp.route("/api/attendance/<int:record_id>/review", methods=["POST"])
def review_attendance_record(record_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    teacher_name = data.get("teacher_name", "Teacher")
    notes = data.get("notes", "")

    valid_statuses = {"present", "absent", "transient", "excused"}
    if not new_status or new_status.lower() not in valid_statuses:
        return jsonify({"success": False, "error": f"Invalid status. Must be one of {valid_statuses}."}), 400

    success = AttendanceRepository.review_record(
        record_id=record_id,
        status=new_status.lower(),
        notes=notes,
        teacher_name=teacher_name
    )
    if success:
        return jsonify({"success": True, "message": "Attendance record successfully reviewed and updated."})
    else:
        return jsonify({"success": False, "error": "Record not found or update failed."}), 404

@attendance_bp.route("/api/sessions/<int:session_id>/attendance/bind", methods=["POST"])
def bind_student_track(session_id):
    data = request.get_json(silent=True) or {}
    track_id = data.get("track_id")
    student_id = data.get("student_id")

    if not track_id or not student_id:
        return jsonify({"success": False, "error": "'track_id' and 'student_id' are required."}), 400

    try:
        success = AttendanceRepository.bind_student_to_track(
            session_id=session_id,
            track_id=track_id,
            student_id=int(student_id)
        )
        if success:
            return jsonify({"success": True, "message": f"Track {track_id} bound to student #{student_id}."})
        else:
            return jsonify({"success": False, "error": "Failed to bind student to track."}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
