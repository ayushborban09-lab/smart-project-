import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from config import Config

def get_db_path() -> Path:
    Config.init_directories()
    return Config.DATABASE_PATH

@contextmanager
def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes the SQLite database with full schema and default settings."""
    Config.init_directories()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Classrooms
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                subject TEXT,
                department TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # 2. Students
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classroom_id INTEGER NOT NULL,
                student_id_number TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                assigned_track_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
            );
        """)

        # 3. Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classroom_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                input_type TEXT NOT NULL DEFAULT 'webcam',
                video_source TEXT,
                audio_source TEXT,
                started_at TEXT,
                ended_at TEXT,
                duration_seconds REAL DEFAULT 0.0,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
            );
        """)

        # 4. Attendance Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                participant_track_id TEXT NOT NULL,
                student_id INTEGER,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                presence_duration_seconds REAL NOT NULL DEFAULT 0.0,
                presence_percentage REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'transient',
                detection_count INTEGER DEFAULT 0,
                avg_head_pose_forward REAL DEFAULT 0.0,
                reviewed_by_teacher INTEGER DEFAULT 0,
                teacher_override TEXT,
                review_notes TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL,
                UNIQUE (session_id, participant_track_id)
            );
        """)

        # 5. Engagement Summaries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                window_index INTEGER NOT NULL,
                visual_score REAL NOT NULL,
                audio_score REAL NOT NULL,
                fused_score REAL NOT NULL,
                engagement_level TEXT NOT NULL,
                forward_facing_ratio REAL DEFAULT 0.0,
                movement_level REAL DEFAULT 0.0,
                inactivity_ratio REAL DEFAULT 0.0,
                speech_ratio REAL DEFAULT 0.0,
                interaction_turns INTEGER DEFAULT 0,
                confidence_score REAL NOT NULL,
                data_quality TEXT NOT NULL,
                modality_state TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
        """)

        # 6. Audio Summaries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                total_speech_sec REAL DEFAULT 0.0,
                total_silence_sec REAL DEFAULT 0.0,
                speaking_turns INTEGER DEFAULT 0,
                noise_floor_db REAL DEFAULT -60.0,
                dominant_state TEXT DEFAULT 'silence',
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
        """)

        # 7. Teaching Recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teaching_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                observation TEXT NOT NULL,
                supporting_indicators TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence TEXT NOT NULL,
                applied_status TEXT DEFAULT 'pending',
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
        """)

        # 8. Session Reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER UNIQUE NOT NULL,
                generated_at TEXT NOT NULL,
                total_enrolled INTEGER DEFAULT 0,
                total_detected INTEGER DEFAULT 0,
                total_present INTEGER DEFAULT 0,
                attendance_rate REAL DEFAULT 0.0,
                avg_engagement_score REAL DEFAULT 0.0,
                visual_index REAL DEFAULT 0.0,
                audio_index REAL DEFAULT 0.0,
                summary_text TEXT,
                recommendations_count INTEGER DEFAULT 0,
                report_data_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
        """)

        # 9. App Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TEXT NOT NULL
            );
        """)

        # Seed default settings if empty
        cursor.execute("SELECT COUNT(*) FROM app_settings;")
        if cursor.fetchone()[0] == 0:
            import datetime
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            default_settings = [
                ("presence_threshold_seconds", str(Config.PRESENCE_THRESHOLD_SECONDS), "Seconds of sustained presence to qualify for attendance", now_iso),
                ("presence_percentage_threshold", str(Config.PRESENCE_PERCENTAGE_THRESHOLD), "Session percentage threshold for attendance qualification", now_iso),
                ("fusion_visual_weight", str(Config.FUSION_VISUAL_WEIGHT), "Weight of visual indicators in fusion engine [0-1]", now_iso),
                ("fusion_audio_weight", str(Config.FUSION_AUDIO_WEIGHT), "Weight of audio indicators in fusion engine [0-1]", now_iso),
                ("fusion_window_seconds", str(Config.FUSION_WINDOW_SECONDS), "Sliding analysis window duration in seconds", now_iso),
                ("privacy_anonymous_mode", "1", "Use anonymous tracking identifiers without real names unless mapped", now_iso),
                ("privacy_retain_raw_media", "0", "Retain raw audio/video recordings on disk (0=false, 1=true)", now_iso),
                ("recommendation_engine_mode", "rule_based", "AI engine baseline: 'rule_based' or 'local_llm'", now_iso),
            ]
            cursor.executemany("INSERT INTO app_settings (key, value, description, updated_at) VALUES (?, ?, ?, ?)", default_settings)
