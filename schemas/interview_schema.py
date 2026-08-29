"""
Schemas for Guided Conversational Voice Intake.
Step-by-step interview definitions and per-question extraction results.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AnswerExtraction(BaseModel):
    """Extracted atomic business fact from a single interview answer."""
    model_config = ConfigDict(extra="ignore")

    field_id: str = Field(..., description="Target field identifier (e.g., 'business_info.business_name')")
    value: Optional[str] = Field(None, description="Extracted textual or numeric value; null if not mentioned")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    notes: Optional[str] = Field(None, description="Extraction reasoning, ambiguities, or unit notations")


class InterviewStep(BaseModel):
    """Definition of a single guided interview question in 3 Ethiopian languages."""
    model_config = ConfigDict(extra="ignore")

    step_id: str = Field(..., description="Step key, e.g., 'S1', 'S2'")
    field_path: str = Field(..., description="Target data path in GIZ Application schema")
    question_en: str = Field(..., description="English question text")
    question_am: str = Field(..., description="Amharic question text (verify with native speaker)")
    question_or: str = Field(..., description="Afaan Oromo question text (verify with native speaker)")
    example_answer: str = Field(..., description="Reference expected answer example")
