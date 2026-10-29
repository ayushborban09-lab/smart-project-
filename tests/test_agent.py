import pytest
from agent.recommendation_rules import RecommendationRules
from agent.recommendation_engine import RecommendationEngine
from database.db import init_db
from database.repositories import SessionRepository, ClassroomRepository

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_recommendation_scenarios():
    rules = RecommendationRules()

    # Scenario 5: Early session (<25s)
    rec_early = rules.evaluate({"fused_score": 70.0}, [], session_duration_sec=15.0)
    assert rec_early["category"] == "Session Initiation"
    assert rec_early["confidence"] == "Preliminary"

    # Scenario 2: Prolonged silence during lecture
    rec_silence = rules.evaluate(
        {"fused_score": 50.0, "speech_ratio": 0.04, "interaction_turns": 1, "forward_facing_ratio": 0.7},
        [{"fused_score": 50.0}, {"fused_score": 50.0}],
        session_duration_sec=120.0
    )
    assert rec_silence["category"] == "Check for Understanding"
    assert "silence" in rec_silence["observation"].lower()

    # Scenario 3: High collaborative interaction
    rec_collab = rules.evaluate(
        {"fused_score": 88.0, "speech_ratio": 0.50, "interaction_turns": 12, "forward_facing_ratio": 0.85},
        [{"fused_score": 80.0}, {"fused_score": 85.0}],
        session_duration_sec=200.0
    )
    assert rec_collab["category"] == "Pedagogical Reflection"
    assert rec_collab["confidence"] == "High"

    # Scenario 4: Degraded observation quality
    rec_quality = rules.evaluate(
        {"fused_score": 50.0, "data_quality": "Degraded", "confidence_score": 0.45},
        [{"fused_score": 50.0}],
        session_duration_sec=80.0
    )
    assert rec_quality["category"] == "Observation Quality"

def test_recommendation_engine_cooldown_and_storage():
    cls_id = ClassroomRepository.create("AI Class", "AI-101")
    sess_id = SessionRepository.create(cls_id, "Session AI")

    engine = RecommendationEngine(cooldown_seconds=10.0)
    
    # First generation
    eng_data = {"fused_score": 85.0, "speech_ratio": 0.45, "interaction_turns": 10, "data_quality": "Optimal"}
    rec1 = engine.generate(sess_id, eng_data, session_duration_sec=100.0, force=True)
    assert rec1 is not None
    assert "id" in rec1

    # Second immediate call within cooldown should return None
    rec2 = engine.generate(sess_id, eng_data, session_duration_sec=102.0, force=False)
    assert rec2 is None
