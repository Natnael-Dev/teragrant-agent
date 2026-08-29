"""
Audio Extractor Agent for Multilingual Voice Intake.
Transcribes and extracts business narrative facts from spoken audio in Amharic, Afaan Oromo, English, etc.
"""

import json
import mimetypes
from pathlib import Path
from typing import Optional, Any
from pydantic import ValidationError

from google.genai import types

from .config import get_gemini_client, call_gemini_with_fallback
from .schemas import AudioTranscriptExtraction


AUDIO_SYSTEM_PROMPT = """You are an expert multilingual transcription and data extraction officer.
You must perform your task in TWO STRICT STEPS.

STEP 1: VERBATIM TRANSCRIPTION
Transcribe the audio EXACTLY as spoken, word-for-word, in the original language (Amharic, Afaan Oromo, or English). Do not summarize. Do not correct grammar. If a word is unclear, use [unclear].

STEP 2: FACT EXTRACTION (BASED ONLY ON STEP 1)
Read your transcript from Step 1. Extract the following facts ONLY if they are explicitly stated in the transcript. NEVER guess or infer.
- business_name
- employee_count (integer)
- female_staff (integer)
- product_type
- location
- financial_figures (list of strings with currency)

ENTITY ISOLATION RULE: You must extract ONLY the core entity. Ignore all conversational filler, greetings, meta-speech, and pronouns.
Examples:
If user says 'Hello, my name is Dexter', the name is 'Dexter' (NOT 'Hello my name is Dexter').
If user says 'Uh, we are located in Bekoji', the location is 'Bekoji'.
If user says 'I have about 8 workers', the count is 8.

OUTPUT FORMAT:
Return ONLY a valid JSON object matching the AudioTranscriptExtraction schema. The 'transcript' field MUST contain the exact output of Step 1."""


def extract_audio_story(
    audio_path: str,
    target_language: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> AudioTranscriptExtraction:
    """
    Transcribes audio and extracts structured business facts from the spoken voice note.
    Raises RuntimeError on failed extraction to prevent silent empty intake.
    """
    file_path = Path(audio_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found at: {audio_path}")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    if not audio_bytes:
        raise ValueError(f"Audio file at {audio_path} is empty (0 bytes).")

    ext = file_path.suffix.lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".webm": "audio/webm",
    }
    guessed_type, _ = mimetypes.guess_type(str(file_path))
    mime_type = mime_map.get(ext) or guessed_type or "audio/mpeg"
    if ext == ".wav" or mime_type in ("audio/x-wav", "audio/wave"):
        mime_type = "audio/wav"

    ai_client = client or get_gemini_client(api_key=api_key)

    audio_part = types.Part.from_bytes(
        data=audio_bytes,
        mime_type=mime_type,
    )
    schema_instruction = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(AudioTranscriptExtraction.model_json_schema(), default=str)}"
    text_prompt = "Transcribe this voice note and extract verified facts.\n" + schema_instruction
    contents = [audio_part, types.Part.from_text(text=text_prompt)]

    config = types.GenerateContentConfig(
        system_instruction=AUDIO_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.0,
    )

    try:
        response, _ = call_gemini_with_fallback(
            client=ai_client,
            model=model,
            contents=contents,
            config=config,
        )
        if isinstance(response, dict) and response.get("quota_exhausted"):
            raise RuntimeError(f"QUOTA_EXHAUSTED: {response.get('message', 'Daily API limit reached.')}")
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception as err:
        raise RuntimeError(f"Audio transcription API failed ({mime_type}): {str(err)}") from err

    if not raw_text or not raw_text.strip():
        raise RuntimeError(f"Gemini returned an empty transcription for {file_path.name} ({mime_type}).")

    try:
        return AudioTranscriptExtraction.model_validate_json(raw_text)
    except (ValidationError, json.JSONDecodeError) as err:
        try:
            retry_prompt = f"Your previous JSON was invalid: {str(err)}. Return corrected JSON matching schema:\n{json.dumps(AudioTranscriptExtraction.model_json_schema(), default=str)}"
            retry_contents = [types.Part.from_text(text=retry_prompt), types.Part.from_text(text=raw_text)]
            retry_resp, _ = call_gemini_with_fallback(
                client=ai_client,
                model=model,
                contents=retry_contents,
                config=config,
            )
            retry_text = retry_resp.text if retry_resp and hasattr(retry_resp, "text") else ""
            return AudioTranscriptExtraction.model_validate_json(retry_text)
        except Exception:
            try:
                data = json.loads(raw_text)
                return AudioTranscriptExtraction.model_validate(data)
            except Exception as final_err:
                raise RuntimeError(f"Failed to parse structured audio output: {str(final_err)}. Raw text: {raw_text[:200]}") from final_err
