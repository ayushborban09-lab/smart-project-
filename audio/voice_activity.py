import numpy as np
from typing import Dict, Any, Tuple
from config import Config

class VoiceActivityDetector:
    """
    Offline Voice Activity Detector (VAD).
    Combines Short-Time RMS Energy, Zero Crossing Rate (ZCR),
    and Spectral Centroid with adaptive background noise floor estimation.
    """
    def __init__(self, sample_rate: int = 16000, 
                 energy_threshold: float = 0.012, 
                 zcr_threshold: float = 0.04):
        self.sample_rate = sample_rate
        self.base_energy_threshold = energy_threshold
        self.zcr_threshold = zcr_threshold
        self.noise_floor = 0.003
        self.speech_chunks_count = 0
        self.silence_chunks_count = 0
        self.total_speech_sec = 0.0
        self.total_silence_sec = 0.0

    def reset(self):
        self.noise_floor = 0.003
        self.speech_chunks_count = 0
        self.silence_chunks_count = 0
        self.total_speech_sec = 0.0
        self.total_silence_sec = 0.0

    def process_chunk(self, audio_chunk: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes a 1.0s audio chunk and returns VAD metrics.
        """
        if audio_chunk is None or len(audio_chunk) == 0:
            return {
                "is_speech": False,
                "rms_energy": 0.0,
                "zcr": 0.0,
                "spectral_centroid": 0.0,
                "snr_db": 0.0,
                "noise_floor_db": -60.0
            }

        # 1. RMS Energy
        rms = float(np.sqrt(np.mean(audio_chunk ** 2)))

        # 2. Zero-Crossing Rate
        signs = np.sign(audio_chunk)
        signs[signs == 0] = 1
        zcr = float(np.mean(np.abs(np.diff(signs))) / 2.0)

        # 3. Spectral Centroid via FFT
        magnitude_spectrum = np.abs(np.fft.rfft(audio_chunk))
        frequencies = np.fft.rfftfreq(len(audio_chunk), d=1.0 / self.sample_rate)
        spec_sum = np.sum(magnitude_spectrum)
        if spec_sum > 1e-6:
            spectral_centroid = float(np.sum(frequencies * magnitude_spectrum) / spec_sum)
        else:
            spectral_centroid = 0.0

        # 4. Adaptive Noise Floor Tracking
        if rms < self.noise_floor * 1.5 or rms < 0.005:
            self.noise_floor = 0.95 * self.noise_floor + 0.05 * max(1e-5, rms)

        # Dynamic energy thresholding based on estimated noise floor
        dynamic_threshold = max(self.base_energy_threshold, self.noise_floor * 2.8)

        # 5. Speech Decision
        # Human speech typically has moderate ZCR (> 0.02 and < 0.35) and spectral centroid between 300Hz and 3500Hz
        is_speech = (
            rms >= dynamic_threshold and
            (0.015 <= zcr <= 0.40) and
            (250.0 <= spectral_centroid <= 4200.0)
        )

        chunk_duration = len(audio_chunk) / self.sample_rate

        if is_speech:
            self.speech_chunks_count += 1
            self.total_speech_sec += chunk_duration
        else:
            self.silence_chunks_count += 1
            self.total_silence_sec += chunk_duration

        snr_ratio = max(1e-3, rms / max(1e-5, self.noise_floor))
        snr_db = round(float(20.0 * np.log10(snr_ratio)), 1)
        noise_floor_db = round(float(20.0 * np.log10(max(1e-6, self.noise_floor))), 1)

        return {
            "is_speech": is_speech,
            "rms_energy": round(rms, 4),
            "zcr": round(zcr, 4),
            "spectral_centroid": round(spectral_centroid, 1),
            "snr_db": snr_db,
            "noise_floor_db": noise_floor_db,
            "total_speech_sec": round(self.total_speech_sec, 1),
            "total_silence_sec": round(self.total_silence_sec, 1)
        }
