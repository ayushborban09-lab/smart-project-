import time
import requests
import json
from typing import Dict, Any, List, Optional
from config import Config
from .recommendation_rules import RecommendationRules
from database.repositories import RecommendationRepository, SettingsRepository

class RecommendationEngine:
    """
    AI Teaching Recommendation Agent.
    Operates offline by default using transparent pedagogical rule-based models.
    Supports optional locally-hosted LLM integration (e.g. Ollama) with instant fallback.
    """
    def __init__(self, cooldown_seconds: float = 20.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_recommendation_time = 0.0
        self.rules = RecommendationRules()
        self.history: List[Dict[str, Any]] = []

    def reset(self):
        self.last_recommendation_time = 0.0
        self.history.clear()

    def generate(self, session_id: int, 
                 current_engagement: Dict[str, Any], 
                 session_duration_sec: float,
                 force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyzes session state and generates a pedagogical recommendation if cooldown has elapsed.
        """
        now = time.time()
        if not force and (now - self.last_recommendation_time) < self.cooldown_seconds:
            return None

        # Check configuration for local LLM vs rule-based engine
        mode = SettingsRepository.get_value("recommendation_engine_mode", "rule_based")
        recommendation = None

        if mode == "local_llm" or Config.ENABLE_LOCAL_LLM:
            recommendation = self._query_local_llm(current_engagement, session_duration_sec)

        # Fallback to rule-based offline baseline if local LLM is inactive or failed
        if recommendation is None:
            recommendation = self.rules.evaluate(
                current_engagement, self.history, session_duration_sec
            )

        if recommendation is not None:
            self.last_recommendation_time = now
            self.history.append(current_engagement)

            # Store in database
            rec_id = RecommendationRepository.add_recommendation(
                session_id=session_id,
                category=recommendation["category"],
                observation=recommendation["observation"],
                supporting_indicators=recommendation["supporting_indicators"],
                suggested_action=recommendation["suggested_action"],
                reason=recommendation["reason"],
                confidence=recommendation["confidence"]
            )
            recommendation["id"] = rec_id
            recommendation["timestamp"] = now

        return recommendation

    def _query_local_llm(self, current_engagement: Dict[str, Any], session_duration_sec: float) -> Optional[Dict[str, Any]]:
        """
        Queries an optional local LLM server (e.g. Ollama running on localhost).
        Fails safely if service is offline.
        """
        url = Config.LOCAL_LLM_URL
        payload = {
            "model": Config.LOCAL_LLM_MODEL,
            "prompt": f"""You are an educational pedagogy advisor analyzing classroom observation metrics:
Session Duration: {session_duration_sec:.1f}s
Engagement Estimate: {current_engagement.get('fused_score')}%
Speech Activity Ratio: {current_engagement.get('speech_ratio')}
Forward Facing Ratio: {current_engagement.get('forward_facing_ratio')}
Data Quality: {current_engagement.get('data_quality')}

Provide 1 practical, actionable teaching recommendation in JSON format with keys:
category, observation, suggested_action, reason, confidence (High/Medium/Preliminary)""",
            "stream": False,
            "format": "json"
        }
        try:
            resp = requests.post(url, json=payload, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                content = json.loads(data.get("response", "{}"))
                if "suggested_action" in content:
                    content["supporting_indicators"] = {
                        "fused_score": current_engagement.get("fused_score"),
                        "speech_ratio": current_engagement.get("speech_ratio")
                    }
                    return content
        except Exception:
            # Safe offline degradation: fallback to rule-based engine
            pass
        return None
