import numpy as np
from typing import Dict, Any

class FeatureNormalizer:
    """
    Normalizes multi-sensory visual and acoustic observations into standardized [0.0, 1.0] feature spaces.
    """
    @staticmethod
    def normalize_visual_features(raw_visual: Dict[str, Any]) -> Dict[str, float]:
        """
        Input keys:
            forward_facing_ratio: float [0, 1]
            avg_movement_speed: float (pixels/sec)
            avg_inactivity_sec: float
            participant_count: int
        """
        # Forward facing ratio is already in [0, 1]
        forward_score = float(np.clip(raw_visual.get("forward_facing_ratio", 0.7), 0.0, 1.0))

        # Movement: moderate micro-movement is healthy, completely rigid (0) or wild erratic (>200) decreases score
        speed = raw_visual.get("avg_movement_speed", 15.0)
        if speed < 2.0:
            # Low movement / frozen
            movement_score = 0.65
        elif speed <= 45.0:
            # Healthy, attentive posture shifts
            movement_score = 1.0
        elif speed <= 120.0:
            # Moderate movement
            movement_score = 0.75
        else:
            # Erratic / high movement
            movement_score = 0.45

        # Inactivity duration penalty
        inactivity = raw_visual.get("avg_inactivity_sec", 0.0)
        if inactivity < 30.0:
            inactivity_factor = 1.0
        elif inactivity < 90.0:
            inactivity_factor = 0.85
        elif inactivity < 180.0:
            inactivity_factor = 0.65
        else:
            inactivity_factor = 0.40

        # Composite visual engagement index
        # 50% head orientation, 30% posture/movement, 20% active presence factor
        composite_visual = 0.50 * forward_score + 0.30 * movement_score + 0.20 * inactivity_factor

        return {
            "norm_forward_facing": round(forward_score, 3),
            "norm_movement": round(movement_score, 3),
            "norm_inactivity_factor": round(inactivity_factor, 3),
            "composite_visual_score": round(float(np.clip(composite_visual, 0.0, 1.0)), 3)
        }

    @staticmethod
    def normalize_audio_features(raw_audio: Dict[str, Any]) -> Dict[str, float]:
        """
        Input keys:
            speech_ratio: float [0, 1]
            turn_rate_per_min: float
            snr_db: float
            dominant_state: str
        """
        speech_ratio = float(np.clip(raw_audio.get("speech_ratio", 0.0), 0.0, 1.0))
        turn_rate = raw_audio.get("turn_rate_per_min", 0.0)
        
        # In classroom pedagogy, dialogue (30-65% speech with healthy turns) is optimal for engagement.
        # Monologue (>80% speech, 0 turns) is lecture; total silence (<10% speech) is passive.
        if 0.25 <= speech_ratio <= 0.70:
            speech_engagement = 0.90
        elif speech_ratio > 0.70:
            speech_engagement = 0.70
        elif 0.10 <= speech_ratio < 0.25:
            speech_engagement = 0.55
        else:
            speech_engagement = 0.35

        # Turn score: 3 to 12 turns/min represents lively back-and-forth
        norm_turns = min(1.0, turn_rate / 8.0)
        
        # Audio composite: 60% conversational turns / interaction, 40% speech presence
        composite_audio = 0.55 * norm_turns + 0.45 * speech_engagement

        return {
            "norm_speech_ratio": round(speech_ratio, 3),
            "norm_turn_rate": round(norm_turns, 3),
            "composite_audio_score": round(float(np.clip(composite_audio, 0.0, 1.0)), 3)
        }
