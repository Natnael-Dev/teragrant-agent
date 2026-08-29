"""
Provenance Ledger Schema.
Defines epistemic status and audit metadata for every extracted application field.
"""

from enum import Enum
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class FieldStatus(str, Enum):
    """Epistemic status of an extracted field in the grant application."""
    DOCUMENT_VERIFIED = "DOCUMENT_VERIFIED"    # Extracted from official legible document (OCR)
    APPLICANT_STATED = "APPLICANT_STATED"      # Stated verbally in audio note or voice interview
    AI_INFERRED = "AI_INFERRED"                # Derived or inferred by AI reasoning
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"  # Ambiguous or partial fact requiring applicant check
    MISSING = "MISSING"                        # Not provided or completely unreadable
    CONTRADICTED = "CONTRADICTED"              # Conflicting data between distinct sources


class FieldProvenance(BaseModel):
    """
    Detailed provenance record tracking the source, confidence, and audit trail of a field.
    """
    model_config = ConfigDict(extra="forbid")

    field_path: str = Field(
        ...,
        description="Path of the schema field (e.g. 'business_info.company_name', 'employment.total_staff')"
    )
    value: Optional[Any] = Field(
        default=None,
        description="The extracted or normalized value of the field"
    )
    status: FieldStatus = Field(
        ...,
        description="Epistemic verification status of the field"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level in the extraction (0.0 = low/unverified, 1.0 = high/verified)"
    )
    source_type: str = Field(
        ...,
        description="Source category: 'voice', 'license', 'workshop', 'interview', 'derived', or 'none'"
    )
    evidence_snippet: str = Field(
        ...,
        description="Verbatim text quote from audio transcript or OCR text from document"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of extraction"
    )
    cross_check: Optional[str] = Field(
        default=None,
        description="Cross-verification or corroborating observation from other multimodal sources"
    )
