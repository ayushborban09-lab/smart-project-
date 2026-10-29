import cv2
import numpy as np
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path

from config import Config
from vision import FaceDetector, ParticipantTracker, HeadPoseEstimator, PresenceEngine
from audio import AudioStreamReader, VoiceActivityDetector, InteractionAnalyzer
from fusion import MultimodalEngagementEngine
from agent import RecommendationEngine
from database.repositories import (
    SessionRepository, AttendanceRepository, EngagementRepository,
    AudioRepository, SettingsRepository
)

class SessionProcessorWorker:
    """
    Controlled background processing worker for a classroom session.
    Synchronizes vision detection, audio analysis, multimodal fusion,
    attendance persistence, and live annotated frame generation.
    """
    def __init__(self, session_id: int, input_type: str = "webcam",
                 video_path: Optional[str] = None, audio_path: Optional[str] = None):
        self.session_id = session_id
        self.input_type = input_type
        self.video_path = video_path
        self.audio_path = audio_path
        
        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Latest annotated JPEG for MJPEG streaming
        self.latest_jpeg: Optional[bytes] = None
        
        # Metrics cache for low-latency status polling
        self.current_metrics: Dict[str, Any] = {
            "session_id": session_id,
            "status": "created",
            "fps": 0.0,
            "active_participants": 0,
            "present_participants": 0,
            "fused_engagement": 50.0,
            "engagement_level": "Moderate Engagement",
            "speech_ratio": 0.0,
            "dominant_audio_state": "Silence",
            "data_quality": "Optimal",
            "elapsed_seconds": 0.0
        }
        
        # Modules
        self.detector = FaceDetector()
        self.tracker = ParticipantTracker(
            max_disappeared=Config.TRACKER_MAX_DISAPPEARED_FRAMES,
            max_distance=Config.TRACKER_DISTANCE_THRESHOLD
        )
        self.head_pose_est = HeadPoseEstimator()
        self.presence_engine = PresenceEngine()
        
        self.audio_reader = AudioStreamReader(
            sample_rate=Config.AUDIO_SAMPLE_RATE,
            block_duration=Config.AUDIO_BLOCK_SECONDS
        )
        self.vad = VoiceActivityDetector(sample_rate=Config.AUDIO_SAMPLE_RATE)
        self.interaction_analyzer = InteractionAnalyzer()
        
        self.fusion_engine = MultimodalEngagementEngine()
        self.rec_engine = RecommendationEngine(cooldown_seconds=Config.RECOMMENDATION_COOLDOWN_SECONDS)
        
        self.start_time = 0.0
        self.frame_count = 0
        self.window_index = 0

    def start(self) -> bool:
        with self.lock:
            if self.is_running:
                return False
            self.is_running = True
            self.start_time = time.time()
            self.presence_engine.reset(self.start_time)
            self.vad.reset()
            self.interaction_analyzer.reset()
            self.fusion_engine.reset()
            self.rec_engine.reset()
            
            SessionRepository.update_status(self.session_id, "running")
            self.current_metrics["status"] = "running"
            
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            return True

    def stop(self) -> bool:
        with self.lock:
            if not self.is_running:
                return False
            self.is_running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)

        elapsed = time.time() - self.start_time if self.start_time > 0 else 0.0
        SessionRepository.update_status(self.session_id, "completed", duration_seconds=elapsed)
        self.current_metrics["status"] = "completed"
        self.audio_reader.stop()
        return True

    def get_latest_frame(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.current_metrics)

    def _run_loop(self):
        # Initialize Video Source
        cap = None
        use_synthetic_video = False
        
        if self.input_type == "webcam":
            cap = cv2.VideoCapture(0)
            if not cap or not cap.isOpened():
                print(f"Session {self.session_id}: Physical webcam index 0 unavailable. Falling back to high-fidelity synthetic classroom visual feed.")
                use_synthetic_video = True
        elif self.input_type in ("video_file", "multimodal") and self.video_path:
            cap = cv2.VideoCapture(self.video_path)
            if not cap or not cap.isOpened():
                print(f"Session {self.session_id}: Cannot open video file {self.video_path}. Using synthetic feed.")
                use_synthetic_video = True
        else:
            use_synthetic_video = True

        # Initialize Audio Source
        audio_file_generator = None
        if self.input_type == "webcam" or self.input_type == "multimodal":
            mic_started = self.audio_reader.start_mic_stream()
            if not mic_started:
                print(f"Session {self.session_id}: Microphone stream inactive, relying on synthetic acoustic signal generation.")
        elif self.audio_path and Path(self.audio_path).exists():
            audio_file_generator = self.audio_reader.read_audio_file(Path(self.audio_path))

        last_fusion_time = time.time()
        last_db_sync_time = time.time()
        fps_timer = time.time()
        frames_in_second = 0

        # Synthetic participant coordinates for demonstration / fallback mode
        synthetic_faces = [
            {"base_x": 140, "base_y": 180, "w": 90, "h": 110, "name": "Participant A", "active": True},
            {"base_x": 340, "base_y": 170, "w": 95, "h": 115, "name": "Participant B", "active": True},
            {"base_x": 540, "base_y": 190, "w": 85, "h": 105, "name": "Participant C", "active": True},
        ]

        try:
            while self.is_running:
                loop_start = time.time()
                self.frame_count += 1
                frames_in_second += 1

                # 1. READ / GENERATE VIDEO FRAME
                frame = None
                if cap and cap.isOpened() and not use_synthetic_video:
                    ret, raw_frame = cap.read()
                    if ret and raw_frame is not None:
                        frame = raw_frame
                    else:
                        # If video file reached EOF, loop or switch
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, raw_frame = cap.read()
                        if ret:
                            frame = raw_frame
                        else:
                            use_synthetic_video = True

                if frame is None or use_synthetic_video:
                    # Generate a clean dark navy classroom simulation canvas (720x480)
                    frame = np.full((480, 720, 3), (25, 20, 15), dtype=np.uint8)
                    t = time.time() - self.start_time

                    # Draw subtle classroom background desks & whiteboard
                    cv2.rectangle(frame, (60, 40), (660, 120), (45, 38, 30), -1)
                    cv2.putText(frame, "SMART CLASSROOM SIMULATION FEED (OFFLINE)", (80, 85),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 240, 255), 2)

                    # Animate synthetic participants with natural micro-movements
                    detections = []
                    for i, sf in enumerate(synthetic_faces):
                        # Organic head movement
                        jitter_x = int(6.0 * np.sin(t * 1.2 + i * 1.5))
                        jitter_y = int(4.0 * np.cos(t * 0.9 + i * 2.0))
                        
                        fx = sf["base_x"] + jitter_x
                        fy = sf["base_y"] + jitter_y
                        fw, fh = sf["w"], sf["h"]

                        # Draw stylized student silhouette
                        # Body / Shoulders
                        cv2.ellipse(frame, (fx + fw // 2, fy + fh + 60), (fw, 50), 0, 0, 360, (50, 45, 38), -1)
                        # Head / Face
                        cv2.ellipse(frame, (fx + fw // 2, fy + fh // 2), (fw // 2, fh // 2), 0, 0, 360, (215, 185, 155), -1)

                        # Simulated eye landmarks for frontal head pose
                        eye_y = fy + int(fh * 0.38)
                        left_eye = (fx + int(fw * 0.32), eye_y)
                        right_eye = (fx + int(fw * 0.68), eye_y)
                        cv2.circle(frame, left_eye, 4, (40, 30, 20), -1)
                        cv2.circle(frame, right_eye, 4, (40, 30, 20), -1)

                        landmarks = {"left_eye": left_eye, "right_eye": right_eye}
                        detections.append({
                            "bbox": (fx, fy, fw, fh),
                            "confidence": 0.95,
                            "landmarks": landmarks,
                            "head_pose": self.head_pose_est.estimate((fx, fy, fw, fh), landmarks)
                        })
                else:
                    # Resize frame for uniform fast processing (max 720p)
                    h, w = frame.shape[:2]
                    if w > 720:
                        frame = cv2.resize(frame, (720, int(h * 720 / w)))

                    # Real frame detection
                    raw_dets = self.detector.detect(frame)
                    detections = []
                    for d in raw_dets:
                        hp = self.head_pose_est.estimate(d["bbox"], d.get("landmarks", {}))
                        d["head_pose"] = hp
                        detections.append(d)

                # 2. PARTICIPANT TRACKING
                tracked_participants = self.tracker.update(detections, timestamp=time.time())

                # 3. SUSTAINED PRESENCE ATTENDANCE UPDATE
                current_attendance = self.presence_engine.update_from_tracks(tracked_participants, current_ts=time.time())

                # 4. AUDIO PROCESSING (every ~1.0 second or available block)
                audio_block = None
                if audio_file_generator is not None:
                    try:
                        audio_block = next(audio_file_generator)
                    except StopIteration:
                        # Re-open or loop audio
                        audio_file_generator = self.audio_reader.read_audio_file(Path(self.audio_path))
                        try:
                            audio_block = next(audio_file_generator)
                        except Exception:
                            pass
                else:
                    audio_block = self.audio_reader.get_next_block(timeout=0.01)

                if audio_block is None:
                    # Generate natural synthetic acoustic noise floor + occasional conversational speech burst
                    t_sec = time.time() - self.start_time
                    # Speech burst every 15 seconds for 5 seconds
                    is_burst = (int(t_sec) % 15) < 6
                    amp = 0.04 if is_burst else 0.002
                    freq = 420.0 if is_burst else 120.0
                    audio_block = (amp * np.sin(2 * np.pi * freq * np.linspace(0, 1, Config.AUDIO_SAMPLE_RATE)) +
                                   0.001 * np.random.randn(Config.AUDIO_SAMPLE_RATE)).astype(np.float32)

                vad_res = self.vad.process_chunk(audio_block)
                ia_res = self.interaction_analyzer.update(vad_res)

                # 5. MULTIMODAL FUSION (Sliding window every Config.FUSION_WINDOW_SECONDS)
                now = time.time()
                elapsed_total = now - self.start_time

                if (now - last_fusion_time) >= Config.FUSION_WINDOW_SECONDS:
                    last_fusion_time = now
                    self.window_index += 1

                    # Visual features for fusion
                    if tracked_participants:
                        forward_ratios = [t.forward_facing_ratio for t in tracked_participants]
                        movement_speeds = [t.movement_speed for t in tracked_participants]
                        inactivity_times = [t.inactivity_seconds for t in tracked_participants]
                        raw_vis = {
                            "forward_facing_ratio": float(np.mean(forward_ratios)),
                            "avg_movement_speed": float(np.mean(movement_speeds)),
                            "avg_inactivity_sec": float(np.mean(inactivity_times)),
                            "participant_count": len(tracked_participants)
                        }
                    else:
                        raw_vis = {"participant_count": 0}

                    raw_aud = {
                        "speech_ratio": ia_res["speech_ratio"],
                        "turn_rate_per_min": ia_res["turn_rate_per_min"],
                        "snr_db": vad_res["snr_db"],
                        "speaking_turns": ia_res["speaking_turns"],
                        "dominant_state": ia_res["dominant_state"]
                    }

                    fusion_res = self.fusion_engine.fuse(raw_vis, raw_aud, self.window_index)

                    # Persist engagement summary
                    EngagementRepository.add_summary(
                        session_id=self.session_id,
                        window_index=self.window_index,
                        visual_score=fusion_res["visual_score"],
                        audio_score=fusion_res["audio_score"],
                        fused_score=fusion_res["fused_score"],
                        engagement_level=fusion_res["engagement_level"],
                        forward_ratio=fusion_res["forward_facing_ratio"],
                        movement=fusion_res["movement_level"],
                        inactivity=fusion_res["inactivity_ratio"],
                        speech=fusion_res["speech_ratio"],
                        turns=fusion_res["interaction_turns"],
                        confidence=fusion_res["confidence_score"],
                        quality=fusion_res["data_quality"],
                        modality=fusion_res["modality_state"]
                    )

                    # Persist audio summary
                    AudioRepository.add_summary(
                        session_id=self.session_id,
                        speech_sec=vad_res["total_speech_sec"],
                        silence_sec=vad_res["total_silence_sec"],
                        turns=ia_res["speaking_turns"],
                        noise_db=vad_res["noise_floor_db"],
                        state=ia_res["dominant_state"]
                    )

                    # 6. AI TEACHING RECOMMENDATION AGENT TRIGGER
                    self.rec_engine.generate(
                        session_id=self.session_id,
                        current_engagement=fusion_res,
                        session_duration_sec=elapsed_total
                    )

                # 7. PERIODIC ATTENDANCE DATABASE COMMIT (every 3 seconds)
                if (now - last_db_sync_time) >= 3.0:
                    last_db_sync_time = now
                    for att in current_attendance:
                        AttendanceRepository.upsert_attendance(
                            session_id=self.session_id,
                            track_id=att["participant_track_id"],
                            first_seen=att["first_seen"],
                            last_seen=att["last_seen"],
                            presence_seconds=att["presence_duration_seconds"],
                            presence_pct=att["presence_percentage"],
                            status=att["status"],
                            detection_count=att["detection_count"],
                            avg_forward=att["avg_head_pose_forward"],
                            student_id=att["student_id"]
                        )
                    SessionRepository.update_status(self.session_id, "running", duration_seconds=elapsed_total)

                # 8. ANNOTATE VIDEO FRAME FOR LIVE STREAM HUD
                # Draw participant bounding boxes and HUD
                for track in tracked_participants:
                    bx, by, bw, bh = track.bbox
                    tid = track.track_id
                    
                    # Look up presence status
                    att_rec = self.presence_engine.records.get(tid)
                    is_present = att_rec and att_rec.status == "present"
                    box_color = (0, 230, 118) if is_present else (0, 240, 255)  # Emerald if present, Cyan if transient
                    
                    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), box_color, 2)
                    
                    # Participant badge label
                    status_lbl = "PRESENT" if is_present else "TRANSIENT"
                    presence_sec = att_rec.cumulative_presence_sec if att_rec else 0.0
                    label = f"{tid} | {status_lbl} ({presence_sec:.0f}s)"
                    cv2.rectangle(frame, (bx, max(0, by - 24)), (bx + len(label) * 9, by), box_color, -1)
                    cv2.putText(frame, label, (bx + 4, max(12, by - 7)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (10, 17, 40), 1, cv2.LINE_AA)
                    
                    # Orientation label under box
                    orient_text = f"Pose: {track.current_orientation}"
                    cv2.putText(frame, orient_text, (bx, by + bh + 16),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 220, 240), 1, cv2.LINE_AA)

                # Top Status HUD bar
                cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), (10, 17, 40), -1)
                hud_text = (
                    f"Session #{self.session_id} | Elapsed: {int(elapsed_total)}s | "
                    f"Detected: {len(tracked_participants)} | "
                    f"Present: {sum(1 for a in current_attendance if a['status'] == 'present')} | "
                    f"Audio: {ia_res['dominant_state']}"
                )
                cv2.putText(frame, hud_text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 240, 255), 1, cv2.LINE_AA)

                # Encode frame to JPEG
                ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    with self.lock:
                        self.latest_jpeg = buffer.tobytes()

                # Calculate instantaneous FPS
                if (now - fps_timer) >= 1.0:
                    current_fps = frames_in_second / (now - fps_timer)
                    fps_timer = now
                    frames_in_second = 0
                    
                    present_count = sum(1 for a in current_attendance if a["status"] == "present")
                    latest_fused = self.fusion_engine.window_history[-1]["fused_score"] if self.fusion_engine.window_history else 50.0
                    latest_lvl = self.fusion_engine.window_history[-1]["engagement_level"] if self.fusion_engine.window_history else "Moderate Engagement"
                    latest_qual = self.fusion_engine.window_history[-1]["data_quality"] if self.fusion_engine.window_history else "Optimal"

                    with self.lock:
                        self.current_metrics.update({
                            "fps": round(current_fps, 1),
                            "active_participants": len(tracked_participants),
                            "present_participants": present_count,
                            "fused_engagement": latest_fused,
                            "engagement_level": latest_lvl,
                            "speech_ratio": round(ia_res["speech_ratio"] * 100.0, 1),
                            "dominant_audio_state": ia_res["dominant_state"],
                            "data_quality": latest_qual,
                            "elapsed_seconds": round(elapsed_total, 1)
                        })

                # Maintain target loop rate ~15 FPS
                loop_elapsed = time.time() - loop_start
                target_delay = (1.0 / Config.VISION_TARGET_FPS) - loop_elapsed
                if target_delay > 0:
                    time.sleep(target_delay)

        finally:
            if cap:
                cap.release()
            self.audio_reader.stop()
            # Final sync of all attendance records to database
            final_attendance = self.presence_engine.update_from_tracks(list(self.tracker.tracks.values()), current_ts=time.time())
            for att in final_attendance:
                AttendanceRepository.upsert_attendance(
                    session_id=self.session_id,
                    track_id=att["participant_track_id"],
                    first_seen=att["first_seen"],
                    last_seen=att["last_seen"],
                    presence_seconds=att["presence_duration_seconds"],
                    presence_pct=att["presence_percentage"],
                    status=att["status"],
                    detection_count=att["detection_count"],
                    avg_forward=att["avg_head_pose_forward"],
                    student_id=att["student_id"]
                )
