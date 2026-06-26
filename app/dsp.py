import numpy as np
import librosa

TARGET_SAMPLE_RATE = 16000


class AudioDSPPipeline:
    """
    Transforms raw Int16 PCM byte buffers into clean, resampled,
    normalized float32 audio tensors ready for downstream speech models.
    """

    def __init__(self, source_sample_rate: int, target_sample_rate: int = TARGET_SAMPLE_RATE):
        self.source_sample_rate = source_sample_rate
        self.target_sample_rate = target_sample_rate

    def bytes_to_tensor(self, raw_bytes: bytes) -> np.ndarray:
        """Int16 PCM bytes -> float32 array scaled to [-1.0, 1.0]."""
        int16_array = np.frombuffer(raw_bytes, dtype=np.int16)
        return int16_array.astype(np.float32) / 32768.0

    def resample(self, audio: np.ndarray) -> np.ndarray:
        if self.source_sample_rate == self.target_sample_rate:
            return audio
        return librosa.resample(
            audio, orig_sr=self.source_sample_rate, target_sr=self.target_sample_rate
        )

    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """Peak normalization. Skips silent/empty buffers safely."""
        peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
        if peak < 1e-6:
            return audio
        return audio / peak

    def process(self, raw_bytes: bytes) -> np.ndarray:
        audio = self.bytes_to_tensor(raw_bytes)
        audio = self.resample(audio)
        audio = self.normalize(audio)
        return audio