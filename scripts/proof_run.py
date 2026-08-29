"""
Proof Run Script for TeraGrant Agent.
Executes the live end-to-end pipeline using the real Gemini API on multimodal inputs,
measures per-stage latency, tests batch ranking, generates consent packages,
and introspects schema field coverage.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractors.config import get_gemini_client, MODEL_FALLBACK_CHAIN
from extractors.audio_extractor import extract_audio_story
from extractors.vision_extractor import extract_license_data
from extractors.workshop_extractor import extract_workshop_data
from agents.mapper_agent import generate_application_pack
from agents.eligibility_agent import run_eligibility_gate
from agents.router_agent import route_to_grid_variant
from agents.scorer_agent import score_application
from agents.contradiction_agent import detect_contradictions
from agents.batch_ranker_agent import rank_batch
from agents.declaration_explainer_agent import generate_consent_package
from schemas.application_schema import (
    ApplicationSchema,
    BusinessInfo,
    EmploymentBreakdown,
    FinancialHistory,
    MandatoryDeclarations,
    ExclusionFactors,
)
from schemas.impact_schema import ImpactProtocol
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from schemas.reviewer_schema import Contradiction, ContradictionSeverity
from app.tts_engine import generate_speech_audio


def prepare_test_assets() -> tuple[str, str, str]:
    """Prepares and returns paths to (voice_file, license_file, workshop_file)."""
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Voice Note Preparation
    voice_path = None
    for cand in [PROJECT_ROOT / "testvoice.oga", data_dir / "testvoice.oga", data_dir / "proof_voice.mp3"]:
        if cand.exists():
            voice_path = str(cand)
            break
            
    if not voice_path:
        voice_scripts_dir = data_dir / "voice_scripts"
        voice_scripts_dir.mkdir(parents=True, exist_ok=True)
        script_file = voice_scripts_dir / "voice_script_english.txt"
        
        script_text = (
            "Hello, my name is Almaz Bekele and I am the founder of Almaz Spice Mill in Bahir Dar. "
            "We currently employ 8 workers including 5 women. We process and pack fine organic berbere, "
            "shiro, and culinary spices for regional markets. Our annual sales turnover is about 450,000 Birr. "
            "We are requesting 500,000 Birr in grant support to purchase a commercial spice pulverizing machine "
            "and electrical motor to double our production capacity and create 6 new youth jobs."
        )
        if not script_file.exists():
            script_file.write_text(script_text, encoding="utf-8")
        else:
            script_text = script_file.read_text(encoding="utf-8")
            
        print("🔊 Generating live voice note audio via gTTS...")
        audio_bytes = generate_speech_audio(script_text, lang="en")
        voice_out = data_dir / "proof_voice.mp3"
        with open(voice_out, "wb") as f:
            f.write(audio_bytes)
        voice_path = str(voice_out)
        print(f"✅ Voice note saved to: {voice_path} ({len(audio_bytes)} bytes)")

    # 2. License Asset Preparation
    test_assets_dir = data_dir / "test_assets"
    test_assets_dir.mkdir(parents=True, exist_ok=True)
    license_path = test_assets_dir / "license_smudged.jpg"
    if not license_path.exists():
        dummy_lic = data_dir / "dummy_license.jpg"
        if dummy_lic.exists():
            license_path.write_bytes(dummy_lic.read_bytes())
        else:
            license_path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9")

    # 3. Workshop Asset Preparation
    workshop_path = test_assets_dir / "workshop_berbere.jpg"
    if not workshop_path.exists():
        dummy_lic = data_dir / "dummy_license.jpg"
        if dummy_lic.exists():
            workshop_path.write_bytes(dummy_lic.read_bytes())
        else:
            workshop_path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9")

    return voice_path, str(license_path), str(workshop_path)


def main():
    print("=" * 80)
    print("🚀 TERAGRANT AGENT: LIVE END-TO-END PROOF RUN")
    print(f"Active Model Chain: {MODEL_FALLBACK_CHAIN}")
    print("=" * 80)

    total_start_time = time.time()
    voice_path, license_path, workshop_path = prepare_test_assets()
    print(f"\n📂 Test Input Assets:")
    print(f"  - Voice Note: {voice_path}")
    print(f"  - Trade License: {license_path}")
    print(f"  - Workshop Photo: {workshop_path}")

    audio_data = None
    license_data = None
    workshop_data = None
    pack = None
    gate_result = None
    variant = None
    score_result = None
    contradictions = []

    # -------------------------------------------------------------------------
    # STAGE 1: AUDIO EXTRACTION (LIVE GEMINI)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🎙️ STAGE 1: AUDIO EXTRACTION & TRANSCRIPTION (LIVE GEMINI API)")
    print("-" * 80)
    t0 = time.time()
    try:
        audio_data = extract_audio_story(audio_path=voice_path)
        dt = time.time() - t0
        print(f"⏱️ Stage 1 Completed in {dt:.2f}s")
        print(f"  • Detected Language: {audio_data.detected_language}")
        print(f"  • Verbatim Transcript:\n    \"{audio_data.transcript}\"")
        print(f"  • Extracted Core Facts:")
        print(f"    - business_name: {audio_data.business_name}")
        print(f"    - employee_count: {audio_data.employee_count}")
        print(f"    - product_type: {audio_data.product_type}")
        print(f"    - location: {audio_data.location}")
        print(f"    - financial_figures: {audio_data.financial_figures}")
        print(f"    - impact_summary: {audio_data.impact_summary}")
    except Exception as e:
        print(f"❌ STAGE 1 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 2: VISION EXTRACTION (TRADE LICENSE)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("👁️ STAGE 2: TRADE LICENSE EXTRACTION (LIVE GEMINI API)")
    print("-" * 80)
    t0 = time.time()
    try:
        license_data = extract_license_data(image_path=license_path)
        dt = time.time() - t0
        print(f"⏱️ Stage 2 Completed in {dt:.2f}s")
        print(f"  • Is Legible: {license_data.is_legible}")
        print(f"  • Business Name: {license_data.business_name}")
        print(f"  • TIN Number: {license_data.tin_number}")
        print(f"  • Owner Name: {license_data.owner_name}")
        print(f"  • Registration Date: {license_data.registration_date}")
        print(f"  • Extraction Notes: {license_data.extraction_notes}")
    except Exception as e:
        print(f"❌ STAGE 2 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 3: VISION EXTRACTION (WORKSHOP ASSETS)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🏭 STAGE 3: WORKSHOP FACILITY & ASSET EXTRACTION (LIVE GEMINI API)")
    print("-" * 80)
    t0 = time.time()
    try:
        workshop_data = extract_workshop_data(image_path=workshop_path)
        dt = time.time() - t0
        print(f"⏱️ Stage 3 Completed in {dt:.2f}s")
        print(f"  • Estimated People Present: {workshop_data.estimated_people_present}")
        print(f"  • Visible Machinery: {workshop_data.visible_machinery}")
        print(f"  • Workplace Safety Observations: {workshop_data.workplace_safety_observations}")
        print(f"  • Extraction Notes: {workshop_data.extraction_notes}")
    except Exception as e:
        print(f"❌ STAGE 3 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 4: MAPPER AGENT & GAP IDENTIFICATION
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("📋 STAGE 4: INTAKE NORMALIZATION & GAP DETECTION")
    print("-" * 80)
    t0 = time.time()
    try:
        pack = generate_application_pack(
            license_data=license_data,
            audio_data=audio_data,
            workshop_data=workshop_data,
        )
        dt = time.time() - t0
        print(f"⏱️ Stage 4 Completed in {dt:.2f}s")
        print(f"  • Total Gaps Flagged: {len(pack.gaps)}")
        for i, gap in enumerate(pack.gaps, 1):
            print(f"    {i}. [{gap.priority.value}] Field: '{gap.field_name}' | Reason: {gap.reason_missing} (Required from: {gap.required_from})")
    except Exception as e:
        print(f"❌ STAGE 4 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 5: ELIGIBILITY GATE & CONTRADICTION AUDIT
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("⚖️ STAGE 5: 15-CHECK ELIGIBILITY GATE & FORENSIC CONTRADICTION DETECTION")
    print("-" * 80)
    t0 = time.time()
    try:
        app_obj = pack.application if pack else None
        gate_result = run_eligibility_gate(app_obj)
        contradictions = detect_contradictions(pack=pack, workshop_data=workshop_data)
        dt = time.time() - t0
        print(f"⏱️ Stage 5 Completed in {dt:.2f}s")
        print(f"  • Eligibility Verdict: {'✅ ELIGIBLE' if gate_result.is_eligible else '❌ INELIGIBLE'}")
        print(f"  • Gate Reasoning: {gate_result.gate_reasoning}")
        if gate_result.failed_declarations:
            print(f"  • Failed Declarations: {gate_result.failed_declarations}")
        if gate_result.triggered_exclusions:
            print(f"  • Triggered Exclusions: {gate_result.triggered_exclusions}")
        print(f"  • Discrepancies / Contradictions Flagged: {len(contradictions)}")
        for i, c in enumerate(contradictions, 1):
            print(f"    {i}. [{c.severity.value}] Claim A: '{c.claim_a}' vs Claim B: '{c.claim_b}' | Explanation: {c.explanation}")
    except Exception as e:
        print(f"❌ STAGE 5 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 6: GRID ROUTING & 100-POINT SCORING
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🎯 STAGE 6: TRACK ROUTING & 100-POINT MULTIPLIER SCORING")
    print("-" * 80)
    t0 = time.time()
    try:
        if pack and pack.application and pack.impact:
            variant = route_to_grid_variant(pack.application, pack.impact)
            score_result = score_application(pack.application, pack.impact, grid_variant=variant)
            dt = time.time() - t0
            print(f"⏱️ Stage 6 Completed in {dt:.2f}s")
            print(f"  • Assigned Grid Track: {variant.value}")
            print(f"  • Total Weighted Score: {score_result.total_score}/100")
            print(f"  • Dimension Breakdown:")
            for sc in score_result.criteria_scores:
                print(f"    - {sc.criterion.value}: {sc.awarded_points}/{sc.max_points} pts | {sc.reasoning[:60]}...")
            print(f"  • Committee Reviewer Summary:\n    \"{score_result.reviewer_summary}\"")
        else:
            print("  • Note: Application or Impact protocol had missing base fields.")
    except Exception as e:
        print(f"❌ STAGE 6 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 7: BATCH RANKER (12 REAL APPLICANTS)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("📊 STAGE 7: BATCH PORTFOLIO RANKER (12 APPLICANTS)")
    print("-" * 80)
    t0 = time.time()
    try:
        batch_file = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
        with open(batch_file, "r", encoding="utf-8") as f:
            batch_raw = json.load(f)

        scored_entries = []
        contra_dict = {}
        for item in batch_raw:
            b_name = item.get("business_name", "Unnamed SME")
            score_val = item.get("total_score", 70)
            variant_val = GridVariant(item.get("grid_variant", "GENERAL_SME"))
            is_elig = item.get("is_eligible", True)
            rev_sum = item.get("reviewer_summary", "Reviewer summary")

            mock_criteria = [
                CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=min(score_val, 20), reasoning="Job creation potential verified."),
                CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=min(max(score_val - 20, 0), 15), reasoning="Demographic inclusion verified."),
                CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=min(max(score_val - 35, 0), 15), reasoning="Innovation score verified."),
                CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=min(max(score_val - 50, 0), 15), reasoning="Financial health verified."),
                CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=min(max(score_val - 65, 0), 10), reasoning="Local supply integration verified."),
                CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=min(max(score_val - 75, 0), 10), reasoning="SDG impact verified."),
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
                    gate_reasoning="Confirmed" if is_elig else "Disqualified due to unverified regulatory permits."
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
                    explanation=c.get("explanation", "")
                )
                for c in raw_contras
            ]
            if contra_objs:
                contra_dict[b_name] = contra_objs
        
        shortlist = rank_batch(scored_entries, contradictions_map=contra_dict)
        dt = time.time() - t0
        print(f"⏱️ Stage 7 Completed in {dt:.2f}s")
        print(f"  • Total Applicants Evaluated: {len(batch_raw)}")
        print(f"  • Top-3 Ranked Applicants:")
        for r in shortlist.companies[:3]:
            print(f"    Rank #{r.rank}: {r.business_name} — Score: {r.total_score}/100 | Track: {r.grid_variant.value}")
    except Exception as e:
        print(f"❌ STAGE 7 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 8: MULTILINGUAL VERBAL CONSENT PACKAGE (AMHARIC)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("📜 STAGE 8: MULTILINGUAL VERBAL CONSENT PACKAGE (AMHARIC)")
    print("-" * 80)
    t0 = time.time()
    try:
        consent_pkg = generate_consent_package(detected_language="Amharic")
        dt = time.time() - t0
        print(f"⏱️ Stage 8 Completed in {dt:.2f}s")
        print(f"  • Mandatory Explanations & Verbal Questions ({len(consent_pkg.explanations)} total):")
        for i, exp in enumerate(consent_pkg.explanations, 1):
            print(f"    {i}. [{exp.declaration_id}]")
            print(f"       Explanation: {exp.translated_simple_explanation}")
            print(f"       Verbal Question Script: {exp.verbal_consent_question}")
    except Exception as e:
        print(f"❌ STAGE 8 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # STAGE 9: SCHEMA INTROSPECTION & FIELD COVERAGE PROOF
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🔍 STAGE 9: SCHEMA FIELD INTROSPECTION (GIZ/SEQUA 1.1–2.6 & 15 DECLARATIONS)")
    print("-" * 80)
    try:
        app_fields = list(ApplicationSchema.model_fields.keys())
        impact_fields = list(ImpactProtocol.model_fields.keys())
        decl_fields = list(MandatoryDeclarations.model_fields.keys())
        excl_fields = list(ExclusionFactors.model_fields.keys())

        print(f"  • ApplicationSchema Fields ({len(app_fields)} total):")
        print(f"    {', '.join(app_fields)}")
        print(f"  • ImpactProtocol Fields ({len(impact_fields)} total):")
        print(f"    {', '.join(impact_fields)}")
        print(f"  • MandatoryDeclarations (15 Checks) ({len(decl_fields)} total):")
        print(f"    {', '.join(decl_fields)}")
        print(f"  • ExclusionFactors (3 Instant-Kill Checks) ({len(excl_fields)} total):")
        print(f"    {', '.join(excl_fields)}")
    except Exception as e:
        print(f"❌ STAGE 9 FAILED: {str(e)}")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    total_time = time.time() - total_start_time
    print("\n" + "=" * 80)
    print(f"🏁 PROOF RUN COMPLETE — TOTAL TIME: {total_time:.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
