"""
TeraGrant Impact Protocol Schema
Defines Pydantic models for grant impact projections, SDG alignment, and verifiable milestones.
"""

from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SDGIndicator(str, Enum):
    """The 17 United Nations Sustainable Development Goals (SDGs)."""
    SDG_01_NO_POVERTY = "SDG 1: No Poverty"
    SDG_02_ZERO_HUNGER = "SDG 2: Zero Hunger"
    SDG_03_GOOD_HEALTH = "SDG 3: Good Health and Well-being"
    SDG_04_QUALITY_EDUCATION = "SDG 4: Quality Education"
    SDG_05_GENDER_EQUALITY = "SDG 5: Gender Equality"
    SDG_06_CLEAN_WATER = "SDG 6: Clean Water and Sanitation"
    SDG_07_AFFORDABLE_ENERGY = "SDG 7: Affordable and Clean Energy"
    SDG_08_DECENT_WORK = "SDG 8: Decent Work and Economic Growth"
    SDG_09_INDUSTRY_INNOVATION = "SDG 9: Industry, Innovation, and Infrastructure"
    SDG_10_REDUCED_INEQUALITIES = "SDG 10: Reduced Inequalities"
    SDG_11_SUSTAINABLE_CITIES = "SDG 11: Sustainable Cities and Communities"
    SDG_12_RESPONSIBLE_CONSUMPTION = "SDG 12: Responsible Consumption and Production"
    SDG_13_CLIMATE_ACTION = "SDG 13: Climate Action"
    SDG_14_LIFE_BELOW_WATER = "SDG 14: Life Below Water"
    SDG_15_LIFE_ON_LAND = "SDG 15: Life on Land"
    SDG_16_PEACE_JUSTICE = "SDG 16: Peace, Justice, and Strong Institutions"
    SDG_17_PARTNERSHIPS = "SDG 17: Partnerships for the Goals"


class Milestone(BaseModel):
    """Verifiable project milestone with audit proof requirement."""
    model_config = ConfigDict(extra="forbid")

    milestone_id: Optional[str] = Field(None, description="Unique milestone reference (e.g. M1, M2)")
    title: str = Field(..., min_length=3, description="Summary of the deliverable/milestone")
    description: Optional[str] = Field(None, description="Detailed operational output")
    target_month: Optional[int] = Field(None, ge=1, le=60, description="Project timeline month for delivery")
    verification_evidence: str = Field(
        ...,
        min_length=3,
        description="Specific verifiable proof (e.g., machinery receipt, training sign-in sheet, test certificate)"
    )


class ImpactProtocol(BaseModel):
    """
    Impact Protocol Schema:
    - Project Title, Location, Target Beneficiaries, ETB Financial Target, Sector
    - Selected SDGs (from the 17 checkboxes)
    - Verifiable milestone list
    """
    model_config = ConfigDict(extra="forbid")

    project_title: str = Field(..., min_length=3, max_length=255, description="Grant project title")
    location: str = Field(..., min_length=2, description="Target implementation site/region/woreda")
    target_beneficiaries: int = Field(..., ge=1, description="Direct and indirect estimated beneficiaries")
    etb_financial_target: float = Field(..., ge=0.0, description="Total budget/funding target requested in ETB")
    sector: str = Field(..., min_length=2, description="Project thematic sector")
    sdgs: List[SDGIndicator] = Field(
        ...,
        min_length=1,
        description="At least 1 selected SDG indicator from the 17 official SDGs"
    )
    milestones: List[Union[Milestone, str]] = Field(
        ...,
        min_length=1,
        description="List of verifiable milestones (strings or structured Milestone objects)"
    )

    @field_validator("sdgs")
    @classmethod
    def validate_unique_sdgs(cls, sdg_list: List[SDGIndicator]) -> List[SDGIndicator]:
        if not sdg_list:
            raise ValueError("At least one SDG must be selected.")
        # Ensure unique items preserving order
        seen = set()
        unique_sdgs = []
        for s in sdg_list:
            if s not in seen:
                seen.add(s)
                unique_sdgs.append(s)
        return unique_sdgs

    @field_validator("milestones")
    @classmethod
    def validate_milestones_non_empty(cls, milestones: List[Union[Milestone, str]]) -> List[Union[Milestone, str]]:
        if not milestones:
            raise ValueError("At least one verifiable milestone is required.")
        for m in milestones:
            if isinstance(m, str) and len(m.strip()) < 3:
                raise ValueError("Milestone description must be at least 3 characters.")
        return milestones
