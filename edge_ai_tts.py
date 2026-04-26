import os
import io
import logging
import asyncio
import edge_tts
from pydub import AudioSegment
from cache import cache

# --- Constants ---
GENERATE_SPEECH = os.environ.get("GENERATE_SPEECH", "true").lower() == "true"
DEFAULT_VOICE = "en-US-AriaNeural"

# Voice Mapping to prevent "Invalid Voice" errors
VOICE_MAP = {
    "Aoede": "en-US-EmmaNeural",
    "Gacrux": "en-US-AndrewNeural",
    "Puck": "en-GB-ThomasNeural",
    "Salma": "ar-EG-SalmaNeural",
    "Shakir": "ar-EG-ShakirNeural"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TTSGenerationError(Exception):
    pass

async def _synthesize_edge_tts_impl(text: str, voice_name: str) -> tuple[bytes, str]:
    if not GENERATE_SPEECH:
        raise TTSGenerationError("GENERATE_SPEECH is disabled.")

    # Translate the voice name if it's an old Gemini name
    target_voice = VOICE_MAP.get(voice_name, voice_name)

    try:
        communicate = edge_tts.Communicate(text, target_voice)
        audio_data = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        if not audio_data:
            raise TTSGenerationError("No audio data received.")

        # If FFmpeg is installed, pydub works. 
        # If you still have issues with FFmpeg, you can skip pydub 
        # and return audio_data directly since edge-tts returns mp3.
        try:
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            mp3_buffer = io.BytesIO()
            audio_segment.export(mp3_buffer, format="mp3")
            return mp3_buffer.getvalue(), "audio/mpeg"
        except Exception as pydub_err:
            logging.warning(f"Pydub failed (FFmpeg issue?), returning raw data: {pydub_err}")
            return audio_data, "audio/mpeg"

    except Exception as e:
        logging.error(f"Edge-TTS Error: {e}")
        raise TTSGenerationError(f"Unexpected error: {e}")

def _run_tts_sync(text: str, voice_name: str):
    """
    Handles the async loop safely to ensure we return DATA, not a COROUTINE.
    """
    try:
        # Create a new event loop for this thread (important for Flask)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_synthesize_edge_tts_impl(text, voice_name))
        loop.close()
        return result
    except Exception as e:
        logging.error(f"Sync Wrapper Error: {e}")
        return None, None

_memoized_tts_func = cache.memoize()(_run_tts_sync)

def synthesize_tts(text: str, voice_name: str = DEFAULT_VOICE) -> tuple[bytes | None, str | None]:
    if not GENERATE_SPEECH:
        key = _memoized_tts_func.__cache_key__(text, voice_name)
        result = cache.get(key, default=None)
        return result if result else (None, None)

    return _memoized_tts_func(text, voice_name)