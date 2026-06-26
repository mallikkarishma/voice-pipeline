import asyncio
import logging
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect

from app.dsp import AudioDSPPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-pipeline")

audio_queue: asyncio.Queue = asyncio.Queue(maxsize=500)

# One DSP pipeline per connected client, keyed by client_id.
# Each client may have a different native mic sample rate.
client_pipelines: dict[str, AudioDSPPipeline] = {}


async def audio_consumer():
    while True:
        client_id, chunk = await audio_queue.get()
        pipeline = client_pipelines.get(client_id)
        if pipeline is None:
            logger.warning(f"No DSP pipeline for client={client_id}, dropping chunk")
            audio_queue.task_done()
            continue

        tensor = pipeline.process(chunk)
        peak = float(np.max(np.abs(tensor))) if tensor.size else 0.0
        logger.info(
            f"[dsp] client={client_id} in_samples={len(chunk) // 2} "
            f"out_samples={tensor.shape[0]} peak={peak:.3f} "
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
async def audio_stream(
    websocket: WebSocket,
    client_id: str,
    sample_rate: int = Query(default=48000),
):
    await websocket.accept()
    client_pipelines[client_id] = AudioDSPPipeline(source_sample_rate=sample_rate)
    logger.info(f"Client '{client_id}' connected at {sample_rate}Hz.")
    try:
        while True:
            data = await websocket.receive_bytes()
            try:
                audio_queue.put_nowait((client_id, data))
            except asyncio.QueueFull:
                logger.warning(f"Queue full — dropping chunk from {client_id}")
    except WebSocketDisconnect:
        logger.info(f"Client '{client_id}' disconnected.")
        client_pipelines.pop(client_id, None)