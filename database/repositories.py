import json
import datetime
from typing import List, Optional, Dict, Any
from .db import get_db_connection
from .models import (
    Classroom, Student, SessionModel, AttendanceRecord,
    EngagementSummary, AudioSummary, TeachingRecommendation, SessionReport
)

def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class ClassroomRepository:
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.*, 
                       (SELECT COUNT(*) FROM students s WHERE s.classroom_id = c.id) as enrolled_count,
                       (SELECT COUNT(*) FROM sessions se WHERE se.classroom_id = c.id) as session_count
                FROM classrooms c
                ORDER BY c.created_at DESC
            """)
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def get_by_id(classroom_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM classrooms WHERE id = ?", (classroom_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(name: str, code: str, subject: str = "", department: str = "") -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO classrooms (name, code, subject, department, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    subject = excluded.subject,
                    department = excluded.department
            """, (name.strip(), code.strip().upper(), subject.strip(), department.strip(), now))
            if cur.lastrowid and cur.lastrowid > 0:
                return cur.lastrowid
            cur.execute("SELECT id FROM classrooms WHERE code = ?", (code.strip().upper(),))
            row = cur.fetchone()
            return row["id"] if row else 1

class StudentRepository:
    @staticmethod
    def get_by_classroom(classroom_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM students WHERE classroom_id = ? ORDER BY student_id_number ASC", (classroom_id,))
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def create(classroom_id: int, student_id_number: str, name: str, email: str = "", assigned_track_id: Optional[str] = None) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute(
                "INSERT INTO students (classroom_id, student_id_number, name, email, assigned_track_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (classroom_id, student_id_number.strip(), name.strip(), email.strip(), assigned_track_id, now)
            )
            return cur.lastrowid

    @staticmethod
    def assign_track(student_id: int, track_id: str) -> bool:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE students SET assigned_track_id = ? WHERE id = ?", (track_id, student_id))
            return cur.rowcount > 0

class SessionRepository:
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, c.name as classroom_name, c.code as classroom_code,
                       (SELECT COUNT(*) FROM attendance_records a WHERE a.session_id = s.id AND a.status = 'present') as present_count,
                       (SELECT COUNT(*) FROM attendance_records a WHERE a.session_id = s.id) as total_detected_count
                FROM sessions s
                JOIN classrooms c ON s.classroom_id = c.id
                ORDER BY s.created_at DESC
            """)
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def get_by_id(session_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, c.name as classroom_name, c.code as classroom_code
                FROM sessions s
                JOIN classrooms c ON s.classroom_id = c.id
                WHERE s.id = ?
            """, (session_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(classroom_id: int, title: str, input_type: str = "webcam", video_source: str = "", audio_source: str = "", notes: str = "") -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO sessions (classroom_id, title, status, input_type, video_source, audio_source, duration_seconds, notes, created_at)
                VALUES (?, ?, 'created', ?, ?, ?, 0.0, ?, ?)
            """, (classroom_id, title.strip(), input_type, video_source, audio_source, notes.strip(), now))
            return cur.lastrowid

    @staticmethod
    def update_status(session_id: int, status: str, duration_seconds: Optional[float] = None) -> bool:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            if status == "running":
                cur.execute("UPDATE sessions SET status = 'running', started_at = COALESCE(started_at, ?) WHERE id = ?", (now, session_id))
            elif status in ("completed", "stopped"):
                cur.execute("UPDATE sessions SET status = ?, ended_at = ?, duration_seconds = COALESCE(?, duration_seconds) WHERE id = ?", 
                            (status, now, duration_seconds, session_id))
            else:
                cur.execute("UPDATE sessions SET status = ? WHERE id = ?", (status, session_id))
            return cur.rowcount > 0

class AttendanceRepository:
    @staticmethod
    def get_by_session(session_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.*, s.name as student_name, s.student_id_number
                FROM attendance_records a
                LEFT JOIN students s ON a.student_id = s.id
                WHERE a.session_id = ?
                ORDER BY a.presence_duration_seconds DESC
            """, (session_id,))
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def upsert_attendance(session_id: int, track_id: str, first_seen: str, last_seen: str, 
                          presence_seconds: float, presence_pct: float, status: str, 
                          detection_count: int, avg_forward: float, student_id: Optional[int] = None) -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO attendance_records 
                    (session_id, participant_track_id, student_id, first_seen, last_seen, 
                     presence_duration_seconds, presence_percentage, status, detection_count, 
                     avg_head_pose_forward, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, participant_track_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    presence_duration_seconds = excluded.presence_duration_seconds,
                    presence_percentage = excluded.presence_percentage,
                    status = CASE WHEN attendance_records.reviewed_by_teacher = 1 
                                  THEN attendance_records.status 
                                  ELSE excluded.status END,
                    detection_count = excluded.detection_count,
                    avg_head_pose_forward = excluded.avg_head_pose_forward,
                    student_id = COALESCE(excluded.student_id, attendance_records.student_id),
                    updated_at = excluded.updated_at
            """, (session_id, track_id, student_id, first_seen, last_seen, 
                  presence_seconds, presence_pct, status, detection_count, avg_forward, now))

    @staticmethod
    def review_record(record_id: int, status: str, notes: str = "", teacher_name: str = "Teacher") -> bool:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                UPDATE attendance_records
                SET status = ?, reviewed_by_teacher = 1, teacher_override = ?, review_notes = ?, updated_at = ?
                WHERE id = ?
            """, (status, teacher_name, notes, now, record_id))
            return cur.rowcount > 0

    @staticmethod
    def bind_student_to_track(session_id: int, track_id: str, student_id: int) -> bool:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                UPDATE attendance_records
                SET student_id = ?, updated_at = ?
                WHERE session_id = ? AND participant_track_id = ?
            """, (student_id, now, session_id, track_id))
            return cur.rowcount > 0

class EngagementRepository:
    @staticmethod
    def add_summary(session_id: int, window_index: int, visual_score: float, audio_score: float,
                    fused_score: float, engagement_level: str, forward_ratio: float, 
                    movement: float, inactivity: float, speech: float, turns: int,
                    confidence: float, quality: str, modality: str) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO engagement_summaries
                (session_id, timestamp, window_index, visual_score, audio_score, fused_score,
                 engagement_level, forward_facing_ratio, movement_level, inactivity_ratio,
                 speech_ratio, interaction_turns, confidence_score, data_quality, modality_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, now, window_index, visual_score, audio_score, fused_score,
                  engagement_level, forward_ratio, movement, inactivity, speech, turns,
                  confidence, quality, modality))
            return cur.lastrowid

    @staticmethod
    def get_by_session(session_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM engagement_summaries
                WHERE session_id = ?
                ORDER BY window_index ASC
            """, (session_id,))
            return [dict(row) for row in cur.fetchall()]

class AudioRepository:
    @staticmethod
    def add_summary(session_id: int, speech_sec: float, silence_sec: float, turns: int, noise_db: float, state: str) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO audio_summaries
                (session_id, timestamp, total_speech_sec, total_silence_sec, speaking_turns, noise_floor_db, dominant_state)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, now, speech_sec, silence_sec, turns, noise_db, state))
            return cur.lastrowid

    @staticmethod
    def get_by_session(session_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM audio_summaries WHERE session_id = ? ORDER BY id ASC", (session_id,))
            return [dict(row) for row in cur.fetchall()]

class RecommendationRepository:
    @staticmethod
    def add_recommendation(session_id: int, category: str, observation: str, supporting_indicators: Dict[str, Any],
                           suggested_action: str, reason: str, confidence: str) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO teaching_recommendations
                (session_id, timestamp, category, observation, supporting_indicators, suggested_action, reason, confidence, applied_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (session_id, now, category, observation, json.dumps(supporting_indicators), suggested_action, reason, confidence))
            return cur.lastrowid

    @staticmethod
    def get_by_session(session_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM teaching_recommendations WHERE session_id = ? ORDER BY id DESC", (session_id,))
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                if isinstance(r.get("supporting_indicators"), str):
                    try:
                        r["supporting_indicators"] = json.loads(r["supporting_indicators"])
                    except Exception:
                        pass
            return rows

    @staticmethod
    def update_status(recommendation_id: int, status: str) -> bool:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE teaching_recommendations SET applied_status = ? WHERE id = ?", (status, recommendation_id))
            return cur.rowcount > 0

class ReportRepository:
    @staticmethod
    def get_by_session(session_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM session_reports WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if row:
                res = dict(row)
                if isinstance(res.get("report_data_json"), str):
                    try:
                        res["report_data"] = json.loads(res["report_data_json"])
                    except Exception:
                        res["report_data"] = {}
                return res
            return None

    @staticmethod
    def upsert_report(session_id: int, total_enrolled: int, total_detected: int, total_present: int,
                      attendance_rate: float, avg_engagement: float, visual_index: float,
                      audio_index: float, summary_text: str, recs_count: int, report_data: Dict[str, Any]) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO session_reports
                (session_id, generated_at, total_enrolled, total_detected, total_present, attendance_rate,
                 avg_engagement_score, visual_index, audio_index, summary_text, recommendations_count, report_data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    total_enrolled = excluded.total_enrolled,
                    total_detected = excluded.total_detected,
                    total_present = excluded.total_present,
                    attendance_rate = excluded.attendance_rate,
                    avg_engagement_score = excluded.avg_engagement_score,
                    visual_index = excluded.visual_index,
                    audio_index = excluded.audio_index,
                    summary_text = excluded.summary_text,
                    recommendations_count = excluded.recommendations_count,
                    report_data_json = excluded.report_data_json
            """, (session_id, now, total_enrolled, total_detected, total_present, attendance_rate,
                  avg_engagement, visual_index, audio_index, summary_text, recs_count, json.dumps(report_data)))
            return cur.lastrowid

class SettingsRepository:
    @staticmethod
    def get_all() -> Dict[str, str]:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM app_settings")
            return {row["key"]: row["value"] for row in cur.fetchall()}

    @staticmethod
    def get_value(key: str, default: str = "") -> str:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    @staticmethod
    def set_value(key: str, value: str, description: str = "") -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = utc_now_iso()
            cur.execute("""
                INSERT INTO app_settings (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, str(value), description, now))
