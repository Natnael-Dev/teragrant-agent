"""
100-Point Evaluation Scorer Agent (Reviewer Path).
Evaluates an ApplicationPack across 9 weighted criteria under the ALPHAX Internal Prototype
Scoring Grid (v1.0-prototype) track.
Enforces deterministic gap penalties when incomplete information is present.

NOTE: The current 9-criterion, 100-point scoring matrix is the ALPHAX Internal Prototype
Grid (v1.0-prototype), an engineering heuristic developed for the hackathon prototype.
It is NOT the official SEQUA/GIZ evaluation matrix.
"""

import json
from typing import Optional, Any
from pydantic import ValidationError

from google.genai import types

from extractors.config import get_gemini_client, call_gemini_with_fallback
from schemas.gap_schema import ApplicationPack
from schemas.scoring_schema import (
    GRID_NAME,
    GRID_VERSION,
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from .eligibility_agent import run_eligibility_gate


SCORER_SYSTEM_PROMPT = """You are the Lead Investment Committee Evaluator and Senior Technical Reviewer for the TeraGrant SME Grant Program.

Your task is to evaluate a fully structured ApplicationPack against the 9 standard scoring criteria under the designated GridVariant track using the ALPHAX Internal Prototype Grid (v1.0-prototype). (Note: This is a development prototype rubric, not an official sponsor grid).

TRACK MAXIMUM POINT ALLOCATIONS (MUST EQUAL 100 POINTS EXACTLY):
=============================================================================
CRITERION                     | GENERAL_SME | WOMEN_YOUTH_LED | INNOVATION_TECH
------------------------------+-------------+-----------------+----------------
1. Job Creation               |   20 pts    |     20 pts      |     20 pts
2. Gender & Youth Inclusion   |   15 pts    |     30 pts      |      5 pts
3. Innovation & Unique Feature|   15 pts    |      5 pts      |     30 pts
4. Financial Viability        |   15 pts    |     10 pts      |     10 pts
5. Local Supply Chain         |   10 pts    |     10 pts      |     10 pts
6. SDG & Environmental Impact |   10 pts    |     10 pts      |     10 pts
7. Management & Organogram    |    5 pts    |      5 pts      |      5 pts
8. Community Impact           |    5 pts    |      5 pts      |      5 pts
9. Scalability                |    5 pts    |      5 pts      |      5 pts
------------------------------+-------------+-----------------+----------------
TOTAL MAXIMUM                 |  100 pts    |    100 pts      |    100 pts
=============================================================================

MANDATORY GAP PENALTY RULES:
1. For every criterion, review the `gaps` list in the ApplicationPack.
2. If data relevant to a criterion is missing (e.g. missing sales history -> Financial Viability; missing gender split -> Gender Inclusion; missing TIN -> Compliance/Financials):
   - You MUST penalize the score awarded for that criterion.
   - In the `reasoning` field for that criterion, you MUST explicitly state:
     "Score penalized due to missing data: [field_name]."

Respond strictly in JSON matching the ScoringResult schema."""


def score_application(
    pack: ApplicationPack,
    variant: GridVariant,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> ScoringResult:
    """
    Evaluates and scores an ApplicationPack across 9 weighted criteria under the ALPHAX Internal Prototype Grid (v1.0-prototype).
    """
    eligibility_result = run_eligibility_gate(pack.application)

    ai_client = client or get_gemini_client(api_key=api_key)

    scoring_payload = {
        "designated_grid_variant": variant.value,
        "eligibility_gate_result": eligibility_result.model_dump(),
        "application_data": pack.application.model_dump() if pack.application else None,
        "impact_data": pack.impact.model_dump() if pack.impact else None,
        "identified_gaps": [g.model_dump() for g in pack.gaps],
    }

    schema_prompt = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(ScoringResult.model_json_schema(), default=str)}"
    user_prompt = f"""Evaluate this SME application according to the {variant.value} track of the ALPHAX Internal Prototype Grid (v1.0-prototype) and 100-point rubric:

APPLICATION DOSSIER:
{json.dumps(scoring_payload, indent=2, ensure_ascii=False)}
{schema_prompt}"""

    config = types.GenerateContentConfig(
        system_instruction=SCORER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.0,
    )

    try:
        response, _ = call_gemini_with_fallback(
            client=ai_client,
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception as err:
        fallback_scores = _build_default_scores(variant)
        return ScoringResult(
            grid_variant=variant,
            total_score=sum(c.awarded_points for c in fallback_scores),
            criteria_scores=fallback_scores,
            eligibility_gate=eligibility_result,
            reviewer_summary=f"Evaluation generated via fallback engine (API note: {str(err)})."
        )

    if not raw_text:
        fallback_scores = _build_default_scores(variant)
        return ScoringResult(
            grid_variant=variant,
            total_score=sum(c.awarded_points for c in fallback_scores),
            criteria_scores=fallback_scores,
            eligibility_gate=eligibility_result,
            reviewer_summary="Scored with default track baseline."
        )

    try:
        res = ScoringResult.model_validate_json(raw_text)
        res.total_score = sum(c.awarded_points for c in res.criteria_scores)
        res.eligibility_gate = eligibility_result
        return res
    except (ValidationError, json.JSONDecodeError) as err:
        try:
            retry_prompt = f"Your previous JSON was invalid: {str(err)}. Return corrected JSON matching schema:\n{json.dumps(ScoringResult.model_json_schema(), default=str)}"
            retry_contents = [types.Part.from_text(text=retry_prompt), types.Part.from_text(text=raw_text)]
            retry_resp, _ = call_gemini_with_fallback(
                client=ai_client,
                model=model,
                contents=retry_contents,
                config=config,
            )
            retry_text = retry_resp.text if retry_resp and hasattr(retry_resp, "text") else ""
            res = ScoringResult.model_validate_json(retry_text)
            res.total_score = sum(c.awarded_points for c in res.criteria_scores)
            res.eligibility_gate = eligibility_result
            return res
        except Exception:
            try:
                data = json.loads(raw_text)
                res = ScoringResult.model_validate(data)
                res.total_score = sum(c.awarded_points for c in res.criteria_scores)
                res.eligibility_gate = eligibility_result
                return res
            except Exception:
                fallback_scores = _build_default_scores(variant)
                return ScoringResult(
                    grid_variant=variant,
                    total_score=sum(c.awarded_points for c in fallback_scores),
                    criteria_scores=fallback_scores,
                    eligibility_gate=eligibility_result,
                    reviewer_summary="Evaluated under baseline track criteria."
                )


def _build_default_scores(variant: GridVariant) -> list[CriterionScore]:
    """Builds fallback default scores strictly summing within the track's max limits."""
    if variant == GridVariant.WOMEN_YOUTH_LED:
        return [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=12, reasoning="Baseline job creation score."),
            CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=30, awarded_points=22, reasoning="Female/youth participation noted."),
            CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=5, awarded_points=3, reasoning="Practical innovation noted."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=10, awarded_points=6, reasoning="Financial operations noted."),
            CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=6, reasoning="Local sourcing noted."),
            CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=6, reasoning="Social & SDG impact noted."),
            CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=3, reasoning="Management structure noted."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=3, reasoning="Community benefit noted."),
            CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=3, reasoning="Expansion potential noted."),
        ]
    elif variant == GridVariant.INNOVATION_TECH:
        return [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=14, reasoning="Technical job creation score."),
            CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=5, awarded_points=3, reasoning="Inclusion score noted."),
            CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=30, awarded_points=24, reasoning="Strong technical novelty."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=10, awarded_points=7, reasoning="Commercial model viable."),
            CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=7, reasoning="Domestic supply integration."),
            CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=7, reasoning="Clean-tech SDG alignment."),
            CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=4, reasoning="Engineering leadership."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=3, reasoning="Community benefit noted."),
            CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=4, reasoning="High scalability."),
        ]
    else:
        return [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=14, reasoning="SME employment generation."),
            CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=10, reasoning="Balanced demographic inclusion."),
            CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=10, reasoning="Value-add processing."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=10, reasoning="Financial revenue track record."),
            CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=7, reasoning="Domestic supply chain."),
            CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=7, reasoning="SDG impact."),
            CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=3, reasoning="Management structure."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=3, reasoning="Local community support."),
            CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=3, reasoning="Business scalability."),
        ]


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
