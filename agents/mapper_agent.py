"""
Multimodal Mapper & Gap Analysis Agent.
Merges raw OCR license data, workshop observations, and voice note transcriptions into structured ApplicationPack models.
Enforces zero-hallucination policies and generates explicit Gap records for any missing information.
"""

import json
from typing import Optional, Any
from pydantic import ValidationError

from google.genai import types

from extractors.config import get_gemini_client, call_gemini_with_fallback
from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction, WorkshopExtraction
from schemas.gap_schema import ApplicationPack, Gap, GapPriority


MAPPER_SYSTEM_PROMPT = """You are the Senior Intake & Form Mapping Agent for the TeraGrant SME Grant Program.

Your responsibility is to take raw data extracted from multimodal intake sources:
1. License OCR Data (from official paper trade license / registration certificate)
2. Audio Transcript & Facts (from the applicant's spoken voice note)
3. Optional Workshop Photo Observations (machinery & headcount evidence)

And systematically merge them into a structured ApplicationPack containing:
- ApplicationSchema (Sections 1.1 - 2.6: Business Info, Employment, Financials, Organogram, Declarations, Exclusions)
- ImpactProtocol (Project title, location, beneficiaries, financial target, sector, SDGs, Milestones)
- Gaps (List of missing, unverified, or ambiguous fields)

CRITICAL ANTI-HALLUCINATION & GAP IDENTIFICATION RULES:
1. SOURCE PRECEDENCE:
   - For formal legal identity (Business Name, TIN, official location), prioritize the License OCR if present. If no license is provided, use the business name and owner name stated in the audio.
   - For operational narrative, headcount, business story, products, and impact goals, utilize the Audio extraction.
2. GENDER & DEMOGRAPHIC CALCULATIONS:
   - If total staff is stated (e.g. 8 workers) and a partial gender count is given (e.g. 6 women):
     Calculate the complementary count (Male: 2, Female: 6, Other: 0) so that male + female + other equals total_staff exactly.
   - If total staff is given but gender breakdown is omitted, create an explicit Gap for 'employment.gender_split'.
3. FINANCIAL TARGETS & ASSETS:
   - Map requested machinery and birr figures (e.g. 500,000 birr for packing machine) into impact.etb_financial_target and impact.project_title / machinery_list.
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
   - All 3 exclusion factors default to false unless evidence indicates otherwise."""


def generate_application_pack(
    license_data: LicenseExtraction,
    audio_data: AudioTranscriptExtraction,
    workshop_data: Optional[WorkshopExtraction] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> ApplicationPack:
    """
    Synthesizes raw intake data into an ApplicationPack with structured schemas and identified gaps.
    """
    ai_client = client or get_gemini_client(api_key=api_key)

    intake_context = {
        "license_ocr_input": license_data.model_dump(),
        "audio_transcript_input": audio_data.model_dump(),
        "workshop_photo_input": workshop_data.model_dump() if workshop_data else None,
    }

    schema_prompt = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(ApplicationPack.model_json_schema(), default=str)}"
    user_prompt = f"""Merge the following intake sources into an ApplicationPack.
Follow all anti-hallucination instructions strictly.

INTAKE DATA:
{json.dumps(intake_context, indent=2, ensure_ascii=False)}
{schema_prompt}"""

    config = types.GenerateContentConfig(
        system_instruction=MAPPER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.0,
    )

    try:
        response, _ = call_gemini_with_fallback(
            client=ai_client,
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
                    reason_missing=f"Mapper API failure: {str(err)}",
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
                    reason_missing="Empty mapping response from Gemini.",
                    required_from="Applicant",
                    priority=GapPriority.HIGH,
                )
            ]
        )

    try:
        return ApplicationPack.model_validate_json(raw_text)
    except (ValidationError, json.JSONDecodeError) as err:
        try:
            retry_prompt = f"Your previous JSON was invalid: {str(err)}. Return corrected JSON matching schema:\n{json.dumps(ApplicationPack.model_json_schema(), default=str)}"
            retry_contents = [types.Part.from_text(text=retry_prompt), types.Part.from_text(text=raw_text)]
            retry_resp, _ = call_gemini_with_fallback(
                client=ai_client,
                model=model,
                contents=retry_contents,
                config=config,
            )
            retry_text = retry_resp.text if retry_resp and hasattr(retry_resp, "text") else ""
            return ApplicationPack.model_validate_json(retry_text)
        except Exception as retry_err:
            try:
                data = json.loads(raw_text)
                return ApplicationPack.model_validate(data)
            except Exception:
                raise RuntimeError(f"Mapper failed to generate valid ApplicationPack: {str(retry_err)}")
