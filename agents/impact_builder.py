"""
Impact Protocol Builder Agent.
Constructs evidence-based ImpactProtocol models with verifiable milestones,
SDG mapping, and beneficiary metrics from guided interview answers or audio transcripts.
"""

import re
import json
from typing import Dict, Any, Optional, List, Union
from google.genai import types

from schemas.interview_schema import InterviewStep
from schemas.impact_schema import ImpactProtocol, Milestone, SDGIndicator
from extractors.config import get_gemini_client, call_gemini_with_fallback


IMPACT_QUESTIONS: List[InterviewStep] = [
    InterviewStep(
        step_id="S8",
        field_path="impact.target_beneficiaries_description",
        question_en="Who benefits from your business in your local community or supply chain, and how?",
        question_am="በአካባቢዎ ማህበረሰብ ወይም የአቅርቦት ሰንሰለት ውስጥ ከስራዎ ማን ይጠቀማል፣ በምን መልኩስ?",  # verify with native speaker
        question_or="Hawaasa keessan keessatti hojii keessan irraa eenyutu fayyadama, akkamitti?",  # verify with native speaker
        example_answer="Local smallholder farmers supply raw chillies, and 12 youth workers gain steady employment.",
    ),
    InterviewStep(
        step_id="S9",
        field_path="impact.target_beneficiaries",
        question_en="Approximately how many total people or households will benefit from this grant project?",
        question_am="ከዚህ የድጋፍ ፕሮጀክት በግምት ስንት ሰዎች ወይም አባወራዎች ተጠቃሚ ይሆናሉ?",  # verify with native speaker
        question_or="Piroojektii deeggarsa kana irraa walumaagalatti namoonni yookiin maatiin meeqa ni fayyadamu?",  # verify with native speaker
        example_answer="Around 150 smallholder households and 8 full-time workers.",
    ),
    InterviewStep(
        step_id="S10",
        field_path="impact.operational_changes",
        question_en="What specific changes or improvements will this grant create in your production or services?",
        question_am="ይህ ድጋፍ በማምረት ወይም በአገልግሎት አሰጣጥዎ ላይ ምን አይነት ተጨባጭ ለውጥ ያመጣል?",  # verify with native speaker
        question_or="Deeggarsi kun oomisha yookiin tajaajila keessan irratti jijjiirama akkamii fida?",  # verify with native speaker
        example_answer="Double our processing volume from 500kg to 1,000kg daily and reduce processing loss by 40%.",
    ),
    InterviewStep(
        step_id="S11",
        field_path="impact.procurement_items",
        question_en="What specific machinery, equipment, or materials will you buy with the grant funds?",
        question_am="በተሰጠው የገንዘብ ድጋፍ ምን አይነት ማሽነሪ፣ እቃ ወይም ግብዓት ይገዛሉ?",  # verify with native speaker
        question_or="Maallaqa deeggarsaa kanaan maashinii, meeshaa yookiin galtee akkamii bitattu?",  # verify with native speaker
        example_answer="A 3-phase commercial spice pulverizer and motorized packaging sealer.",
    ),
    InterviewStep(
        step_id="S12",
        field_path="impact.verification_milestones",
        question_en="How will we know the project succeeded, and what physical proof or documentation can you provide?",
        question_am="ፕሮጀክቱ መሳካቱን በምን እናውቃለን፣ ምንስ አይነት ማስረጃ ማቅረብ ይችላሉ?",  # verify with native speaker
        question_or="Piroojektiin kun milkaa'uu isaa akkamitti beekna, ragaa akkamii dhiyeessuu dandeessu?",  # verify with native speaker
        example_answer="Purchase tax invoices, installation photos, electrical inspection report, and updated payroll sheets.",
    ),
]


def _parse_beneficiaries(val: Any) -> int:
    if isinstance(val, int) and val > 0:
        return val
    if isinstance(val, (float, str)):
        digits = re.findall(r"\d+", str(val))
        if digits:
            num = int(digits[0])
            return max(num, 1)
    return 50


def _parse_financial_target(val: Any, default: float = 500000.0) -> float:
    if isinstance(val, (int, float)) and val > 0:
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace(",", "").replace("ETB", "").replace("Birr", "").strip()
        digits = re.findall(r"\d+\.?\d*", cleaned)
        if digits:
            return float(digits[0])
    return default


def _infer_sdgs(text_corpus: str) -> List[SDGIndicator]:
    lower = text_corpus.lower()
    sdgs = []

    if any(k in lower for k in ["farm", "agri", "food", "crop", "grain", "spice", "honey", "dairy", "harvest"]):
        sdgs.append(SDGIndicator.SDG_02_ZERO_HUNGER)
    if any(k in lower for k in ["woman", "women", "female", "girl", "mother"]):
        sdgs.append(SDGIndicator.SDG_05_GENDER_EQUALITY)
    if any(k in lower for k in ["solar", "clean energy", "biogas", "hydro", "electric"]):
        sdgs.append(SDGIndicator.SDG_07_AFFORDABLE_ENERGY)
    if any(k in lower for k in ["job", "worker", "employee", "youth", "employment", "wage"]):
        sdgs.append(SDGIndicator.SDG_08_DECENT_WORK)
    if any(k in lower for k in ["machine", "manufacture", "tech", "solar", "hardware", "process", "factory"]):
        sdgs.append(SDGIndicator.SDG_09_INDUSTRY_INNOVATION)
    if any(k in lower for k in ["waste", "recycle", "organic", "circular"]):
        sdgs.append(SDGIndicator.SDG_12_RESPONSIBLE_CONSUMPTION)

    # Always ensure at least SDG 8 and 9 if empty
    if not sdgs:
        sdgs = [SDGIndicator.SDG_08_DECENT_WORK, SDGIndicator.SDG_09_INDUSTRY_INNOVATION]
    return list(dict.fromkeys(sdgs))


def build_impact_protocol(
    answers_dict: Dict[str, Any],
    audio_facts: Optional[Dict[str, Any]] = None,
) -> ImpactProtocol:
    """
    Constructs a verified ImpactProtocol model from interview answers and audio facts.
    """
    facts = audio_facts or {}
    corpus = " ".join([str(v) for v in answers_dict.values()] + [str(v) for v in facts.values()])

    b_name = answers_dict.get("business_name") or facts.get("business_name") or "SME Enterprise"
    procurement = answers_dict.get("impact.procurement_items") or facts.get("product_type") or "Production Equipment"
    project_title = f"{b_name} — {procurement} Modernization & Value Addition Project"

    location = answers_dict.get("location") or facts.get("location") or "Addis Ababa / Regional Hub"
    raw_beneficiaries = answers_dict.get("impact.target_beneficiaries") or answers_dict.get("target_beneficiaries") or 100
    target_beneficiaries = _parse_beneficiaries(raw_beneficiaries)

    fin_val = answers_dict.get("requested_etb") or facts.get("financial_figures")
    etb_target = _parse_financial_target(fin_val, default=500000.0)

    sector = facts.get("product_type") or answers_dict.get("sector") or "Agro-Processing & Light Manufacturing"
    sdgs = _infer_sdgs(corpus)

    m1_evidence = answers_dict.get("impact.verification_milestones") or "Official commercial invoice, equipment serial numbers, and delivery receipt."
    milestones = [
        Milestone(
            milestone_id="M1",
            title=f"Procurement and Delivery of {procurement}",
            description=f"Acquisition, delivery, and site inspection of specified equipment.",
            target_month=2,
            verification_evidence=m1_evidence,
        ),
        Milestone(
            milestone_id="M2",
            title="Installation, Electrical Commissioning, and Staff Safety Training",
            description="Complete installation of equipment, test runs, and operator safety onboarding.",
            target_month=4,
            verification_evidence="Signed commissioning acceptance report, on-site photos, and staff attendance register.",
        ),
        Milestone(
            milestone_id="M3",
            title="Operational Scaling, Output Verification, and Target Job Creation",
            description="Achieve verified production capacity target and onboard new workers.",
            target_month=6,
            verification_evidence="Updated monthly production output logs, sales receipts, and formal employee payroll records.",
        ),
    ]

    return ImpactProtocol(
        project_title=project_title,
        location=location,
        target_beneficiaries=target_beneficiaries,
        etb_financial_target=etb_target,
        sector=sector,
        sdgs=sdgs,
        milestones=milestones,
    )
