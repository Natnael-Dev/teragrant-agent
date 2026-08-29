"""
TeraGrant Agents Package.
Contains intelligent intake mapping, deterministic eligibility vetting,
grid routing, 100-point evaluation scoring, contradiction detection,
batch ranking, and multilingual consent explanation agents.
"""

from .mapper_agent import generate_application_pack
from .eligibility_agent import run_eligibility_gate
from .router_agent import route_to_grid_variant
from .scorer_agent import score_application
from .contradiction_agent import detect_contradictions
from .batch_ranker_agent import rank_batch
from .declaration_explainer_agent import generate_consent_package

__all__ = [
    "generate_application_pack",
    "run_eligibility_gate",
    "route_to_grid_variant",
    "score_application",
    "detect_contradictions",
    "rank_batch",
    "generate_consent_package",
]
