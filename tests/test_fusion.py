import pytest
from fusion.feature_normalizer import FeatureNormalizer
from fusion.engagement_engine import MultimodalEngagementEngine, ETHICAL_DISCLAIMER

def test_feature_normalizer():
    # Visual normalization
    vis = FeatureNormalizer.normalize_visual_features({
        "forward_facing_ratio": 0.90,
        "avg_movement_speed": 20.0,
        "avg_inactivity_sec": 10.0,
        "participant_count": 5
    })
    assert 0.0 <= vis["composite_visual_score"] <= 1.0
    assert vis["norm_forward_facing"] == 0.90
    assert vis["norm_movement"] == 1.0

    # Audio normalization
    aud = FeatureNormalizer.normalize_audio_features({
        "speech_ratio": 0.40,
        "turn_rate_per_min": 6.0,
        "snr_db": 20.0
    })
    assert 0.0 <= aud["composite_audio_score"] <= 1.0

def test_multimodal_fusion_modes():
    engine = MultimodalEngagementEngine(visual_weight=0.6, audio_weight=0.4)

    # 1. Combined Multimodal Mode
    res_multi = engine.fuse(
        raw_visual={"forward_facing_ratio": 0.85, "avg_movement_speed": 25.0, "avg_inactivity_sec": 5.0, "participant_count": 3},
        raw_audio={"speech_ratio": 0.45, "turn_rate_per_min": 7.0, "snr_db": 15.0, "speaking_turns": 8}
    )
    assert res_multi["modality_state"] == "Multimodal"
    assert res_multi["weights_used"]["visual"] == 0.6
    assert res_multi["weights_used"]["audio"] == 0.4
    assert res_multi["fused_score"] > 60.0
    assert res_multi["ethical_notice"] == ETHICAL_DISCLAIMER

    # 2. Visual-Only Mode (Microphone unavailable)
    res_vis_only = engine.fuse(
        raw_visual={"forward_facing_ratio": 0.80, "avg_movement_speed": 30.0, "avg_inactivity_sec": 10.0, "participant_count": 2},
        raw_audio=None
    )
    assert res_vis_only["modality_state"] == "Visual-Only"
    assert res_vis_only["weights_used"]["visual"] == 1.0
    assert res_vis_only["weights_used"]["audio"] == 0.0

    # 3. Audio-Only Mode (Camera unavailable)
    res_aud_only = engine.fuse(
        raw_visual=None,
        raw_audio={"speech_ratio": 0.50, "turn_rate_per_min": 5.0, "snr_db": 18.0}
    )
    assert res_aud_only["modality_state"] == "Audio-Only"
    assert res_aud_only["weights_used"]["visual"] == 0.0
    assert res_aud_only["weights_used"]["audio"] == 1.0
