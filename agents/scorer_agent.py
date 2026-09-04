"""
100-Point Evaluation Scorer Agent (Reviewer Path).
Evaluates an ApplicationPack across 9 weighted criteria under the ALPHAX Internal Prototype
Scoring Grid (v1.0-prototype) track.

Under the Scoring Decision Contract:
"CODE OWNS THE NUMBERS. AI OWNS THE SENTENCES."
- All numerical scoring is performed deterministically by `agents/rule_engine.py`.
- Gemini LLM is restricted exclusively to generating qualitative reviewer narratives.
- Zero numerical discretion or point assignment is delegated to the AI model.

NOTE: The current 9-criterion, 100-point scoring matrix is the ALPHAX Internal Prototype
Grid (v1.0-prototype), an engineering heuristic developed for the hackathon prototype.
It is NOT the official SEQUA/GIZ evaluation matrix.
"""

import json
from typing import Optional, Any, Dict, List

from google.genai import types

from extractors.config import get_gemini_client, call_gemini_with_fallback
from schemas.gap_schema import ApplicationPack
from schemas.provenance_schema import FieldStatus, FieldProvenance
from schemas.scoring_schema import (
    GRID_NAME,
    GRID_VERSION,
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from agents.rule_engine import (
    evaluate_criterion,
    calculate_total_score,
)
from agents.eligibility_agent import run_eligibility_gate


REVIEWER_SUMMARY_SYSTEM_PROMPT = """You are the Lead Investment Committee Evaluator and Senior Technical Reviewer for the TeraGrant SME Grant Program.

The numerical evaluation has been completed by the deterministic rule engine.
Your task is to write ONLY the executive reviewer summary (a 2-3 sentence explanation of the score, enterprise strengths, risks, and site-visit recommendation).

You MUST NOT generate or modify any numerical points or criteria scores. Code owns the numbers; AI owns the sentences.

Respond strictly in JSON matching this schema:
{
  "reviewer_summary": "2-3 sentence executive summary explaining the enterprise evaluation, strengths, risks, and site-visit recommendation."
}"""

CRITERION_GAP_KEYWORDS: Dict[CriterionName, List[str]] = {
    CriterionName.JOB_CREATION: ["staff", "employee", "employment", "headcount", "worker"],
    CriterionName.GENDER_YOUTH_INCLUSION: ["gender", "female", "women", "youth", "demographic"],
    CriterionName.INNOVATION_UNIQUE_FEATURE: ["innovation", "machinery", "equipment", "tech", "patent", "milestone"],
    CriterionName.FINANCIAL_VIABILITY: ["financial", "sales", "revenue", "turnover", "tin", "audit", "profit"],
    CriterionName.LOCAL_SUPPLY_CHAIN: ["supply", "supplier", "sourcing", "domestic", "raw_material"],
    CriterionName.SDG_ENVIRONMENTAL_IMPACT: ["sdg", "environmental", "climate", "waste", "carbon", "sustainability"],
    CriterionName.MANAGEMENT_ORGANOGRAM: ["organogram", "license", "registration", "management", "governance", "structure"],
    CriterionName.COMMUNITY_IMPACT: ["beneficiar", "community", "social_impact", "clinic", "school"],
    CriterionName.SCALABILITY: ["scalab", "expansion", "growth", "market"],
}


def extract_facts_from_pack(pack: Optional[ApplicationPack]) -> dict:
    """
    Extracts normalized factual metrics from ApplicationPack for deterministic rule evaluation.
    """
    facts: Dict[str, Any] = {}
    if not pack:
        return facts

    app = pack.application
    if app:
        if app.business_info:
            b = app.business_info
            facts["business_name"] = b.business_name
            facts["tin_number"] = b.tin_number
            facts["location"] = b.location
            facts["sector"] = b.sector
            facts["years_in_operation"] = b.years_in_operation
            facts["business_info.years_in_operation"] = b.years_in_operation
            facts["ownership_structure"] = b.ownership_structure
            facts["female_ownership_percentage"] = b.female_ownership_percentage
            facts["business_info.female_ownership_percentage"] = b.female_ownership_percentage

        if app.employment:
            e = app.employment
            facts["total_staff"] = e.total_staff
            facts["employment.total_staff"] = e.total_staff
            facts["employee_count"] = e.total_staff
            if e.gender_split:
                facts["female_staff"] = e.gender_split.female
                facts["employment.gender_split.female"] = e.gender_split.female
                facts["male_staff"] = e.gender_split.male
            if e.age_split:
                facts["youth_staff"] = e.age_split.youth_18_29
                facts["employment.age_split.youth_18_29"] = e.age_split.youth_18_29

        if app.financials:
            f = app.financials
            if f.sales_history:
                facts["financials.sales_history"] = f.sales_history
                rev_values = [
                    s.revenue_etb for s in f.sales_history
                    if hasattr(s, "revenue_etb") and s.revenue_etb is not None
                ]
                if rev_values:
                    facts["revenue_etb"] = max(rev_values)
                    facts["annual_sales"] = max(rev_values)
            if f.machinery_list:
                facts["machinery_list"] = f.machinery_list
                facts["visible_machinery"] = f.machinery_list
                facts["machinery_count"] = len(f.machinery_list)

        if app.organogram:
            facts["organogram"] = app.organogram
            facts["organogram_count"] = len(app.organogram)

    impact = pack.impact
    if impact:
        facts["project_title"] = impact.project_title
        facts["impact.project_title"] = impact.project_title
        facts["impact.location"] = impact.location
        facts["target_beneficiaries"] = impact.target_beneficiaries
        facts["impact.target_beneficiaries"] = impact.target_beneficiaries
        facts["etb_financial_target"] = impact.etb_financial_target
        if impact.sdgs:
            facts["sdgs"] = [s.value if hasattr(s, "value") else str(s) for s in impact.sdgs]
            facts["sdg_count"] = len(impact.sdgs)
        if impact.milestones:
            facts["milestones"] = impact.milestones
            m_text = " ".join([
                m if isinstance(m, str) else getattr(m, "title", str(m))
                for m in impact.milestones
            ]).lower()
            if any(term in m_text for term in ("solar", "tech", "modular", "patent", "assembly", "inverter")):
                facts["tech_innovation"] = True
                facts["has_proprietary_tech"] = True

    return facts


def extract_provenance_from_pack(pack: Optional[ApplicationPack], facts: dict) -> dict:
    """
    Extracts the provenance ledger from the pack.
    If the pack was submitted with self-reported application facts but without an explicit
    OCR verification ledger, defaults populated fields to APPLICANT_STATED (capped at 65%).
    If pack has no facts or is missing, returns empty dictionary (treated as MISSING).
    """
    if not pack:
        return {}

    prov = dict(pack.provenance or {})
    if not prov and (pack.application or pack.impact):
        # Default self-reported facts to APPLICANT_STATED
        for key in facts.keys():
            prov[key] = FieldStatus.APPLICANT_STATED

    return prov


def score_application(
    pack: ApplicationPack,
    variant: GridVariant,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> ScoringResult:
    """
    Evaluates and scores an ApplicationPack across 9 weighted criteria under the ALPHAX Internal Prototype Grid (v1.0-prototype).
    
    Architecture (Scoring Decision Contract):
    1. Pure Python code owns all numerical points via `agents/rule_engine.py`.
    2. Epistemic provenance caps and gap deductions are applied deterministically.
    3. Gemini LLM is invoked strictly to author the qualitative `reviewer_summary`.
    """
    # 1. Deterministic Eligibility Gate
    eligibility_result = run_eligibility_gate(pack.application if pack else None)

    # 2. Extract facts and provenance from ApplicationPack
    facts = extract_facts_from_pack(pack)
    provenance = extract_provenance_from_pack(pack, facts)

    # 3. Deterministic Criterion Evaluation (Pure Python Rule Engine)
    criteria_scores: List[CriterionScore] = []
    for criterion in CriterionName:
        cs = evaluate_criterion(
            criterion_name=criterion,
            variant=variant,
            facts=facts,
            provenance=provenance,
        )

        # Gap penalty: Annotate missing evidence identified in the pack's gap ledger
        if pack and pack.gaps:
            relevant_gaps = [
                g for g in pack.gaps
                if any(kw in g.field_name.lower() for kw in CRITERION_GAP_KEYWORDS.get(criterion, []))
            ]
            if relevant_gaps:
                gap_notes = " ".join([
                    f"Score penalized due to missing data: {g.field_name}."
                    for g in relevant_gaps
                ])
                updated_reasoning = f"{cs.reasoning} {gap_notes}".strip()
                cs = CriterionScore(
                    criterion=cs.criterion,
                    max_points=cs.max_points,
                    awarded_points=cs.awarded_points,
                    reasoning=updated_reasoning,
                )

        criteria_scores.append(cs)

    # 4. Deterministic Total Score Calculation
    total_score = calculate_total_score(criteria_scores)

    # 5. Narrative Reviewer Summary Generation (LLM owns ONLY sentences)
    ai_client = client or get_gemini_client(api_key=api_key)

    summary_payload = {
        "grid_variant": variant.value,
        "total_score": total_score,
        "eligibility_passed": eligibility_result.is_eligible,
        "eligibility_reasoning": eligibility_result.gate_reasoning,
        "deterministic_criteria_scores": [
            {
                "criterion": cs.criterion.value,
                "awarded_points": cs.awarded_points,
                "max_points": cs.max_points,
                "reasoning": cs.reasoning,
            }
            for cs in criteria_scores
        ],
        "identified_gaps": [
            {"field": g.field_name, "priority": g.priority.value, "reason": g.reason_missing}
            for g in (pack.gaps if pack else [])
        ],
    }

    user_prompt = f"""Generate a concise, 2-3 sentence executive reviewer summary for this evaluated application:

DETERMINISTIC EVALUATION RESULTS:
{json.dumps(summary_payload, indent=2, ensure_ascii=False)}

Respond strictly in JSON with the 'reviewer_summary' string."""

    config = types.GenerateContentConfig(
        system_instruction=REVIEWER_SUMMARY_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.0,
    )

    reviewer_summary = "Scoring completed; narrative summary unavailable."
    try:
        response, _ = call_gemini_with_fallback(
            client=ai_client,
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
        if raw_text:
            try:
                data = json.loads(raw_text)
                if isinstance(data, dict) and data.get("reviewer_summary"):
                    reviewer_summary = str(data["reviewer_summary"]).strip()
                elif isinstance(data, str) and len(data.strip()) >= 20:
                    reviewer_summary = data.strip()
            except json.JSONDecodeError:
                if len(raw_text.strip()) >= 20:
                    reviewer_summary = raw_text.strip()
    except Exception:
        # LLM fallback still produces a valid ScoringResult with deterministic scores
        reviewer_summary = "Scoring completed; narrative summary unavailable."

    if len(reviewer_summary) < 20:
        reviewer_summary = "Scoring completed; narrative summary unavailable."

    return ScoringResult(
        grid_variant=variant,
        total_score=total_score,
        criteria_scores=criteria_scores,
        eligibility_gate=eligibility_result,
        reviewer_summary=reviewer_summary,
    )


# =============================================================================
# TRANSPARENCY ENGINES (DETERMINISTIC + EVIDENCE-BASED)
# =============================================================================

def compare_grid_variants(
    application: Optional[Any],
    impact: Optional[Any],
    pack: Optional[ApplicationPack] = None,
    client: Optional[Any] = None,
) -> dict:
    """
    Evaluates the application under all 3 grid variants and returns their scores
    alongside the deterministic routing recommendation.
    """
    from .router_agent import route_to_grid_variant

    if pack is None:
        pack = ApplicationPack(application=application, impact=impact, gaps=[])

    recommended_variant = route_to_grid_variant(pack.application, pack.impact)

    variant_scores = {}
    for var in [GridVariant.GENERAL_SME, GridVariant.WOMEN_YOUTH_LED, GridVariant.INNOVATION_TECH]:
        res = score_application(pack=pack, variant=var, client=client)
        variant_scores[var.value] = res.total_score

    routing_reason = (
        f"Automated track recommendation: {recommended_variant.value} based on applicant demographic split, "
        f"innovation focus, and project impact objectives."
    )

    return {
        "variant_scores": variant_scores,
        "recommended_variant": recommended_variant.value,
        "routing_reason": routing_reason,
    }


def score_sensitivity(
    pack: ApplicationPack,
    scoring_result: ScoringResult,
) -> dict:
    """
    Performs deterministic gap sensitivity analysis.
    Identifies how many recoverable points are blocked by each missing field.
    """
    gap_criterion_map = {
        "tin_number": CriterionName.FINANCIAL_VIABILITY,
        "financials": CriterionName.FINANCIAL_VIABILITY,
        "turnover": CriterionName.FINANCIAL_VIABILITY,
        "gender": CriterionName.GENDER_YOUTH_INCLUSION,
        "female": CriterionName.GENDER_YOUTH_INCLUSION,
        "staff": CriterionName.JOB_CREATION,
        "employee": CriterionName.JOB_CREATION,
        "employment": CriterionName.JOB_CREATION,
        "milestones": CriterionName.INNOVATION_UNIQUE_FEATURE,
        "machinery": CriterionName.INNOVATION_UNIQUE_FEATURE,
        "license": CriterionName.MANAGEMENT_ORGANOGRAM,
        "registration": CriterionName.MANAGEMENT_ORGANOGRAM,
        "sdg": CriterionName.SDG_ENVIRONMENTAL_IMPACT,
        "supply": CriterionName.LOCAL_SUPPLY_CHAIN,
    }

    score_by_crit = {cs.criterion: cs for cs in scoring_result.criteria_scores}
    sensitivities = []
    seen_criteria = set()

    for gap in pack.gaps:
        matched_crit = CriterionName.LOCAL_SUPPLY_CHAIN
        for key, crit in gap_criterion_map.items():
            if key in gap.field_name.lower():
                matched_crit = crit
                break

        crit_score = score_by_crit.get(matched_crit)
        if crit_score and matched_crit not in seen_criteria:
            recoverable = max(0, crit_score.max_points - crit_score.awarded_points)
            seen_criteria.add(matched_crit)
        else:
            recoverable = 2

        sensitivities.append({
            "gap_field": gap.field_name,
            "criterion": matched_crit.value,
            "recoverable_points": recoverable,
            "priority": gap.priority.value,
            "required_from": gap.required_from,
        })

    total_recoverable = sum(s["recoverable_points"] for s in sensitivities)
    potential_total = min(100, scoring_result.total_score + total_recoverable)

    return {
        "current_score": scoring_result.total_score,
        "potential_total": potential_total,
        "total_recoverable_points": total_recoverable,
        "sensitivities": sensitivities,
    }


def submission_readiness(
    pack: ApplicationPack,
    gate: EligibilityGate,
    contradictions: list,
    consent_records: Optional[list] = None,
) -> dict:
    """
    Calculates overall submission readiness score (0-100%) and enumerates blockers.
    """
    from schemas.reviewer_schema import ContradictionSeverity

    critical_contras = [c for c in contradictions if getattr(c, "severity", None) == ContradictionSeverity.CRITICAL]
    high_gaps = pack.high_priority_gaps if hasattr(pack, "high_priority_gaps") else []

    checks = {
        "eligibility_gate_passed": gate.is_eligible,
        "zero_critical_contradictions": len(critical_contras) == 0,
        "high_priority_gaps_resolved": len(high_gaps) == 0,
        "application_schema_present": pack.application is not None,
        "impact_protocol_present": pack.impact is not None,
    }

    if consent_records is not None:
        active_yes = [r for r in consent_records if getattr(r, "status", None) == "ACTIVE" and getattr(r, "response_verdict", None) == "YES"]
        checks["mandatory_declarations_consented"] = len(active_yes) >= 3

    passed_count = sum(1 for v in checks.values() if v is True)
    total_count = len(checks)
    readiness_pct = round((passed_count / total_count) * 100.0, 1)

    blockers = []
    if not gate.is_eligible:
        blockers.append(f"Eligibility Gate Failed: {gate.gate_reasoning}")
    for c in critical_contras:
        blockers.append(f"Critical Contradiction: {c.explanation}")
    for g in high_gaps:
        blockers.append(f"High Priority Gap: '{g.field_name}' ({g.reason_missing})")

    return {
        "readiness_pct": readiness_pct,
        "is_ready": readiness_pct >= 100.0 and len(blockers) == 0,
        "checks": checks,
        "blockers": blockers,
    }


def reproducibility_check(
    pack: ApplicationPack,
    variant: GridVariant,
    iterations: int = 2,
    client: Optional[Any] = None,
) -> dict:
    """
    Runs the scoring engine multiple times on the same input to test deterministic consistency.
    """
    scores = []
    for _ in range(iterations):
        res = score_application(pack=pack, variant=variant, client=client)
        scores.append(res.total_score)

    is_identical = len(set(scores)) <= 1
    diff = max(scores) - min(scores) if scores else 0

    return {
        "is_identical": is_identical,
        "scores": scores,
        "diff": diff,
    }
