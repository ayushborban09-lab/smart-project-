from flask import Blueprint, jsonify, Response, send_file
from analytics.report_generator import ReportGenerator
from database.repositories import ReportRepository, SessionRepository
from config import Config

report_bp = Blueprint("reports", __name__)

@report_bp.route("/api/reports/<int:session_id>", methods=["GET"])
def get_session_report(session_id):
    sess = SessionRepository.get_by_id(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session not found."}), 404

    try:
        # Generate or refresh report
        report = ReportGenerator.generate(session_id)
        return jsonify({"success": True, "data": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@report_bp.route("/api/reports/<int:session_id>/html", methods=["GET"])
def view_html_report(session_id):
    try:
        report_data = ReportGenerator.generate(session_id)
        html = ReportGenerator._render_html_report(report_data)
        return Response(html, mimetype="text/html")
    except Exception as e:
        return Response(f"<h3>Error generating report: {e}</h3>", mimetype="text/html", status=500)

@report_bp.route("/api/reports/<int:session_id>/download", methods=["GET"])
def download_report(session_id):
    json_path = Config.REPORTS_FOLDER / f"session_{session_id}_report.json"
    if not json_path.exists():
        ReportGenerator.generate(session_id)
    return send_file(json_path, as_attachment=True, download_name=f"session_{session_id}_report.json")
