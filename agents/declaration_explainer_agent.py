"""
Multilingual Declaration Explainer & Verbal Consent Agent (Applicant Path).
Translates complex legal grant covenants into clear, grassroots explanations (Amharic, Afaan Oromo, English)
and generates verbal consent reading scripts. Strictly enforces zero-automated checkbox ticking.
"""

import json
from typing import Optional, Any
from google.genai import types

from extractors.config import get_gemini_client
from schemas.application_schema import MandatoryDeclarations
from schemas.consent_schema import ConsentPackage, DeclarationExplanation
from utils.schema_sanitizer import sanitize_schema_for_gemini


# The 3 most critical legal declarations selected for grassroots verbal explanation
CRITICAL_DECLARATIONS = [
    {
        "id": "declaration_05_anti_bribery_corruption",
        "legal_text": "The applicant strictly commits to zero tolerance towards bribery, extortion, kickbacks, and corruption in all project activities and procurement.",
    },
    {
        "id": "declaration_08_child_labor_prevention",
        "legal_text": "The applicant certifies that no children under the legal minimum age are employed, and no forced labor or hazardous working conditions are utilized across operations or supply chains.",
    },
    {
        "id": "declaration_02_truthful_information",
        "legal_text": "The applicant solemnly confirms that all statements, financial figures, records, and documents submitted in this application are true, accurate, and free from deliberate misrepresentation.",
    },
]

EXPLAINER_SYSTEM_PROMPT = """You are a compassionate, trusted legal aid worker and SME advocate in Ethiopia.

Your mission is to translate and simplify the 3 most critical grant legal declarations into the applicant's preferred spoken language ({language}: Amharic, Afaan Oromo, or English).

The explanation MUST:
1. Be expressed in warm, culturally respectful, plain spoken language that a rural workshop owner or smallholder farmer with limited formal education can effortlessly understand.
2. Avoid dense legal jargon (e.g. translate 'zero tolerance towards kickbacks' into everyday concepts like 'never paying money under the table to win favors').
3. Construct a polite, direct verbal question for a voice intake agent to ask the applicant over the phone or in person to obtain their explicit, verbal consent.

=============================================================================
CRITICAL ANTI-AUTOMATION & CONSENT INTEGRITY RULE:
=============================================================================
You are generating the SCRIPT for a voice agent to read. YOU MUST NEVER TICK THE CHECKBOX. The output is only the text to be spoken. The actual checkbox can ONLY be ticked after the human applicant explicitly hears the question and gives verifiable verbal agreement.

Respond strictly in JSON matching the ConsentPackage schema."""


def generate_consent_package(
    declarations: Optional[MandatoryDeclarations] = None,
    detected_language: str = "Amharic",
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> ConsentPackage:
    """
    Generates plain-language verbal explanation scripts and consent questions in the applicant's language.

    Args:
        declarations: Optional MandatoryDeclarations instance.
        detected_language: Target spoken language ('Amharic', 'Oromo' / 'Afaan Oromo', 'English').
        model: Gemini model identifier.
        api_key: Optional API key override.
        client: Optional pre-configured genai Client.

    Returns:
        ConsentPackage: Pydantic model with 3 translated verbal explanation scripts and anti-auto-tick warning.
    """
    ai_client = client or get_gemini_client(api_key=api_key)

    system_prompt = EXPLAINER_SYSTEM_PROMPT.format(language=detected_language)

    user_payload = {
        "target_language": detected_language,
        "covenants_to_translate": CRITICAL_DECLARATIONS,
    }

    user_prompt = f"""Translate and simplify these 3 critical declarations for verbal voice explanation in {detected_language}:

DECLARATIONS:
{json.dumps(user_payload, indent=2, ensure_ascii=False)}

Respond strictly in JSON matching the ConsentPackage schema."""

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=sanitize_schema_for_gemini(ConsentPackage),
        temperature=0.0,
    )

    try:
        response = ai_client.models.generate_content(
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception:
        raw_text = ""
    if not raw_text:
        # High quality fallback scripts for offline/testing resilience
        fallback_explanations = _build_fallback_consent(detected_language)
        return ConsentPackage(
            explanations=fallback_explanations,
            overall_warning="CRITICAL CONSTRAINT: This package contains verbal explanation scripts for the voice agent only. Checkboxes MUST NEVER be auto-ticked. Consent must be explicitly and verifiably confirmed by the applicant."
        )

    try:
        consent_pkg = ConsentPackage.model_validate_json(raw_text)
    except Exception:
        data = json.loads(raw_text)
        consent_pkg = ConsentPackage.model_validate(data)

    return consent_pkg


def _build_fallback_consent(language: str) -> list[DeclarationExplanation]:
    """Generates baseline bilingual scripts when LLM response is empty."""
    is_oromo = "orom" in language.lower()
    is_amharic = "amh" in language.lower()

    if is_oromo:
        return [
            DeclarationExplanation(
                declaration_id="declaration_05_anti_bribery_corruption",
                original_legal_text=CRITICAL_DECLARATIONS[0]["legal_text"],
                translated_simple_explanation="Waliigalteen kun maallaqa gargaarsaa kanaan mattaa kennuu ykn fudhachuu akka hin dandeenye mirkaneessa.",
                target_language="Afaan Oromo",
                verbal_consent_question="Qajeelfama mattaa ittisuu kana dhageessanii irratti walii galtuu?"
            ),
            DeclarationExplanation(
                declaration_id="declaration_08_child_labor_prevention",
                original_legal_text=CRITICAL_DECLARATIONS[1]["legal_text"],
                translated_simple_explanation="Daa'imman umriin isaanii hin geenye hojjechiisuun dhorkaadha.",
                target_language="Afaan Oromo",
                verbal_consent_question="Hojii keessan keessatti daa'imman akka hin hojjenne mirkaneessituu?"
            ),
            DeclarationExplanation(
                declaration_id="declaration_02_truthful_information",
                original_legal_text=CRITICAL_DECLARATIONS[2]["legal_text"],
                translated_simple_explanation="Odeeffannoon galchitan hundi dhugaa ta'uu qaba.",
                target_language="Afaan Oromo",
                verbal_consent_question="Odeeffannoon kennitan hundi dhugaa ta'uu ni mirkaneessituu?"
            ),
        ]
    elif is_amharic:
        return [
            DeclarationExplanation(
                declaration_id="declaration_05_anti_bribery_corruption",
                original_legal_text=CRITICAL_DECLARATIONS[0]["legal_text"],
                translated_simple_explanation="ይህ ውል በስራዎ ውስጥ ጉቦ ወይም ማጭበርበር ፈጽሞ እንዳይኖር ቃል የሚገቡበት ነው።",
                target_language="Amharic",
                verbal_consent_question="በዚህ የጉቦና የሙስና መከላከያ መርህ ላይ በሙሉ ፈቃድዎ ተስማምተዋል?"
            ),
            DeclarationExplanation(
                declaration_id="declaration_08_child_labor_prevention",
                original_legal_text=CRITICAL_DECLARATIONS[1]["legal_text"],
                translated_simple_explanation="ህፃናትን ለጉልበት ስራ አለማሰራት እና ትምህርታቸውን እንዳያቋርጡ ማድረግ ግዴታ ነው።",
                target_language="Amharic",
                verbal_consent_question="በድርጅትዎ ውስጥ ምንም አይነት የህፃናት ጉልበት ብዝበዛ እንደሌለ ያረጋግጣሉ?"
            ),
            DeclarationExplanation(
                declaration_id="declaration_02_truthful_information",
                original_legal_text=CRITICAL_DECLARATIONS[2]["legal_text"],
                translated_simple_explanation="የሰጡት መረጃ በሙሉ እውነተኛና ትክክለኛ መሆኑን ማረጋገጥ ይኖርብዎታል።",
                target_language="Amharic",
                verbal_consent_question="የሰጡት መረጃ በሙሉ ትክክለኛ መሆኑን በቃልዎ ያረጋግጣሉ?"
            ),
        ]
    else:
        return [
            DeclarationExplanation(
                declaration_id="declaration_05_anti_bribery_corruption",
                original_legal_text=CRITICAL_DECLARATIONS[0]["legal_text"],
                translated_simple_explanation="This rule means you promise never to pay bribes, kickbacks, or secret fees to win contracts or grants.",
                target_language="English",
                verbal_consent_question="Do you verbally confirm and agree to follow this zero-bribery policy?"
            ),
            DeclarationExplanation(
                declaration_id="declaration_08_child_labor_prevention",
                original_legal_text=CRITICAL_DECLARATIONS[1]["legal_text"],
                translated_simple_explanation="This rule ensures that no underage children work in your workshop or facility under hazardous conditions.",
                target_language="English",
                verbal_consent_question="Do you confirm that your business strictly does not employ child labor?"
            ),
            DeclarationExplanation(
                declaration_id="declaration_02_truthful_information",
                original_legal_text=CRITICAL_DECLARATIONS[2]["legal_text"],
                translated_simple_explanation="This confirms that all figures, worker counts, and sales numbers provided are completely honest and accurate.",
                target_language="English",
                verbal_consent_question="Do you solemnly confirm that all information provided in your application is true?"
            ),
        ]
