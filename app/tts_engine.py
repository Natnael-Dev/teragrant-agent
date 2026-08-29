"""
TTS Engine using gTTS to produce MP3 audio bytes for Python/Streamlit native autoplay.
"""
import io
from gtts import gTTS


def generate_speech_audio(text: str, lang: str = "en") -> bytes:
    """
    Generates spoken audio bytes (MP3) from text using gTTS.
    Maps English, Amharic, and Afaan Oromo appropriately.
    """
    lang_map = {
        "Amharic": "am",
        "am": "am",
        "Oromo": "om",
        "om": "om",
        "English": "en",
        "en": "en",
        "Afaan Oromo": "om",
    }
    target_lang = lang_map.get(lang, "en")
    try:
        tts = gTTS(text=text, lang=target_lang)
    except Exception:
        # Fallback to English if the specific dialect is unsupported
        tts = gTTS(text=text, lang="en")

    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()
