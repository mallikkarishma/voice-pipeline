import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-pipeline")

# Shared in-memory buffer. Items are (client_id, raw_bytes).
# maxsize caps memory if a future consumer (DSP/Whisper) falls behind.
audio_queue: asyncio.Queue = asyncio.Queue(maxsize=500)


async def audio_consumer():
    """
    Drains the queue continuously. For Week 1 this just proves the
    pipeline is flowing end-to-end. Week 3 replaces this loop's body
    with real DSP processing.
    """
    while True:
        client_id, chunk = await audio_queue.get()
        logger.info(
            f"[consumer] client={client_id} chunk_size={len(chunk)}B "
            f"queue_depth={audio_queue.qsize()}"
        )
        audio_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_task = asyncio.create_task(audio_consumer())
    logger.info("Audio consumer started.")
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    logger.info("Audio consumer stopped.")


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/audio/{client_id}")
async def audio_stream(websocket: WebSocket, client_id: str):
    await websocket.accept()
    logger.info(f"Client '{client_id}' connected.")
    try:
        while True:
            data = await websocket.receive_bytes()
            try:
                audio_queue.put_nowait((client_id, data))
            except asyncio.QueueFull:
                logger.warning(f"Queue full — dropping chunk from {client_id}")
    except WebSocketDisconnect:
        logger.info(f"Client '{client_id}' disconnected.")