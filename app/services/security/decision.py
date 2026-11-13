"""Monotonic decision merge and workflow state utilities."""

from typing import Optional, Tuple

DECISION_RANK = {
    "PASS": 0,
    "REVIEW_REQUIRED": 1,
    "BLOCKED": 2,
}


def max_decision(a: str, b: str) -> str:
    """Return the stricter of two decisions."""
    return a if DECISION_RANK.get(a, 1) >= DECISION_RANK.get(b, 1) else b


def merge_policy_and_ai(
    policy_decision: str,
    ai_recommended_decision: Optional[str],
) -> Tuple[str, str]:
    """Combine authoritative deterministic policy with advisory AI recommendation.

    Monotonic escalation rule:
    - AI can never downgrade a policy decision (BLOCKED/REVIEW_REQUIRED stays).
    - If policy == PASS and AI recommends REVIEW_REQUIRED or BLOCKED, escalate
      only to REVIEW_REQUIRED (AI never unilaterally triggers BLOCKED).
    """
    if policy_decision not in DECISION_RANK:
        policy_decision = "REVIEW_REQUIRED"

    if not ai_recommended_decision or ai_recommended_decision not in DECISION_RANK:
        return policy_decision, "policy"

    if policy_decision == "PASS" and ai_recommended_decision in ("REVIEW_REQUIRED", "BLOCKED"):
        return "REVIEW_REQUIRED", "ai_escalation"

    return policy_decision, "policy"


def workflow_state_for_decision(final_decision: str) -> str:
    """Map an automated final decision to initial workflow_state."""
    mapping = {
        "PASS": "auto_passed",
        "REVIEW_REQUIRED": "awaiting_review",
        "BLOCKED": "blocked",
    }
    return mapping.get(final_decision, "awaiting_review")

