"""
Unit tests for the isolated Deterministic Rule Engine (agents/rule_engine.py).
Verifies:
1. Pure-Python deterministic criterion scoring bands
2. Epistemic provenance caps (DOCUMENT_VERIFIED, APPLICANT_STATED, AI_INFERRED, NEEDS_CONFIRMATION, MISSING, CONTRADICTED)
3. Zero-point rules for missing/contradicted evidence
4. Total score summation
5. Strict integer score guarantee (no floating point leaks)
6. 100-point total maximums across all 3 GridVariant tracks
7. 100% deterministic reproducibility across multiple evaluations
8. Absence of LLM / external API calls
"""

import inspect
import pytest
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
)
from schemas.provenance_schema import FieldStatus, FieldProvenance
from agents.rule_engine import (
    CRITERION_MAX_POINTS,
    resolve_provenance_status,
    evaluate_criterion,
    calculate_total_score,
    evaluate_all_criteria,
)


# =============================================================================
# 1. CRITERION STEP-FUNCTION / BAND TESTS
# =============================================================================

class TestCriterionBands:
    """Test every criterion step-function under DOCUMENT_VERIFIED provenance."""

    def test_job_creation_bands(self):
        prov = {"employment.total_staff": FieldStatus.DOCUMENT_VERIFIED}

        # 20+ workers -> 20 pts (max)
        s_20 = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {"total_staff": 25}, prov)
        assert s_20.awarded_points == 20
        assert isinstance(s_20.awarded_points, int)

        # 10-19 workers -> 14 pts
        s_10 = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {"total_staff": 10}, prov)
        assert s_10.awarded_points == 14
        assert isinstance(s_10.awarded_points, int)

        # 5-9 workers -> 8 pts
        s_5 = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {"total_staff": 5}, prov)
        assert s_5.awarded_points == 8
        assert isinstance(s_5.awarded_points, int)

        # 1-4 workers -> 2 pts
        s_2 = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {"total_staff": 3}, prov)
        assert s_2.awarded_points == 2
        assert isinstance(s_2.awarded_points, int)

        # 0 workers -> 0 pts
        s_0 = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {"total_staff": 0}, prov)
        assert s_0.awarded_points == 0

    def test_financial_viability_bands(self):
        prov = {"financials.sales_history": FieldStatus.DOCUMENT_VERIFIED}

        # >= 1M ETB -> 15 pts (max)
        s_1m = evaluate_criterion(CriterionName.FINANCIAL_VIABILITY, GridVariant.GENERAL_SME, {"revenue_etb": 1_200_000}, prov)
        assert s_1m.awarded_points == 15
        assert isinstance(s_1m.awarded_points, int)

        # 500k-1M ETB -> 10 pts
        s_500k = evaluate_criterion(CriterionName.FINANCIAL_VIABILITY, GridVariant.GENERAL_SME, {"revenue_etb": 600_000}, prov)
        assert s_500k.awarded_points == 10
        assert isinstance(s_500k.awarded_points, int)

        # 100k-500k ETB -> 6 pts
        s_100k = evaluate_criterion(CriterionName.FINANCIAL_VIABILITY, GridVariant.GENERAL_SME, {"revenue_etb": 250_000}, prov)
        assert s_100k.awarded_points == 6
        assert isinstance(s_100k.awarded_points, int)

        # < 100k ETB -> 3 pts
        s_50k = evaluate_criterion(CriterionName.FINANCIAL_VIABILITY, GridVariant.GENERAL_SME, {"revenue_etb": 50_000}, prov)
        assert s_50k.awarded_points == 3
        assert isinstance(s_50k.awarded_points, int)

        # 0 ETB -> 0 pts
        s_0 = evaluate_criterion(CriterionName.FINANCIAL_VIABILITY, GridVariant.GENERAL_SME, {"revenue_etb": 0}, prov)
        assert s_0.awarded_points == 0

    def test_gender_youth_inclusion_bands(self):
        prov = {"female_ownership_percentage": FieldStatus.DOCUMENT_VERIFIED}

        # Exceptional: 60% female equity + majority female staff -> 15 pts (max)
        facts_top = {
            "female_ownership_percentage": 60.0,
            "total_staff": 10,
            "female_staff": 6,
            "youth_staff": 7,
        }
        s_top = evaluate_criterion(CriterionName.GENDER_YOUTH_INCLUSION, GridVariant.GENERAL_SME, facts_top, prov)
        assert s_top.awarded_points == 15

        # Strong: 35% female equity -> 10 pts
        facts_strong = {"female_ownership_percentage": 35.0, "total_staff": 10, "female_staff": 2}
        s_strong = evaluate_criterion(CriterionName.GENDER_YOUTH_INCLUSION, GridVariant.GENERAL_SME, facts_strong, prov)
        assert s_strong.awarded_points == 10

        # Moderate: 15% female equity -> 6 pts
        facts_mod = {"female_ownership_percentage": 15.0, "total_staff": 10, "female_staff": 1}
        s_mod = evaluate_criterion(CriterionName.GENDER_YOUTH_INCLUSION, GridVariant.GENERAL_SME, facts_mod, prov)
        assert s_mod.awarded_points == 6

        # Zero equity/staff -> 0 pts
        s_none = evaluate_criterion(CriterionName.GENDER_YOUTH_INCLUSION, GridVariant.GENERAL_SME, {}, prov)
        assert s_none.awarded_points == 0

    def test_innovation_bands(self):
        prov = {"visible_machinery": FieldStatus.DOCUMENT_VERIFIED}

        # High: proprietary tech -> 15 pts
        s_high = evaluate_criterion(CriterionName.INNOVATION_UNIQUE_FEATURE, GridVariant.GENERAL_SME, {"has_proprietary_tech": True}, prov)
        assert s_high.awarded_points == 15

        # Medium: 2 machinery items -> 10 pts
        s_med = evaluate_criterion(CriterionName.INNOVATION_UNIQUE_FEATURE, GridVariant.GENERAL_SME, {"machinery_list": ["Mixer", "Oven"]}, prov)
        assert s_med.awarded_points == 10

        # Basic: 1 machinery item -> 6 pts
        s_basic = evaluate_criterion(CriterionName.INNOVATION_UNIQUE_FEATURE, GridVariant.GENERAL_SME, {"machinery_list": ["Packaging unit"]}, prov)
        assert s_basic.awarded_points == 6

        # Empty -> 0 pts
        s_0 = evaluate_criterion(CriterionName.INNOVATION_UNIQUE_FEATURE, GridVariant.GENERAL_SME, {}, prov)
        assert s_0.awarded_points == 0

    def test_local_supply_chain_bands(self):
        prov = {"local_sourcing_pct": FieldStatus.DOCUMENT_VERIFIED}

        # 85% local sourcing -> 10 pts (max)
        s_85 = evaluate_criterion(CriterionName.LOCAL_SUPPLY_CHAIN, GridVariant.GENERAL_SME, {"local_sourcing_pct": 85.0}, prov)
        assert s_85.awarded_points == 10

        # 55% local sourcing -> 7 pts
        s_55 = evaluate_criterion(CriterionName.LOCAL_SUPPLY_CHAIN, GridVariant.GENERAL_SME, {"local_sourcing_pct": 55.0}, prov)
        assert s_55.awarded_points == 7

        # 25% local sourcing -> 4 pts
        s_25 = evaluate_criterion(CriterionName.LOCAL_SUPPLY_CHAIN, GridVariant.GENERAL_SME, {"local_sourcing_pct": 25.0}, prov)
        assert s_25.awarded_points == 4

        # 0% -> 0 pts
        s_0 = evaluate_criterion(CriterionName.LOCAL_SUPPLY_CHAIN, GridVariant.GENERAL_SME, {"local_sourcing_pct": 0.0}, prov)
        assert s_0.awarded_points == 0

    def test_sdg_environmental_bands(self):
        prov = {"impact.sdgs": FieldStatus.DOCUMENT_VERIFIED}

        # 3 SDGs -> 10 pts (max)
        s_3 = evaluate_criterion(CriterionName.SDG_ENVIRONMENTAL_IMPACT, GridVariant.GENERAL_SME, {"sdgs": ["SDG 1", "SDG 5", "SDG 8"]}, prov)
        assert s_3.awarded_points == 10

        # 2 SDGs -> 7 pts
        s_2 = evaluate_criterion(CriterionName.SDG_ENVIRONMENTAL_IMPACT, GridVariant.GENERAL_SME, {"sdgs": ["SDG 8", "SDG 9"]}, prov)
        assert s_2.awarded_points == 7

        # 1 SDG -> 4 pts
        s_1 = evaluate_criterion(CriterionName.SDG_ENVIRONMENTAL_IMPACT, GridVariant.GENERAL_SME, {"sdgs": ["SDG 1"]}, prov)
        assert s_1.awarded_points == 4

        # 0 SDGs -> 0 pts
        s_0 = evaluate_criterion(CriterionName.SDG_ENVIRONMENTAL_IMPACT, GridVariant.GENERAL_SME, {"sdgs": []}, prov)
        assert s_0.awarded_points == 0

    def test_management_organogram_bands(self):
        prov = {"organogram": FieldStatus.DOCUMENT_VERIFIED}

        # 3 roles and 4 years -> 5 pts (max)
        s_full = evaluate_criterion(
            CriterionName.MANAGEMENT_ORGANOGRAM,
            GridVariant.GENERAL_SME,
            {"organogram": ["CEO", "CFO", "Operations Head"], "years_in_operation": 4},
            prov,
        )
        assert s_full.awarded_points == 5

        # 2 roles -> 3 pts
        s_mid = evaluate_criterion(
            CriterionName.MANAGEMENT_ORGANOGRAM,
            GridVariant.GENERAL_SME,
            {"organogram": ["Manager", "Accountant"], "years_in_operation": 1},
            prov,
        )
        assert s_mid.awarded_points == 3

        # None -> 0 pts
        s_0 = evaluate_criterion(CriterionName.MANAGEMENT_ORGANOGRAM, GridVariant.GENERAL_SME, {}, prov)
        assert s_0.awarded_points == 0

    def test_community_impact_bands(self):
        prov = {"impact.target_beneficiaries": FieldStatus.DOCUMENT_VERIFIED}

        # 1500 beneficiaries -> 5 pts (max)
        s_high = evaluate_criterion(CriterionName.COMMUNITY_IMPACT, GridVariant.GENERAL_SME, {"target_beneficiaries": 1500}, prov)
        assert s_high.awarded_points == 5

        # 300 beneficiaries -> 3 pts
        s_mid = evaluate_criterion(CriterionName.COMMUNITY_IMPACT, GridVariant.GENERAL_SME, {"target_beneficiaries": 300}, prov)
        assert s_mid.awarded_points == 3

        # 60 beneficiaries -> 2 pts
        s_low = evaluate_criterion(CriterionName.COMMUNITY_IMPACT, GridVariant.GENERAL_SME, {"target_beneficiaries": 60}, prov)
        assert s_low.awarded_points == 2

        # 0 beneficiaries -> 0 pts
        s_0 = evaluate_criterion(CriterionName.COMMUNITY_IMPACT, GridVariant.GENERAL_SME, {"target_beneficiaries": 0}, prov)
        assert s_0.awarded_points == 0

    def test_scalability_bands(self):
        prov = {"scalability": FieldStatus.DOCUMENT_VERIFIED}

        # Regional expansion plan -> 5 pts (max)
        s_high = evaluate_criterion(CriterionName.SCALABILITY, GridVariant.GENERAL_SME, {"growth_capacity": "Regional expansion across Oromia"}, prov)
        assert s_high.awarded_points == 5

        # Established expansion plan -> 3 pts
        s_mid = evaluate_criterion(CriterionName.SCALABILITY, GridVariant.GENERAL_SME, {"has_expansion_plan": True}, prov)
        assert s_mid.awarded_points == 3

        # None -> 0 pts
        s_0 = evaluate_criterion(CriterionName.SCALABILITY, GridVariant.GENERAL_SME, {}, prov)
        assert s_0.awarded_points == 0


# =============================================================================
# 2. PROVENANCE CAPS & ZERO-POINT RULES
# =============================================================================

class TestProvenanceCaps:
    """
    Verifies the Scoring Decision Contract provenance rules:
    - DOCUMENT_VERIFIED: full points (100%)
    - APPLICANT_STATED / AI_INFERRED: capped at 65% of band points (rounded)
    - NEEDS_CONFIRMATION: capped at 50% of band points (rounded)
    - MISSING / CONTRADICTED: 0 points
    """

    def test_job_creation_provenance_caps(self):
        # 10 employees = 14 pts raw band points under GENERAL_SME
        facts = {"total_staff": 10}

        # DOCUMENT_VERIFIED -> 14 pts (100%)
        prov_doc = {"total_staff": FieldStatus.DOCUMENT_VERIFIED}
        res_doc = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_doc)
        assert res_doc.awarded_points == 14
        assert "DOCUMENT_VERIFIED" in res_doc.reasoning

        # APPLICANT_STATED -> 9 pts (65% of 14 = 9.1 -> 9)
        prov_app = {"total_staff": FieldStatus.APPLICANT_STATED}
        res_app = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_app)
        assert res_app.awarded_points == 9
        assert "Capped at 65%" in res_app.reasoning

        # AI_INFERRED -> 9 pts (65% of 14 = 9.1 -> 9)
        prov_ai = {"total_staff": FieldStatus.AI_INFERRED}
        res_ai = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_ai)
        assert res_ai.awarded_points == 9
        assert "Capped at 65%" in res_ai.reasoning

        # NEEDS_CONFIRMATION -> 7 pts (50% of 14 = 7.0 -> 7)
        prov_nc = {"total_staff": FieldStatus.NEEDS_CONFIRMATION}
        res_nc = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_nc)
        assert res_nc.awarded_points == 7
        assert "Capped at 50%" in res_nc.reasoning

        # MISSING -> 0 pts
        prov_mis = {"total_staff": FieldStatus.MISSING}
        res_mis = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_mis)
        assert res_mis.awarded_points == 0
        assert "0 points awarded" in res_mis.reasoning

        # CONTRADICTED -> 0 pts
        prov_con = {"total_staff": FieldStatus.CONTRADICTED}
        res_con = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_con)
        assert res_con.awarded_points == 0
        assert "0 points awarded" in res_con.reasoning

    def test_provenance_cap_with_field_provenance_object(self):
        """Verify handling of FieldProvenance dataclass instances."""
        facts = {"total_staff": 25}  # 20 pts raw
        prov_obj = {
            "total_staff": FieldProvenance(
                field_path="employment.total_staff",
                value=25,
                status=FieldStatus.APPLICANT_STATED,
                confidence=0.85,
                source_type="interview",
                evidence_snippet="We currently employ 25 staff members in our factory.",
            )
        }
        res = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov_obj)
        # 20 * 0.65 = 13 pts
        assert res.awarded_points == 13
        assert isinstance(res.awarded_points, int)


# =============================================================================
# 3. EDGE CASES: MISSING FACTS, EMPTY PROVENANCE, NONE INPUTS
# =============================================================================

class TestEdgeCases:
    """Test handling of None, empty dictionaries, and absent data."""

    def test_fact_is_none_awards_zero(self):
        prov = {"employment.total_staff": FieldStatus.DOCUMENT_VERIFIED}
        res = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {"total_staff": None}, prov)
        assert res.awarded_points == 0
        assert isinstance(res.awarded_points, int)

    def test_facts_dict_empty_awards_zero(self):
        prov = {"employment.total_staff": FieldStatus.DOCUMENT_VERIFIED}
        res = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, {}, prov)
        assert res.awarded_points == 0

    def test_facts_is_none_awards_zero(self):
        prov = {"employment.total_staff": FieldStatus.DOCUMENT_VERIFIED}
        res = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, None, prov)
        assert res.awarded_points == 0

    def test_empty_provenance_treated_as_missing(self):
        # Even with facts present, empty provenance must default to MISSING (0 points)
        facts = {"total_staff": 25, "revenue_etb": 2_000_000}
        res_job = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, {})
        assert res_job.awarded_points == 0
        assert "MISSING" in res_job.reasoning

        res_fin = evaluate_criterion(CriterionName.FINANCIAL_VIABILITY, GridVariant.GENERAL_SME, facts, {})
        assert res_fin.awarded_points == 0
        assert "MISSING" in res_fin.reasoning

    def test_provenance_is_none_treated_as_missing(self):
        facts = {"total_staff": 25}
        res = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, None)
        assert res.awarded_points == 0
        assert "MISSING" in res.reasoning

    def test_strict_integer_type_guarantee(self):
        """Ensure no float math leaks into awarded_points across all criteria and caps."""
        sample_facts = {
            "total_staff": 13,
            "female_ownership_percentage": 42.5,
            "has_proprietary_tech": True,
            "revenue_etb": 750_000,
            "local_sourcing_pct": 65.0,
            "sdgs": ["SDG 1", "SDG 5"],
            "organogram": ["CEO", "Manager"],
            "years_in_operation": 2,
            "target_beneficiaries": 450,
            "growth_capacity": "Scalable production",
        }
        # APPLICANT_STATED triggers fractional 65% calculation
        prov_applicant = {c.value: FieldStatus.APPLICANT_STATED for c in CriterionName}

        scores = evaluate_all_criteria(GridVariant.GENERAL_SME, sample_facts, prov_applicant)
        assert len(scores) == 9
        for s in scores:
            assert isinstance(s.awarded_points, int), f"Criterion {s.criterion} returned non-integer: {s.awarded_points}"
            assert isinstance(s.max_points, int)


# =============================================================================
# 4. TRACK MAXIMUMS & VARIANT WEIGHTING
# =============================================================================

class TestVariantTracksAndWeights:
    """Verify max point allocations across all 3 GridVariant tracks."""

    def test_all_variants_sum_to_100_points(self):
        for variant in GridVariant:
            max_dict = CRITERION_MAX_POINTS[variant]
            total_max = sum(max_dict.values())
            assert total_max == 100, f"Variant {variant} total max points is {total_max}, expected 100"
            assert len(max_dict) == 9, f"Variant {variant} must contain exactly 9 criteria"

    def test_women_youth_variant_doubles_inclusion(self):
        general_max = CRITERION_MAX_POINTS[GridVariant.GENERAL_SME][CriterionName.GENDER_YOUTH_INCLUSION]
        women_max = CRITERION_MAX_POINTS[GridVariant.WOMEN_YOUTH_LED][CriterionName.GENDER_YOUTH_INCLUSION]
        assert general_max == 15
        assert women_max == 30  # Doubled to 30 points

    def test_innovation_tech_variant_doubles_innovation(self):
        general_max = CRITERION_MAX_POINTS[GridVariant.GENERAL_SME][CriterionName.INNOVATION_UNIQUE_FEATURE]
        tech_max = CRITERION_MAX_POINTS[GridVariant.INNOVATION_TECH][CriterionName.INNOVATION_UNIQUE_FEATURE]
        assert general_max == 15
        assert tech_max == 30  # Doubled to 30 points

    def test_evaluate_all_criteria_returns_9_scores_with_100_max(self):
        for variant in GridVariant:
            scores = evaluate_all_criteria(variant, {}, {})
            assert len(scores) == 9
            total_max = sum(s.max_points for s in scores)
            assert total_max == 100


# =============================================================================
# 5. TOTAL SCORE SUMMATION
# =============================================================================

class TestTotalScoreSummation:
    """Test calculate_total_score utility function."""

    def test_calculate_total_score_sum(self):
        scores = [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=14, reasoning="Band awarded 14 points for 10 employees."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=10, reasoning="Band awarded 10 points for 600k ETB turnover."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=3, reasoning="Band awarded 3 points for 300 community beneficiaries."),
        ]
        total = calculate_total_score(scores)
        assert total == 27
        assert isinstance(total, int)

    def test_calculate_total_score_empty(self):
        assert calculate_total_score([]) == 0


# =============================================================================
# 6. REPRODUCIBILITY & DETERMINISM (10 REPETITIONS)
# =============================================================================

class TestDeterminismAndReproducibility:
    """Ensure identical inputs yield 100% identical outputs over 10 iterations."""

    def test_reproducibility_single_criterion(self):
        facts = {"total_staff": 12}
        prov = {"total_staff": FieldStatus.APPLICANT_STATED}

        first_score = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov)

        for _ in range(10):
            rep_score = evaluate_criterion(CriterionName.JOB_CREATION, GridVariant.GENERAL_SME, facts, prov)
            assert rep_score.awarded_points == first_score.awarded_points
            assert rep_score.max_points == first_score.max_points
            assert rep_score.reasoning == first_score.reasoning

    def test_reproducibility_all_criteria(self):
        facts = {
            "total_staff": 25,
            "female_ownership_percentage": 55.0,
            "female_staff": 15,
            "youth_staff": 18,
            "has_proprietary_tech": True,
            "revenue_etb": 1_500_000,
            "local_sourcing_pct": 85.0,
            "sdgs": ["SDG 1", "SDG 5", "SDG 8"],
            "organogram": ["CEO", "CTO", "COO"],
            "years_in_operation": 4,
            "target_beneficiaries": 1200,
            "growth_capacity": "National expansion",
        }
        prov = {c.value: FieldStatus.DOCUMENT_VERIFIED for c in CriterionName}

        first_scores = evaluate_all_criteria(GridVariant.GENERAL_SME, facts, prov)
        first_total = calculate_total_score(first_scores)

        for _ in range(10):
            rep_scores = evaluate_all_criteria(GridVariant.GENERAL_SME, facts, prov)
            rep_total = calculate_total_score(rep_scores)

            assert rep_total == first_total
            for s1, s2 in zip(first_scores, rep_scores):
                assert s1.criterion == s2.criterion
                assert s1.awarded_points == s2.awarded_points
                assert s1.max_points == s2.max_points
                assert s1.reasoning == s2.reasoning


# =============================================================================
# 7. ZERO LLM INVOCATION AUDIT
# =============================================================================

class TestZeroLLMCalls:
    """Verify that rule_engine has zero dependencies or calls to Gemini/LLMs."""

    def test_no_llm_imports_or_references(self):
        import agents.rule_engine as re_module
        source = inspect.getsource(re_module)

        forbidden = [
            "call_gemini",
            "google.genai",
            "genai",
            "GenerativeModel",
            "openai",
            "anthropic",
            "chat.completions",
        ]
        for term in forbidden:
            assert term not in source, f"Rule engine violates contract: found forbidden LLM term '{term}'"
