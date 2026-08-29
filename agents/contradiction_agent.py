"""
Contradiction Detection Agent (Reviewer Path).
Combines deterministic Python mathematical validation with Gemini semantic discrepancy analysis.
"""

import json
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from google.genai import types

from extractors.config import get_gemini_client
from schemas.gap_schema import ApplicationPack
from schemas.reviewer_schema import Contradiction, ContradictionSeverity


class SemanticContradictionResponse(BaseModel):
    """Container schema for LLM semantic contradiction outputs."""
    model_config = ConfigDict(extra="forbid")

    contradictions: List[Contradiction] = Field(
        default_factory=list,
        description="List of detected semantic contradictions"
    )


CONTRADICTION_SYSTEM_PROMPT = """You are the Senior Forensic Auditor and Due Diligence Investigator for the TeraGrant SME Grant Program.

Your task is to identify subtle, non-obvious SEMANTIC and NARRATIVE CONTRADICTIONS within an applicant's file across:
1. License OCR Records (official dates, location, business name, owner name)
2. Operational Narrative & Spoken Voice Note (claims of years in operation, products, locations)
3. Financial Figures (revenue history vs funding target vs machinery capacity)
4. Milestone Timelines vs Operational Feasibility

EXAMPLES OF SEMANTIC CONTRADICTIONS:
- License was issued in 2024 (e.g., 2016 E.C.), but applicant claims in their story to have been operating for 10 years.
- Applicant claims to operate a nationwide logistics network, but declares 0 vehicles or machinery.
- Project location in impact protocol differs from registered business license municipality.
- Financial grant target is 10,000,000 ETB, but declared annual revenue is only 50,000 ETB with no collateral or assets.

CRITICAL RULES:
1. ONLY flag genuine contradictions supported by evidence in the provided data. Do not hallucinate fake discrepancies.
2. Classify severity accurately:
   - CRITICAL: Severe misrepresentation, fraudulent document timeline, or fundamental operational conflict.
   - WARNING: Minor discrepancy that might be explained by informal trading history or calendar conversion (E.C. vs G.C.).
3. Return an empty list if no semantic contradictions exist.

Respond strictly in JSON matching the SemanticContradictionResponse schema."""


def detect_contradictions(
    pack: ApplicationPack,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> List[Contradiction]:
    """
    Detects internal and cross-document contradictions within an ApplicationPack.
    Executes deterministic mathematical checks in pure Python first, then invokes Gemini for semantic checks.

    Args:
        pack: The complete ApplicationPack.
        model: Gemini model identifier.
        api_key: Optional API key override.
        client: Optional pre-configured genai Client.

    Returns:
        List[Contradiction]: Combined list of mathematical and semantic contradictions.
    """
    contradictions: List[Contradiction] = []

    # =========================================================================
    # 1. PURE PYTHON MATHEMATICAL & LOGICAL CHECKS
    # =========================================================================
    if pack.application and pack.application.employment:
        emp = pack.application.employment
        total_staff = emp.total_staff
        gender_sum = emp.gender_split.total
        age_sum = emp.age_split.total

        # Gender headcount mismatch
        if gender_sum != total_staff:
            contradictions.append(
                Contradiction(
                    claim_a=f"Total declared staff headcount is {total_staff}",
                    claim_b=f"Sum of gender breakdown is {gender_sum} (Male: {emp.gender_split.male}, Female: {emp.gender_split.female}, Other: {emp.gender_split.other})",
                    severity=ContradictionSeverity.CRITICAL,
                    explanation=f"Mathematical contradiction: The staff headcount ({total_staff}) does not equal the sum of the gender distribution ({gender_sum}).",
                )
            )

        # Age band headcount mismatch
        if age_sum != total_staff:
            contradictions.append(
                Contradiction(
                    claim_a=f"Total declared staff headcount is {total_staff}",
                    claim_b=f"Sum of age band breakdown is {age_sum} (Youth 18-29: {emp.age_split.youth_18_29}, Adults 30-50: {emp.age_split.adults_30_50}, Seniors 50+: {emp.age_split.seniors_above_50})",
                    severity=ContradictionSeverity.CRITICAL,
                    explanation=f"Mathematical contradiction: The staff headcount ({total_staff}) does not equal the sum of the age demographic distribution ({age_sum}).",
                )
            )

    # =========================================================================
    # 2. GEMINI SEMANTIC & CROSS-DOCUMENT CHECKS
    # =========================================================================
    ai_client = client or get_gemini_client(api_key=api_key)

    audit_payload = {
        "application_data": pack.application.model_dump() if pack.application else None,
        "impact_data": pack.impact.model_dump() if pack.impact else None,
        "identified_gaps": [g.model_dump() for g in pack.gaps],
    }

    user_prompt = f"""Perform a deep forensic contradiction audit on this application pack:

APPLICATION FILE:
{json.dumps(audit_payload, indent=2, ensure_ascii=False)}

Identify all semantic discrepancies and return the SemanticContradictionResponse JSON."""

    config = types.GenerateContentConfig(
        system_instruction=CONTRADICTION_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=SemanticContradictionResponse,
        temperature=0.0,
    )

    try:
        response = ai_client.models.generate_content(
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception:
        raw_text = ""
    if raw_text:
        try:
            semantic_res = SemanticContradictionResponse.model_validate_json(raw_text)
            contradictions.extend(semantic_res.contradictions)
        except Exception:
            data = json.loads(raw_text)
            semantic_res = SemanticContradictionResponse.model_validate(data)
            contradictions.extend(semantic_res.contradictions)

    return contradictions
