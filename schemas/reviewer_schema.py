"""
Reviewer Path Schemas: Contradictions, Batch Ranking, and Shortlist Models.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field, ConfigDict

from .scoring_schema import GridVariant


class ContradictionSeverity(str, Enum):
    """Severity classification of identified discrepancies."""
    CRITICAL = "CRITICAL"    # Disqualifying or mathematical impossibility (e.g. headcount sum mismatch)
    WARNING = "WARNING"      # Plausible temporal or narrative discrepancy requiring site-visit clarification


class Contradiction(BaseModel):
    """
    Structured record of a detected discrepancy between documents, numbers, or statements.
    """
    model_config = ConfigDict(extra="forbid")

    claim_a: str = Field(..., min_length=2, description="First extracted data point, document fact, or claim")
    claim_b: str = Field(..., min_length=2, description="Contradicting statement, record, or calculated total")
    severity: ContradictionSeverity = Field(..., description="Severity level of the discrepancy")
    explanation: str = Field(..., min_length=10, description="Clear description of the contradiction and its implications")


class RankedCompany(BaseModel):
    """
    Individual company entry within a ranked batch evaluation.
    """
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1, description="Numerical position in the batch ranking (1 = top candidate)")
    business_name: str = Field(..., min_length=2, description="Enterprise legal or trade name")
    total_score: int = Field(..., ge=0, le=100, description="Total score awarded out of 100")
    grid_variant: GridVariant = Field(..., description="Applied evaluation grid variant")
    justification: str = Field(
        ...,
        min_length=20,
        description="One paragraph executive justification for the awarded rank and funding priority."
    )
    site_visit_questions: List[str] = Field(
        default_factory=list,
        description="List of 3 targeted inspection questions for field verification."
    )
    contradictions: List[Contradiction] = Field(
        default_factory=list,
        description="Any flagged contradictions or data anomalies for this enterprise."
    )


class RankedShortlist(BaseModel):
    """
    Complete ranked portfolio output for a batch of SME grant applications.
    """
    model_config = ConfigDict(extra="forbid")

    companies: List[RankedCompany] = Field(..., description="Ordered list of ranked candidates (descending by score)")
    batch_summary: str = Field(
        ...,
        min_length=20,
        description="Executive summary of the batch evaluation, cutoff recommendations, and portfolio trends."
    )
