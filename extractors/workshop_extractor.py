"""
Workshop Facility Vision Extractor Agent.
Extracts visible machinery assets, estimated headcount, and safety conditions from facility photos.
"""

import json
from pathlib import Path
from typing import Optional, Any
from pydantic import ValidationError

from google.genai import types

from .config import get_gemini_client, call_gemini_with_fallback
from .schemas import WorkshopExtraction


WORKSHOP_SYSTEM_PROMPT = """You are an industrial facility evaluator and due diligence engineer for SME grant verification.

Your task is to analyze an uploaded workshop, factory, or agricultural facility photograph and extract:
1. Estimated number of people / workers present in the frame
2. Visible machinery, specialized tools, workbenches, and equipment
3. Basic workplace safety observations (lighting, protective gear, orderliness, clear hazards)
4. Overall legibility and quality of the facility image

CRITICAL ZERO-HALLUCINATION RULES:
- ONLY report machinery and people that are genuinely identifiable in the photograph.
- If no people are visible, return 0 or null.
- If the image is blurry or dark, set is_legible=false with descriptive extraction_notes."""


def extract_workshop_data(
    image_path: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> WorkshopExtraction:
    """
    Extracts machinery, workforce presence, and safety conditions from a workshop image.
    """
    file_path = Path(image_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Workshop image file not found at: {image_path}")

    with open(file_path, "rb") as f:
        image_bytes = f.read()

    ext = file_path.suffix.lower()
    mime_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime_type = mime_type_map.get(ext, "image/jpeg")

    ai_client = client or get_gemini_client(api_key=api_key)

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    prompt_text = (
        "Analyze this workshop / SME facility photo and extract visible machinery, workers, and conditions.\n\n"
        f"RETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(WorkshopExtraction.model_json_schema(), default=str)}"
    )
    contents = [image_part, types.Part.from_text(text=prompt_text)]

    config = types.GenerateContentConfig(
        system_instruction=WORKSHOP_SYSTEM_PROMPT,
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
        return WorkshopExtraction(
            is_legible=False,
            extraction_notes=f"Workshop extraction error: {str(err)}"
        )

    if not raw_text:
        return WorkshopExtraction(
            is_legible=False,
            extraction_notes="Empty response received from vision model."
        )

    # Robust parsing with 1 retry
    try:
        return WorkshopExtraction.model_validate_json(raw_text)
    except (ValidationError, json.JSONDecodeError) as err:
        try:
            retry_prompt = f"Your previous JSON was invalid: {str(err)}. Return corrected JSON matching schema:\n{json.dumps(WorkshopExtraction.model_json_schema(), default=str)}"
            retry_contents = [types.Part.from_text(text=retry_prompt), types.Part.from_text(text=raw_text)]
            retry_resp, _ = call_gemini_with_fallback(
                client=ai_client,
                model=model,
                contents=retry_contents,
                config=config,
            )
            retry_text = retry_resp.text if retry_resp and hasattr(retry_resp, "text") else ""
            return WorkshopExtraction.model_validate_json(retry_text)
        except Exception:
            try:
                data = json.loads(raw_text)
                return WorkshopExtraction.model_validate(data)
            except Exception:
                return WorkshopExtraction(
                    is_legible=False,
                    extraction_notes="Failed to parse structured workshop data."
                )
