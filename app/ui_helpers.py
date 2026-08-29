"""
Deterministic UI Helpers for TeraGrant Agent (Batch 24).
Pure functions for calculating evidence percentages, row status, and KPI statistics.
"""

from typing import Dict, Any, List


def evidence_pct(provenance: Dict[str, Any]) -> int:
    """
    Calculates percentage of verified fields out of total non-missing fields in provenance ledger.
    """
    if not provenance:
        return 0
    total = 0
    verified = 0
    for prov in provenance.values():
        status = prov.get("status") if isinstance(prov, dict) else getattr(prov, "status", None)
        status_str = getattr(status, "value", str(status))
        if status_str != "MISSING":
            total += 1
            if status_str in ("DOCUMENT_VERIFIED", "VERIFIED"):
                verified += 1
    if total == 0:
        return 0
    return int(round((verified / total) * 100))


def row_status(eligible: bool, score: int) -> str:
    """
    Determines shortlist table status:
    - 'Shortlisted' if eligible and score >= 70
    - 'Reviewed' if eligible and 55 <= score < 70
    - 'Pending' otherwise
    """
    if eligible:
        if score >= 70:
            return "Shortlisted"
        elif score >= 55:
            return "Reviewed"
    return "Pending"


def kpi_stats(batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes summary KPI stats for the Reviewer Dashboard:
    - total_applications
    - eligible (green)
    - ineligible (red)
    - needs_review (amber)
    - average_score (blue, integer / 100)
    - contradictions (red count)
    """
    if not batch_results:
        return {
            "total_applications": 0,
            "eligible": 0,
            "ineligible": 0,
            "needs_review": 0,
            "average_score": 0,
            "contradictions": 0,
        }
    total = len(batch_results)
    eligible = 0
    ineligible = 0
    needs_review = 0
    scores = []
    total_contras = 0

    for item in batch_results:
        is_elig = item.get("is_eligible", True)
        score = item.get("total_score", 0)
        scores.append(score)
        contras = item.get("contradictions", [])
        total_contras += len(contras)

        if not is_elig:
            ineligible += 1
        elif score >= 70 and not contras:
            eligible += 1
        else:
            needs_review += 1

    avg_score = int(round(sum(scores) / len(scores))) if scores else 0

    return {
        "total_applications": total,
        "eligible": eligible,
        "ineligible": ineligible,
        "needs_review": needs_review,
        "average_score": avg_score,
        "contradictions": total_contras,
    }
