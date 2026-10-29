import os
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from database.db import init_db, get_db_path
from database.repositories import (
    ClassroomRepository, StudentRepository, SessionRepository,
    SettingsRepository, AttendanceRepository, EngagementRepository,
    AudioRepository, RecommendationRepository
)
from routes import class_bp, session_bp, attendance_bp, analytics_bp, report_bp
from session_manager import SessionManager

def create_app():
    Config.init_directories()
    init_db()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(class_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(report_bp)

    manager = SessionManager()

    # System Health Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        import cv2
        # Check camera index 0
        cap = cv2.VideoCapture(0)
        camera_available = cap.isOpened() if cap else False
        if cap:
            cap.release()

        # Check microphone
        mic_available = False
        try:
            import sounddevice as sd
            devs = sd.query_devices()
            mic_available = any(d.get("max_input_channels", 0) > 0 for d in devs)
        except Exception:
            pass

        return jsonify({
            "status": "healthy",
            "offline_mode": True,
            "cloud_dependencies": False,
            "database": {
                "connected": True,
                "path": str(get_db_path())
            },
            "hardware": {
                "camera_detected": camera_available,
                "microphone_detected": mic_available,
                "fallback_simulation_ready": True
            },
            "active_workers": len(manager.workers)
        })

    # File Upload Endpoint
    @app.route("/api/upload", methods=["POST"])
    def upload_file():
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file part in the request."}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected."}), 400

        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        allowed = Config.ALLOWED_VIDEO_EXTENSIONS.union(Config.ALLOWED_AUDIO_EXTENSIONS)
        if ext not in allowed:
            return jsonify({"success": False, "error": f"File type '.{ext}' not allowed. Permitted: {sorted(list(allowed))}"}), 400

        save_path = Config.UPLOAD_FOLDER / filename
        file.save(str(save_path))

        file_type = "video" if ext in Config.ALLOWED_VIDEO_EXTENSIONS else "audio"
        return jsonify({
            "success": True,
            "filename": filename,
            "file_type": file_type,
            "file_path": str(save_path),
            "message": f"{file_type.capitalize()} file uploaded successfully."
        })

    # App Settings Endpoints
    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        settings = SettingsRepository.get_all()
        return jsonify({"success": True, "data": settings})

    @app.route("/api/settings", methods=["POST"])
    def update_settings():
        data = request.get_json(silent=True) or {}
        for key, val in data.items():
            SettingsRepository.set_value(key, str(val))
        return jsonify({"success": True, "message": "Settings updated successfully."})

    # Seed Demo Data Endpoint
    @app.route("/api/demo/seed", methods=["POST"])
    def seed_demo_data():
        try:
            # Create demo classroom
            cls_id = ClassroomRepository.create(
                name="AI & Computer Vision 401",
                code="CS-401",
                subject="Artificial Intelligence",
                department="Computer Science"
            )

            # Create sample enrolled students
            s1 = StudentRepository.create(cls_id, "STU-001", "Alex Rivera", "alex@university.edu")
            s2 = StudentRepository.create(cls_id, "STU-002", "Elena Rostova", "elena@university.edu")
            s3 = StudentRepository.create(cls_id, "STU-003", "Marcus Vance", "marcus@university.edu")
            s4 = StudentRepository.create(cls_id, "STU-004", "Sophia Lin", "sophia@university.edu")

            # Create sample session
            sess_id = SessionRepository.create(
                classroom_id=cls_id,
                title="Neural Networks & Deep Learning Seminar",
                input_type="multimodal",
                notes="Lecture with interactive think-pair-share segments."
            )

            # Seed demo attendance with sustained presence
            AttendanceRepository.upsert_attendance(
                session_id=sess_id, track_id="P-101",
                first_seen="2026-10-30T09:00:00Z", last_seen="2026-10-30T09:45:00Z",
                presence_seconds=2600.0, presence_pct=96.3, status="present",
                detection_count=1820, avg_forward=0.88, student_id=s1
            )
            AttendanceRepository.upsert_attendance(
                session_id=sess_id, track_id="P-102",
                first_seen="2026-10-30T09:01:15Z", last_seen="2026-10-30T09:44:30Z",
                presence_seconds=2510.0, presence_pct=93.0, status="present",
                detection_count=1740, avg_forward=0.82, student_id=s2
            )
            AttendanceRepository.upsert_attendance(
                session_id=sess_id, track_id="P-103",
                first_seen="2026-10-30T09:02:00Z", last_seen="2026-10-30T09:43:00Z",
                presence_seconds=2420.0, presence_pct=89.6, status="present",
                detection_count=1680, avg_forward=0.79, student_id=s3
            )
            AttendanceRepository.upsert_attendance(
                session_id=sess_id, track_id="P-104",
                first_seen="2026-10-30T09:20:00Z", last_seen="2026-10-30T09:20:12Z",
                presence_seconds=12.0, presence_pct=0.4, status="transient",
                detection_count=15, avg_forward=0.40, student_id=None
            )

            # Seed demo engagement windows
            import numpy as np
            for i in range(1, 13):
                vis = round(float(np.random.uniform(72, 94)), 1)
                aud = round(float(np.random.uniform(60, 90)), 1)
                fused = round(0.55 * vis + 0.45 * aud, 1)
                lvl = "High Engagement" if fused >= 75 else "Moderate Engagement"
                EngagementRepository.add_summary(
                    session_id=sess_id, window_index=i, visual_score=vis, audio_score=aud,
                    fused_score=fused, engagement_level=lvl, forward_ratio=0.85,
                    movement=0.70, inactivity=0.15, speech=0.45, turns=i * 2,
                    confidence=0.92, quality="Optimal", modality="Multimodal"
                )

            AudioRepository.add_summary(
                session_id=sess_id, speech_sec=1140.0, silence_sec=1560.0,
                turns=24, noise_db=-45.2, state="Active Discussion / Q&A"
            )

            # Seed demo teaching recommendations
            RecommendationRepository.add_recommendation(
                session_id=sess_id,
                category="Interactive Check",
                observation="High collaborative interaction detected during multi-turn dialogue.",
                supporting_indicators={"fused_score": 86.4, "speaking_turns": 24, "speech_ratio": 0.45},
                suggested_action="Review and bookmark the concept check questions used during this interval.",
                reason="Lively turn-taking suggests high conceptual resonance and peer-to-peer engagement.",
                confidence="High"
            )

            SessionRepository.update_status(sess_id, "completed", duration_seconds=2700.0)

            return jsonify({
                "success": True,
                "message": "Demo data populated successfully.",
                "classroom_id": cls_id,
                "session_id": sess_id
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # Frontend Page Routes
    @app.route("/")
    def dashboard_view():
        return render_template("dashboard.html", active_page="dashboard")

    @app.route("/sessions")
    def sessions_view():
        return render_template("sessions.html", active_page="sessions")

    @app.route("/attendance")
    def attendance_view():
        return render_template("attendance.html", active_page="attendance")

    @app.route("/reports")
    def reports_view():
        return render_template("reports.html", active_page="reports")

    return app

# WSGI application entrypoint for Vercel & production servers
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"============================================================")
    print(f" MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT")
    print(f" Local Privacy-Preserving Offline Server")
    print(f" URL: http://127.0.0.1:{port}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

