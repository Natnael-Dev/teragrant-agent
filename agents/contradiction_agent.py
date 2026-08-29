"""
Contradiction Detection Agent (Reviewer Path).
Combines deterministic Python mathematical validation, visual evidence cross-checks,
and Gemini semantic discrepancy analysis.
"""

import json
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, ValidationError

from google.genai import types

from extractors.config import get_gemini_client, call_gemini_with_fallback
from extractors.schemas import WorkshopExtraction
from schemas.gap_schema import ApplicationPack
from schemas.reviewer_schema import Contradiction, ContradictionSeverity, ContradictionKind


class SemanticContradictionResponse(BaseModel):
    """Container schema for LLM semantic contradiction outputs."""
    model_config = ConfigDict(extra="ignore")

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

CRITICAL TAXONOMY CLASSIFICATION:
For each finding, classify 'kind' into exactly one of:
- CONTRADICTION: Direct factual or mathematical impossibility
- DISCREPANCY: Disagreement between distinct observation sources (e.g. photo vs audio)
- MISSING_EVIDENCE: Unsubstantiated narrative claim lacking corroboration
- PLAUSIBLE: Narrative claim consistent with operations but currently unverified by physical artifacts

CRITICAL RULES:
1. ONLY flag genuine contradictions supported by evidence in the provided data. Do not hallucinate fake discrepancies.
2. Classify severity accurately (CRITICAL or WARNING).
3. Return an empty list if no semantic contradictions exist."""


def detect_contradictions(
    pack: ApplicationPack,
    workshop_data: Optional[WorkshopExtraction] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> List[Contradiction]:
    """
    Detects internal, cross-document, and visual contradictions within an ApplicationPack.
    Executes deterministic mathematical and visual checks in pure Python first, then invokes Gemini for semantic checks.
    """
    contradictions: List[Contradiction] = []

    # =========================================================================
    # 1. PURE PYTHON MATHEMATICAL CHECKS
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
                    kind=ContradictionKind.CONTRADICTION,
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
                    kind=ContradictionKind.CONTRADICTION,
                    explanation=f"Mathematical contradiction: The staff headcount ({total_staff}) does not equal the sum of the age demographic distribution ({age_sum}).",
                )
            )

        # Visual workshop photo headcount cross-check
        if workshop_data and workshop_data.estimated_people_present is not None:
            photo_count = workshop_data.estimated_people_present
            if abs(photo_count - total_staff) > 2 and total_staff > 0:
                contradictions.append(
                    Contradiction(
                        claim_a=f"Application declares a total staff headcount of {total_staff}",
                        claim_b=f"Workshop facility photo shows approximately {photo_count} worker(s) present",
                        severity=ContradictionSeverity.WARNING,
                        kind=ContradictionKind.DISCREPANCY,
                        explanation=f"Visual evidence discrepancy: Declared workforce ({total_staff}) differs notably from observed on-site workers ({photo_count}) in facility photo.",
                    )
                )

    # =========================================================================
    # 2. GEMINI SEMANTIC & CROSS-DOCUMENT CHECKS
    # =========================================================================
    ai_client = client or get_gemini_client(api_key=api_key)

    audit_payload = {
        "application_data": pack.application.model_dump() if pack.application else None,
        "impact_data": pack.impact.model_dump() if pack.impact else None,
        "workshop_observations": workshop_data.model_dump() if workshop_data else None,
        "identified_gaps": [g.model_dump() for g in pack.gaps],
    }

    schema_prompt = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(SemanticContradictionResponse.model_json_schema(), default=str)}"
    user_prompt = f"""Perform a deep forensic contradiction audit on this application pack:

APPLICATION FILE:
{json.dumps(audit_payload, indent=2, ensure_ascii=False)}
{schema_prompt}"""

    config = types.GenerateContentConfig(
        system_instruction=CONTRADICTION_SYSTEM_PROMPT,
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
    except Exception:
        raw_text = ""

    if raw_text:
        try:
            semantic_res = SemanticContradictionResponse.model_validate_json(raw_text)
            contradictions.extend(semantic_res.contradictions)
        except (ValidationError, json.JSONDecodeError):
            try:
                data = json.loads(raw_text)
                semantic_res = SemanticContradictionResponse.model_validate(data)
                contradictions.extend(semantic_res.contradictions)
            except Exception:
                pass

    return contradictions
