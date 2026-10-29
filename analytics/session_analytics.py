from typing import Dict, Any, List
import numpy as np

class SessionAnalytics:
    """
    Computes session-level aggregate metrics, trend distributions, and chart-ready timelines.
    """
    @staticmethod
    def aggregate_session(session_info: Dict[str, Any],
                          attendance_records: List[Dict[str, Any]],
                          engagement_summaries: List[Dict[str, Any]],
                          audio_summaries: List[Dict[str, Any]],
                          recommendations: List[Dict[str, Any]],
                          enrolled_count: int = 0) -> Dict[str, Any]:
        """
        Calculates holistic analytics summary for a classroom session.
        """
        total_detected = len(attendance_records)
        present_records = [r for r in attendance_records if r.get("status") == "present"]
        total_present = len(present_records)

        # Attendance Rate
        if enrolled_count > 0:
            attendance_rate = round((total_present / enrolled_count) * 100.0, 1)
        elif total_detected > 0:
            attendance_rate = round((total_present / total_detected) * 100.0, 1)
        else:
            attendance_rate = 0.0

        # Engagement Aggregates
        if engagement_summaries:
            fused_scores = [s.get("fused_score", 0.0) for s in engagement_summaries]
            visual_scores = [s.get("visual_score", 0.0) for s in engagement_summaries]
            audio_scores = [s.get("audio_score", 0.0) for s in engagement_summaries]

            avg_engagement = round(float(np.mean(fused_scores)), 1)
            visual_index = round(float(np.mean(visual_scores)), 1)
            audio_index = round(float(np.mean(audio_scores)), 1)

            # Categorical distribution
            high_count = sum(1 for s in fused_scores if s >= 75.0)
            mod_count = sum(1 for s in fused_scores if 50.0 <= s < 75.0)
            low_count = sum(1 for s in fused_scores if s < 50.0)
            total_windows = len(fused_scores)

            distribution = {
                "high_pct": round((high_count / total_windows) * 100.0, 1),
                "moderate_pct": round((mod_count / total_windows) * 100.0, 1),
                "low_pct": round((low_count / total_windows) * 100.0, 1)
            }
        else:
            avg_engagement = 0.0
            visual_index = 0.0
            audio_index = 0.0
            distribution = {"high_pct": 0.0, "moderate_pct": 0.0, "low_pct": 0.0}

        # Conversational / Speech Dynamics
        total_speaking_turns = max([a.get("speaking_turns", 0) for a in audio_summaries], default=0)
        total_speech_sec = max([a.get("total_speech_sec", 0.0) for a in audio_summaries], default=0.0)
        total_silence_sec = max([a.get("total_silence_sec", 0.0) for a in audio_summaries], default=0.0)

        # Timeline generation for Chart.js
        timeline = []
        for i, s in enumerate(engagement_summaries):
            timeline.append({
                "time_label": f"T+{i * 10}s",
                "fused_score": s.get("fused_score", 0.0),
                "visual_score": s.get("visual_score", 0.0),
                "audio_score": s.get("audio_score", 0.0),
                "speech_ratio": round(s.get("speech_ratio", 0.0) * 100.0, 1),
                "forward_ratio": round(s.get("forward_facing_ratio", 0.0) * 100.0, 1)
            })

        # Generate descriptive analytical summary text
        summary_text = (
            f"Session '{session_info.get('title')}' recorded {total_present} present participants "
            f"out of {total_detected} detected tracks ({attendance_rate}% attendance). "
            f"The mean experimental engagement index was {avg_engagement}% "
            f"(Visual: {visual_index}%, Audio: {audio_index}%) with {total_speaking_turns} conversational turns."
        )

        return {
            "session_id": session_info.get("id"),
            "session_title": session_info.get("title"),
            "duration_seconds": session_info.get("duration_seconds", 0.0),
            "enrolled_count": enrolled_count,
            "total_detected": total_detected,
            "total_present": total_present,
            "attendance_rate": attendance_rate,
            "avg_engagement_score": avg_engagement,
            "visual_index": visual_index,
            "audio_index": audio_index,
            "distribution": distribution,
            "total_speaking_turns": total_speaking_turns,
            "total_speech_sec": round(total_speech_sec, 1),
            "total_silence_sec": round(total_silence_sec, 1),
            "timeline": timeline,
            "recommendations_count": len(recommendations),
            "summary_text": summary_text
        }
