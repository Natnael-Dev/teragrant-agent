"""
Adversarial and Epistemic Stress Test Suite (Batch K - Final Release Gate).
Validates that the system resists 'confidently complete' AI anti-patterns:
1. Missing evidence remains MISSING and yields 0 points (no silent default averages).
2. Contradictions preserve BOTH claims without silent adjudication.
3. 100% deterministic reproducibility across repeated executions on identical inputs.
4. Graceful resilience and fallback honesty against malformed/corrupted LLM responses.
"""

import json
from unittest.mock import patch, MagicMock

from schemas.gap_schema import ApplicationPack
from schemas.provenance_schema import FieldStatus, FieldProvenance
from schemas.scoring_schema import GridVariant, CriterionName
from schemas.reviewer_schema import ContradictionKind
from extractors.schemas import AudioTranscriptExtraction, LicenseExtraction, WorkshopExtraction
from agents.mapper_agent import _build_deterministic_pack
from agents.contradiction_agent import detect_contradictions
from agents.scorer_agent import score_application
from agents.rule_engine import evaluate_criterion


def test_missing_evidence_yields_zero_not_default():
    """
    Feed an ApplicationPack with completely missing employment and financial data.
    Assert that the deterministic rule engine awards exactly 0 points for those criteria.
    Assert that the provenance state remains MISSING (no silent defaults or injected averages).
    """
    empty_license = LicenseExtraction(
        is_legible=False,
        business_name=None,
        tin_number=None,
        license_number=None,
        location=None,
        line_of_business=None,
        capital_amount=None,
    )
    empty_audio = AudioTranscriptExtraction(
        transcript="",
        detected_language="English",
        business_name=None,
        employee_count=None,
        location=None,
        financial_figures=[],
    )

    pack = _build_deterministic_pack(
        license_data=empty_license,
        audio_data=empty_audio,
        workshop_data=None,
    )

    # Verify provenance states are strictly MISSING
    assert pack.provenance["employment.total_staff"].status == FieldStatus.MISSING
    assert pack.provenance["employment.total_staff"].value is None
    assert pack.provenance["financials.annual_turnover_etb"].status == FieldStatus.MISSING
    assert pack.provenance["financials.annual_turnover_etb"].value is None

    # Evaluate Job Creation criterion directly
    job_score = evaluate_criterion(
        criterion_name=CriterionName.JOB_CREATION,
        variant=GridVariant.GENERAL_SME,
        facts={},
        provenance=pack.provenance,
    )
    assert job_score.awarded_points == 0, f"Expected 0 points for missing employment, got {job_score.awarded_points}"
    assert job_score.provenance_state in [FieldStatus.MISSING.value, "MISSING"]

    # Evaluate Financial Viability criterion directly
    fin_score = evaluate_criterion(
        criterion_name=CriterionName.FINANCIAL_VIABILITY,
        variant=GridVariant.GENERAL_SME,
        facts={},
        provenance=pack.provenance,
    )
    assert fin_score.awarded_points == 0, f"Expected 0 points for missing financials, got {fin_score.awarded_points}"
    assert fin_score.provenance_state in [FieldStatus.MISSING.value, "MISSING"]

    # Also evaluate full pack scoring to ensure total score reflects missing data
    scoring_res = score_application(pack=pack, variant=GridVariant.GENERAL_SME)
    assert scoring_res.total_score == 0, f"Expected 0 total points, got {scoring_res.total_score}"


def test_contradiction_does_not_silently_adjudicate():
    """
    Feed an ApplicationPack where audio claims 20 staff but workshop photo shows 5 workers.
    Assert that the system records the provenance as CONTRADICTED.
    Assert that both conflicting claims ('20' and '5') are preserved in the contradiction audit.
    """
    audio = AudioTranscriptExtraction(
        transcript="We have twenty employees actively operating in our workshop.",
        detected_language="English",
        business_name="Adama Oil Extraction",
        employee_count=20,
    )
    workshop = WorkshopExtraction(
        is_legible=True,
        estimated_people_present=5,
        visible_machinery=["Oil expeller"],
        extraction_notes="Visual count confirms 5 people present",
    )

    pack = _build_deterministic_pack(
        license_data=None,
        audio_data=audio,
        workshop_data=workshop,
    )

    # Provenance for total_staff must be explicitly CONTRADICTED
    assert "employment.total_staff" in pack.provenance
    assert pack.provenance["employment.total_staff"].status == FieldStatus.CONTRADICTED

    # Contradiction detection must retain both claims without picking an average
    contradictions = detect_contradictions(pack=pack, workshop_data=workshop)
    discrepancy = next(
        (c for c in contradictions if c.kind == ContradictionKind.DISCREPANCY and "photo" in c.claim_b.lower()),
        None,
    )
    assert discrepancy is not None, f"Expected visual discrepancy contradiction, got {contradictions}"
    assert "20" in discrepancy.claim_a, f"Expected claim_a to preserve 20, got '{discrepancy.claim_a}'"
    assert "5" in discrepancy.claim_b, f"Expected claim_b to preserve 5, got '{discrepancy.claim_b}'"


def test_reproducibility_identical_inputs_identical_scores():
    """
    Execute score_application 10 times consecutively on the exact same ApplicationPack fixture.
    Assert that the total_score integer and individual criterion scores are 100% identical every run.
    """
    fixture_path = "data/fixtures/demo_extraction.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pack = ApplicationPack.model_validate(data)

    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"reviewer_summary": "Deterministic audit test summary."})

    scores = []
    criterion_score_breakdowns = []

    for _ in range(10):
        with patch(
            "agents.scorer_agent.call_gemini_with_fallback",
            return_value=(mock_resp, "mock-gemini-offline"),
        ):
            res = score_application(pack=pack, variant=GridVariant.GENERAL_SME)
            scores.append(res.total_score)
            criterion_score_breakdowns.append([c.awarded_points for c in res.criteria_scores])

    # All 10 scores must be strictly identical
    assert len(set(scores)) == 1, f"Non-deterministic score variation detected across runs: {scores}"
    first_breakdown = criterion_score_breakdowns[0]
    for b in criterion_score_breakdowns:
        assert b == first_breakdown, f"Non-deterministic criterion breakdown variation: {b} != {first_breakdown}"


def test_malformed_ai_json_falls_back_gracefully():
    """
    Mock the Gemini LLM to return malformed, corrupt, or truncated JSON.
    Assert that score_application catches the error without crashing,
    preserves all deterministic Python criteria scores, and outputs the honest fallback summary.
    """
    fixture_path = "data/fixtures/demo_extraction.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pack = ApplicationPack.model_validate(data)

    # Simulate Gemini API raising error due to malformed/corrupt JSON response payload
    with patch(
        "agents.scorer_agent.call_gemini_with_fallback",
        side_effect=RuntimeError("Malformed JSON / garbage response stream received from LLM endpoint"),
    ):
        result = score_application(pack=pack, variant=GridVariant.GENERAL_SME)

    # Mathematical points calculated by Python rule engine are unaffected
    assert result.total_score > 0, "Deterministic scoring must succeed despite LLM failure"
    assert len(result.criteria_scores) == 9

    # System catches exception and returns the fallback summary
    assert result.reviewer_summary == "Scoring completed; narrative summary unavailable."
