import asyncio
import os
import sys
import wave

import websockets

CHUNK_SIZE = 4096
SERVER_URI = "ws://127.0.0.1:8000/ws/audio/test-client-1"


def load_audio_bytes(path: str | None) -> bytes:
    if path:
        with wave.open(path, "rb") as wf:
            return wf.readframes(wf.getnframes())
    # No file given: fake 5 seconds of 16-bit mono noise at 16kHz
    return os.urandom(16000 * 2 * 5)


async def stream_audio(path: str | None):
    audio_bytes = load_audio_bytes(path)
    async with websockets.connect(SERVER_URI) as ws:
        print(f"Connected. Streaming {len(audio_bytes)} bytes...")
        for i in range(0, len(audio_bytes), CHUNK_SIZE):
            await ws.send(audio_bytes[i:i + CHUNK_SIZE])
            await asyncio.sleep(0.05)  # simulate real-time pacing
        print("Done.")


if __name__ == "__main__":
    wav_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(stream_audio(wav_path))