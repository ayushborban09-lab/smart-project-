from typing import Dict, Any, List
from collections import deque
import time

class InteractionAnalyzer:
    """
    Analyzes conversational turns, speaking dynamics, and classroom interaction patterns.
    """
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.state_history = deque(maxlen=window_size)  # Stores bool (is_speech) per second
        self.energy_history = deque(maxlen=window_size)
        self.speaking_turns = 0
        self.consecutive_speech_chunks = 0
        self.consecutive_silence_chunks = 0
        self.last_state = False

    def reset(self):
        self.state_history.clear()
        self.energy_history.clear()
        self.speaking_turns = 0
        self.consecutive_speech_chunks = 0
        self.consecutive_silence_chunks = 0
        self.last_state = False

    def update(self, vad_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates interaction statistics with latest VAD outcome.
        """
        is_speech = vad_result.get("is_speech", False)
        rms = vad_result.get("rms_energy", 0.0)

        self.state_history.append(is_speech)
        self.energy_history.append(rms)

        # Detect speaking turn transitions:
        # A new turn occurs when speech resumes after at least 1-3 seconds of pause
        if is_speech:
            self.consecutive_speech_chunks += 1
            if not self.last_state and self.consecutive_silence_chunks >= 1:
                self.speaking_turns += 1
            self.consecutive_silence_chunks = 0
        else:
            self.consecutive_silence_chunks += 1
            self.consecutive_speech_chunks = 0

        self.last_state = is_speech

        # Window analysis
        total_chunks = len(self.state_history)
        if total_chunks == 0:
            speech_ratio = 0.0
            silence_ratio = 1.0
        else:
            speech_count = sum(1 for s in self.state_history if s)
            speech_ratio = speech_count / total_chunks
            silence_ratio = 1.0 - speech_ratio

        # Turns per minute normalized to window
        window_duration_min = max(0.1, total_chunks / 60.0)
        recent_turns = self.speaking_turns
        turn_rate = recent_turns / window_duration_min

        # Classify dominant classroom interaction modality
        if speech_ratio > 0.70 and turn_rate < 6.0:
            dominant_state = "Lecture / Monologue"
            interaction_score = 0.45
        elif speech_ratio > 0.30 and turn_rate >= 6.0:
            dominant_state = "Active Discussion / Q&A"
            interaction_score = 0.85
        elif speech_ratio > 0.50 and turn_rate >= 10.0:
            dominant_state = "Collaborative Group Activity"
            interaction_score = 0.90
        elif speech_ratio < 0.15:
            dominant_state = "Quiet / Individual Work"
            interaction_score = 0.30
        else:
            dominant_state = "Moderate Interaction"
            interaction_score = 0.60

        return {
            "speaking_turns": self.speaking_turns,
            "turn_rate_per_min": round(turn_rate, 1),
            "speech_ratio": round(speech_ratio, 3),
            "silence_ratio": round(silence_ratio, 3),
            "interaction_score": round(interaction_score, 2),
            "dominant_state": dominant_state,
            "consecutive_speech_sec": self.consecutive_speech_chunks,
            "consecutive_silence_sec": self.consecutive_silence_chunks
        }
