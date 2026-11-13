"""GitHub Issues integration for creating fix requests automatically from SEMAR reviews."""

from typing import Dict, Any, List, Optional

import httpx

from app.utils.config import (
    GITHUB_DISPATCH_TOKEN,
    GITHUB_REPO_OWNER,
    GITHUB_REPO_NAME,
    SEMAR_WEB_URL,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _build_issue_body(
    assessment: Dict[str, Any],
    reviewer: str,
    reason: str,
    selected_fids: List[str],
) -> str:
    target_version = assessment.get("target_version", "-")
    platform = assessment.get("platform_type", "esp32")
    source = assessment.get("source") or {}
    ai = assessment.get("ai_result") or {}
    findings = assessment.get("findings") or []

    if selected_fids:
        chosen = [f for f in findings if f.get("fid") in set(selected_fids)]
    else:
        chosen = [f for f in findings if f.get("severity") in ("critical", "high", "medium")][:15]

    lines = [
        f"## SEMAR OTA Security Review — Fix Requested",
        "",
        f"- **Firmware Version:** `{target_version}` (`{platform}`)",
        f"- **Git Commit:** `{source.get('git_commit') or '-'}`",
        f"- **Assessment ID:** `{assessment.get('_id')}`",
        f"- **Policy Profile:** `{(assessment.get('policy_result') or {}).get('profile', 'lab')}`",
        f"- **Final Decision:** `{assessment.get('final_decision')}`",
        f"- **Reviewer:** `{reviewer}`",
        f"- **SEMAR Link:** {SEMAR_WEB_URL}/security-assessment/{assessment.get('_id')}",
        "",
        "### Reviewer Notes",
        reason,
        "",
    ]

    if ai.get("summary"):
        lines.extend(["### AI Risk Summary", ai["summary"], ""])

    if chosen:
        lines.append("### Findings to Fix")
        for f in chosen:
            loc = f.get("location") or {}
            loc_str = f"`{loc.get('file')}:{loc.get('line') or '?'}`" if loc.get("file") else "-"
            comp = f.get("component") or {}
            comp_str = f"`{comp.get('name')}@{comp.get('version') or '?'}`" if comp.get("name") else ""
            lines.append(
                f"- **[{str(f.get('severity', 'medium')).upper()}]** `{f.get('fid')}` — "
                f"{f.get('title') or f.get('rule_id')} ({loc_str} {comp_str})".strip()
            )
        lines.append("")

    mitigations = ai.get("mitigations") or []
    if mitigations:
        lines.append("### Recommended Mitigations (AI)")
        for m in mitigations[:10]:
            target = f" (`{m['target']}`)" if m.get("target") else ""
            lines.append(f"{m.get('priority', 1)}. {m.get('action')}{target}")
        lines.append("")

    return "\n".join(lines)


async def create_fix_issue(
    assessment: Dict[str, Any],
    reviewer: str,
    reason: str,
    selected_fids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a GitHub issue on the firmware repository; fail softly if token is unconfigured."""
    source = assessment.get("source") or {}
    repo_full = source.get("repo") or f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
    if "/" not in repo_full:
        repo_full = f"{GITHUB_REPO_OWNER}/{repo_full}"

    title = f"[OTA Security Review] Fix required for {assessment.get('target_version')} ({assessment.get('platform_type', 'esp32')})"
    body = _build_issue_body(assessment, reviewer, reason, selected_fids or [])

    if not GITHUB_DISPATCH_TOKEN or "please change" in GITHUB_DISPATCH_TOKEN.lower():
        logger.warning("GITHUB_DISPATCH_TOKEN not configured; skipping remote GitHub issue creation")
        return {"created": False, "error": "GITHUB_DISPATCH_TOKEN not configured"}

    url = f"https://api.github.com/repos/{repo_full}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_DISPATCH_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": title,
        "body": body,
        "labels": ["security", "ota-review"],
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "created": True,
                    "number": data.get("number"),
                    "url": data.get("html_url"),
                }
            # Fallback if repo lacks custom labels
            if resp.status_code == 422:
                payload.pop("labels", None)
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "created": True,
                        "number": data.get("number"),
                        "url": data.get("html_url"),
                    }
            logger.error(f"GitHub issue creation failed ({resp.status_code}): {resp.text}")
            return {"created": False, "error": f"GitHub API {resp.status_code}"}
    except Exception as exc:
        logger.error(f"GitHub issue request exception: {exc}")
        return {"created": False, "error": str(exc)}

