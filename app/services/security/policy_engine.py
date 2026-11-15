"""Deterministic YAML-driven security policy engine (lab / production profiles)."""

import os
from typing import Dict, Any, List, Optional

import yaml

from app.services.security.decision import max_decision
from app.utils.config import SECURITY_POLICY_PROFILE

POLICIES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "security_policies")
)


def load_policy(profile: Optional[str] = None) -> Dict[str, Any]:
    """Load policy YAML for the selected profile ('lab' or 'production')."""
    selected = (profile or SECURITY_POLICY_PROFILE or "lab").strip().lower()
    if selected not in ("lab", "production"):
        selected = "lab"
    path = os.path.join(POLICIES_DIR, f"{selected}.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _matches_any_condition(finding: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    if "cvss_gte" in cond:
        cvss = finding.get("cvss")
        if cvss is not None and float(cvss) >= float(cond["cvss_gte"]):
            return True
    if "epss_gte" in cond:
        epss = finding.get("epss")
        if epss is not None and float(epss) >= float(cond["epss_gte"]):
            return True
    if cond.get("kev") is True and finding.get("kev") is True:
        return True
    return False


def _finding_matches_rule(finding: Dict[str, Any], match_cfg: Dict[str, Any]) -> bool:
    if finding.get("reachable") is False:
        return False
    if "category" in match_cfg and finding.get("category") != match_cfg["category"]:
        return False
    if "rule_ids" in match_cfg and finding.get("rule_id") not in match_cfg["rule_ids"]:
        return False
    if "severities" in match_cfg and finding.get("severity") not in match_cfg["severities"]:
        return False
    if "any_of" in match_cfg:
        if not any(_matches_any_condition(finding, c) for c in match_cfg["any_of"]):
            return False
    return True


def evaluate_policy(
    findings: List[Dict[str, Any]],
    summary: Dict[str, Any],
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate normalized findings and summary against deterministic policy rules."""
    policy = load_policy(profile)
    final_decision = "PASS"
    triggered_rules: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    for rule in policy.get("rules") or []:
        match_cfg = rule.get("match") or {}
        matched_fids: List[str] = []

        if "metric" in match_cfg:
            if match_cfg["metric"] == "sbom_coverage_lt":
                cov = float(summary.get("sbom_coverage", 0.0))
                if summary.get("components", 0) > 0 and cov < float(match_cfg.get("value", 90.0)):
                    matched_fids = ["METRIC:sbom_coverage"]
        else:
            matched_fids = [
                f["fid"] for f in findings if _finding_matches_rule(f, match_cfg)
            ]

        if not matched_fids:
            continue

        entry = {
            "rule_id": rule["id"],
            "description": rule.get("description", ""),
            "decision": rule.get("decision", "REVIEW_REQUIRED"),
            "matched_count": len(matched_fids),
            "sample_fids": matched_fids[:10],
        }
        if rule.get("warning"):
            warnings.append(entry)
        else:
            triggered_rules.append(entry)
            final_decision = max_decision(final_decision, entry["decision"])

    return {
        "profile": policy.get("profile", profile or SECURITY_POLICY_PROFILE),
        "decision": final_decision,
        "triggered_rules": triggered_rules,
        "warnings": warnings,
    }

