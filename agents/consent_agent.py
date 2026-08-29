"""
Consent Audit Agent.
Handles per-declaration verbal consent recording, multilingual affirmation parsing,
and consent lifecycle management (ACTIVE/REVOKED/NOT_GIVEN).
Strictly prevents automated ticking and ensures one YES never marks other declarations.
"""

from typing import Optional, List
from datetime import datetime, timezone

from schemas.application_schema import MandatoryDeclarations
from schemas.consent_schema import (
    ConsentRecord,
    ConsentVerdict,
    ConsentStatus,
)


AFFIRMATIVE_TERMS = {
    # English
    "yes", "i agree", "agreed", "i accept", "confirm", "confirmed", "sure", "absolutely", "i do",
    # Amharic
    "አዎ", "እስማማለሁ", "እሺ", "ትክክል", "እቀበላለሁ", "እስማማለው", "አረጋግጣለሁ",
    # Afaan Oromo
    "eeyyee", "nan walii gala", "tole", "sirriidha", "eeyyee nan fudhadha",
}

NEGATIVE_TERMS = {
    # English
    "no", "i disagree", "i do not agree", "refuse", "i decline", "no way",
    # Amharic
    "አይ", "አልስማማም", "አይሆንም", "አልቀበልም", "አይደለም",
    # Afaan Oromo
    "lakki", "walii hin galu", "hin fudhadhu",
}


def evaluate_verdict(response_transcript: str) -> ConsentVerdict:
    """
    Deterministically parses spoken response into YES, NO, or UNCLEAR across English, Amharic, and Afaan Oromo.
    """
    clean = response_transcript.strip().lower()
    if not clean:
        return ConsentVerdict.UNCLEAR

    for aff in AFFIRMATIVE_TERMS:
        if aff in clean:
            return ConsentVerdict.YES

    for neg in NEGATIVE_TERMS:
        if neg in clean:
            return ConsentVerdict.NO

    return ConsentVerdict.UNCLEAR


def record_consent(
    declaration_id: str,
    language: str,
    explanation_delivered: bool,
    response_transcript: str,
    audio_ref: Optional[str] = None,
) -> ConsentRecord:
    """
    Records an explicit verbal consent audit record for a single, isolated declaration.
    """
    verdict = evaluate_verdict(response_transcript) if explanation_delivered else ConsentVerdict.UNCLEAR
    status = ConsentStatus.ACTIVE if verdict == ConsentVerdict.YES else (
        ConsentStatus.NOT_GIVEN if verdict == ConsentVerdict.UNCLEAR else ConsentStatus.NOT_GIVEN
    )

    return ConsentRecord(
        declaration_id=declaration_id,
        language=language,
        explanation_delivered=explanation_delivered,
        response_transcript=response_transcript,
        response_verdict=verdict,
        timestamp=datetime.now(timezone.utc).isoformat(),
        audio_ref=audio_ref,
        status=status,
    )


def revoke_consent(record: ConsentRecord, reason: str = "") -> ConsentRecord:
    """
    Revokes previously granted consent for a declaration.
    """
    return record.model_copy(
        update={
            "status": ConsentStatus.REVOKED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def sync_declarations_from_consent_records(
    records: List[ConsentRecord],
    declarations: Optional[MandatoryDeclarations] = None,
) -> MandatoryDeclarations:
    """
    Safely projects verified consent records onto MandatoryDeclarations.
    A declaration is set to True ONLY if it has an individual ACTIVE YES record.
    All other declarations remain unchanged (or False by default).
    """
    decl = declarations or MandatoryDeclarations()
    decl_dict = decl.model_dump()

    for rec in records:
        if rec.status == ConsentStatus.ACTIVE and rec.response_verdict == ConsentVerdict.YES:
            if rec.declaration_id in decl_dict:
                decl_dict[rec.declaration_id] = True
        elif rec.status == ConsentStatus.REVOKED:
            if rec.declaration_id in decl_dict:
                decl_dict[rec.declaration_id] = False

    return MandatoryDeclarations.model_validate(decl_dict)
