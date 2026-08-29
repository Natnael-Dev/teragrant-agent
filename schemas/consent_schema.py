"""
Multilingual Consent & Declaration Explanation Schemas (Applicant Path).
Ensures explicit, informed consent with zero automated checkbox ticking.
"""

from typing import List
from pydantic import BaseModel, Field, ConfigDict


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
