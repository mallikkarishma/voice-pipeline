import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger("voice-pipeline")

MODEL_SIZE = "base"


class Transcriber:
    def __init__(self, model_size=MODEL_SIZE):
        logger.info(f"Loading faster-whisper model '{model_size}' (first run downloads weights)...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(audio, language="en", beam_size=5)
        return " ".join(segment.text.strip() for segment in segments).strip()