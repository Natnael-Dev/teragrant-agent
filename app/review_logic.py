"""
Review Logic for TeraGrant Reviewer Dashboard (Batch 28F).
Pure Python functions for loading portfolio batch JSON and calculating ranked shortlists.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from schemas.scoring_schema import GridVariant, CriterionName, CriterionScore, ScoringResult, EligibilityGate
from schemas.reviewer_schema import Contradiction, ContradictionSeverity, ContradictionKind, RankedShortlist
from agents.batch_ranker_agent import rank_batch
from app.ui_helpers import kpi_stats, row_status, evidence_pct

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_reviewer_data(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads the 12-applicant portfolio and computes deterministic KPI stats and ranked shortlists.
    """
    sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
    if not sample_path.exists():
        return {
            "kpis": kpi_stats([]),
            "shortlist": None,
            "raw_items": [],
            "error": "Sample batch file not found."
        }

    with open(sample_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    scored_entries = []
    contra_dict = {}

    for item in raw_items:
        b_name = item.get("business_name", "Unnamed SME")
        score_val = item.get("total_score", 70)
        variant_val = GridVariant(item.get("grid_variant", "GENERAL_SME"))
        is_elig = item.get("is_eligible", True)
        rev_sum = item.get("reviewer_summary", "Technical reviewer evaluation summary.")

        mock_criteria = [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=min(score_val, 20), reasoning="Job creation potential verified."),
            CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=min(max(score_val - 20, 0), 15), reasoning="Demographic inclusion verified."),
            CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=min(max(score_val - 35, 0), 15), reasoning="Technical novelty verified."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=min(max(score_val - 50, 0), 15), reasoning="Financial health verified."),
            CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=min(max(score_val - 65, 0), 10), reasoning="Domestic supply verified."),
            CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=min(max(score_val - 75, 0), 10), reasoning="Environmental impact verified."),
            CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=min(max(score_val - 85, 0), 5), reasoning="Management verified."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=0, reasoning="Community benefit noted."),
            CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=0, reasoning="Scalability noted."),
        ]
        sc_res = ScoringResult(
            grid_variant=variant_val,
            total_score=sum(c.awarded_points for c in mock_criteria),
            criteria_scores=mock_criteria,
            eligibility_gate=EligibilityGate(
                is_eligible=is_elig,
                failed_declarations=[] if is_elig else ["environmental_compliance"],
                triggered_exclusions=[],
                gate_reasoning="Confirmed" if is_elig else "Disqualified due to regulatory permits."
            ),
            reviewer_summary=rev_sum
        )
        scored_entries.append((b_name, sc_res))

        raw_contras = item.get("contradictions", [])
        contra_objs = [
            Contradiction(
                claim_a=c.get("claim_a", ""),
                claim_b=c.get("claim_b", ""),
                severity=ContradictionSeverity(c.get("severity", "WARNING")),
                kind=ContradictionKind(c.get("kind", "DISCREPANCY")),
                explanation=c.get("explanation", "")
            )
            for c in raw_contras
        ]
        if contra_objs:
            contra_dict[b_name] = contra_objs

    eff_key = api_key or os.getenv("GEMINI_API_KEY")
    shortlist = rank_batch(scored_entries, contradictions_map=contra_dict, api_key=eff_key)
    kpis = kpi_stats(raw_items)

    return {
        "kpis": kpis,
        "shortlist": shortlist,
        "raw_items": raw_items,
        "error": None
    }
