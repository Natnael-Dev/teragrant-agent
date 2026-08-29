"""
Extractors package for TeraGrant Agent.
Provides multimodal OCR for trade licenses, workshop photos, and multilingual audio transcription.
"""

from .config import get_gemini_client, get_api_key, call_gemini_with_fallback, MODEL_FALLBACK_CHAIN
from .schemas import LicenseExtraction, WorkshopExtraction, AudioTranscriptExtraction
from .vision_extractor import extract_license_data
from .workshop_extractor import extract_workshop_data
from .audio_extractor import extract_audio_story

__all__ = [
    "get_gemini_client",
    "get_api_key",
    "call_gemini_with_fallback",
    "MODEL_FALLBACK_CHAIN",
    "LicenseExtraction",
    "WorkshopExtraction",
    "AudioTranscriptExtraction",
    "extract_license_data",
    "extract_workshop_data",
    "extract_audio_story",
]
