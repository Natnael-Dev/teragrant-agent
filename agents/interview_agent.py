"""
Guided Conversational Intake Agent (State Machine).
Orchestrates a 7-step guided interview where the AI asks targeted questions,
extracts atomic facts per step, updates the digital twin form incrementally,
and synthesizes accumulated answers into a standard AudioTranscriptExtraction.
"""

import json
import re
from typing import List, Dict, Optional, Any
from pydantic import ValidationError
from google.genai import types

from schemas.interview_schema import InterviewStep, AnswerExtraction
from extractors.schemas import AudioTranscriptExtraction
from extractors.config import get_gemini_client, call_gemini_with_fallback


# =============================================================================
# 7-STEP TRILINGUAL INTERVIEW DEFINITIONS
# Note: Amharic and Afaan Oromo questions are approximate (verify with native speaker).
# =============================================================================
INTERVIEW_STEPS: List[InterviewStep] = [
    InterviewStep(
        step_id="S1",
        field_path="business_info.business_name",
        question_en="What is your name, and what is the name of your business?",
        question_am="ስምዎ ማን ይባል? የንግድ ቋምስ ስም ማን ነው?",  # verify with native speaker
        question_or="Maqaan kee eenyu? Maqaan daldala keetoo maalii?",  # verify with native speaker
        example_answer="My name is Almaz Bekele and my business is Almaz Spice Mill.",
    ),
    InterviewStep(
        step_id="S2",
        field_path="business_info.location",
        question_en="Where is your business located? City or woreda.",
        question_am="ንግድዎ የት ቦታ ይገኛል? ከተማ ወይም ወረዳ?",  # verify with native speaker
        question_or="Daldalli kee eessatti argama?",  # verify with native speaker
        example_answer="Bahir Dar, Amhara Region.",
    ),
    InterviewStep(
        step_id="S3",
        field_path="business_info.sector",
        question_en="What do you make or sell?",
        question_am="ምን ያመርታሉ ወይም ይሸጣሉ?",  # verify with native speaker
        question_or="Maal oomishtuu ykn gurgurtaa?",  # verify with native speaker
        example_answer="We produce ground spices, berbere and shiro.",
    ),
    InterviewStep(
        step_id="S4",
        field_path="employment.total_staff",
        question_en="How many people work for you, and how many of them are women?",
        question_am="ስንት ሰዎች ይሰሩልዎታል? ስንቱ ሴቶች ናቸው?",  # verify with native speaker
        question_or="Hojjattoota meeqatu siif hojjeta? Meeqatu dubartoota?",  # verify with native speaker
        example_answer="8 workers, 6 of them are women.",
    ),
    InterviewStep(
        step_id="S5",
        field_path="business_info.years_in_operation",
        question_en="For how many years have you been operating?",
        question_am="ስንት ዓመት ሆነዎት እየሰሩ?",  # verify with native speaker
        question_or="Waggaa meeqaaf hojjechaa jirta?",  # verify with native speaker
        example_answer="3 years.",
    ),
    InterviewStep(
        step_id="S6",
        field_path="impact.etb_financial_target",
        question_en="What do you need for your business, and how much does it cost in birr?",
        question_am="ለንግድዎ ምን ያስፈልግዎታል? ዋጋውስ ስንት ብር ነው?",  # verify with native speaker
        question_or="Maaltu daldala keetiif barbaachisa? Birrii meeqa?",  # verify with native speaker
        example_answer="Commercial spice pulverizer machine costing 450,000 Birr.",
    ),
    InterviewStep(
        step_id="S7",
        field_path="impact.project_title",
        question_en="Who buys your product, and where?",
        question_am="ማን ነው ምርትዎን የሚገዛው? የትስ?",  # verify with native speaker
        question_or="Eentutu oomisha kee bita? Eessatti?",  # verify with native speaker
        example_answer="Local household consumers and regional restaurant cooperatives.",
    ),
]


EXTRACTION_SYSTEM_PROMPT = """You are a strict data extraction specialist.
Your task is to extract ONE specific fact from a spoken interview transcript matching the target field.

ENTITY ISOLATION RULE: You must extract ONLY the core entity. Ignore all conversational filler, greetings, meta-speech, and pronouns.
Examples:
If user says 'Hello, my name is Dexter', the name is 'Dexter' (NOT 'Hello my name is Dexter').
If user says 'Uh, we are located in Bekoji', the location is 'Bekoji'.
If user says 'I have about 8 workers', the count is 8.

CRITICAL RULES:
1. ONLY extract the core entity fact directly requested for the given field.
2. If the user's answer does not contain the requested fact or is completely irrelevant/incoherent, return value null and confidence 0.0.
3. NEVER guess, assume, or hallucinate missing details.
4. Return confidence between 0.0 (unclear/missing) and 1.0 (explicit, clear statement).

Output JSON with keys:
- "field_id": string (the exact field_path requested)
- "value": string or null
- "confidence": float (0.0 to 1.0)
- "notes": string or null"""


def extract_answer(
    step: InterviewStep,
    transcript: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> AnswerExtraction:
    """
    Extracts an atomic fact from a single interview answer using Gemini.
    """
    if not transcript or not transcript.strip():
        return AnswerExtraction(field_id=step.field_path, value=None, confidence=0.0, notes="Empty answer transcript.")

    ai_client = client or get_gemini_client(api_key=api_key)

    schema_instruction = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(AnswerExtraction.model_json_schema(), default=str)}"
    user_prompt = f"""Target Field: {step.field_path}
Step Description / Context: {step.question_en}
Applicant Spoken Answer:
"{transcript.strip()}"
{schema_instruction}"""

    config = types.GenerateContentConfig(
        system_instruction=EXTRACTION_SYSTEM_PROMPT,
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
        return AnswerExtraction(
            field_id=step.field_path,
            value=None,
            confidence=0.0,
            notes=f"Extraction model error: {str(err)}"
        )

    if not raw_text:
        return AnswerExtraction(field_id=step.field_path, value=None, confidence=0.0, notes="Empty model response.")

    try:
        return AnswerExtraction.model_validate_json(raw_text)
    except (ValidationError, json.JSONDecodeError) as parse_err:
        try:
            retry_prompt = f"Your previous JSON was invalid: {str(parse_err)}. Return corrected JSON matching schema:\n{json.dumps(AnswerExtraction.model_json_schema(), default=str)}"
            retry_resp, _ = call_gemini_with_fallback(
                client=ai_client,
                model=model,
                contents=[types.Part.from_text(text=retry_prompt), types.Part.from_text(text=raw_text)],
                config=config,
            )
            retry_text = retry_resp.text if retry_resp and hasattr(retry_resp, "text") else ""
            return AnswerExtraction.model_validate_json(retry_text)
        except Exception:
            try:
                data = json.loads(raw_text)
                return AnswerExtraction.model_validate(data)
            except Exception:
                return AnswerExtraction(field_id=step.field_path, value=None, confidence=0.0, notes="Failed to parse output.")


def _parse_staff_counts(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Regex / rule-based fallback parser for headcount and female staff split.
    Handles phrases like '8 workers, 6 women', '12 staff with 7 female', '5 people'.
    """
    if not text:
        return None, None

    clean_text = text.lower().replace(",", " ")
    
    # Pattern 1: Explicit labels
    total_match = re.search(r'(\d+)\s*(?:total|workers?|employees?|staff|people|technicians?)', clean_text)
    female_match = re.search(r'(\d+)\s*(?:female|women|girls?|ladies)', clean_text)

    total_staff = int(total_match.group(1)) if total_match else None
    female_staff = int(female_match.group(1)) if female_match else None

    # Pattern 2: Consecutive digits if labels missed
    if total_staff is None:
        all_digits = [int(d) for d in re.findall(r'\b\d+\b', clean_text)]
        if len(all_digits) == 1:
            total_staff = all_digits[0]
        elif len(all_digits) >= 2:
            total_staff = all_digits[0]
            female_staff = all_digits[1]

    # Logical bound check: female cannot exceed total
    if total_staff is not None and female_staff is not None and female_staff > total_staff:
        # swap if accidentally reversed
        total_staff, female_staff = female_staff, total_staff

    return total_staff, female_staff


def merge_answer(
    interview_data: Dict[str, Any],
    step: InterviewStep,
    extraction: AnswerExtraction,
) -> Dict[str, Any]:
    """
    Merges a verified extracted answer into the accumulated interview data dictionary.
    Sets values only if extraction.value is not None and confidence >= 0.5.
    """
    updated_data = dict(interview_data)

    if not extraction or extraction.value is None or extraction.confidence < 0.5:
        # Do not merge low-confidence or null extractions
        return updated_data

    val = str(extraction.value).strip()

    if step.step_id == "S1":  # Name & Business
        updated_data["company_name"] = val
        updated_data["business_name"] = val
    elif step.step_id == "S2":  # Location
        updated_data["address"] = val
        updated_data["location"] = val
    elif step.step_id == "S3":  # Product / Sector
        updated_data["main_products"] = val
        updated_data["sector"] = val
    elif step.step_id == "S4":  # Staff & Female staff
        total_s, female_s = _parse_staff_counts(val)
        updated_data["staff_raw"] = val
        if total_s is not None:
            updated_data["total_staff"] = total_s
        if female_s is not None:
            updated_data["female_staff"] = female_s
    elif step.step_id == "S5":  # Years in operation
        years_match = re.search(r'\b\d+\b', val)
        if years_match:
            updated_data["years_in_operation"] = int(years_match.group(0))
        else:
            updated_data["years_in_operation"] = val
    elif step.step_id == "S6":  # Financial request & machinery
        updated_data["machinery_requested"] = val
        # Extract currency number if present
        curr_match = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:birr|etb)?', val.lower())
        if curr_match:
            num_str = curr_match.group(1).replace(",", "")
            try:
                updated_data["requested_etb"] = f"{int(float(num_str)):,} ETB"
            except ValueError:
                updated_data["requested_etb"] = val
        else:
            updated_data["requested_etb"] = val
    elif step.step_id == "S7":  # Market / Commercial target
        updated_data["market_target"] = val
        updated_data["project_title"] = f"{updated_data.get('company_name', 'SME')} — {val[:40]}"

    return updated_data


def synthesize_audio_extraction(
    interview_data: Dict[str, Any],
    transcript_parts: List[str],
) -> AudioTranscriptExtraction:
    """
    Builds an AudioTranscriptExtraction from accumulated interview Q&A.
    Allows the entire existing mapper, gate, router, and scorer pipeline to be reused unmodified.
    """
    full_transcript = "\n".join(t for t in transcript_parts if t and t.strip())
    if not full_transcript:
        full_transcript = "Guided interview voice intake completed."

    b_name = interview_data.get("company_name") or interview_data.get("business_name")
    loc = interview_data.get("address") or interview_data.get("location")
    prod = interview_data.get("main_products") or interview_data.get("sector")
    
    tot_staff = interview_data.get("total_staff")
    if tot_staff is not None:
        try:
            tot_staff = int(tot_staff)
        except (ValueError, TypeError):
            tot_staff = None

    fin_list = []
    if interview_data.get("requested_etb"):
        fin_list.append(str(interview_data["requested_etb"]))

    machinery = interview_data.get("machinery_requested", "Equipment upgrades")
    market = interview_data.get("market_target", "Commercial markets")
    impact_sum = f"Need: {machinery}. Target market: {market}."

    return AudioTranscriptExtraction(
        transcript=full_transcript,
        detected_language=interview_data.get("detected_language", "English"),
        business_name=b_name,
        employee_count=tot_staff,
        product_type=prod,
        location=loc,
        financial_figures=fin_list,
        impact_summary=impact_sum,
    )
