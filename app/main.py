import asyncio
import logging
from contextlib import asynccontextmanager

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect

from app.dsp import AudioDSPPipeline
from app.transcriber import Transcriber
from app.intent_parser import IntentParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-pipeline")

audio_queue = asyncio.Queue(maxsize=500)

client_pipelines = {}
client_buffers = {}
client_buffer_samples = {}

TRANSCRIBE_WINDOW_SECONDS = 3
TRANSCRIBE_WINDOW_SAMPLES = 16000 * TRANSCRIBE_WINDOW_SECONDS

transcriber = None
intent_parser = None


async def audio_consumer():
    loop = asyncio.get_running_loop()
    while True:
        client_id, chunk = await audio_queue.get()
        pipeline = client_pipelines.get(client_id)
        if pipeline is None:
            logger.debug(f"No DSP pipeline for client={client_id}, dropping chunk")
            audio_queue.task_done()
            continue

        tensor = pipeline.process(chunk)
        peak = float(np.max(np.abs(tensor))) if tensor.size else 0.0
        logger.debug(
            f"[dsp] client={client_id} in_samples={len(chunk) // 2} "
            f"out_samples={tensor.shape[0]} peak={peak:.3f} "
            f"queue_depth={audio_queue.qsize()}"
        )

        buffer = client_buffers.setdefault(client_id, [])
        buffer.append(tensor)
        client_buffer_samples[client_id] = client_buffer_samples.get(client_id, 0) + tensor.shape[0]

        if client_buffer_samples[client_id] >= TRANSCRIBE_WINDOW_SAMPLES:
            window_audio = np.concatenate(buffer)
            client_buffers[client_id] = []
            client_buffer_samples[client_id] = 0

            text = await loop.run_in_executor(None, transcriber.transcribe, window_audio)
            if text:
                logger.info(f"[transcript] client={client_id}: {text}")
                intent_result = await loop.run_in_executor(None, intent_parser.parse, text)
                logger.info(f"[intent] client={client_id}: {intent_result}")
            else:
                logger.info(f"[transcript] client={client_id}: (silence/no speech detected)")

        audio_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcriber, intent_parser
    transcriber = Transcriber()
    intent_parser = IntentParser()
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
async def audio_stream(websocket: WebSocket, client_id: str, sample_rate: int = Query(default=48000)):
    await websocket.accept()
    client_pipelines[client_id] = AudioDSPPipeline(source_sample_rate=sample_rate)
    client_buffers[client_id] = []
    client_buffer_samples[client_id] = 0
    logger.info(f"Client '{client_id}' connected at {sample_rate}Hz.")
    try:
        while True:
            data = await websocket.receive_bytes()
            try:
                audio_queue.put_nowait((client_id, data))
            except asyncio.QueueFull:
                logger.warning(f"Queue full, dropping chunk from {client_id}")
    except WebSocketDisconnect:
        logger.info(f"Client '{client_id}' disconnected.")
        client_pipelines.pop(client_id, None)
        client_buffers.pop(client_id, None)
        client_buffer_samples.pop(client_id, None)