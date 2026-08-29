"""
Grid Variant Router Agent.
Analyzes normalized application information and project impact goals to assign the appropriate 100-point scoring grid variant:
- WOMEN_YOUTH_LED
- INNOVATION_TECH
- GENERAL_SME
"""

import json
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, ValidationError

from google.genai import types

from extractors.config import get_gemini_client, call_gemini_with_fallback
from schemas.application_schema import ApplicationSchema
from schemas.impact_schema import ImpactProtocol
from schemas.scoring_schema import GridVariant


class RouterDecision(BaseModel):
    """Structured decision output from the grid variant router."""
    model_config = ConfigDict(extra="ignore")

    variant: Optional[GridVariant] = Field(
        default=None,
        description="The assigned evaluation track (WOMEN_YOUTH_LED, INNOVATION_TECH, or GENERAL_SME)"
    )
    grid_variant: Optional[GridVariant] = Field(
        default=None,
        description="Alternative alias for assigned evaluation track"
    )
    reasoning: Optional[str] = Field(
        default="Routed based on applicant profile",
        description="Detailed justification for selecting this track variant over others"
    )
    routing_rationale: Optional[str] = Field(
        default=None,
        description="Alternative alias for routing justification"
    )

    @property
    def resolved_variant(self) -> GridVariant:
        return self.variant or self.grid_variant or GridVariant.GENERAL_SME


ROUTER_SYSTEM_PROMPT = """You are the Lead Portfolio Strategist and Triage Officer for the TeraGrant SME Grant Program.

Your task is to analyze an applicant's business profile and project impact protocol to assign the enterprise to the single most appropriate Evaluation Grid Variant:

VARIANT CRITERIA:
1. WOMEN_YOUTH_LED:
   - ≥ 50% ownership by women OR by youth aged 18-29
   - OR leadership team / workforce predominantly comprised of women and youth with clear empowerment goals.

2. INNOVATION_TECH:
   - High degree of technological innovation, proprietary hardware/software development, novel processing methods, clean-tech, or import-substituting product engineering.

3. GENERAL_SME:
   - Standard agro-processing, retail, trade, manufacturing, logistics, or services that do not meet the specialized criteria for Women/Youth or Tech tracks.

Respond strictly in JSON matching the RouterDecision schema."""


def route_to_grid_variant(
    application: ApplicationSchema,
    impact: ImpactProtocol,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> GridVariant:
    """
    Routes an application to the optimal 100-point scoring grid variant.
    """
    ai_client = client or get_gemini_client(api_key=api_key)

    intake_summary = {
        "business_name": application.business_info.business_name if application.business_info else None,
        "sector": application.business_info.sector if application.business_info else None,
        "female_ownership_percentage": application.business_info.female_ownership_percentage if application.business_info else 0.0,
        "employment": application.employment.model_dump() if application.employment else None,
        "project_title": impact.project_title if impact else None,
        "impact_sector": impact.sector if impact else None,
        "sdgs": [sdg.value if hasattr(sdg, "value") else str(sdg) for sdg in impact.sdgs] if impact else [],
        "milestones": [m.model_dump() if hasattr(m, "model_dump") else m for m in impact.milestones] if impact else [],
    }

    schema_prompt = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(RouterDecision.model_json_schema(), default=str)}"
    user_prompt = f"""Evaluate this SME application dossier and assign the appropriate GridVariant:

APPLICANT PROFILE:
{json.dumps(intake_summary, indent=2, ensure_ascii=False)}
{schema_prompt}"""

    config = types.GenerateContentConfig(
        system_instruction=ROUTER_SYSTEM_PROMPT,
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
        # Heuristic fallback
        if application.business_info and application.business_info.female_ownership_percentage >= 50.0:
            return GridVariant.WOMEN_YOUTH_LED
        return GridVariant.GENERAL_SME

    if not raw_text:
        if application.business_info and application.business_info.female_ownership_percentage >= 50.0:
            return GridVariant.WOMEN_YOUTH_LED
        return GridVariant.GENERAL_SME

    try:
        decision = RouterDecision.model_validate_json(raw_text)
        return decision.resolved_variant
    except (ValidationError, json.JSONDecodeError):
        try:
            data = json.loads(raw_text)
            decision = RouterDecision.model_validate(data)
            return decision.resolved_variant
        except Exception:
            if application.business_info and application.business_info.female_ownership_percentage >= 50.0:
                return GridVariant.WOMEN_YOUTH_LED
            return GridVariant.GENERAL_SME
