"""
Scoring and Evaluation Schemas for TeraGrant Reviewer Path.
Defines Pydantic models for the ALPHAX Internal Prototype Scoring Grid (v1.0-prototype),
Eligibility Gate, and Grid Routing variants.

NOTE: The current 9-criterion, 100-point scoring matrix is the ALPHAX Internal Prototype
Grid (v1.0-prototype), an engineering heuristic developed for the hackathon prototype.
It is NOT the official SEQUA/GIZ evaluation matrix. Future versions will support pluggable
official donor rubrics.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict

# Scoring Framework Metadata Constants
GRID_NAME: str = "ALPHAX Internal Prototype Scoring Grid"
GRID_VERSION: str = "v1.0-prototype"


class ExclusionFactor(str, Enum):
    """Instant-kill exclusion factors for grant applicants."""
    BANKRUPTCY_INSOLVENCY = "BANKRUPTCY_INSOLVENCY"
    SANCTIONS_CRIMINAL = "SANCTIONS_CRIMINAL"
    PROHIBITED_ACTIVITIES = "PROHIBITED_ACTIVITIES"


class EligibilityGate(BaseModel):
    """
    Deterministic eligibility assessment output.
    An applicant is eligible ONLY if all 15 declarations are confirmed (True)
    AND 0 exclusion factors are triggered.
    """
    model_config = ConfigDict(extra="forbid")

    is_eligible: bool = Field(
        ...,
        description="True ONLY if all 15 declarations are True AND 0 exclusion factors are True."
    )
    failed_declarations: List[str] = Field(
        default_factory=list,
        description="Names of the specific declarations that were False or unconfirmed."
    )
    triggered_exclusions: List[ExclusionFactor] = Field(
        default_factory=list,
        description="List of instant-kill exclusion criteria that were triggered."
    )
    gate_reasoning: str = Field(
        ...,
        min_length=5,
        description="One clear sentence explaining the deterministic eligibility verdict."
    )


class GridVariant(str, Enum):
    """The 3 targeted evaluation scoring grid variants."""
    GENERAL_SME = "GENERAL_SME"                # Standard balanced weights
    WOMEN_YOUTH_LED = "WOMEN_YOUTH_LED"        # Double weight on Gender/Youth Inclusion (30 pts)
    INNOVATION_TECH = "INNOVATION_TECH"        # Double weight on Innovation & Unique Features (30 pts)


class CriterionName(str, Enum):
    """The 9 standardized criteria in the TeraGrant 100-point evaluation matrix."""
    JOB_CREATION = "JOB_CREATION"                            # Max 20 pts
    GENDER_YOUTH_INCLUSION = "GENDER_YOUTH_INCLUSION"        # Max 15 pts standard, 30 pts in WOMEN_YOUTH_LED
    INNOVATION_UNIQUE_FEATURE = "INNOVATION_UNIQUE_FEATURE"  # Max 15 pts standard, 30 pts in INNOVATION_TECH
    FINANCIAL_VIABILITY = "FINANCIAL_VIABILITY"              # Max 15 pts standard, 10 pts in variants
    LOCAL_SUPPLY_CHAIN = "LOCAL_SUPPLY_CHAIN"                # Max 10 pts
    SDG_ENVIRONMENTAL_IMPACT = "SDG_ENVIRONMENTAL_IMPACT"    # Max 10 pts
    MANAGEMENT_ORGANOGRAM = "MANAGEMENT_ORGANOGRAM"          # Max 5 pts
    COMMUNITY_IMPACT = "COMMUNITY_IMPACT"                    # Max 5 pts
    SCALABILITY = "SCALABILITY"                              # Max 5 pts


class CriterionScore(BaseModel):
    """Individual criterion score with evidence-based justification."""
    model_config = ConfigDict(extra="forbid")

    criterion: CriterionName = Field(..., description="The specific evaluation criterion")
    max_points: int = Field(..., ge=1, le=30, description="Maximum possible points allocated for this criterion")
    awarded_points: int = Field(..., ge=0, description="Points awarded by the evaluator (must be <= max_points)")
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Justification sentence(s) citing specific data or penalizing missing Gaps."
    )

    @model_validator(mode="after")
    def validate_awarded_within_max(self) -> "CriterionScore":
        if self.awarded_points > self.max_points:
            raise ValueError(
                f"awarded_points ({self.awarded_points}) cannot exceed max_points ({self.max_points}) "
                f"for criterion {self.criterion}"
            )
        return self


class ScoringResult(BaseModel):
    """
    Complete 100-Point Scoring Evaluation Result:
    - Selected Grid Variant
    - Total Score (<= 100)
    - List of 9 individual Criterion Scores
    - Attached Eligibility Gate assessment
    - Comprehensive Reviewer Summary
    """
    model_config = ConfigDict(extra="forbid")

    grid_variant: GridVariant = Field(..., description="Applied scoring grid variant")
    total_score: int = Field(..., ge=0, le=100, description="Sum of awarded points across all 9 criteria (max 100)")
    criteria_scores: List[CriterionScore] = Field(..., description="Scores for exactly 9 standardized criteria")
    eligibility_gate: EligibilityGate = Field(..., description="Deterministic eligibility verification")
    reviewer_summary: str = Field(
        ...,
        min_length=20,
        description="One paragraph executive summary of enterprise strengths, weaknesses, and site-visit inquiries."
    )

    @field_validator("criteria_scores")
    @classmethod
    def validate_criteria_scores_count(cls, scores: List[CriterionScore]) -> List[CriterionScore]:
        if len(scores) != 9:
            raise ValueError(f"criteria_scores must contain exactly 9 items, got {len(scores)}")
        unique_criteria = {s.criterion for s in scores}
        if len(unique_criteria) != 9:
            raise ValueError(f"criteria_scores must contain 9 distinct criteria, found duplicates.")
        return scores

    @model_validator(mode="after")
    def validate_total_score_sum(self) -> "ScoringResult":
        computed_sum = sum(c.awarded_points for c in self.criteria_scores)
        if self.total_score != computed_sum:
            # Reconcile if minor off-by-one or validate consistency
            self.total_score = computed_sum
        if self.total_score > 100:
            raise ValueError(f"total_score ({self.total_score}) cannot exceed 100 points.")
        return self
