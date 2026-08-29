"""
Vision Extractor Agent for Trade Licenses.
Extracts business identity, registration date, TIN, and owner details from document photos.
"""

import json
from pathlib import Path
from typing import Optional, Any
from pydantic import ValidationError

from google.genai import types

from .config import get_gemini_client, call_gemini_with_fallback
from .schemas import LicenseExtraction


VISION_SYSTEM_PROMPT = """You are an expert OCR and official document analysis system for Ethiopian and regional trade licenses, commercial registration certificates, and business identification papers.

Your objective is to extract verifiable, factual fields from the uploaded document image.

CRITICAL ZERO-HALLUCINATION RULES:
1. ONLY extract information that is visibly present on the document.
2. If a field is smudged, cut off, obscured by a stamp/stain, or unreadable, YOU MUST return null for that field.
3. NEVER guess or hallucinate digits in a TIN number, dates, or names.
4. Set 'is_legible' to false if the document is unreadable or not an official license."""


def extract_license_data(
    image_path: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> LicenseExtraction:
    """
    Extracts structured business information from a trade license image.
    """
    file_path = Path(image_path)
    if not file_path.exists():
        raise FileNotFoundError(f"License image file not found at: {image_path}")

    with open(file_path, "rb") as f:
        image_bytes = f.read()

    ext = file_path.suffix.lower()
    mime_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    mime_type = mime_type_map.get(ext, "image/jpeg")

    if not model or "2.0" in str(model) or "3.6" in str(model):
        model = "gemini-1.5-flash"

    ai_client = client or get_gemini_client(api_key=api_key)

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )
    schema_instruction = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(LicenseExtraction.model_json_schema(), default=str)}"
    text_prompt = "Extract all readable fields from this trade license.\n" + schema_instruction
    contents = [image_part, types.Part.from_text(text=text_prompt)]

    config = types.GenerateContentConfig(
        system_instruction=VISION_SYSTEM_PROMPT,
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
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception as err:
        return LicenseExtraction(
            is_legible=False,
            extraction_notes=f"Vision model temporarily unavailable: {str(err)}"
        )

    if not raw_text:
        return LicenseExtraction(
            is_legible=False,
            extraction_notes="Empty or null response received from Vision model."
        )

    try:
        return LicenseExtraction.model_validate_json(raw_text)
    except (ValidationError, json.JSONDecodeError) as err:
        try:
            retry_prompt = f"Your previous JSON was invalid: {str(err)}. Return corrected JSON matching schema:\n{json.dumps(LicenseExtraction.model_json_schema(), default=str)}"
            retry_contents = [types.Part.from_text(text=retry_prompt), types.Part.from_text(text=raw_text)]
            retry_resp, _ = call_gemini_with_fallback(
                client=ai_client,
                model=model,
                contents=retry_contents,
                config=config,
            )
            retry_text = retry_resp.text if retry_resp and hasattr(retry_resp, "text") else ""
            return LicenseExtraction.model_validate_json(retry_text)
        except Exception:
            try:
                data = json.loads(raw_text)
                return LicenseExtraction.model_validate(data)
            except Exception:
                return LicenseExtraction(
                    is_legible=False,
                    extraction_notes="Failed to parse structured license data."
                )
