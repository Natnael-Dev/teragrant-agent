"""
Multimodal Mapper & Gap Analysis Agent.
Merges raw OCR license data and voice note transcriptions into structured ApplicationPack models.
Enforces zero-hallucination policies and generates explicit Gap records for any missing information.
"""

import json
from typing import Optional, Any

from google.genai import types

from extractors.config import get_gemini_client
from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction
from schemas.gap_schema import ApplicationPack, Gap, GapPriority
from utils.schema_sanitizer import sanitize_schema_for_gemini


MAPPER_SYSTEM_PROMPT = """You are the Senior Intake & Form Mapping Agent for the TeraGrant SME Grant Program.

Your responsibility is to take raw data extracted from two distinct intake sources:
1. License OCR Data (from official paper trade license / registration certificate)
2. Audio Transcript & Facts (from the applicant's spoken voice note)

And systematically merge them into a structured ApplicationPack containing:
- ApplicationSchema (Sections 1.1 - 2.6: Business Info, Employment, Financials, Organogram, Declarations, Exclusions)
- ImpactProtocol (Project title, location, beneficiaries, financial target, sector, SDGs, Milestones)
- Gaps (List of missing, unverified, or ambiguous fields)

CRITICAL ANTI-HALLUCINATION & GAP IDENTIFICATION RULES:
1. SOURCE PRECEDENCE:
   - For formal legal identity (Business Name, TIN, official location), prioritize the License OCR.
   - For operational narrative, headcount, business story, products, and impact goals, utilize the Audio extraction.
2. GENDER & DEMOGRAPHIC CALCULATIONS:
   - If total staff is stated (e.g. 8 workers) and a partial gender count is given (e.g. 6 women):
     Calculate the complementary count (Male: 2, Female: 6, Other: 0) so that male + female + other equals total_staff exactly.
   - If total staff is given but gender breakdown is omitted, create an explicit Gap for 'employment.gender_split'.
3. FINANCIAL TARGETS & ASSETS:
   - Map requested machinery and birr figures (e.g. 500,000 birr) into impact.etb_financial_target and impact.project_title / machinery_list.
4. ABSOLUTE ZERO-HALLUCINATION POLICY:
   - If a field is NOT present in either the license or the audio, LEAVE IT NULL OR EMPTY.
   - DO NOT fabricate missing TIN numbers, sales numbers, employee gender splits, age breakdowns, or milestones.
5. GAP GENERATION:
   - For EVERY essential field that is missing, unreadable, or incomplete, YOU MUST create a Gap object:
     * field_name: exact path (e.g. 'business_info.tin_number', 'employment.gender_split', 'financials.sales_history')
     * reason_missing: specific explanation (e.g. 'TIN was missing on the uploaded trade license.', 'Voice note mentioned total staff but did not provide gender breakdown.')
     * required_from: 'Applicant', 'Tax Office', 'Guarantor', or 'Site Visit'
     * priority: HIGH, MEDIUM, or LOW
6. DECLARATIONS & EXCLUSIONS:
   - All 15 declarations in ApplicationSchema MUST default to false unless explicitly confirmed.
   - All 3 exclusion factors default to false unless evidence indicates otherwise.
"""


def generate_application_pack(
    license_data: LicenseExtraction,
    audio_data: AudioTranscriptExtraction,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> ApplicationPack:
    """
    Synthesizes raw intake data into an ApplicationPack with structured schemas and identified gaps.

    Args:
        license_data: Extracted license OCR data from VisionExtractor.
        audio_data: Extracted audio transcript and facts from AudioExtractor.
        model: Gemini model identifier (default: 'gemini-2.0-flash').
        api_key: Optional Gemini API key override.
        client: Optional pre-configured genai Client.

    Returns:
        ApplicationPack: Validated Pydantic model with merged application, impact protocol, and gaps.
    """
    ai_client = client or get_gemini_client(api_key=api_key)

    intake_context = {
        "license_ocr_input": license_data.model_dump(),
        "audio_transcript_input": audio_data.model_dump(),
    }

    user_prompt = f"""Merge the following intake sources into an ApplicationPack.
Follow all anti-hallucination instructions strictly.

INTAKE DATA:
{json.dumps(intake_context, indent=2, ensure_ascii=False)}

Respond ONLY with a valid JSON object matching the ApplicationPack schema."""

    config = types.GenerateContentConfig(
        system_instruction=MAPPER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=sanitize_schema_for_gemini(ApplicationPack),
        temperature=0.0,
    )

    try:
        response = ai_client.models.generate_content(
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception as err:
        return ApplicationPack(
            application=None,
            impact=None,
            gaps=[
                Gap(
                    field_name="general_intake",
                    reason_missing=f"Mapper temporarily unavailable or rate-limited: {str(err)}",
                    required_from="Applicant",
                    priority=GapPriority.HIGH,
                )
            ]
        )

    if not raw_text:
        return ApplicationPack(
            application=None,
            impact=None,
            gaps=[
                Gap(
                    field_name="general_intake",
                    reason_missing="Mapper failed to produce a valid response from the intake data.",
                    required_from="Applicant",
                    priority=GapPriority.HIGH,
                )
            ]
        )

    try:
        return ApplicationPack.model_validate_json(raw_text)
    except Exception:
        data = json.loads(raw_text)
        return ApplicationPack.model_validate(data)
