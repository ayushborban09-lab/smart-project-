from flask import Blueprint, request, jsonify
from database.repositories import (
    EngagementRepository, AudioRepository, RecommendationRepository,
    SessionRepository, AttendanceRepository, StudentRepository
)
from analytics.session_analytics import SessionAnalytics
from fusion.engagement_engine import ETHICAL_DISCLAIMER

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/api/sessions/<int:session_id>/analytics", methods=["GET"])
def get_session_analytics(session_id):
    session = SessionRepository.get_by_id(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session not found."}), 404

    attendance = AttendanceRepository.get_by_session(session_id)
    engagement = EngagementRepository.get_by_session(session_id)
    audio = AudioRepository.get_by_session(session_id)
    recommendations = RecommendationRepository.get_by_session(session_id)
    enrolled = StudentRepository.get_by_classroom(session["classroom_id"])

    analytics = SessionAnalytics.aggregate_session(
        session_info=session,
        attendance_records=attendance,
        engagement_summaries=engagement,
        audio_summaries=audio,
        recommendations=recommendations,
        enrolled_count=len(enrolled)
    )

    analytics["ethical_notice"] = ETHICAL_DISCLAIMER
    return jsonify({"success": True, "data": analytics})

@analytics_bp.route("/api/sessions/<int:session_id>/recommendations", methods=["GET"])
def get_recommendations(session_id):
    recs = RecommendationRepository.get_by_session(session_id)
    return jsonify({"success": True, "data": recs, "count": len(recs)})

@analytics_bp.route("/api/recommendations/<int:rec_id>/status", methods=["POST"])
def update_recommendation_status(rec_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    valid_statuses = {"pending", "acknowledged", "applied", "dismissed"}

    if not new_status or new_status.lower() not in valid_statuses:
        return jsonify({"success": False, "error": f"Invalid status. Must be one of {valid_statuses}."}), 400

    success = RecommendationRepository.update_status(rec_id, new_status.lower())
    if success:
        return jsonify({"success": True, "message": "Recommendation status updated."})
    else:
        return jsonify({"success": False, "error": "Recommendation not found."}), 404
