import numpy as np
import soundfile as sf
import queue
import threading
import time
from typing import Optional, Tuple, Generator
from pathlib import Path

class AudioStreamReader:
    """
    Manages live microphone streaming or audio file playback.
    Thread-safe and privacy-preserving: processes audio chunks in memory
    without writing raw recordings to disk.
    """
    def __init__(self, sample_rate: int = 16000, block_duration: float = 1.0):
        self.sample_rate = sample_rate
        self.block_size = int(sample_rate * block_duration)
        self.buffer_queue = queue.Queue(maxsize=100)
        self.is_running = False
        self.stream = None
        self.thread = None

    def start_mic_stream(self) -> bool:
        """Starts real-time microphone stream via sounddevice if hardware is available."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            has_input = any(d.get("max_input_channels", 0) > 0 for d in devices)
            if not has_input:
                print("No microphone input channels detected.")
                return False

            def callback(indata, frames, time_info, status):
                if status:
                    pass
                # Convert stereo to mono if necessary
                mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
                try:
                    self.buffer_queue.put_nowait(mono.copy().astype(np.float32))
                except queue.Full:
                    try:
                        self.buffer_queue.get_nowait()
                        self.buffer_queue.put_nowait(mono.copy().astype(np.float32))
                    except Exception:
                        pass

            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.block_size,
                dtype="float32",
                callback=callback
            )
            self.stream.start()
            self.is_running = True
            return True
        except Exception as e:
            print(f"Microphone input initialization notice: {e}. Running in video-only / recorded audio mode.")
            self.is_running = False
            return False

    def read_audio_file(self, file_path: Path) -> Generator[np.ndarray, None, None]:
        """
        Reads an audio file in sequential blocks matching the configured sample rate and duration.
        """
        data, sr = sf.read(str(file_path), dtype="float32")
        # Convert multi-channel to mono
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # Resample if sample rate doesn't match
        if sr != self.sample_rate:
            from scipy.signal import resample
            num_samples = int(len(data) * self.sample_rate / sr)
            data = resample(data, num_samples).astype(np.float32)

        # Chunk into block_size slices
        for i in range(0, len(data), self.block_size):
            chunk = data[i: i + self.block_size]
            if len(chunk) < self.block_size:
                # Pad last chunk with silence
                chunk = np.pad(chunk, (0, self.block_size - len(chunk)))
            yield chunk

    def get_next_block(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """Retrieves next audio block from live queue."""
        try:
            return self.buffer_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self.is_running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        while not self.buffer_queue.empty():
            try:
                self.buffer_queue.get_nowait()
            except Exception:
                break
