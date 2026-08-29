"""
Vision Extractor for Paper Trade Licenses and Registration Certificates.
Uses Gemini Vision models with strict zero-hallucination prompts.
"""

import json
import mimetypes
from pathlib import Path
from typing import Optional, Any

from google.genai import types

from .config import get_gemini_client
from .schemas import LicenseExtraction
from utils.schema_sanitizer import sanitize_schema_for_gemini


VISION_SYSTEM_PROMPT = """You are an expert OCR and official document analysis system for Ethiopian and regional trade licenses, commercial registration certificates, and business identification papers.

Your sole duty is to extract exact, verifiable, verbatim information from the provided license image into structured JSON format.

CRITICAL ANTI-HALLUCINATION & INTEGRITY RULES:
1. ONLY extract information that is explicitly and clearly visible in the image.
2. If any field (business name, TIN, registration date, owner name, location) is blurry, smudged, cut off, obscured, or missing, YOU MUST SET THAT FIELD TO null (None).
3. NEVER guess, synthesize, interpolate, or extrapolate names, numbers, or dates.
4. If the image is completely illegible, corrupted, or does not contain a business license/certificate, set "is_legible": false and state the reason in "extraction_notes".
5. For TIN numbers, extract the exact numeric sequence without fabricating missing digits.
6. For dates, transcribe verbatim as written (whether Ethiopian Calendar E.C. or Gregorian Calendar G.C.).
"""

VISION_EXTRACTION_PROMPT = """Examine the attached license or registration certificate image.
Extract the following fields strictly according to the anti-hallucination rules:
- business_name: Registered trade or business name.
- tin_number: Taxpayer Identification Number.
- registration_date: Date of issuance or registration.
- owner_name: Legal owner, general manager, or representative named on the license.
- location: Business address, city, woreda, or zone.
- is_legible: Boolean indicating whether the document is readable.
- extraction_notes: Any notes about clarity, stamp visibility, or missing elements.

Respond ONLY with a valid JSON object matching the requested schema."""


def extract_license_data(
    image_path: str,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> LicenseExtraction:
    """
    Extract structured business information from a license image using Gemini Vision.

    Args:
        image_path: Absolute or relative path to the image file (jpg, png, webp, pdf).
        model: Gemini model identifier (default: "gemini-2.0-flash").
        api_key: Optional Gemini API key override.
        client: Optional pre-configured genai Client (useful for unit testing/mocking).

    Returns:
        LicenseExtraction: Validated Pydantic model with extracted license fields.

    Raises:
        FileNotFoundError: If the specified image path does not exist.
    """
    file_path = Path(image_path)
    if not file_path.exists():
        raise FileNotFoundError(f"License image not found at path: {image_path}")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        ext = file_path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

    # Read binary bytes
    with open(file_path, "rb") as f:
        image_bytes = f.read()

    # Get client
    ai_client = client or get_gemini_client(api_key=api_key)

    # Prepare multimodal content
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        types.Part.from_text(text=VISION_EXTRACTION_PROMPT),
    ]

    # Configure structured generation
    config = types.GenerateContentConfig(
        system_instruction=VISION_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=sanitize_schema_for_gemini(LicenseExtraction),
        temperature=0.0,  # Zero temperature for deterministic extraction
    )

    try:
        response = ai_client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception as err:
        return LicenseExtraction(
            is_legible=False,
            extraction_notes=f"Vision model temporarily unavailable or rate-limited: {str(err)}"
        )

    if not raw_text:
        return LicenseExtraction(
            is_legible=False,
            extraction_notes="Empty or null response received from Vision model."
        )

    try:
        return LicenseExtraction.model_validate_json(raw_text)
    except Exception:
        # Fallback to json dictionary parsing if needed
        data = json.loads(raw_text)
        return LicenseExtraction.model_validate(data)
