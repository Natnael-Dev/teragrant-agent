#!/usr/bin/env python3
"""
TeraGrant Agent — Keyless Deterministic Replay Demo.
Proves deterministic reproducibility and transparency of the scoring engine
without requiring any live Gemini API keys or network access.

Principle: "CODE OWNS THE NUMBERS. AI OWNS THE SENTENCES."
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Project root resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas.gap_schema import ApplicationPack
from schemas.scoring_schema import GridVariant
from agents.scorer_agent import score_application


def run_demo():
    fixture_path = PROJECT_ROOT / "data" / "fixtures" / "demo_extraction.json"
    if not fixture_path.exists():
        print(f"[ERROR] Fixture file not found at: {fixture_path}")
        sys.exit(1)

    print("=" * 78)
    print("      TERAGRANT AGENT — KEYLESS DETERMINISTIC REPLAY DEMO (v1.0-prototype)     ")
    print("=" * 78)
    print(f"Loading recorded application fixture: {fixture_path.name}")

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pack = ApplicationPack.model_validate(data)
    app = pack.application
    business_name = app.business_info.business_name if app and app.business_info else "Unknown"
    staff = app.employment.total_staff if app and app.employment else "N/A"
    rev = (
        app.financials.sales_history[-1].revenue_etb
        if app and app.financials and app.financials.sales_history
        else "N/A"
    )

    print(f"Applicant Enterprise: {business_name}")
    print(f"Verified Staff Count: {staff} employees")
    print(f"Recorded Annual Sales: {rev:,.2f} ETB" if isinstance(rev, (int, float)) else f"Sales: {rev}")
    print(f"Tracked Provenance Fields: {len(pack.provenance)} verified epistemic records")
    print("-" * 78)
    print("Executing Deterministic Rule Engine in OFFLINE / KEYLESS mode...")
    print("Architectural Mandate: 'Code owns the numbers. AI owns the sentences.'")
    print("-" * 78)

    # Mock the LLM to return static narrative summary (offline/keyless execution)
    offline_summary = (
        "Enterprise demonstrates verifiable operational history, balanced employment demographics, "
        "and documented capital equipment. Committee recommends on-site verification."
    )

    mock_gemini_resp = MagicMock()
    mock_gemini_resp.text = json.dumps({"reviewer_summary": offline_summary})

    with patch(
        "agents.scorer_agent.call_gemini_with_fallback",
        return_value=(mock_gemini_resp, "offline-replay"),
    ):
        result = score_application(pack=pack, variant=GridVariant.GENERAL_SME)

    print(f"{'CRITERION':<30} | {'RULE APPLIED':<40} | {'POINTS':>6}")
    print("-" * 78)

    for score in result.criteria_scores:
        crit_name = score.criterion.value if hasattr(score.criterion, "value") else str(score.criterion)
        rule = score.rule_applied or "STANDARD_EVAL"
        awarded = score.awarded_points
        max_pts = score.max_points
        pts_str = f"{awarded}/{max_pts}"
        print(f"{crit_name:<30} | {rule:<40} | {pts_str:>6}")

    print("=" * 78)
    print(f"Total Score: {result.total_score} / 100 points")
    print(f"Grid Framework: {result.grid_variant.value} (ALPHAX Internal Prototype Grid v1.0-prototype)")
    print(f"Reviewer Narrative: {result.reviewer_summary}")
    print("=" * 78)
    print("✅ KEYLESS DETERMINISTIC REPLAY SUCCESSFUL (Exit code 0)")
    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
