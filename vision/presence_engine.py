import time
import datetime
from typing import Dict, Any, List, Optional
from config import Config

def utc_iso(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()

class ParticipantPresence:
    def __init__(self, track_id: str, first_seen_ts: float):
        self.track_id = track_id
        self.first_seen = first_seen_ts
        self.last_seen = first_seen_ts
        self.cumulative_presence_sec = 0.0
        self.detection_count = 1
        self.forward_facing_count = 0
        self.status = "transient"  # transient, present, absent, excused
        self.student_id: Optional[int] = None
        self.reviewed_by_teacher = False
        self.teacher_override: Optional[str] = None
        self.review_notes: Optional[str] = None
        self.last_update_ts = first_seen_ts

    def record_frame(self, current_ts: float, is_forward: bool):
        # Accumulate presence if interval since last update is within active frame threshold (< 2.5s)
        dt = current_ts - self.last_update_ts
        if 0 < dt < 2.5:
            self.cumulative_presence_sec += dt
        elif self.cumulative_presence_sec == 0.0:
            self.cumulative_presence_sec = 0.1  # Initial observation increment

        self.last_seen = current_ts
        self.last_update_ts = current_ts
        self.detection_count += 1
        if is_forward:
            self.forward_facing_count += 1

    @property
    def avg_forward_facing(self) -> float:
        if self.detection_count == 0:
            return 0.0
        return round(self.forward_facing_count / self.detection_count, 3)


class PresenceEngine:
    """
    Sustained Presence Attendance Engine.
    Determines participant attendance using continuous temporal presence
    rather than instantaneous single-frame detection.
    """
    def __init__(self, presence_threshold_seconds: Optional[float] = None,
                 presence_percentage_threshold: Optional[float] = None):
        self.threshold_seconds = presence_threshold_seconds or Config.PRESENCE_THRESHOLD_SECONDS
        self.threshold_percentage = presence_percentage_threshold or Config.PRESENCE_PERCENTAGE_THRESHOLD
        self.records: Dict[str, ParticipantPresence] = {}
        self.session_start_time = time.time()

    def reset(self, start_time: Optional[float] = None):
        self.records.clear()
        self.session_start_time = start_time or time.time()

    def update_from_tracks(self, active_tracks: List[Any], current_ts: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Updates presence records from the active participant tracks.
        """
        if current_ts is None:
            current_ts = time.time()

        elapsed_session_time = max(1.0, current_ts - self.session_start_time)

        for track in active_tracks:
            tid = track.track_id
            if tid not in self.records:
                self.records[tid] = ParticipantPresence(tid, track.first_seen)

            rec = self.records[tid]
            rec.record_frame(current_ts, getattr(track, "is_forward", True))

        # Evaluate attendance status for each tracked participant
        results = []
        for tid, rec in self.records.items():
            presence_ratio = min(1.0, rec.cumulative_presence_sec / elapsed_session_time)
            
            # If teacher has already reviewed and set an override, respect teacher decision
            if not rec.reviewed_by_teacher:
                # Mark 'present' only if sustained presence threshold or percentage is met
                # For sessions under 30s, require at least min(session_time * threshold_percentage, threshold_seconds)
                meets_time = rec.cumulative_presence_sec >= self.threshold_seconds
                meets_pct = (elapsed_session_time >= 20.0 and presence_ratio >= self.threshold_percentage)
                
                if meets_time or meets_pct:
                    rec.status = "present"
                else:
                    rec.status = "transient"

            results.append({
                "participant_track_id": tid,
                "student_id": rec.student_id,
                "first_seen": utc_iso(rec.first_seen),
                "last_seen": utc_iso(rec.last_seen),
                "presence_duration_seconds": round(rec.cumulative_presence_sec, 1),
                "presence_percentage": round(presence_ratio * 100.0, 1),
                "status": rec.status,
                "detection_count": rec.detection_count,
                "avg_head_pose_forward": rec.avg_forward_facing,
                "reviewed_by_teacher": 1 if rec.reviewed_by_teacher else 0,
                "teacher_override": rec.teacher_override,
                "review_notes": rec.review_notes
            })

        return results

    def link_student(self, track_id: str, student_id: int):
        if track_id in self.records:
            self.records[track_id].student_id = student_id

    def override_attendance(self, track_id: str, new_status: str, teacher_name: str = "Teacher", notes: str = ""):
        if track_id in self.records:
            rec = self.records[track_id]
            rec.status = new_status
            rec.reviewed_by_teacher = True
            rec.teacher_override = teacher_name
            rec.review_notes = notes
