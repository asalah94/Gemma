"""
Speech-to-Text service using Groq Whisper Large v3.
Replaces the old stt.py (which had a hardcoded API key).

Requires GROQ_API_KEY in environment / .env file.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Map from interview_simulator language names → ISO 639-1 codes
_LANG_CODE = {
    "Arabic":  "ar",
    "English": "en",
    "French":  "fr",
    "Spanish": "es",
    "German":  "de",
    "Italian": "it",
    "Turkish": "tr",
    "Urdu":    "ur",
}

# Medical context prompt — Arabic first so Whisper picks up the language correctly
_MEDICAL_PROMPT = (
    "مقابلة طبية. المريض يصف الأعراض والألم والأدوية والحساسية والتاريخ المرضي. "
    "Medical interview. Patient describing symptoms, pain, medications, allergies, "
    "and medical history."
)


# def transcribe_audio(audio_bytes: bytes, language: str | None = None) -> str:
#     """
#     Transcribe audio bytes (WAV/MP3/OGG/…) to text using Groq Whisper.

#     Parameters
#     ----------
#     audio_bytes : bytes
#         Raw audio data from st.audio_input() or any other source.
#     language : str | None
#         Optional language hint (use interview_simulator language names,
#         e.g. 'Arabic', 'English'). If None, defaults to Arabic.

#     Returns
#     -------
#     str  — The transcribed text.

#     Raises
#     ------
#     EnvironmentError  — If GROQ_API_KEY is not set.
#     RuntimeError      — If transcription fails.
#     """
#     api_key = os.environ.get("GROQ_API_KEY", "").strip()
#     if not api_key:
#         raise EnvironmentError(
#             "GROQ_API_KEY is not set. Add it to your .env file:\n"
#             "  GROQ_API_KEY=gsk_your_key_here"
#         )

#     client = Groq(api_key=api_key)

#     kwargs: dict = {
#         "file": ("audio.webm", audio_bytes),  # webm = actual format sent by browsers
#         "model": "whisper-large-v3-turbo",
#         "prompt": _MEDICAL_PROMPT,            # bilingual medical context
#         "response_format": "json",
#         "temperature": 0.0,
#         "language": "ar",                     # force Arabic — fixes dialect errors
#     }

#     # Override language only if explicitly passed
#     if language:
#         lang_code = _LANG_CODE.get(language)
#         if lang_code:
#             kwargs["language"] = lang_code

#     try:
#         result = client.audio.transcriptions.create(**kwargs)
#         return result.text.strip()
#     except Exception as exc:
#         raise RuntimeError(f"Groq Whisper transcription failed: {exc}") from exc



from deepgram import DeepgramClient
from deepgram.core.events import EventType


def transcribe_audio(audio_bytes: bytes, language: str | None = None) -> str:
    
            client = DeepgramClient()
            response = client.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model="nova-3",
                language="ar",
            )
            print(response.results.channels[0].alternatives[0].transcript)
            return response.results.channels[0].alternatives[0].transcript


