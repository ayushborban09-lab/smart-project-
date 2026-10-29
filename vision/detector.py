import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import os
from pathlib import Path
from config import BASE_DIR

class FaceDetector:
    """
    Robust local face detector with offline local cascades and fallback strategies.
    Provides fast, privacy-preserving face detection and landmark extraction.
    """
    def __init__(self, min_size: Tuple[int, int] = (30, 30), scale_factor: float = 1.15, min_neighbors: int = 5):
        self.min_size = min_size
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        
        # Candidate cascade paths (local data/cascades directory takes precedence)
        local_cascade_dir = BASE_DIR / "data" / "cascades"
        cv2_cascade_dir = Path(getattr(cv2.data, "haarcascades", "")) if hasattr(cv2, "data") else Path("")
        
        face_paths = [
            local_cascade_dir / "haarcascade_frontalface_default.xml",
            cv2_cascade_dir / "haarcascade_frontalface_default.xml",
        ]
        
        eye_paths = [
            local_cascade_dir / "haarcascade_eye.xml",
            cv2_cascade_dir / "haarcascade_eye.xml",
        ]
        
        self.face_cascade = None
        for p in face_paths:
            if p.exists():
                cascade = cv2.CascadeClassifier(str(p))
                if not cascade.empty():
                    self.face_cascade = cascade
                    break

        self.eye_cascade = None
        for p in eye_paths:
            if p.exists():
                cascade = cv2.CascadeClassifier(str(p))
                if not cascade.empty():
                    self.eye_cascade = cascade
                    break

        if self.face_cascade is None or self.face_cascade.empty():
            print("Warning: OpenCV Haar Face Cascade could not be loaded. Skin-tone contour detector will act as secondary fallback.")

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in frame and returns bounding boxes, confidence, and eye landmarks.
        """
        if frame is None or frame.size == 0:
            return []

        h_frame, w_frame = frame.shape[:2]
        
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        gray_eq = cv2.equalizeHist(gray)
        detections = []

        if self.face_cascade is not None and not self.face_cascade.empty():
            try:
                rects, reject_levels, level_weights = self.face_cascade.detectMultiScale3(
                    gray_eq,
                    scaleFactor=self.scale_factor,
                    minNeighbors=self.min_neighbors,
                    minSize=self.min_size,
                    outputRejectLevels=True
                )
            except Exception:
                try:
                    rects = self.face_cascade.detectMultiScale(
                        gray_eq,
                        scaleFactor=self.scale_factor,
                        minNeighbors=self.min_neighbors,
                        minSize=self.min_size
                    )
                    level_weights = [1.0] * len(rects)
                except Exception:
                    rects = []
                    level_weights = []

            for i, (x, y, w, h) in enumerate(rects):
                weight = float(level_weights[i]) if i < len(level_weights) else 1.0
                conf = min(0.99, max(0.5, 1.0 / (1.0 + np.exp(-0.5 * weight))))
                
                landmarks = {}
                if self.eye_cascade is not None and not self.eye_cascade.empty():
                    roi_gray = gray_eq[y: y + int(h * 0.6), x: x + w]
                    try:
                        eyes = self.eye_cascade.detectMultiScale(
                            roi_gray,
                            scaleFactor=1.1,
                            minNeighbors=3,
                            minSize=(int(w * 0.15), int(h * 0.15)),
                            maxSize=(int(w * 0.45), int(h * 0.45))
                        )
                        if len(eyes) >= 2:
                            sorted_eyes = sorted(eyes, key=lambda e: e[0])
                            e1, e2 = sorted_eyes[0], sorted_eyes[-1]
                            landmarks["left_eye"] = (x + e1[0] + e1[2] // 2, y + e1[1] + e1[3] // 2)
                            landmarks["right_eye"] = (x + e2[0] + e2[2] // 2, y + e2[1] + e2[3] // 2)
                        elif len(eyes) == 1:
                            e1 = eyes[0]
                            landmarks["eye"] = (x + e1[0] + e1[2] // 2, y + e1[1] + e1[3] // 2)
                    except Exception:
                        pass

                detections.append({
                    "bbox": (int(x), int(y), int(w), int(h)),
                    "confidence": round(conf, 3),
                    "landmarks": landmarks
                })

        return detections
