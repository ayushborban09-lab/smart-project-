import pytest
import time
from vision.presence_engine import PresenceEngine
from vision.tracker import ParticipantTracker
from database.repositories import AttendanceRepository, SessionRepository, ClassroomRepository
from database.db import init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_sustained_presence_threshold():
    # Configure presence threshold to 5.0 seconds for quick testing
    engine = PresenceEngine(presence_threshold_seconds=5.0, presence_percentage_threshold=0.3)
    start_time = 1000.0
    engine.reset(start_time)

    class DummyTrack:
        def __init__(self, tid, first_seen):
            self.track_id = tid
            self.first_seen = first_seen
            self.is_forward = True

    # 1. Brief appearance of 2 seconds (Transient)
    t1 = DummyTrack("P-TEST-1", start_time)
    engine.update_from_tracks([t1], current_ts=start_time + 1.0)
    engine.update_from_tracks([t1], current_ts=start_time + 2.0)
    
    records = engine.update_from_tracks([t1], current_ts=start_time + 2.0)
    rec1 = next(r for r in records if r["participant_track_id"] == "P-TEST-1")
    assert rec1["status"] == "transient", f"Expected transient status for 2s appearance, got {rec1['status']}"

    # 2. Sustained presence reaching 6 seconds (Present)
    for sec in range(3, 7):
        engine.update_from_tracks([t1], current_ts=start_time + float(sec))
    
    records = engine.update_from_tracks([t1], current_ts=start_time + 6.0)
    rec1 = next(r for r in records if r["participant_track_id"] == "P-TEST-1")
    assert rec1["status"] == "present", f"Expected present status after 6s sustained presence, got {rec1['status']}"
    assert rec1["presence_duration_seconds"] >= 5.0

def test_attendance_deduplication():
    # Test SQLite repository deduplication on same session and track
    cls_id = ClassroomRepository.create("Test Class", "TC-101")
    sess_id = SessionRepository.create(cls_id, "Test Session")

    # First insert
    AttendanceRepository.upsert_attendance(
        session_id=sess_id, track_id="P-DEDUP-1", first_seen="2026-10-30T10:00:00Z",
        last_seen="2026-10-30T10:01:00Z", presence_seconds=60.0, presence_pct=50.0,
        status="present", detection_count=30, avg_forward=0.85
    )

    # Second upsert for same track in same session (updates, does not create duplicate row)
    AttendanceRepository.upsert_attendance(
        session_id=sess_id, track_id="P-DEDUP-1", first_seen="2026-10-30T10:00:00Z",
        last_seen="2026-10-30T10:02:00Z", presence_seconds=120.0, presence_pct=75.0,
        status="present", detection_count=60, avg_forward=0.88
    )

    records = AttendanceRepository.get_by_session(sess_id)
    assert len(records) == 1, f"Expected 1 record after upsert, found {len(records)}"
    assert records[0]["presence_duration_seconds"] == 120.0
    assert records[0]["detection_count"] == 60

def test_teacher_override():
    cls_id = ClassroomRepository.create("Override Class", "OC-102")
    sess_id = SessionRepository.create(cls_id, "Override Session")

    AttendanceRepository.upsert_attendance(
        session_id=sess_id, track_id="P-OVERRIDE", first_seen="2026-10-30T10:00:00Z",
        last_seen="2026-10-30T10:00:10Z", presence_seconds=10.0, presence_pct=5.0,
        status="transient", detection_count=5, avg_forward=0.5
    )
    records = AttendanceRepository.get_by_session(sess_id)
    rec_id = records[0]["id"]

    # Teacher manual override to 'present'
    success = AttendanceRepository.review_record(rec_id, "present", "Teacher observed student in room", "Prof. Smith")
    assert success is True

    updated_records = AttendanceRepository.get_by_session(sess_id)
    assert updated_records[0]["status"] == "present"
    assert updated_records[0]["reviewed_by_teacher"] == 1
    assert updated_records[0]["teacher_override"] == "Prof. Smith"
