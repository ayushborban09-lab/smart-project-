from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import datetime

@dataclass
class Classroom:
    id: Optional[int]
    name: str
    code: str
    subject: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Student:
    id: Optional[int]
    classroom_id: int
    student_id_number: str
    name: str
    email: Optional[str] = None
    assigned_track_id: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SessionModel:
    id: Optional[int]
    classroom_id: int
    title: str
    status: str = "created"  # created, running, completed, stopped
    input_type: str = "webcam"  # webcam, video_file, audio_file, multimodal, synthetic
    video_source: Optional[str] = None
    audio_source: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_seconds: float = 0.0
    notes: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AttendanceRecord:
    id: Optional[int]
    session_id: int
    participant_track_id: str
    student_id: Optional[int]
    first_seen: str
    last_seen: str
    presence_duration_seconds: float
    presence_percentage: float
    status: str = "transient"  # present, absent, transient, excused
    detection_count: int = 0
    avg_head_pose_forward: float = 0.0
    reviewed_by_teacher: int = 0
    teacher_override: Optional[str] = None
    review_notes: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EngagementSummary:
    id: Optional[int]
    session_id: int
    timestamp: str
    window_index: int
    visual_score: float
    audio_score: float
    fused_score: float
    engagement_level: str
    forward_facing_ratio: float
    movement_level: float
    inactivity_ratio: float
    speech_ratio: float
    interaction_turns: int
    confidence_score: float
    data_quality: str
    modality_state: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AudioSummary:
    id: Optional[int]
    session_id: int
    timestamp: str
    total_speech_sec: float
    total_silence_sec: float
    speaking_turns: int
    noise_floor_db: float
    dominant_state: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TeachingRecommendation:
    id: Optional[int]
    session_id: int
    timestamp: str
    category: str
    observation: str
    supporting_indicators: str
    suggested_action: str
    reason: str
    confidence: str
    applied_status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SessionReport:
    id: Optional[int]
    session_id: int
    generated_at: str
    total_enrolled: int
    total_detected: int
    total_present: int
    attendance_rate: float
    avg_engagement_score: float
    visual_index: float
    audio_index: float
    summary_text: str
    recommendations_count: int
    report_data_json: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
