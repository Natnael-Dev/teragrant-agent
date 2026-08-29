"""
Grid Router Agent.
Analyzes enterprise demographics, business sector, technology profile, and SDG impact
to route the application to the optimal 100-Point Scoring Grid Variant.
"""

import json
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from google.genai import types

from extractors.config import get_gemini_client
from schemas.application_schema import ApplicationSchema
from schemas.impact_schema import ImpactProtocol
from schemas.scoring_schema import GridVariant


class RouterDecision(BaseModel):
    """Structured decision output from the Grid Router."""
    model_config = ConfigDict(extra="forbid")

    grid_variant: GridVariant = Field(..., description="The selected scoring grid variant")
    routing_rationale: str = Field(..., description="Brief rationale explaining why this variant best fits the applicant")


ROUTER_SYSTEM_PROMPT = """You are the Senior Reviewer Routing Agent for the TeraGrant SME Grant Program.

Your responsibility is to analyze the applicant's business profile, ownership structure, workforce demographics, sector, and SDG impacts to assign the most appropriate 100-Point Scoring Grid Variant:

1. WOMEN_YOUTH_LED:
   - Assign if female equity ownership >= 50%, or business is woman-founded/led.
   - Assign if majority (>50%) of the workforce/leadership is youth (aged 18 to 29).

2. INNOVATION_TECH:
   - Assign if the core business involves software, agri-tech hardware, renewable energy, clean-tech, biotechnology, digital platforms, or patented/novel manufacturing innovations.

3. GENERAL_SME:
   - Assign to standard/traditional commercial enterprises, conventional manufacturing, established trading, food processing, or services that do not primarily qualify for the specialized tracks above.

Respond strictly in JSON matching the RouterDecision schema."""


def route_to_grid_variant(
    application: ApplicationSchema,
    impact: ImpactProtocol,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> GridVariant:
    """
    Routes an application to the most appropriate GridVariant using Gemini analysis.

    Args:
        application: Populated ApplicationSchema.
        impact: Populated ImpactProtocol.
        model: Gemini model identifier (default: 'gemini-2.0-flash').
        api_key: Optional Gemini API key override.
        client: Optional pre-configured genai Client.

    Returns:
        GridVariant: Selected scoring grid variant enum.
    """
    ai_client = client or get_gemini_client(api_key=api_key)

    applicant_data = {
        "business_name": application.business_info.business_name,
        "sector": application.business_info.sector,
        "ownership_structure": application.business_info.ownership_structure,
        "female_ownership_percentage": application.business_info.female_ownership_percentage,
        "total_staff": application.employment.total_staff,
        "gender_split": application.employment.gender_split.model_dump(),
        "age_split": application.employment.age_split.model_dump(),
        "project_title": impact.project_title,
        "impact_sector": impact.sector,
        "sdgs": [s.value for s in impact.sdgs],
    }

    user_prompt = f"""Determine the most fitting GridVariant for this enterprise:

APPLICANT PROFILE:
{json.dumps(applicant_data, indent=2)}

Respond with the RouterDecision JSON."""

    config = types.GenerateContentConfig(
        system_instruction=ROUTER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=RouterDecision,
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
        # Graceful fallback heuristic on failure/rate limit
        if application.business_info.female_ownership_percentage >= 50.0:
            return GridVariant.WOMEN_YOUTH_LED
        return GridVariant.GENERAL_SME

    if not raw_text:
        # Fallback heuristic if LLM response is empty
        if application.business_info.female_ownership_percentage >= 50.0:
            return GridVariant.WOMEN_YOUTH_LED
        return GridVariant.GENERAL_SME

    try:
        decision = RouterDecision.model_validate_json(raw_text)
        return decision.grid_variant
    except Exception:
        data = json.loads(raw_text)
        decision = RouterDecision.model_validate(data)
        return decision.grid_variant
