import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import time
from collections import deque

class TrackedParticipant:
    """
    State container for a single tracked participant.
    """
    def __init__(self, track_id: str, bbox: Tuple[int, int, int, int], timestamp: float):
        self.track_id = track_id
        self.bbox = bbox  # (x, y, w, h)
        self.centroid = (bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0)
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.disappeared_count = 0
        self.total_frames_detected = 1
        
        # Movement & Inactivity Tracking
        self.centroid_history = deque(maxlen=30)
        self.centroid_history.append((self.centroid[0], self.centroid[1], timestamp))
        self.movement_speed = 0.0  # pixels per second
        self.inactivity_seconds = 0.0
        self.last_significant_movement = timestamp
        
        # Head pose history
        self.forward_facing_frames = 0
        self.current_orientation = "Forward"
        self.is_forward = True

    def update(self, bbox: Tuple[int, int, int, int], timestamp: float, head_pose: Optional[Dict[str, Any]] = None):
        self.bbox = bbox
        new_centroid = (bbox[0] + bbox[2] / 2.0, bbox[1] + bbox[3] / 2.0)
        
        dt = max(1e-4, timestamp - self.last_seen)
        dist = np.hypot(new_centroid[0] - self.centroid[0], new_centroid[1] - self.centroid[1])
        instant_speed = dist / dt
        
        # Exponential smoothing on movement speed
        self.movement_speed = 0.7 * self.movement_speed + 0.3 * instant_speed
        
        if dist > 3.0:  # Threshold for noticeable bodily/head micro-movement
            self.last_significant_movement = timestamp
            self.inactivity_seconds = 0.0
        else:
            self.inactivity_seconds = timestamp - self.last_significant_movement

        self.centroid = new_centroid
        self.centroid_history.append((new_centroid[0], new_centroid[1], timestamp))
        self.last_seen = timestamp
        self.disappeared_count = 0
        self.total_frames_detected += 1
        
        if head_pose:
            self.current_orientation = head_pose.get("orientation", "Forward")
            self.is_forward = head_pose.get("is_forward", True)
            if self.is_forward:
                self.forward_facing_frames += 1

    def mark_missed(self, timestamp: float):
        self.disappeared_count += 1
        self.inactivity_seconds = timestamp - self.last_significant_movement

    @property
    def forward_facing_ratio(self) -> float:
        if self.total_frames_detected == 0:
            return 0.0
        return min(1.0, self.forward_facing_frames / self.total_frames_detected)

    @property
    def presence_span(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)


class ParticipantTracker:
    """
    Multi-object tracker with occlusion handling and temporal association.
    Uses distance-matrix matching between tracked centroids and new detections.
    """
    def __init__(self, max_disappeared: int = 45, max_distance: float = 120.0):
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.next_id_counter = 101
        self.tracks: Dict[str, TrackedParticipant] = {}

    def _generate_track_id(self) -> str:
        tid = f"P-{self.next_id_counter}"
        self.next_id_counter += 1
        return tid

    def update(self, detections: List[Dict[str, Any]], timestamp: Optional[float] = None) -> List[TrackedParticipant]:
        """
        Updates participant tracks with new frame detections.
        detections: list of dicts with 'bbox' and optional 'head_pose'
        """
        if timestamp is None:
            timestamp = time.time()

        # If no detections in this frame
        if len(detections) == 0:
            for track in list(self.tracks.values()):
                track.mark_missed(timestamp)
                if track.disappeared_count > self.max_disappeared:
                    del self.tracks[track.track_id]
            return list(self.tracks.values())

        input_bboxes = [d["bbox"] for d in detections]
        input_centroids = np.array([
            (b[0] + b[2] / 2.0, b[1] + b[3] / 2.0) for b in input_bboxes
        ])

        # If currently tracking no participants, register all incoming detections
        if len(self.tracks) == 0:
            for i, det in enumerate(detections):
                tid = self._generate_track_id()
                track = TrackedParticipant(tid, det["bbox"], timestamp)
                if "head_pose" in det:
                    track.update(det["bbox"], timestamp, det["head_pose"])
                self.tracks[tid] = track
            return list(self.tracks.values())

        # Match existing tracks with detections via Euclidean distance
        track_ids = list(self.tracks.keys())
        track_centroids = np.array([self.tracks[tid].centroid for tid in track_ids])

        # Compute distance matrix (N existing tracks x M detections)
        D = np.linalg.norm(track_centroids[:, np.newaxis] - input_centroids, axis=2)

        # Greedy association based on minimum distance
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            # If distance exceeds threshold, do not match (could be a different person)
            if D[row, col] > self.max_distance:
                continue

            tid = track_ids[row]
            det = detections[col]
            self.tracks[tid].update(det["bbox"], timestamp, det.get("head_pose"))

            used_rows.add(row)
            used_cols.add(col)

        # Unmatched existing tracks: mark missed
        unused_rows = set(range(len(track_ids))).difference(used_rows)
        for row in unused_rows:
            tid = track_ids[row]
            self.tracks[tid].mark_missed(timestamp)
            if self.tracks[tid].disappeared_count > self.max_disappeared:
                del self.tracks[tid]

        # Unmatched new detections: register as new tracks
        unused_cols = set(range(len(input_bboxes))).difference(used_cols)
        for col in unused_cols:
            tid = self._generate_track_id()
            det = detections[col]
            track = TrackedParticipant(tid, det["bbox"], timestamp)
            if "head_pose" in det:
                track.update(det["bbox"], timestamp, det["head_pose"])
            self.tracks[tid] = track

        return list(self.tracks.values())
