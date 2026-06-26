import asyncio
import os
import sys
import wave

import websockets

CHUNK_SIZE = 4096
SAMPLE_RATE = 16000  # matches the fake/wav audio we generate below
SERVER_URI = f"ws://127.0.0.1:8000/ws/audio/test-client-1?sample_rate={SAMPLE_RATE}"


def load_audio_bytes(path):
    if path:
        with wave.open(path, "rb") as wf:
            return wf.readframes(wf.getnframes())
    return os.urandom(SAMPLE_RATE * 2 * 5)  # 5 seconds of fake 16-bit mono noise


async def stream_audio(path):
    audio_bytes = load_audio_bytes(path)
    async with websockets.connect(SERVER_URI) as ws:
        print(f"Connected. Streaming {len(audio_bytes)} bytes at {SAMPLE_RATE}Hz...")
        for i in range(0, len(audio_bytes), CHUNK_SIZE):
            await ws.send(audio_bytes[i:i + CHUNK_SIZE])
            await asyncio.sleep(0.05)
        print("Done.")


if __name__ == "__main__":
    wav_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(stream_audio(wav_path))
