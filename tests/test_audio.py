import pytest
import numpy as np
from audio.voice_activity import VoiceActivityDetector
from audio.interaction_analyzer import InteractionAnalyzer

def test_vad_silence_vs_speech():
    vad = VoiceActivityDetector(sample_rate=16000)
    
    # 1. Pure silence / low-level ambient noise
    silence = (0.0005 * np.random.randn(16000)).astype(np.float32)
    res_silence = vad.process_chunk(silence)
    assert res_silence["is_speech"] is False
    assert res_silence["total_silence_sec"] == 1.0

    # 2. Simulated speech signal (moderate energy with typical formant frequencies ~500Hz)
    t = np.linspace(0, 1, 16000, endpoint=False)
    speech = (0.05 * np.sin(2 * np.pi * 500 * t) + 0.02 * np.sin(2 * np.pi * 1200 * t)).astype(np.float32)
    res_speech = vad.process_chunk(speech)
    assert res_speech["is_speech"] is True
    assert res_speech["total_speech_sec"] == 1.0
    assert res_speech["snr_db"] > 10.0

def test_interaction_analyzer_turns_and_states():
    ia = InteractionAnalyzer(window_size=10)

    # Sequence: 3s silence -> 2s speech -> 2s silence -> 2s speech (represents dialogue turn taking)
    # Turn 1
    for _ in range(3):
        ia.update({"is_speech": False, "rms_energy": 0.001})
    for _ in range(2):
        ia.update({"is_speech": True, "rms_energy": 0.05})
    assert ia.speaking_turns >= 1

    # Turn 2
    for _ in range(2):
        ia.update({"is_speech": False, "rms_energy": 0.001})
    for _ in range(2):
        ia.update({"is_speech": True, "rms_energy": 0.05})
    assert ia.speaking_turns >= 2

    # Check metrics
    final_res = ia.update({"is_speech": True, "rms_energy": 0.05})
    assert final_res["speaking_turns"] >= 2
    assert final_res["speech_ratio"] > 0.0
    assert final_res["dominant_state"] in ("Active Discussion / Q&A", "Lecture / Monologue", "Moderate Interaction")
