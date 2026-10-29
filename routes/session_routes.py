from flask import Blueprint, request, jsonify, Response
from database.repositories import SessionRepository
from session_manager import SessionManager
import time

session_bp = Blueprint("sessions", __name__)
manager = SessionManager()

@session_bp.route("/api/sessions", methods=["GET"])
def get_sessions():
    sessions = SessionRepository.get_all()
    # Augment with live running status
    for s in sessions:
        s["is_live"] = manager.is_session_running(s["id"])
    return jsonify({"success": True, "data": sessions})

@session_bp.route("/api/sessions", methods=["POST"])
def create_session():
    data = request.get_json(silent=True) or {}
    classroom_id = data.get("classroom_id")
    title = data.get("title")
    input_type = data.get("input_type", "webcam")
    video_source = data.get("video_source", "")
    audio_source = data.get("audio_source", "")
    notes = data.get("notes", "")

    if not classroom_id or not title:
        return jsonify({"success": False, "error": "'classroom_id' and 'title' are required."}), 400

    try:
        session_id = SessionRepository.create(
            classroom_id=int(classroom_id),
            title=title,
            input_type=input_type,
            video_source=video_source,
            audio_source=audio_source,
            notes=notes
        )
        return jsonify({"success": True, "session_id": session_id, "message": "Session created successfully."}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@session_bp.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    sess = SessionRepository.get_by_id(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session not found."}), 404
    sess["is_live"] = manager.is_session_running(session_id)
    return jsonify({"success": True, "data": sess})

@session_bp.route("/api/sessions/<int:session_id>/start", methods=["POST"])
def start_session_processing(session_id):
    sess = SessionRepository.get_by_id(session_id)
    if not sess:
        return jsonify({"success": False, "error": "Session not found."}), 404

    data = request.get_json(silent=True) or {}
    input_type = data.get("input_type", sess.get("input_type", "webcam"))
    video_source = data.get("video_source", sess.get("video_source"))
    audio_source = data.get("audio_source", sess.get("audio_source"))

    success = manager.start_session(
        session_id=session_id,
        input_type=input_type,
        video_path=video_source,
        audio_path=audio_source
    )
    if success:
        return jsonify({"success": True, "message": f"Processing started for session #{session_id}."})
    else:
        return jsonify({"success": False, "error": "Failed to start session processing."}), 500

@session_bp.route("/api/sessions/<int:session_id>/stop", methods=["POST"])
def stop_session_processing(session_id):
    success = manager.stop_session(session_id)
    if success:
        return jsonify({"success": True, "message": f"Session #{session_id} stopped and finalized."})
    else:
        return jsonify({"success": False, "error": "Session was not running or could not be stopped."}), 400

@session_bp.route("/api/sessions/<int:session_id>/status", methods=["GET"])
def get_session_status(session_id):
    worker = manager.get_worker(session_id)
    if worker and worker.is_running:
        status = worker.get_status()
        return jsonify({"success": True, "is_live": True, "data": status})
    else:
        sess = SessionRepository.get_by_id(session_id)
        if not sess:
            return jsonify({"success": False, "error": "Session not found."}), 404
        return jsonify({
            "success": True,
            "is_live": False,
            "data": {
                "session_id": session_id,
                "status": sess.get("status"),
                "duration_seconds": sess.get("duration_seconds", 0.0),
                "fps": 0.0
            }
        })

@session_bp.route("/api/sessions/<int:session_id>/feed")
def stream_video_feed(session_id):
    """
    MJPEG live video stream endpoint with participant bounding boxes and HUD.
    """
    worker = manager.get_worker(session_id)
    if not worker or not worker.is_running:
        # If session is not currently running, return placeholder image
        import cv2
        import numpy as np
        placeholder = np.full((360, 640, 3), (20, 15, 10), dtype=np.uint8)
        cv2.putText(placeholder, "SESSION INACTIVE / WAITING TO START", (80, 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 240, 255), 2)
        _, jpeg = cv2.imencode(".jpg", placeholder)
        return Response(jpeg.tobytes(), mimetype="image/jpeg")

    def generate_frames():
        while True:
            w = manager.get_worker(session_id)
            if not w or not w.is_running:
                break
            frame_bytes = w.get_latest_frame()
            if frame_bytes:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            time.sleep(0.06)  # Approx 15 FPS

    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
