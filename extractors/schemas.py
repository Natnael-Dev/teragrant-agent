"""
Extraction schemas for raw Vision OCR and Audio Transcription outputs.
These are intermediate parsing models before normalization into the master application schema.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LicenseExtraction(BaseModel):
    """
    Structured extraction from Ethiopian/regional trade licenses and certificates.
    Fields return None if unreadable or not visible. Hallucinations are strictly forbidden.
    """
    model_config = ConfigDict(extra="ignore")

    business_name: Optional[str] = Field(
        default=None,
        description="Official registered business or enterprise name as printed on the license"
    )
    tin_number: Optional[str] = Field(
        default=None,
        description="Taxpayer Identification Number (TIN) (typically 10-digit number in Ethiopia)"
    )
    registration_date: Optional[str] = Field(
        default=None,
        description="Date of registration/issuance in Ethiopian (E.C.) or Gregorian (G.C.) calendar"
    )
    owner_name: Optional[str] = Field(
        default=None,
        description="Full name of the principal business owner, manager, or general manager"
    )
    location: Optional[str] = Field(
        default=None,
        description="Registered address, city, sub-city, zone, or woreda/region"
    )
    is_legible: bool = Field(
        default=True,
        description="False if the document is excessively blurry, obscured, corrupted, or unreadable"
    )
    extraction_notes: Optional[str] = Field(
        default=None,
        description="Any observations regarding document legibility, missing stamps, or visual issues"
    )


class AudioTranscriptExtraction(BaseModel):
    """
    Structured extraction from voice notes (Amharic, Afaan Oromo, English, etc.).
    Extracts raw transcript and verified business facts mentioned by the applicant.
    """
    model_config = ConfigDict(extra="ignore")

    transcript: str = Field(
        ...,
        description="Verbatim or near-verbatim transcription of the voice note"
    )
    detected_language: str = Field(
        ...,
        description="Primary language spoken (e.g., 'Amharic', 'Afaan Oromo', 'English', 'Tigrinya')"
    )
    business_name: Optional[str] = Field(
        default=None,
        description="Business name explicitly stated by the speaker, or None if omitted"
    )
    employee_count: Optional[int] = Field(
        default=None,
        description="Total employee or worker headcount mentioned by speaker"
    )
    product_type: Optional[str] = Field(
        default=None,
        description="Primary product, crop, manufacture item, or service described"
    )
    location: Optional[str] = Field(
        default=None,
        description="Town, region, woreda, or operating area stated by the speaker"
    )
    financial_figures: List[str] = Field(
        default_factory=list,
        description="Any sales, revenue, cost, or funding numbers mentioned (e.g. '500,000 Birr')"
    )
    impact_summary: Optional[str] = Field(
        default=None,
        description="Concise summary of the business operations, challenges, and grant objectives"
    )
