"""
Audio Extractor for Multilingual Voice Notes (Amharic, Afaan Oromo, English, etc.).
Uses Gemini multimodal audio understanding with zero-hallucination fact extraction.
"""

import json
import mimetypes
from pathlib import Path
from typing import Optional, Any

from google.genai import types

from .config import get_gemini_client
from .schemas import AudioTranscriptExtraction


AUDIO_SYSTEM_PROMPT = """You are an expert multilingual audio transcriber and SME grant analyst specializing in Ethiopian and East African languages (Amharic, Afaan Oromo, English, Tigrinya, Somali).

Your task is twofold:
1. Provide a verbatim or near-verbatim transcription of the spoken audio note in its original language.
2. Extract verified factual business entities explicitly mentioned by the speaker.

CRITICAL ANTI-HALLUCINATION & PRECISION RULES:
1. Transcribe the audio faithfully. If words are muffled or unclear, transcribe as best as possible without inventing content.
2. Accurately detect the primary spoken language (e.g., 'Amharic', 'Afaan Oromo', 'English', 'Tigrinya', 'Somali').
3. For structured facts (employee_count, product_type, location, business_name, financial_figures):
   - ONLY extract values if the speaker explicitly states them.
   - If the speaker does not state an employee count, set "employee_count": null.
   - If no financial numbers are mentioned, set "financial_figures": [].
   - DO NOT extrapolate, assume, or fabricate any missing numbers, products, or locations.
4. "impact_summary" should summarize the operational story, challenges, and proposed project as communicated by the applicant.
"""

AUDIO_EXTRACTION_PROMPT = """Listen carefully to the attached voice note.
Perform full transcription and structured fact extraction.
Output the result strictly in JSON matching the following schema:
- transcript: Full text of what the speaker said.
- detected_language: Primary language identified (e.g. 'Amharic', 'Afaan Oromo', 'English').
- business_name: Business name if explicitly spoken, or null.
- employee_count: Exact integer headcount mentioned, or null.
- product_type: Core products or services described, or null.
- location: Operating location/region mentioned, or null.
- financial_figures: List of any revenue, expense, or grant funding amounts stated.
- impact_summary: Concise synopsis of their business story and objectives.

Respond ONLY with a valid JSON object matching the requested schema."""


def extract_audio_story(
    audio_path: str,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> AudioTranscriptExtraction:
    """
    Extract transcript and structured business facts from an audio voice note using Gemini.

    Args:
        audio_path: Absolute or relative path to the audio file (mp3, wav, m4a, ogg).
        model: Gemini model identifier (default: "gemini-2.0-flash").
        api_key: Optional Gemini API key override.
        client: Optional pre-configured genai Client (useful for unit testing/mocking).

    Returns:
        AudioTranscriptExtraction: Validated Pydantic model with transcript and structured facts.

    Raises:
        FileNotFoundError: If the specified audio file path does not exist.
    """
    file_path = Path(audio_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found at path: {audio_path}")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        ext = file_path.suffix.lower()
        mime_map = {
            ".mp3": "audio/mp3",
            ".wav": "audio/wav",
            ".m4a": "audio/m4a",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }
        mime_type = mime_map.get(ext, "audio/mp3")

    # Read binary bytes
    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    # Get client
    ai_client = client or get_gemini_client(api_key=api_key)

    # Prepare multimodal content
    contents = [
        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        types.Part.from_text(text=AUDIO_EXTRACTION_PROMPT),
    ]

    # Configure structured generation
    config = types.GenerateContentConfig(
        system_instruction=AUDIO_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=AudioTranscriptExtraction,
        temperature=0.0,
    )

    try:
        response = ai_client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception as err:
        return AudioTranscriptExtraction(
            transcript="",
            detected_language="Unknown",
            impact_summary=f"Audio model temporarily unavailable or rate-limited: {str(err)}"
        )

    if not raw_text:
        return AudioTranscriptExtraction(
            transcript="",
            detected_language="Unknown",
            impact_summary="Failed to transcribe or extract audio story."
        )

    try:
        return AudioTranscriptExtraction.model_validate_json(raw_text)
    except Exception:
        data = json.loads(raw_text)
        return AudioTranscriptExtraction.model_validate(data)
