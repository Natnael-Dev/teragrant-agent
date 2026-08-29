from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ConsentVerdict(str, Enum):
    """Verbal declaration consent response classification."""
    YES = "YES"
    NO = "NO"
    UNCLEAR = "UNCLEAR"


class ConsentStatus(str, Enum):
    """Lifecycle status of recorded consent."""
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    NOT_GIVEN = "NOT_GIVEN"


class ConsentRecord(BaseModel):
    """
    Audit record capturing verbal consent for a specific single declaration.
    Enforces strict 1-to-1 mapping (one declaration per record; never global).
    """
    model_config = ConfigDict(extra="forbid")

    declaration_id: str = Field(
        ...,
        description="Exact identifier of the single declaration (e.g. 'declaration_05_anti_bribery_corruption')"
    )
    language: str = Field(
        ...,
        description="Spoken language used for the explanation and consent response (e.g. 'Amharic', 'Oromo', 'English')"
    )
    explanation_delivered: bool = Field(
        ...,
        description="True if the plain-language explanation was read/played to the applicant"
    )
    response_transcript: str = Field(
        ...,
        description="Verbatim transcript of the applicant's spoken reply"
    )
    response_verdict: ConsentVerdict = Field(
        ...,
        description="Parsed consent verdict (YES, NO, or UNCLEAR)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp when consent was recorded"
    )
    audio_ref: Optional[str] = Field(
        default=None,
        description="Optional URI, filepath, or hash reference to the recorded audio proof"
    )
    status: ConsentStatus = Field(
        default=ConsentStatus.ACTIVE,
        description="Current status: ACTIVE, REVOKED, or NOT_GIVEN"
    )


class DeclarationExplanation(BaseModel):
    """
    Plain-language verbal explanation and consent prompt for a legal declaration.
    """
    model_config = ConfigDict(extra="forbid")

    declaration_id: str = Field(
        ...,
        description="Identifier of the declaration field (e.g. declaration_05_anti_bribery_corruption)"
    )
    original_legal_text: str = Field(
        ...,
        description="Formal legal definition and regulatory text of the declaration"
    )
    translated_simple_explanation: str = Field(
        ...,
        min_length=10,
        description="Simplified translation in the applicant's chosen language (Amharic, Afaan Oromo, English)"
    )
    target_language: str = Field(
        ...,
        description="Target spoken language (e.g. 'Amharic', 'Oromo', 'English')"
    )
    verbal_consent_question: str = Field(
        ...,
        min_length=5,
        description="Direct verbal question script asking the applicant for their explicit, recorded confirmation."
    )


class ConsentPackage(BaseModel):
    """
    Complete package of verbal declaration scripts for voice agent intake.
    """
    model_config = ConfigDict(extra="forbid")

    explanations: List[DeclarationExplanation] = Field(
        ...,
        min_length=1,
        description="List of translated and simplified declaration explanation scripts"
    )
    overall_warning: str = Field(
        default="CRITICAL CONSTRAINT: This package contains verbal explanation scripts for the voice agent only. Checkboxes MUST NEVER be auto-ticked. Consent must be explicitly and verifiably confirmed by the applicant.",
        description="Explicit mandate prohibiting automated consent checking."
    )
