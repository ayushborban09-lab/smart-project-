from typing import Dict, Any, List, Optional

class RecommendationRules:
    """
    Offline Rule-Based Pedagogical Recommendation Rules.
    Designed according to educational science and active learning frameworks.
    Produces transparent, explainable recommendations without cloud dependencies.
    """
    @staticmethod
    def evaluate(engagement_data: Dict[str, Any], 
                 recent_history: List[Dict[str, Any]], 
                 session_duration_sec: float) -> Optional[Dict[str, Any]]:
        """
        Evaluates current signals and recent window history to trigger actionable teaching suggestions.
        """
        data_quality = engagement_data.get("data_quality", "Acceptable")

        # Scenario 4: Poor input quality / repeated sensor occlusion (Priority Alert)
        if data_quality in ("Degraded", "Insufficient"):
            return {
                "category": "Observation Quality",
                "observation": "Camera or acoustic signal quality is currently degraded or partially occluded.",
                "supporting_indicators": {
                    "data_quality": data_quality,
                    "confidence_score": engagement_data.get("confidence_score", 0.0)
                },
                "suggested_action": "Check classroom camera angle, room lighting, and microphone proximity.",
                "reason": "Stable observations prevent false transients and ensure reliable presence verification.",
                "confidence": "Medium"
            }

        # Scenario 5: Insufficient data or very early session
        if session_duration_sec < 25.0 or len(recent_history) < 2:
            return {
                "category": "Session Initiation",
                "observation": "Session has recently begun; initial participant tracks are establishing baseline presence.",
                "supporting_indicators": {
                    "session_duration_sec": round(session_duration_sec, 1),
                    "observation_windows": len(recent_history)
                },
                "suggested_action": "Proceed with introductory remarks or warm-up; allow baseline sensor stabilization.",
                "reason": "Accurate engagement trends require a multi-window observation period to avoid premature inferences.",
                "confidence": "Preliminary"
            }

        # Extract indicators from the current window
        fused_score = engagement_data.get("fused_score", 50.0)
        forward_ratio = engagement_data.get("forward_facing_ratio", 0.5)
        speech_ratio = engagement_data.get("speech_ratio", 0.0)
        turns = engagement_data.get("interaction_turns", 0)
        inactivity_ratio = engagement_data.get("inactivity_ratio", 0.0)

        # Compute trend over last 3-5 windows if available
        last_scores = [h.get("fused_score", 50.0) for h in recent_history[-4:]]
        score_trend = last_scores[-1] - last_scores[0] if len(last_scores) >= 2 else 0.0

        # Scenario 3: High interaction burst during particular segment
        if turns >= 8 and speech_ratio >= 0.40 and fused_score >= 80.0:
            return {
                "category": "Pedagogical Reflection",
                "observation": "High collaborative interaction detected with active multi-turn dialogue.",
                "supporting_indicators": {
                    "fused_score": fused_score,
                    "speaking_turns": turns,
                    "speech_ratio": speech_ratio
                },
                "suggested_action": "Note or bookmark the current discussion topic or prompt for future lesson design.",
                "reason": "Observable participatory dynamics indicate strong student involvement in the current topic.",
                "confidence": "High"
            }

        # Scenario 2: Prolonged silence during lecture
        if speech_ratio < 0.10 and session_duration_sec > 90.0:
            return {
                "category": "Check for Understanding",
                "observation": "Prolonged silence observed during instruction.",
                "supporting_indicators": {
                    "speech_ratio": speech_ratio,
                    "speaking_turns": turns,
                    "duration_seconds": round(session_duration_sec, 1)
                },
                "suggested_action": "Invite clarifying questions or run a 30-second concept check rather than assuming disengagement.",
                "reason": "Quiet intervals often occur while students process dense material; an explicit check helps gauge comprehension.",
                "confidence": "High"
            }

        # Scenario 1: Downward engagement trend over multiple intervals
        if score_trend < -15.0 or (fused_score < 45.0 and forward_ratio < 0.40):
            return {
                "category": "Interactive Check",
                "observation": "Observed participant focus and interaction have decreased across consecutive observation intervals.",
                "supporting_indicators": {
                    "score_trend_delta": round(score_trend, 1),
                    "current_fused_score": fused_score,
                    "forward_facing_ratio": forward_ratio
                },
                "suggested_action": "Introduce a 2-minute 'Think-Pair-Share', a quick polling question, or a brief physical posture break.",
                "reason": "Brief collaborative micro-activities reset attention spans and convert passive listening into active recall.",
                "confidence": "High"
            }

        # Scenario 4b: High inactivity duration / sedentary stagnation
        if inactivity_ratio > 0.65:
            return {
                "category": "Classroom Pace",
                "observation": "Prolonged physical inactivity detected across the classroom.",
                "supporting_indicators": {
                    "inactivity_ratio": inactivity_ratio,
                    "forward_facing_ratio": forward_ratio
                },
                "suggested_action": "Ask participants to raise hands, stand for a rapid exercise, or transition to a board activity.",
                "reason": "Sustained sedentary posture lowers physiological arousal; kinesthetic transitions restore mental alertness.",
                "confidence": "Medium"
            }

        # Default pedagogical maintenance suggestion
        return {
            "category": "Instructional Flow",
            "observation": "Classroom metrics show balanced participation and steady observation continuity.",
            "supporting_indicators": {
                "fused_score": fused_score,
                "forward_facing_ratio": forward_ratio,
                "speech_ratio": speech_ratio
            },
            "suggested_action": "Maintain current instructional pace and prepare the next transition milestone.",
            "reason": "Balanced signals indicate effective pacing and clear student attentiveness.",
            "confidence": "Medium"
        }
