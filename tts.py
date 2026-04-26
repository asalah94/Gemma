import asyncio
from typing import Optional

try:
    import edge_tts
except Exception:
    edge_tts = None


async def get_text_response(prompt: str) -> str:
    """Return a text response for the given prompt.

    This is used by `interview_simulator` for short LLM calls. Prefer the
    local MedGemma wrapper if available, otherwise return a deterministic
    fallback so the app can function offline.
    """
    if not prompt:
        return ""

    try:
        from medgemma import medgemma_get_text_response

        messages = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]
        return medgemma_get_text_response(messages)
    except Exception:
        # Offline fallback: return a short simulated reply
        return f"[simulated response] {prompt[:400]}"


async def save_arabic_sample_audio(output_file: str = "arabic_legal_voice.mp3") -> Optional[str]:
    """Save a short Arabic TTS sample to `output_file` using edge-tts.

    Returns the output filename on success, otherwise None.
    """
    if edge_tts is None:
        return None

    TEXT = (
        "بناءً على أحكام القانون المدني، فإن عقد الإيجار يُعد من العقود الملزمة للجانبين، "
        "حيث يلتزم المؤجر بتمكين المستأجر من الانتفاع بالعين المؤجرة."
    )
    VOICE = "ar-EG-SalmaNeural"

    try:
        communicate = edge_tts.Communicate(TEXT, VOICE)
        await communicate.save(output_file)
        return output_file
    except Exception:
        return None
