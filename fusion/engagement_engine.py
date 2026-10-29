import time
import numpy as np
from typing import Dict, Any, List, Optional
from config import Config
from .feature_normalizer import FeatureNormalizer

ETHICAL_DISCLAIMER = (
    "Experimental estimate derived from observable signals. "
    "Not an objective measurement of student learning, intelligence, or emotional state."
)

class MultimodalEngagementEngine:
    """
    Multimodal Data Fusion Engine for Classroom Engagement Estimation.
    Fuses computer vision metrics and audio signal indicators into a transparent,
    explainable engagement index with dynamic modality failover.
    """
    def __init__(self, visual_weight: Optional[float] = None, audio_weight: Optional[float] = None):
        self.visual_weight = visual_weight if visual_weight is not None else Config.FUSION_VISUAL_WEIGHT
        self.audio_weight = audio_weight if audio_weight is not None else Config.FUSION_AUDIO_WEIGHT
        self.normalizer = FeatureNormalizer()
        self.window_history: List[Dict[str, Any]] = []

    def reset(self):
        self.window_history.clear()

    def fuse(self, raw_visual: Optional[Dict[str, Any]] = None,
             raw_audio: Optional[Dict[str, Any]] = None,
             window_index: int = 1) -> Dict[str, Any]:
        """
        Combines visual and audio observation vectors into an engagement estimate.
        Handles missing modalities gracefully.
        """
        has_visual = raw_visual is not None and raw_visual.get("participant_count", 0) > 0
        has_audio = raw_audio is not None and "speech_ratio" in raw_audio

        # Determine active modality and dynamic weights
        if has_visual and has_audio:
            modality_state = "Multimodal"
            w_v = self.visual_weight
            w_a = self.audio_weight
            # Ensure weights sum to 1.0
            total_w = w_v + w_a
            w_v, w_a = w_v / total_w, w_a / total_w
        elif has_visual:
            modality_state = "Visual-Only"
            w_v, w_a = 1.0, 0.0
        elif has_audio:
            modality_state = "Audio-Only"
            w_v, w_a = 0.0, 1.0
        else:
            modality_state = "Insufficient Input"
            w_v, w_a = 0.5, 0.5

        # Process Visual indicators
        if has_visual:
            norm_vis = self.normalizer.normalize_visual_features(raw_visual)
            visual_score = norm_vis["composite_visual_score"]
            forward_facing_ratio = norm_vis["norm_forward_facing"]
            movement_level = norm_vis["norm_movement"]
            inactivity_ratio = 1.0 - norm_vis["norm_inactivity_factor"]
        else:
            visual_score = 0.50
            forward_facing_ratio = 0.0
            movement_level = 0.0
            inactivity_ratio = 0.0

        # Process Audio indicators
        if has_audio:
            norm_aud = self.normalizer.normalize_audio_features(raw_audio)
            audio_score = norm_aud["composite_audio_score"]
            speech_ratio = norm_aud["norm_speech_ratio"]
            interaction_turns = raw_audio.get("speaking_turns", 0)
        else:
            audio_score = 0.50
            speech_ratio = 0.0
            interaction_turns = 0

        # Multimodal fusion computation
        if modality_state == "Insufficient Input":
            fused_score = 0.50
            confidence = 0.20
            data_quality = "Insufficient"
        else:
            fused_score = (w_v * visual_score) + (w_a * audio_score)
            
            # Confidence estimation
            base_conf = 0.85 if modality_state == "Multimodal" else 0.65
            if has_visual and raw_visual.get("participant_count", 0) >= 2:
                base_conf = min(0.95, base_conf + 0.05)
            if has_audio and raw_audio.get("snr_db", 0.0) < 5.0:
                base_conf = max(0.40, base_conf - 0.15)
            confidence = round(base_conf, 2)

            if confidence >= 0.80:
                data_quality = "Optimal"
            elif confidence >= 0.60:
                data_quality = "Acceptable"
            else:
                data_quality = "Degraded"

        fused_percentage = round(float(fused_score * 100.0), 1)

        # Categorize engagement level
        if fused_percentage >= 75.0:
            engagement_level = "High Engagement"
        elif fused_percentage >= 50.0:
            engagement_level = "Moderate Engagement"
        elif fused_percentage >= 35.0:
            engagement_level = "Passive / Quiet Listening"
        else:
            engagement_level = "Low Activity / Needs Interaction"

        result = {
            "window_index": window_index,
            "timestamp": time.time(),
            "fused_score": fused_percentage,
            "visual_score": round(visual_score * 100.0, 1),
            "audio_score": round(audio_score * 100.0, 1),
            "engagement_level": engagement_level,
            "forward_facing_ratio": round(forward_facing_ratio, 3),
            "movement_level": round(movement_level, 3),
            "inactivity_ratio": round(inactivity_ratio, 3),
            "speech_ratio": round(speech_ratio, 3),
            "interaction_turns": interaction_turns,
            "confidence_score": confidence,
            "data_quality": data_quality,
            "modality_state": modality_state,
            "weights_used": {"visual": round(w_v, 2), "audio": round(w_a, 2)},
            "ethical_notice": ETHICAL_DISCLAIMER
        }

        self.window_history.append(result)
        return result
