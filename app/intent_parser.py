import json
import logging
import os

from groq import Groq

logger = logging.getLogger("voice-pipeline")

GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are an intent parser for a voice assistant. Given a spoken sentence transcribed from audio, extract the intent and entities as JSON.

Respond with ONLY valid JSON, no markdown, no explanation, in this exact shape:
{"intent": "<intent_name>", "entities": {<key>: <value>}, "confidence": <0.0-1.0>}

Valid intents: turn_on_device, turn_off_device, set_timer, get_weather, play_music, set_volume, ask_question, greeting, unknown

If the sentence does not clearly match any intent, use "unknown" with empty entities and confidence 0.0.
"""


class IntentParser:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set. Add it to your .env file.")
        self.client = Groq(api_key=api_key)

    def parse(self, text):
        if not text.strip():
            return {"intent": "unknown", "entities": {}, "confidence": 0.0}

        raw = ""
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                max_tokens=200,
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Intent parser returned non-JSON: {raw}")
            return {"intent": "unknown", "entities": {}, "confidence": 0.0}
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            return {"intent": "unknown", "entities": {}, "confidence": 0.0}