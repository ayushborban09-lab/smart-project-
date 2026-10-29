import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "multimodal-agent-local-secret-2026")
    
    # Vercel serverless runtime detection (filesystem is read-only except /tmp)
    IS_VERCEL = os.environ.get("VERCEL") is not None
    
    # Storage Paths
    if IS_VERCEL:
        INSTANCE_DIR = Path("/tmp/instance")
        DATA_DIR = Path("/tmp/data")
    else:
        INSTANCE_DIR = BASE_DIR / "instance"
        DATA_DIR = BASE_DIR / "data"

    UPLOAD_FOLDER = DATA_DIR / "uploads"
    REPORTS_FOLDER = DATA_DIR / "reports"
    SAMPLE_MEDIA_FOLDER = BASE_DIR / "data" / "samples"
    
    DATABASE_PATH = INSTANCE_DIR / "database.db"
    
    # Attendance Tracking Rules
    PRESENCE_THRESHOLD_SECONDS = float(os.environ.get("PRESENCE_THRESHOLD_SECONDS", 15.0))
    PRESENCE_PERCENTAGE_THRESHOLD = float(os.environ.get("PRESENCE_PERCENTAGE_THRESHOLD", 0.30))
    TRACKER_MAX_DISAPPEARED_FRAMES = int(os.environ.get("TRACKER_MAX_DISAPPEARED_FRAMES", 45))
    TRACKER_DISTANCE_THRESHOLD = float(os.environ.get("TRACKER_DISTANCE_THRESHOLD", 120.0))
    
    # Vision Processing
    VISION_TARGET_FPS = int(os.environ.get("VISION_TARGET_FPS", 15))
    DETECTION_INTERVAL_FRAMES = int(os.environ.get("DETECTION_INTERVAL_FRAMES", 2))
    HEAD_POSE_PITCH_FORWARD_RANGE = (-25.0, 25.0)
    HEAD_POSE_YAW_FORWARD_RANGE = (-30.0, 30.0)
    
    # Audio Processing
    AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE", 16000))
    AUDIO_BLOCK_SECONDS = float(os.environ.get("AUDIO_BLOCK_SECONDS", 1.0))
    AUDIO_VAD_ENERGY_THRESHOLD = float(os.environ.get("AUDIO_VAD_ENERGY_THRESHOLD", 0.012))
    AUDIO_VAD_ZCR_THRESHOLD = float(os.environ.get("AUDIO_VAD_ZCR_THRESHOLD", 0.04))
    
    # Multimodal Fusion
    FUSION_VISUAL_WEIGHT = float(os.environ.get("FUSION_VISUAL_WEIGHT", 0.55))
    FUSION_AUDIO_WEIGHT = float(os.environ.get("FUSION_AUDIO_WEIGHT", 0.45))
    FUSION_WINDOW_SECONDS = float(os.environ.get("FUSION_WINDOW_SECONDS", 10.0))
    
    # AI Recommendation Agent
    RECOMMENDATION_COOLDOWN_SECONDS = 15.0
    ENABLE_LOCAL_LLM = os.environ.get("ENABLE_LOCAL_LLM", "false").lower() in ("true", "1")
    LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/api/generate")
    LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "llama3.2:latest")
    
    # Privacy & Retention
    RETAIN_RAW_MEDIA = False
    ANONYMOUS_TRACKING_DEFAULT = True
    DATA_RETENTION_DAYS = 90
    
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
    ALLOWED_AUDIO_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a"}
    MAX_CONTENT_LENGTH = 250 * 1024 * 1024  # 250 MB
    
    @classmethod
    def init_directories(cls):
        """Ensure necessary directories exist on the local file system."""
        cls.INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.SAMPLE_MEDIA_FOLDER.mkdir(parents=True, exist_ok=True)
