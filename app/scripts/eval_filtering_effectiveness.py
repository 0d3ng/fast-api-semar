"""Evaluation 1: Multi-Stage Filtering Effectiveness Statistics for SEMAR Firmware Security Gate.

Usage:
    python -m app.scripts.eval_filtering_effectiveness
    python -m app.scripts.eval_filtering_effectiveness --out-dir logs/evaluation
"""

import argparse
import asyncio
import csv
import json
import os
from collections import Counter
from typing import Any, Dict, List

from app.services.security.ai_analyzer import _build_context_payload
from app.utils.db import db

DEFAULT_OUT_DIR = os.path.join("logs", "evaluation")


def _pct_reduction(before: float, after: float) -> float:
    if before <= 0:
        return 0.0
    return round(((before - after) / before) * 100.0, 2)


def _pct_ratio(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _classify_unreachable_reason(hint: str) -> str:
    hl = (hint or "").lower()
    if "ipv6" in hl or "lwip" in hl:
        return "sdkconfig_feature_disabled (IPv6)"
    if "bluetooth" in hl or "bt" in hl:
        return "sdkconfig_feature_disabled (Bluetooth)"
    if "arm cortex-m" in hl or "mpu" in hl or "trustzone" in hl:
        return "arch_mismatch (ARM Cortex-M MPU on ESP32)"
    if "ubuntu" in hl or "d-bus" in hl:
        return "os_mismatch (Linux D-Bus on RTOS)"
    if "false positive" in hl or "human review" in hl:
        return "human_review_fp_inheritance"
    return "other"


def _legacy_unoptimized_prompt_chars(doc: Dict[str, Any]) -> int:
    """Reconstruct legacy prompt size before optimization (40 findings, raw diff list, full descriptions)."""
    findings = doc.get("findings") or []
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    non_low = [f for f in findings if str(f.get("severity") or "medium").lower() not in ("low", "info")]
    non_low.sort(
        key=lambda f: (
            0 if f.get("reachable", True) is not False else 1,
            sev_rank.get(str(f.get("severity") or "medium").lower(), 2),
        )
    )
    selected = non_low[:40]
    payload = {
        "release_context": {
            **(doc.get("source") or {}),
            "target_version": doc.get("target_version"),
            "platform_type": doc.get("platform_type"),
        },
        "policy_baseline": doc.get("policy_result") or {},
        "summary": doc.get("summary") or {},
        "diff_vs_previous": doc.get("diff_vs_previous"),
        "findings": selected,
    }
    return len(json.dumps(payload, ensure_ascii=False, sort_keys=True))


async def collect_evaluation() -> Dict[str, Any]:
    """Query MongoDB assessments and compute filtering statistics across builds."""
    docs = await db.ota_security_assessments.find({"deleted_at": None}).sort("inserted_at", 1).to_list(100)
    builds_stats: List[Dict[str, Any]] = []
    unreachable_catalog: List[Dict[str, Any]] = []

    for d in docs:
        findings = d.get("findings") or []
        summary = d.get("summary") or {}
        policy = d.get("policy_result") or {}
        ai = d.get("ai_result") or {}
        diff = d.get("diff_vs_previous") or {}
        source = d.get("source") or {}

        raw_per_tool: Counter = Counter()
        overlap_pairs: Counter = Counter()
        cat_counts: Counter = Counter()
        sev_counts: Counter = Counter()
        sev_reach_counts: Counter = Counter()

        raw_total = 0
        dedup_multi_tool = 0
        for f in findings:
            tools_list = f.get("tools") or ([f.get("tool")] if f.get("tool") else ["unknown"])
            raw_total += len(tools_list)
            for t in tools_list:
                raw_per_tool[str(t)] += 1
            if len(tools_list) > 1:
                dedup_multi_tool += 1
                overlap_pairs["+".join(sorted(set(map(str, tools_list))))] += 1

            cat = str(f.get("category") or "unknown")
            sev = str(f.get("severity") or "medium").lower()
            is_reach = f.get("reachable", True) is not False
            cat_counts[cat] += 1
            sev_counts[sev] += 1
            if is_reach:
                sev_reach_counts[sev] += 1
            else:
                hint = f.get("reachable_hint") or ""
                unreachable_catalog.append({
                    "version": d.get("target_version"),
                    "fid": f.get("fid"),
                    "cve_or_rule": f.get("cve") or f.get("rule_id"),
                    "component": (f.get("component") or {}).get("name"),
                    "severity": sev,
                    "cvss": f.get("cvss"),
                    "reason_category": _classify_unreachable_reason(hint),
                    "hint": hint,
                })

        unique_total = len(findings)
        dedup_removed = raw_total - unique_total
        dedup_rate = _pct_reduction(raw_total, unique_total)

        reach_true = sum(1 for f in findings if f.get("reachable", True) is not False)
        reach_false = sum(1 for f in findings if f.get("reachable") is False)
        reach_reduction_rate = _pct_reduction(unique_total, reach_true)

        crit_high_unique = sev_counts["critical"] + sev_counts["high"]
        crit_high_reach = sev_reach_counts["critical"] + sev_reach_counts["high"]
        crit_high_fp_elim_rate = _pct_reduction(crit_high_unique, crit_high_reach)

        low_info_total = sev_counts["low"] + sev_counts["info"]
        non_low_reach = reach_true - sum(
            1 for f in findings
            if f.get("reachable", True) is not False and str(f.get("severity") or "").lower() in ("low", "info")
        )
        noise_filter_rate = _pct_ratio(low_info_total, unique_total)

        prev_approved_non_low = sum(
            1 for f in findings
            if f.get("reachable", True) is not False
            and str(f.get("severity") or "").lower() not in ("low", "info")
            and f.get("previously_approved") is True
        )
        new_non_low_reach = non_low_reach - prev_approved_non_low
        baseline_reuse_rate = _pct_ratio(prev_approved_non_low, non_low_reach)

        compact_ctx = _build_context_payload(
            source_meta={
                **source,
                "target_version": d.get("target_version"),
                "platform_type": d.get("platform_type"),
            },
            findings=findings,
            summary=summary,
            policy_result=policy,
            diff_vs_previous=diff if diff else None,
        )
        compact_chars = len(json.dumps(compact_ctx, ensure_ascii=False, sort_keys=True))
        legacy_chars = _legacy_unoptimized_prompt_chars(d)
        prompt_findings_count = len(compact_ctx.get("findings") or [])

        unreach_breakdown = Counter(
            _classify_unreachable_reason(f.get("reachable_hint") or "")
            for f in findings if f.get("reachable") is False
        )

        builds_stats.append({
            "version": d.get("target_version"),
            "components": summary.get("components", 0),
            "sbom_coverage": summary.get("sbom_coverage", 0.0),
            "raw_findings_total": raw_total,
            "unique_findings_total": unique_total,
            "dedup_merged_groups": dedup_multi_tool,
            "dedup_removed": dedup_removed,
            "dedup_rate_pct": dedup_rate,
            "raw_per_tool": dict(raw_per_tool),
            "overlap_pairs": dict(overlap_pairs),
            "categories": dict(cat_counts),
            "severities_unique": dict(sev_counts),
            "severities_reachable": dict(sev_reach_counts),
            "reachable_findings": reach_true,
            "unreachable_findings": reach_false,
            "unreachable_breakdown": dict(unreach_breakdown),
            "reachability_reduction_pct": reach_reduction_rate,
            "crit_high_unique": crit_high_unique,
            "crit_high_reachable": crit_high_reach,
            "crit_high_fp_elim_pct": crit_high_fp_elim_rate,
            "low_info_noise_count": low_info_total,
            "noise_filter_pct": noise_filter_rate,
            "non_low_reachable": non_low_reach,
            "prev_approved_non_low": prev_approved_non_low,
            "new_non_low_reachable": new_non_low_reach,
            "baseline_reuse_pct": baseline_reuse_rate,
            "diff_new": len(diff.get("new") or []),
            "diff_resolved": len(diff.get("resolved") or []),
            "diff_persisting": len(diff.get("persisting") or []),
            "inherited_fp_count": diff.get("inherited_fp_count"),
            "prompt_findings_sent": prompt_findings_count,
            "prompt_item_reduction_vs_raw_pct": _pct_reduction(raw_total, prompt_findings_count),
            "legacy_prompt_chars": legacy_chars,
            "compact_prompt_chars": compact_chars,
            "prompt_char_compression_pct": _pct_reduction(legacy_chars, compact_chars),
            "policy_decision": policy.get("decision"),
            "ai_status": ai.get("status"),
            "ai_decision": ai.get("recommended_decision"),
            "ai_latency_ms": ai.get("latency_ms"),
            "ai_tokens_total": (ai.get("tokens") or {}).get("prompt", 0) + (ai.get("tokens") or {}).get("completion", 0),
            "grounding_ok": (ai.get("validation") or {}).get("grounding_ok"),
            "final_decision": d.get("final_decision"),
            "decision_source": d.get("decision_source"),
            "workflow_state": d.get("workflow_state"),
        })

    return {"builds": builds_stats, "unreachable_catalog": unreachable_catalog}


def write_outputs(data: Dict[str, Any], out_dir: str = DEFAULT_OUT_DIR) -> str:
    """Write JSON, CSV, LaTeX, and Markdown summary files and return the JSON path."""
    os.makedirs(out_dir, exist_ok=True)
    builds = data["builds"]

    json_path = os.path.join(out_dir, "filtering_evaluation_stats.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(out_dir, "filtering_summary.csv")
    csv_fields = [
        "version", "components", "sbom_coverage",
        "raw_findings_total", "unique_findings_total", "dedup_removed", "dedup_rate_pct",
        "reachable_findings", "unreachable_findings", "reachability_reduction_pct",
        "crit_high_unique", "crit_high_reachable", "crit_high_fp_elim_pct",
        "low_info_noise_count", "noise_filter_pct",
        "non_low_reachable", "prev_approved_non_low", "new_non_low_reachable", "baseline_reuse_pct",
        "prompt_findings_sent", "prompt_item_reduction_vs_raw_pct",
        "legacy_prompt_chars", "compact_prompt_chars", "prompt_char_compression_pct",
        "policy_decision", "ai_decision", "final_decision", "decision_source", "workflow_state",
        "ai_latency_ms", "ai_tokens_total",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for b in builds:
            writer.writerow({k: b.get(k) for k in csv_fields})

    tex_path = os.path.join(out_dir, "filtering_latex_tables.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Auto-generated LaTeX Table: Multi-Stage Filtering Funnel across Firmware Builds\n")
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write("\\caption{Multi-Stage Security Finding Filtering Effectiveness Across Firmware Builds}\n")
        f.write("\\label{tab:filtering-funnel}\n")
        f.write("\\resizebox{\\linewidth}{!}{%\n")
        f.write("\\begin{tabular}{lrrrrrrrrl}\n\\hline\n")
        f.write("Build & Comp. & Cov.(\\%) & Raw & Dedup & Unreach. & Crit/High & Non-Low & LLM Ctx & Final Gate \\\\\n")
        f.write(" & & & & & & (Raw$\\rightarrow$Reach) & Reach. & (Items / Chars) & Decision \\\\\n\\hline\n")
        for b in builds:
            short_ver = b["version"].split("-")[-1]
            f.write(
                f"{short_ver} & {b['components']} & {b['sbom_coverage']:.2f} & "
                f"{b['raw_findings_total']} & {b['unique_findings_total']} (-{b['dedup_rate_pct']:.1f}\\%) & "
                f"{b['unreachable_findings']} & {b['crit_high_unique']}$\\rightarrow${b['crit_high_reachable']} & "
                f"{b['non_low_reachable']} & {b['prompt_findings_sent']} / {b['compact_prompt_chars']} & "
                f"{b['final_decision']} \\\\\n"
            )
        f.write("\\hline\n\\end{tabular}}\n\\end{table}\n")

    md_path = os.path.join(out_dir, "filtering_evaluation_report.md")
    lines: List[str] = ["# Evaluation 1: Multi-Stage Filtering Effectiveness Report\n"]
    lines.append("| Build | Komponen | SBOM Cov. | Raw | Unik (Dedup) | Unreachable | Crit/High (Raw -> Reach) | Non-Low Reach. | Prompt (Item / Chars) | Final |")
    lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: | :---: |")
    for b in builds:
        short = b["version"].split("-")[-1]
        lines.append(
            f"| {short} | {b['components']} | {b['sbom_coverage']}% | {b['raw_findings_total']} | "
            f"{b['unique_findings_total']} (-{b['dedup_rate_pct']}%) | {b['unreachable_findings']} | "
            f"{b['crit_high_unique']} -> {b['crit_high_reachable']} (-{b['crit_high_fp_elim_pct']}%) | "
            f"{b['non_low_reachable']} | {b['prompt_findings_sent']} / {b['compact_prompt_chars']} | **{b['final_decision']}** |"
        )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Saved evaluation files to {os.path.abspath(out_dir)}:")
    for p in (json_path, csv_path, tex_path, md_path):
        print(f" - {p}")
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract SEMAR security filtering statistics.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Output directory (default: logs/evaluation)")
    args = parser.parse_args()

    data = asyncio.get_event_loop().run_until_complete(collect_evaluation())
    write_outputs(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
