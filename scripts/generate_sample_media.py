import cv2
import numpy as np
import soundfile as sf
from pathlib import Path
import sys

# Ensure project root is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import Config

def generate_sample_classroom_video(output_path: Path, duration_sec: int = 15, fps: int = 15):
    """
    Synthesizes a realistic 720p classroom video test file with moving participants.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 720, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    total_frames = duration_sec * fps
    participants = [
        {"base_x": 160, "base_y": 190, "w": 90, "h": 110, "color": (210, 180, 150)},
        {"base_x": 360, "base_y": 180, "w": 95, "h": 115, "color": (220, 190, 160)},
        {"base_x": 560, "base_y": 200, "w": 85, "h": 105, "color": (200, 170, 140)}
    ]

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        frame = np.full((height, width, 3), (25, 20, 15), dtype=np.uint8)

        # Draw Classroom Board
        cv2.rectangle(frame, (60, 40), (660, 120), (45, 38, 30), -1)
        cv2.putText(frame, "SAMPLE RECORDED CLASSROOM LECTURE", (120, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 240, 255), 2)

        for i, p in enumerate(participants):
            # Natural micro-posture movement
            dx = int(8.0 * np.sin(t * 1.5 + i * 2.0))
            dy = int(5.0 * np.cos(t * 1.2 + i * 1.5))
            fx, fy = p["base_x"] + dx, p["base_y"] + dy
            fw, fh = p["w"], p["h"]

            # Draw participant
            cv2.ellipse(frame, (fx + fw // 2, fy + fh + 60), (fw, 50), 0, 0, 360, (50, 45, 38), -1)
            cv2.ellipse(frame, (fx + fw // 2, fy + fh // 2), (fw // 2, fh // 2), 0, 0, 360, p["color"], -1)

            # Eyes
            eye_y = fy + int(fh * 0.38)
            cv2.circle(frame, (fx + int(fw * 0.32), eye_y), 4, (40, 30, 20), -1)
            cv2.circle(frame, (fx + int(fw * 0.68), eye_y), 4, (40, 30, 20), -1)

        out.write(frame)

    out.release()
    print(f"Sample classroom video created: {output_path} ({duration_sec}s, {total_frames} frames)")

def generate_sample_classroom_audio(output_path: Path, duration_sec: int = 15, sample_rate: int = 16000):
    """
    Synthesizes a 16kHz classroom audio file with alternating speech and silence turns.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_samples = duration_sec * sample_rate
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    
    # Base background ambient room noise
    audio = 0.002 * np.random.randn(total_samples)

    # Speech burst from t=2s to t=6s (Instructor)
    mask1 = (t >= 2.0) & (t <= 6.0)
    audio[mask1] += 0.06 * np.sin(2 * np.pi * 440 * t[mask1]) + 0.03 * np.sin(2 * np.pi * 880 * t[mask1])

    # Speech burst from t=8s to t=12s (Student Q&A)
    mask2 = (t >= 8.0) & (t <= 12.0)
    audio[mask2] += 0.05 * np.sin(2 * np.pi * 520 * t[mask2]) + 0.02 * np.sin(2 * np.pi * 1040 * t[mask2])

    sf.write(str(output_path), audio.astype(np.float32), sample_rate)
    print(f"Sample classroom audio created: {output_path} ({duration_sec}s, 16kHz)")

if __name__ == "__main__":
    Config.init_directories()
    vid_file = Config.SAMPLE_MEDIA_FOLDER / "sample_classroom_video.mp4"
    aud_file = Config.SAMPLE_MEDIA_FOLDER / "sample_classroom_audio.wav"
    generate_sample_classroom_video(vid_file, duration_sec=10)
    generate_sample_classroom_audio(aud_file, duration_sec=10)
