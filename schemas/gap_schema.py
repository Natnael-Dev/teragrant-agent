"""
Gap Analysis and Application Pack Schemas.
Defines Pydantic models for tracking missing application fields and packaging final intakes.
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict

from .application_schema import ApplicationSchema
from .impact_schema import ImpactProtocol
from .provenance_schema import FieldProvenance


class GapPriority(str, Enum):
    """Priority level for resolving missing application information."""
    HIGH = "HIGH"        # Blocks eligibility evaluation or legal compliance
    MEDIUM = "MEDIUM"    # Impedes scoring precision or impact verification
    LOW = "LOW"          # Supplementary or cosmetic details


class Gap(BaseModel):
    """
    Identified data gap during multimodal intake mapping.
    Documents precisely what field is missing, why, and who must provide it.
    """
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(
        ...,
        min_length=1,
        description="The exact schema field name or path that is missing (e.g. 'business_info.tin_number')"
    )
    reason_missing: str = Field(
        ...,
        min_length=3,
        description="Specific reason the field could not be extracted from the provided intake sources"
    )
    required_from: str = Field(
        ...,
        min_length=2,
        description="Stakeholder required to supply the missing information (e.g., 'Applicant', 'Guarantor', 'Site Visit')"
    )
    priority: GapPriority = Field(
        default=GapPriority.HIGH,
        description="Urgency priority of resolving this data gap"
    )


class ApplicationPack(BaseModel):
    """
    Complete intake package containing:
    - Normalized ApplicationSchema
    - Normalized ImpactProtocol
    - List of explicitly tracked Gaps (missing data)
    - Provenance Ledger mapping each field to its epistemic audit trail
    """
    model_config = ConfigDict(extra="forbid")

    application: Optional[ApplicationSchema] = Field(
        default=None,
        description="Populated ApplicationSchema (or None if critical base info is missing)"
    )
    impact: Optional[ImpactProtocol] = Field(
        default=None,
        description="Populated ImpactProtocol (or None if impact parameters are missing)"
    )
    gaps: List[Gap] = Field(
        default_factory=list,
        description="List of identified information gaps and missing data items"
    )
    provenance: Dict[str, FieldProvenance] = Field(
        default_factory=dict,
        description="Provenance ledger mapping field paths to epistemic status and evidence snippets"
    )

    @property
    def has_gaps(self) -> bool:
        """Returns True if there is at least one missing data gap."""
        return len(self.gaps) > 0

    @property
    def high_priority_gaps(self) -> List[Gap]:
        """Filters and returns only HIGH priority gaps."""
        return [g for g in self.gaps if g.priority == GapPriority.HIGH]

    @property
    def is_complete(self) -> bool:
        """Returns True if both application and impact schemas are present and zero gaps remain."""
        return self.application is not None and self.impact is not None and len(self.gaps) == 0
