"""
TeraGrant Agents Package.
Contains intelligent intake mapping, deterministic eligibility vetting,
grid routing, 100-point evaluation scoring, contradiction detection,
batch ranking, and multilingual consent explanation agents.
"""

from .mapper_agent import generate_application_pack
from .eligibility_agent import run_eligibility_gate
from .router_agent import route_to_grid_variant
from .scorer_agent import (
    score_application,
    compare_grid_variants,
    score_sensitivity,
    submission_readiness,
    reproducibility_check,
)
from .contradiction_agent import detect_contradictions
from .batch_ranker_agent import rank_batch
from .declaration_explainer_agent import generate_consent_package
from .consent_agent import (
    record_consent,
    revoke_consent,
    evaluate_verdict,
    sync_declarations_from_consent_records,
)
from .impact_builder import (
    build_impact_protocol,
    IMPACT_QUESTIONS,
)
from .intake_orchestrator import run_intake_parallel
from .interview_agent import (
    INTERVIEW_STEPS,
    extract_answer,
    merge_answer,
    synthesize_audio_extraction,
)

__all__ = [
    "generate_application_pack",
    "run_eligibility_gate",
    "route_to_grid_variant",
    "score_application",
    "compare_grid_variants",
    "score_sensitivity",
    "submission_readiness",
    "reproducibility_check",
    "detect_contradictions",
    "rank_batch",
    "generate_consent_package",
    "record_consent",
    "revoke_consent",
    "evaluate_verdict",
    "sync_declarations_from_consent_records",
    "build_impact_protocol",
    "IMPACT_QUESTIONS",
    "run_intake_parallel",
    "INTERVIEW_STEPS",
    "extract_answer",
    "merge_answer",
    "synthesize_audio_extraction",
]
