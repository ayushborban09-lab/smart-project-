from typing import Dict, Optional, Any
import threading
from session_worker import SessionProcessorWorker
from database.repositories import SessionRepository

class SessionManager:
    """
    Singleton registry managing active background processing workers for sessions.
    Ensures safe concurrency and avoids duplicate workers.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SessionManager, cls).__new__(cls)
                cls._instance.workers: Dict[int, SessionProcessorWorker] = {}
            return cls._instance

    def start_session(self, session_id: int, input_type: str = "webcam",
                      video_path: Optional[str] = None, audio_path: Optional[str] = None) -> bool:
        with self._lock:
            # If an existing worker is active for this session, stop it first
            if session_id in self.workers:
                worker = self.workers[session_id]
                if worker.is_running:
                    return True  # Already running

            sess = SessionRepository.get_by_id(session_id)
            if not sess:
                return False

            worker = SessionProcessorWorker(
                session_id=session_id,
                input_type=input_type,
                video_path=video_path,
                audio_path=audio_path
            )
            success = worker.start()
            if success:
                self.workers[session_id] = worker
            return success

    def stop_session(self, session_id: int) -> bool:
        with self._lock:
            if session_id in self.workers:
                worker = self.workers[session_id]
                worker.stop()
                del self.workers[session_id]
                return True
            else:
                SessionRepository.update_status(session_id, "stopped")
                return True

    def get_worker(self, session_id: int) -> Optional[SessionProcessorWorker]:
        with self._lock:
            return self.workers.get(session_id)

    def is_session_running(self, session_id: int) -> bool:
        with self._lock:
            worker = self.workers.get(session_id)
            return worker.is_running if worker else False
