"""
Deterministic Rule Engine for Grant Evaluation.
Implements pure-Python scoring rules and provenance caps under the Scoring Decision Contract:
"CODE OWNS THE NUMBERS. AI OWNS THE SENTENCES."

Zero LLM calls. Fully reproducible, auditable, and re-derivable.
"""

from typing import Dict, Any, List, Optional, Union
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from schemas.provenance_schema import FieldStatus, FieldProvenance
from agents.eligibility_agent import run_eligibility_gate

# Maximum points allocation per criterion across the 3 targeted tracks
# Total maximum for every track equals 100 points exactly.
CRITERION_MAX_POINTS: Dict[GridVariant, Dict[CriterionName, int]] = {
    GridVariant.GENERAL_SME: {
        CriterionName.JOB_CREATION: 20,
        CriterionName.GENDER_YOUTH_INCLUSION: 15,
        CriterionName.INNOVATION_UNIQUE_FEATURE: 15,
        CriterionName.FINANCIAL_VIABILITY: 15,
        CriterionName.LOCAL_SUPPLY_CHAIN: 10,
        CriterionName.SDG_ENVIRONMENTAL_IMPACT: 10,
        CriterionName.MANAGEMENT_ORGANOGRAM: 5,
        CriterionName.COMMUNITY_IMPACT: 5,
        CriterionName.SCALABILITY: 5,
    },
    GridVariant.WOMEN_YOUTH_LED: {
        CriterionName.JOB_CREATION: 20,
        CriterionName.GENDER_YOUTH_INCLUSION: 30,  # Doubled weight
        CriterionName.INNOVATION_UNIQUE_FEATURE: 5,
        CriterionName.FINANCIAL_VIABILITY: 10,
        CriterionName.LOCAL_SUPPLY_CHAIN: 10,
        CriterionName.SDG_ENVIRONMENTAL_IMPACT: 10,
        CriterionName.MANAGEMENT_ORGANOGRAM: 5,
        CriterionName.COMMUNITY_IMPACT: 5,
        CriterionName.SCALABILITY: 5,
    },
    GridVariant.INNOVATION_TECH: {
        CriterionName.JOB_CREATION: 20,
        CriterionName.GENDER_YOUTH_INCLUSION: 5,
        CriterionName.INNOVATION_UNIQUE_FEATURE: 30,  # Doubled weight
        CriterionName.FINANCIAL_VIABILITY: 10,
        CriterionName.LOCAL_SUPPLY_CHAIN: 10,
        CriterionName.SDG_ENVIRONMENTAL_IMPACT: 10,
        CriterionName.MANAGEMENT_ORGANOGRAM: 5,
        CriterionName.COMMUNITY_IMPACT: 5,
        CriterionName.SCALABILITY: 5,
    },
}

# Primary provenance field keys for each criterion
CRITERION_PROVENANCE_FIELDS: Dict[CriterionName, List[str]] = {
    CriterionName.JOB_CREATION: [
        "employment.total_staff",
        "total_staff",
        "employee_count",
    ],
    CriterionName.GENDER_YOUTH_INCLUSION: [
        "business_info.female_ownership_percentage",
        "female_ownership_percentage",
        "employment.gender_split",
        "gender_split",
    ],
    CriterionName.INNOVATION_UNIQUE_FEATURE: [
        "impact.project_title",
        "visible_machinery",
        "machinery_list",
        "innovation_description",
    ],
    CriterionName.FINANCIAL_VIABILITY: [
        "financials.sales_history",
        "financials.tin_number",
        "annual_sales",
        "revenue_etb",
    ],
    CriterionName.LOCAL_SUPPLY_CHAIN: [
        "local_sourcing_pct",
        "local_supply_chain",
        "impact.location",
    ],
    CriterionName.SDG_ENVIRONMENTAL_IMPACT: [
        "impact.sdgs",
        "sdgs",
        "environmental_impact",
    ],
    CriterionName.MANAGEMENT_ORGANOGRAM: [
        "organogram",
        "business_info.ownership_structure",
        "years_in_operation",
    ],
    CriterionName.COMMUNITY_IMPACT: [
        "impact.target_beneficiaries",
        "target_beneficiaries",
        "community_programs",
    ],
    CriterionName.SCALABILITY: [
        "scalability",
        "expansion_plan",
        "growth_capacity",
    ],
}


def resolve_provenance_status(
    criterion: CriterionName,
    provenance: Optional[Dict[str, Any]],
) -> FieldStatus:
    """
    Resolves the epistemic FieldStatus for a given criterion from the provenance dictionary.
    Defaults to FieldStatus.MISSING if no evidence is provided.
    """
    if not provenance:
        return FieldStatus.MISSING

    # 1. Direct criterion name check
    for key in (criterion.value, criterion.name):
        if key in provenance:
            raw = provenance[key]
            if isinstance(raw, FieldProvenance):
                return raw.status
            if isinstance(raw, FieldStatus):
                return raw
            if isinstance(raw, str):
                try:
                    return FieldStatus(raw)
                except ValueError:
                    pass

    # 2. Check mapped primary fields
    candidates = CRITERION_PROVENANCE_FIELDS.get(criterion, [])
    for field_path in candidates:
        if field_path in provenance:
            raw = provenance[field_path]
            if isinstance(raw, FieldProvenance):
                return raw.status
            if isinstance(raw, FieldStatus):
                return raw
            if isinstance(raw, str):
                try:
                    return FieldStatus(raw)
                except ValueError:
                    pass

    return FieldStatus.MISSING


def _apply_provenance_cap(raw_points: int, status: FieldStatus, max_points: int) -> tuple[int, str]:
    """
    Applies the provenance cap defined in the Scoring Decision Contract:
    - DOCUMENT_VERIFIED: 100% of calculated points
    - APPLICANT_STATED / AI_INFERRED: capped at 65% of calculated points (rounded)
    - NEEDS_CONFIRMATION: capped at 50% of calculated points (rounded)
    - MISSING / CONTRADICTED: 0 points
    """
    if status == FieldStatus.DOCUMENT_VERIFIED:
        awarded = raw_points
        note = "Full points awarded (DOCUMENT_VERIFIED)"
    elif status in (FieldStatus.APPLICANT_STATED, FieldStatus.AI_INFERRED):
        awarded = int(round(raw_points * 0.65))
        note = f"Capped at 65% for {status.value} ({raw_points} -> {awarded} pts)"
    elif status == FieldStatus.NEEDS_CONFIRMATION:
        awarded = int(round(raw_points * 0.50))
        note = f"Capped at 50% for {status.value} ({raw_points} -> {awarded} pts)"
    elif status in (FieldStatus.MISSING, FieldStatus.CONTRADICTED):
        awarded = 0
        note = f"0 points awarded due to {status.value} evidence"
    else:
        awarded = 0
        note = f"0 points awarded (unrecognized status {status})"

    clamped = max(0, min(awarded, max_points))
    return clamped, note


# =============================================================================
# DETERMINISTIC STEP FUNCTIONS (CRITERIA BANDS)
# =============================================================================

def _eval_job_creation(facts: dict, max_points: int) -> tuple[int, str]:
    staff = facts.get("total_staff")
    if staff is None:
        staff = facts.get("employment.total_staff") or facts.get("employee_count")

    if staff is None or staff <= 0:
        return 0, "No employee headcount established (0 pts)"
    if staff >= 20:
        return max_points, f"Enterprise employs {staff} workers (20+ headcount band: {max_points}/{max_points} pts)"
    if staff >= 10:
        # Standard: 14/20
        pts = int(round(max_points * 0.70))
        return pts, f"Enterprise employs {staff} workers (10-19 headcount band: {pts}/{max_points} pts)"
    if staff >= 5:
        # Standard: 8/20
        pts = int(round(max_points * 0.40))
        return pts, f"Enterprise employs {staff} workers (5-9 headcount band: {pts}/{max_points} pts)"
    # 1-4 workers
    pts = int(round(max_points * 0.10))
    return pts, f"Enterprise employs {staff} workers (1-4 headcount band: {pts}/{max_points} pts)"


def _eval_gender_youth(facts: dict, max_points: int) -> tuple[int, str]:
    fem_pct = facts.get("female_ownership_percentage")
    if fem_pct is None:
        fem_pct = facts.get("business_info.female_ownership_percentage")

    total_staff = facts.get("total_staff") or facts.get("employment.total_staff") or 0
    fem_staff = facts.get("female_staff") or facts.get("employment.gender_split.female") or 0
    youth_staff = facts.get("youth_staff") or facts.get("employment.age_split.youth_18_29") or 0

    fem_ratio = (fem_staff / total_staff) if total_staff > 0 else 0.0
    youth_ratio = (youth_staff / total_staff) if total_staff > 0 else 0.0

    if fem_pct is None and total_staff <= 0:
        return 0, "No demographic data provided for gender or youth inclusion (0 pts)"

    eff_fem_pct = fem_pct or 0.0

    # Tier 4: Majority female ownership (>=50%) and substantial female or youth workforce
    if eff_fem_pct >= 50.0 and (fem_ratio >= 0.4 or youth_ratio >= 0.5):
        return max_points, f"Exceptional inclusion: {eff_fem_pct:.0f}% female equity with {fem_ratio*100:.0f}% female / {youth_ratio*100:.0f}% youth staff (Top tier: {max_points}/{max_points} pts)"

    # Tier 3: High female ownership (>=30%) OR major workforce inclusion (>=50%)
    if eff_fem_pct >= 30.0 or fem_ratio >= 0.5 or youth_ratio >= 0.6:
        pts = int(round(max_points * 0.70))
        return pts, f"Strong inclusion: {eff_fem_pct:.0f}% female equity or majority female/youth workforce ({pts}/{max_points} pts)"

    # Tier 2: Meaningful female ownership (>=10%) or significant workforce (>=25%)
    if eff_fem_pct >= 10.0 or fem_ratio >= 0.25 or youth_ratio >= 0.3:
        pts = int(round(max_points * 0.40))
        return pts, f"Moderate inclusion: {eff_fem_pct:.0f}% female equity or {fem_ratio*100:.0f}% female workforce ({pts}/{max_points} pts)"

    # Tier 1: Minimum presence
    if eff_fem_pct > 0 or fem_staff > 0 or youth_staff > 0:
        pts = max(1, int(round(max_points * 0.20)))
        return pts, f"Baseline inclusion: female or youth participation noted ({pts}/{max_points} pts)"

    return 0, "Zero female or youth representation reported (0 pts)"


def _eval_innovation(facts: dict, max_points: int) -> tuple[int, str]:
    has_tech = facts.get("has_proprietary_tech") or facts.get("tech_innovation") or False
    machinery = facts.get("machinery_list") or facts.get("visible_machinery") or []
    machinery_count = len(machinery) if isinstance(machinery, list) else int(facts.get("machinery_count") or 0)
    level = str(facts.get("innovation_level") or "").lower()

    if not has_tech and machinery_count == 0 and not level:
        return 0, "No innovation, technology, or machinery assets established (0 pts)"

    if has_tech or level in ("high", "exceptional") or machinery_count >= 5:
        return max_points, f"High novelty: proprietary technology or advanced machinery fleet ({max_points}/{max_points} pts)"

    if machinery_count >= 2 or level in ("medium", "moderate"):
        pts = int(round(max_points * 0.70))
        return pts, f"Value-add processing: operational machinery and production processes ({pts}/{max_points} pts)"

    if machinery_count >= 1 or level in ("low", "basic"):
        pts = int(round(max_points * 0.40))
        return pts, f"Standard processing: basic machinery assets verified ({pts}/{max_points} pts)"

    pts = max(1, int(round(max_points * 0.20)))
    return pts, f"Minimal innovation: basic operational tools noted ({pts}/{max_points} pts)"


def _eval_financial_viability(facts: dict, max_points: int) -> tuple[int, str]:
    rev = facts.get("revenue_etb")
    if rev is None:
        rev = facts.get("annual_sales") or facts.get("turnover")
    if rev is None and "financials.sales_history" in facts:
        hist = facts["financials.sales_history"]
        if isinstance(hist, list) and hist:
            first = hist[0]
            rev = first.get("revenue_etb") if isinstance(first, dict) else getattr(first, "revenue_etb", None)

    if rev is None or rev <= 0:
        return 0, "No verified revenue or sales history provided (0 pts)"

    # Ethiopian SME Revenue Bands (ETB)
    if rev >= 1_000_000.0:
        return max_points, f"High turnover: {rev:,.0f} ETB annual revenue (>= 1M band: {max_points}/{max_points} pts)"
    if rev >= 500_000.0:
        pts = int(round(max_points * 0.70))
        return pts, f"Stable turnover: {rev:,.0f} ETB annual revenue (500k-1M band: {pts}/{max_points} pts)"
    if rev >= 100_000.0:
        pts = int(round(max_points * 0.40))
        return pts, f"Emerging turnover: {rev:,.0f} ETB annual revenue (100k-500k band: {pts}/{max_points} pts)"

    pts = max(1, int(round(max_points * 0.20)))
    return pts, f"Micro turnover: {rev:,.0f} ETB annual revenue (< 100k band: {pts}/{max_points} pts)"


def _eval_local_supply_chain(facts: dict, max_points: int) -> tuple[int, str]:
    pct = facts.get("local_sourcing_pct")
    suppliers = facts.get("supplier_count") or facts.get("domestic_suppliers") or 0

    if (pct is None or pct <= 0) and suppliers <= 0 and not facts.get("local_supply_chain"):
        return 0, "No domestic supply chain or local sourcing established (0 pts)"

    eff_pct = pct or 0.0
    if eff_pct >= 80.0 or suppliers >= 5:
        return max_points, f"High domestic integration: {eff_pct:.0f}% localized raw materials or {suppliers} suppliers ({max_points}/{max_points} pts)"
    if eff_pct >= 50.0 or suppliers >= 2:
        pts = int(round(max_points * 0.70))
        return pts, f"Substantial domestic sourcing: {eff_pct:.0f}% localized sourcing ({pts}/{max_points} pts)"
    if eff_pct >= 20.0 or suppliers >= 1:
        pts = int(round(max_points * 0.40))
        return pts, f"Moderate domestic sourcing: {eff_pct:.0f}% localized inputs ({pts}/{max_points} pts)"

    if eff_pct > 0 or suppliers > 0:
        pts = max(1, int(round(max_points * 0.20)))
        return pts, f"Initial supply integration noted ({pts}/{max_points} pts)"

    return 0, "No domestic supply chain or local sourcing established (0 pts)"


def _eval_sdg_environmental(facts: dict, max_points: int) -> tuple[int, str]:
    sdgs = facts.get("sdgs") or []
    count = len(sdgs) if isinstance(sdgs, list) else int(facts.get("sdg_count") or 0)
    has_eco = facts.get("has_environmental_practice") or False

    if count <= 0 and not has_eco:
        return 0, "No UN SDG alignment or environmental practices established (0 pts)"

    if count >= 3 or (count >= 2 and has_eco):
        return max_points, f"Strong SDG alignment: {count} verified UN SDGs and clean production practices ({max_points}/{max_points} pts)"
    if count >= 2 or has_eco:
        pts = int(round(max_points * 0.70))
        return pts, f"Moderate impact: {count} verified UN SDGs ({pts}/{max_points} pts)"
    if count >= 1:
        pts = int(round(max_points * 0.40))
        return pts, f"Single SDG identified ({pts}/{max_points} pts)"

    pts = max(1, int(round(max_points * 0.20)))
    return pts, f"Baseline environmental awareness noted ({pts}/{max_points} pts)"


def _eval_management_organogram(facts: dict, max_points: int) -> tuple[int, str]:
    organogram = facts.get("organogram") or []
    org_count = len(organogram) if isinstance(organogram, list) else int(facts.get("organogram_count") or 0)
    years = facts.get("years_in_operation") or facts.get("business_info.years_in_operation") or 0

    if org_count <= 0 and years <= 0:
        return 0, "No management structure or operating history established (0 pts)"

    if org_count >= 3 and years >= 3:
        return max_points, f"Established management: {org_count} structured roles and {years} operating years ({max_points}/{max_points} pts)"
    if org_count >= 2 or years >= 2:
        pts = int(round(max_points * 0.60))
        return pts, f"Documented team: {org_count} roles with {years} operating years ({pts}/{max_points} pts)"
    if org_count >= 1 or years >= 1:
        pts = int(round(max_points * 0.40))
        return pts, f"Emerging team structure ({pts}/{max_points} pts)"

    pts = max(1, int(round(max_points * 0.20)))
    return pts, f"Sole proprietor or early setup ({pts}/{max_points} pts)"


def _eval_community_impact(facts: dict, max_points: int) -> tuple[int, str]:
    beneficiaries = facts.get("target_beneficiaries")
    if beneficiaries is None:
        beneficiaries = facts.get("impact.target_beneficiaries")

    if beneficiaries is None or beneficiaries <= 0:
        return 0, "No community beneficiaries established (0 pts)"

    if beneficiaries >= 1000:
        return max_points, f"High community impact: {beneficiaries:,} target beneficiaries ({max_points}/{max_points} pts)"
    if beneficiaries >= 250:
        pts = int(round(max_points * 0.60))
        return pts, f"Substantial impact: {beneficiaries:,} community beneficiaries ({pts}/{max_points} pts)"
    if beneficiaries >= 50:
        pts = int(round(max_points * 0.40))
        return pts, f"Moderate impact: {beneficiaries:,} community beneficiaries ({pts}/{max_points} pts)"

    pts = max(1, int(round(max_points * 0.20)))
    return pts, f"Localized impact: {beneficiaries} beneficiaries ({pts}/{max_points} pts)"


def _eval_scalability(facts: dict, max_points: int) -> tuple[int, str]:
    growth = str(facts.get("growth_capacity") or facts.get("expansion_plan") or "").lower()
    has_plan = facts.get("has_expansion_plan") or False

    if not growth and not has_plan and not facts.get("scalability"):
        return 0, "No business scalability or expansion plan established (0 pts)"

    if "regional" in growth or "national" in growth or "multi-woreda" in growth:
        return max_points, f"High scalability: regional or inter-woreda market expansion plan ({max_points}/{max_points} pts)"
    if "viable" in growth or "scale" in growth or has_plan:
        pts = int(round(max_points * 0.60))
        return pts, f"Established scalability: production expansion capacity documented ({pts}/{max_points} pts)"

    pts = max(1, int(round(max_points * 0.40)))
    return pts, f"Baseline local scalability potential ({pts}/{max_points} pts)"


# Dispatcher mapping criteria to step functions
STEP_EVALUATORS = {
    CriterionName.JOB_CREATION: _eval_job_creation,
    CriterionName.GENDER_YOUTH_INCLUSION: _eval_gender_youth,
    CriterionName.INNOVATION_UNIQUE_FEATURE: _eval_innovation,
    CriterionName.FINANCIAL_VIABILITY: _eval_financial_viability,
    CriterionName.LOCAL_SUPPLY_CHAIN: _eval_local_supply_chain,
    CriterionName.SDG_ENVIRONMENTAL_IMPACT: _eval_sdg_environmental,
    CriterionName.MANAGEMENT_ORGANOGRAM: _eval_management_organogram,
    CriterionName.COMMUNITY_IMPACT: _eval_community_impact,
    CriterionName.SCALABILITY: _eval_scalability,
}


# =============================================================================
# PUBLIC API: EVALUATE CRITERION & TOTAL SCORE
# =============================================================================

def evaluate_criterion(
    criterion_name: CriterionName,
    variant: GridVariant,
    facts: Optional[Dict[str, Any]],
    provenance: Optional[Dict[str, Any]],
) -> CriterionScore:
    """
    Deterministically evaluates a single criterion under a specific GridVariant track.
    Applies pure-Python step-functions and enforces Scoring Decision Contract provenance caps.

    Zero LLM calls. Fully re-derivable.
    """
    safe_facts = facts or {}
    safe_prov = provenance or {}

    max_points = CRITERION_MAX_POINTS.get(variant, {}).get(criterion_name, 10)
    evaluator = STEP_EVALUATORS.get(criterion_name)

    if not evaluator:
        return CriterionScore(
            criterion=criterion_name,
            max_points=max_points,
            awarded_points=0,
            reasoning=f"No evaluator registered for criterion {criterion_name.value}.",
        )

    # 1. Calculate raw band points from facts
    raw_points, band_desc = evaluator(safe_facts, max_points)

    # 2. Resolve provenance status
    status = resolve_provenance_status(criterion_name, safe_prov)

    # 3. Apply provenance caps
    final_points, cap_note = _apply_provenance_cap(raw_points, status, max_points)

    # 4. Formulate deterministic audit reasoning
    reasoning = f"{band_desc} Provenance status: {status.value}. {cap_note}."

    return CriterionScore(
        criterion=criterion_name,
        max_points=max_points,
        awarded_points=final_points,
        reasoning=reasoning,
    )


def calculate_total_score(criteria_scores: List[CriterionScore]) -> int:
    """Calculates the mathematical sum of awarded points across all criterion scores."""
    return sum(c.awarded_points for c in criteria_scores)


def evaluate_all_criteria(
    variant: GridVariant,
    facts: Optional[Dict[str, Any]],
    provenance: Optional[Dict[str, Any]],
) -> List[CriterionScore]:
    """
    Evaluates all 9 standardized criteria in order under the specified GridVariant track.
    Returns exactly 9 CriterionScore objects whose max_points sum to 100.
    """
    scores = []
    for criterion in CriterionName:
        sc = evaluate_criterion(
            criterion_name=criterion,
            variant=variant,
            facts=facts,
            provenance=provenance,
        )
        scores.append(sc)
    return scores
