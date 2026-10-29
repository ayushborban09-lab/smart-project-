import json
import datetime
from pathlib import Path
from typing import Dict, Any
from config import Config
from database.repositories import (
    SessionRepository, AttendanceRepository, EngagementRepository,
    AudioRepository, RecommendationRepository, ReportRepository, StudentRepository
)
from .session_analytics import SessionAnalytics

class ReportGenerator:
    """
    Generates structured JSON and printable HTML session reports for educators and administration.
    """
    @staticmethod
    def generate(session_id: int) -> Dict[str, Any]:
        Config.init_directories()

        session = SessionRepository.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session with ID {session_id} not found.")

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

        report_payload = {
            "metadata": {
                "report_id": f"REP-SESS-{session_id}",
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "agent_version": "1.0.0",
                "ethical_notice": (
                    "Notice: Attendance is calculated via sustained presence rules. "
                    "Engagement scores are experimental indicators and do not constitute "
                    "proof of academic comprehension or emotional state."
                )
            },
            "session": session,
            "analytics": analytics,
            "attendance": attendance,
            "recommendations": recommendations
        }

        # Save JSON artifact
        json_path = Config.REPORTS_FOLDER / f"session_{session_id}_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2)

        # Generate HTML artifact
        html_content = ReportGenerator._render_html_report(report_payload)
        html_path = Config.REPORTS_FOLDER / f"session_{session_id}_report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Upsert into database
        ReportRepository.upsert_report(
            session_id=session_id,
            total_enrolled=analytics["enrolled_count"],
            total_detected=analytics["total_detected"],
            total_present=analytics["total_present"],
            attendance_rate=analytics["attendance_rate"],
            avg_engagement=analytics["avg_engagement_score"],
            visual_index=analytics["visual_index"],
            audio_index=analytics["audio_index"],
            summary_text=analytics["summary_text"],
            recs_count=analytics["recommendations_count"],
            report_data=report_payload
        )

        return report_payload

    @staticmethod
    def _render_html_report(data: Dict[str, Any]) -> str:
        sess = data["session"]
        ana = data["analytics"]
        att = data["attendance"]
        recs = data["recommendations"]

        att_rows = "".join([
            f"""<tr>
                <td><strong>{r.get('participant_track_id')}</strong></td>
                <td>{r.get('student_name') or 'Anonymous Track'}</td>
                <td><span class="badge {r.get('status')}">{r.get('status').upper()}</span></td>
                <td>{r.get('presence_duration_seconds')}s</td>
                <td>{r.get('presence_percentage')}%</td>
                <td>{r.get('avg_head_pose_forward', 0) * 100:.0f}%</td>
                <td>{'Yes' if r.get('reviewed_by_teacher') else 'Auto'}</td>
            </tr>""" for r in att
        ]) or "<tr><td colspan='7'>No participant tracks recorded.</td></tr>"

        rec_cards = "".join([
            f"""<div class="rec-card">
                <div class="rec-header">
                    <span class="rec-cat">{r.get('category')}</span>
                    <span class="rec-conf">Confidence: {r.get('confidence')}</span>
                </div>
                <div class="rec-obs"><strong>Observation:</strong> {r.get('observation')}</div>
                <div class="rec-act"><strong>Suggested Action:</strong> {r.get('suggested_action')}</div>
                <div class="rec-reason"><strong>Pedagogical Reason:</strong> {r.get('reason')}</div>
            </div>""" for r in recs
        ]) or "<p>No pedagogical recommendations logged for this session.</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Session Report - {sess.get('title')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0A1128; color: #E0E6ED; padding: 30px; }}
        .header {{ border-bottom: 2px solid #00F0FF; padding-bottom: 15px; margin-bottom: 25px; }}
        .header h1 {{ margin: 0; color: #00F0FF; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .kpi-card {{ background: #111D35; padding: 18px; border-radius: 8px; border: 1px solid #1B2A4A; }}
        .kpi-val {{ font-size: 26px; font-weight: bold; color: #00F0FF; }}
        .kpi-lbl {{ font-size: 13px; color: #8A99AD; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; background: #111D35; border-radius: 8px; margin-bottom: 30px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #1B2A4A; font-size: 14px; }}
        th {{ background: #0D1B2A; color: #00F0FF; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge.present {{ background: #00E676; color: #0A1128; }}
        .badge.transient {{ background: #FFB300; color: #0A1128; }}
        .badge.absent {{ background: #FF5252; color: #FFFFFF; }}
        .rec-card {{ background: #111D35; border-left: 4px solid #00F0FF; padding: 15px; margin-bottom: 15px; border-radius: 4px; }}
        .rec-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .rec-cat {{ color: #00F0FF; font-weight: bold; font-size: 13px; }}
        .rec-conf {{ color: #8A99AD; font-size: 12px; }}
        .disclaimer {{ background: #1B2A4A; padding: 12px; border-radius: 6px; font-size: 12px; color: #A0B0C0; margin-top: 40px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Multimodal Attendance & Engagement Agent Report</h1>
        <p>Classroom: {sess.get('classroom_name', 'Class')} ({sess.get('classroom_code', '')}) | Session: {sess.get('title')}</p>
        <p>Status: {sess.get('status').upper()} | Input: {sess.get('input_type')} | Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-val">{ana.get('total_present')} / {ana.get('total_detected')}</div>
            <div class="kpi-lbl">Attendance Rate: {ana.get('attendance_rate')}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{ana.get('avg_engagement_score')}%</div>
            <div class="kpi-lbl">Mean Engagement Index</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{ana.get('visual_index')}% / {ana.get('audio_index')}%</div>
            <div class="kpi-lbl">Visual / Audio Indices</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{ana.get('total_speaking_turns')}</div>
            <div class="kpi-lbl">Conversational Turns</div>
        </div>
    </div>

    <h2>Attendance Log (Sustained Presence)</h2>
    <table>
        <thead>
            <tr>
                <th>Track ID</th>
                <th>Participant Name</th>
                <th>Status</th>
                <th>Observed Presence</th>
                <th>Presence %</th>
                <th>Forward Pose</th>
                <th>Verification</th>
            </tr>
        </thead>
        <tbody>
            {att_rows}
        </tbody>
    </table>

    <h2>Teaching Recommendations & Observations</h2>
    {rec_cards}

    <div class="disclaimer">
        <strong>Privacy & Ethical Compliance:</strong>
        {data['metadata']['ethical_notice']}
    </div>
</body>
</html>"""
