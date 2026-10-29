import math
from typing import Dict, Any, Tuple

class HeadPoseEstimator:
    """
    Estimates 3D head orientation (Yaw, Pitch, Roll) and frontal attention status
    from face bounding box and extracted facial/ocular landmarks.
    Does not require cloud APIs or external heavy weights.
    """
    def __init__(self, yaw_threshold: float = 28.0, pitch_threshold: float = 25.0):
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold

    def estimate(self, bbox: Tuple[int, int, int, int], landmarks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimates orientation for a detected participant face.
        Returns:
            yaw: horizontal rotation in degrees (-left, +right)
            pitch: vertical rotation in degrees (-down, +up)
            roll: planar tilt in degrees
            orientation: semantic label ('Forward', 'Left', 'Right', 'Down', 'Up')
            is_forward: bool indicator of frontal orientation
        """
        x, y, w, h = bbox
        face_center_x = x + w / 2.0
        face_center_y = y + h / 2.0

        yaw = 0.0
        pitch = 0.0
        roll = 0.0
        
        has_two_eyes = "left_eye" in landmarks and "right_eye" in landmarks
        has_one_eye = "eye" in landmarks

        if has_two_eyes:
            lx, ly = landmarks["left_eye"]
            rx, ry = landmarks["right_eye"]
            
            # Eye midpoint
            eye_mid_x = (lx + rx) / 2.0
            eye_mid_y = (ly + ry) / 2.0
            
            # Yaw estimate based on eye midpoint deviation from face horizontal center
            delta_x = eye_mid_x - face_center_x
            yaw = (delta_x / (w * 0.5)) * 45.0  # Normalized to approximate degrees
            
            # Pitch estimate based on eye vertical level relative to standard eye-line (~38% down face)
            expected_eye_y = y + h * 0.38
            delta_y = expected_eye_y - eye_mid_y
            pitch = (delta_y / (h * 0.4)) * 35.0  # Positive is looking up, negative is down
            
            # Roll angle from horizontal eye slope
            dx = rx - lx
            dy = ry - ly
            if abs(dx) > 1e-3:
                roll = math.degrees(math.atan2(dy, dx))
        elif has_one_eye:
            ex, ey = landmarks["eye"]
            # With only one eye visible, participant is typically turned sideways
            if ex < face_center_x:
                yaw = -35.0  # Turned right from participant's POV / left in camera
            else:
                yaw = 35.0
            expected_eye_y = y + h * 0.38
            pitch = ((expected_eye_y - ey) / (h * 0.4)) * 30.0
        else:
            # Without distinct eye features, assume slight downward or profile gaze
            pitch = -15.0
            yaw = 0.0

        # Classify semantic orientation
        if abs(yaw) <= self.yaw_threshold and abs(pitch) <= self.pitch_threshold:
            orientation = "Forward"
            is_forward = True
        elif yaw < -self.yaw_threshold:
            orientation = "Looking Left"
            is_forward = False
        elif yaw > self.yaw_threshold:
            orientation = "Looking Right"
            is_forward = False
        elif pitch < -self.pitch_threshold:
            orientation = "Looking Down"
            is_forward = False
        else:
            orientation = "Looking Up"
            is_forward = False

        return {
            "yaw": round(float(yaw), 1),
            "pitch": round(float(pitch), 1),
            "roll": round(float(roll), 1),
            "orientation": orientation,
            "is_forward": is_forward
        }
