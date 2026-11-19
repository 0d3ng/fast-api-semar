"""Evaluation 2: Qwen3:8B Hyperparameter, Hallucination/Grounding, Consistency & Mode Sensitivity.

Read-only benchmark against local Ollama (`qwen3:8b`) using real SEMAR firmware
assessments from MongoDB. Never modifies database documents.

Usage:
    python -m app.scripts.eval_qwen3_sensitivity
    python -m app.scripts.eval_qwen3_sensitivity --repeats 3 --out-dir logs/evaluation
"""

import argparse
import asyncio
import csv
import json
import os
import statistics
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.schemas.ota_security_assessment_schema import AiAnalysisOutput
from app.services.security.ai_analyzer import (
    SYSTEM_PROMPT,
    _prioritize_findings_for_prompt,
    validate_and_ground_output,
)
from app.utils.config import LLM_BASE_URL, LLM_NUM_CTX
from app.utils.db import db

DEFAULT_OUT_DIR = os.path.join("logs", "evaluation")
DEFAULT_MODEL = "qwen3:8b"


def _build_custom_context(
    doc: Dict[str, Any],
    max_findings: int,
    compact_diff: bool = True,
    trim_fields: bool = True,
) -> Dict[str, Any]:
    """Build LLM context payload with configurable Top-K findings and compaction."""
    findings = doc.get("findings") or []
    summary = doc.get("summary") or {}
    policy = doc.get("policy_result") or {}
    diff = doc.get("diff_vs_previous")
    source = doc.get("source") or {}

    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    non_low = [f for f in findings if str(f.get("severity") or "medium").lower() not in ("low", "info")]
    low_items = [f for f in findings if str(f.get("severity") or "").lower() in ("low", "info")]

    def _tier(f: Dict[str, Any]) -> int:
        sev = str(f.get("severity") or "medium").lower()
        is_reach = f.get("reachable", True) is not False
        is_new = not f.get("previously_approved", False)
        if sev in ("critical", "high") and is_reach:
            return 0 if is_new else 1
        if sev in ("critical", "high") and not is_reach:
            return 2 if is_new else 3
        if is_reach:
            return 4 if is_new else 5
        return 6

    non_low.sort(
        key=lambda f: (
            _tier(f),
            sev_rank.get(str(f.get("severity") or "medium").lower(), 2),
            0 if f.get("category") in ("secret", "code", "config") else 1,
        )
    )
    selected = non_low[:max_findings]
    if len(selected) < max_findings:
        selected.extend(low_items[: max_findings - len(selected)])
    omitted_low = max(0, len(low_items) - max(0, len(selected) - len(non_low)))

    compact_findings = []
    for f in selected:
        desc = f.get("description")
        snip = f.get("snippet")
        if trim_fields:
            desc = (desc or "")[:220] or None
            snip = (snip or "")[:240] or None
        compact_findings.append({
            "fid": f["fid"],
            "category": f.get("category"),
            "tools": f.get("tools", [f.get("tool")]),
            "rule_id": f.get("rule_id"),
            "cve": f.get("cve"),
            "cwe": f.get("cwe"),
            "severity": f.get("severity"),
            "cvss": f.get("cvss"),
            "epss": f.get("epss"),
            "kev": f.get("kev", False),
            "reachable": f.get("reachable", True),
            "reachable_hint": f.get("reachable_hint"),
            "previously_approved": bool(f.get("previously_approved", False)),
            "title": f.get("title"),
            "description": desc,
            "component": f.get("component"),
            "location": f.get("location"),
            "snippet": snip,
        })

    if compact_diff and isinstance(diff, dict):
        diff_block: Any = {
            "previous_version": diff.get("previous_version"),
            "previous_human_approved": bool(diff.get("previous_human_approved", False)),
            "inherited_fp_count": diff.get("inherited_fp_count", 0),
            "new_count": diff.get("new_count", len(diff.get("new", []) or [])),
            "resolved_count": diff.get("resolved_count", len(diff.get("resolved", []) or [])),
            "persisting_count": diff.get("persisting_count", len(diff.get("persisting", []) or [])),
        }
    else:
        diff_block = diff

    return {
        "release_context": {
            "target_version": doc.get("target_version"),
            "platform_type": doc.get("platform_type", "esp32"),
            "idf_version": source.get("idf_version"),
            "ota_protocol": source.get("ota_protocol"),
            "sdkconfig_flags": source.get("sdkconfig_flags") or {},
            "crypto_controls": "SHA-256 firmware hash + ED25519 manifest signature verified on end-device",
        },
        "policy_baseline": {
            "profile": policy.get("profile"),
            "decision": policy.get("decision"),
            "triggered_rules": policy.get("triggered_rules", []),
        },
        "summary": summary,
        "omitted_low_noise_count": omitted_low,
        "diff_vs_previous": diff_block,
        "findings": compact_findings,
    }


def _count_cited_fids(raw_content: str) -> Tuple[int, int]:
    """Return (total_cited_fids, valid_json_flag) from raw LLM JSON text."""
    try:
        parsed = json.loads(raw_content)
        if not isinstance(parsed, dict):
            return 0, 0
        total = 0
        for item in parsed.get("triage") or []:
            if isinstance(item, dict) and item.get("fid"):
                total += 1
        for corr in parsed.get("correlations") or []:
            if isinstance(corr, dict):
                total += len(corr.get("finding_fids") or [])
        for mit in parsed.get("mitigations") or []:
            if isinstance(mit, dict):
                total += len(mit.get("finding_fids") or [])
        return total, 1
    except Exception:
        return 0, 0


async def _call_ollama_trial(
    base_url: str,
    model: str,
    user_prompt: str,
    valid_fids: set,
    temperature: float = 0.0,
    seed: Optional[int] = 42,
    think: bool = False,
    use_schema: bool = True,
    timeout_s: float = 120.0,
) -> Dict[str, Any]:
    """Run a single controlled Ollama inference trial and evaluate schema & grounding."""
    schema = AiAnalysisOutput.model_json_schema()
    options: Dict[str, Any] = {
        "temperature": temperature,
        "num_ctx": int(LLM_NUM_CTX),
    }
    if seed is not None:
        options["seed"] = seed

    payload: Dict[str, Any] = {
        "model": model,
        "stream": False,
        "options": options,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    if use_schema:
        payload["format"] = schema
    if "qwen3" in model.lower():
        payload["think"] = think

    prompt_chars = len(SYSTEM_PROMPT) + len(user_prompt)
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        latency_ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        err = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
        return {
            "status": "error",
            "error": err,
            "prompt_chars": prompt_chars,
            "latency_ms": latency_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "schema_ok": False,
            "grounding_ok": False,
            "cited_fids": 0,
            "rejected_items": 0,
            "hallucination_rate_pct": 0.0,
            "recommended_decision": None,
            "overall_risk": None,
            "triage_count": 0,
            "mitigations_count": 0,
        }

    raw_content = (data.get("message") or {}).get("content") or ""
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    cited_fids, _ = _count_cited_fids(raw_content)

    try:
        output, val_meta = validate_and_ground_output(raw_content, valid_fids)
        rejected = int(val_meta.get("rejected_items") or 0)
        hall_rate = round((rejected / cited_fids) * 100.0, 2) if cited_fids > 0 else 0.0
        return {
            "status": "ok",
            "error": None,
            "prompt_chars": prompt_chars,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "schema_ok": True,
            "grounding_ok": bool(val_meta.get("grounding_ok")),
            "cited_fids": cited_fids,
            "rejected_items": rejected,
            "hallucination_rate_pct": hall_rate,
            "recommended_decision": output.recommended_decision,
            "overall_risk": output.overall_risk,
            "triage_count": len(output.triage or []),
            "mitigations_count": len(output.mitigations or []),
        }
    except Exception as exc:
        err = f"{type(exc).__name__}: {str(exc)[:180]}"
        return {
            "status": "schema_fail",
            "error": err,
            "prompt_chars": prompt_chars,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "schema_ok": False,
            "grounding_ok": False,
            "cited_fids": cited_fids,
            "rejected_items": 0,
            "hallucination_rate_pct": 0.0,
            "recommended_decision": None,
            "overall_risk": None,
            "triage_count": 0,
            "mitigations_count": 0,
        }


def _mode_consistency_pct(values: List[Any]) -> float:
    valid = [v for v in values if v is not None]
    if not valid:
        return 0.0
    most_common_count = Counter(valid).most_common(1)[0][1]
    return round((most_common_count / len(values)) * 100.0, 2)


async def run_benchmark(
    model: str = DEFAULT_MODEL,
    base_url: str = LLM_BASE_URL,
    repeats: int = 3,
    timeout_s: float = 120.0,
) -> Dict[str, Any]:
    """Execute Experiments 2A (Temperature), 2B (Context Top-K), and 2C (Modes) on qwen3:8b."""
    doc = await db.ota_security_assessments.find_one(
        {"target_version": {"$regex": "build225"}, "deleted_at": None}
    )
    if not doc:
        doc = await db.ota_security_assessments.find_one({"deleted_at": None}, sort=[("inserted_at", -1)])
    if not doc:
        raise RuntimeError("No security assessment documents found in MongoDB.")

    target_ver = doc.get("target_version")
    findings = doc.get("findings") or []
    valid_fids = {f["fid"] for f in findings if f.get("fid")}

    # Key high-priority findings in build225 (High/Crit + code + config non-low)
    key_fids = {
        f["fid"]
        for f in findings
        if f.get("fid")
        and (
            str(f.get("severity") or "").lower() in ("critical", "high")
            or (f.get("category") in ("code", "config", "secret") and str(f.get("severity") or "").lower() != "low")
        )
    }

    print(f"[Benchmark] Target assessment: {target_ver} ({len(findings)} findings, {len(key_fids)} key findings)")
    print(f"[Benchmark] Ollama server: {base_url} | Model: {model}")

    # Warmup call so model stays hot in VRAM (eliminates cold-start noise)
    print("[Warmup] Loading model into VRAM...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        await client.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "stream": False,
                "think": False,
                "options": {"temperature": 0, "num_predict": 16},
                "messages": [{"role": "user", "content": "Reply OK"}],
            },
        )
    print("[Warmup] Done.")

    # ==========================================================================
    # Experiment 2A: Temperature Sensitivity (0.0, 0.3, 0.7, 1.0) x K repeats
    # ==========================================================================
    ctx_15 = _build_custom_context(doc, max_findings=15, compact_diff=True, trim_fields=True)
    prompt_15 = (
        "Analyze the following firmware security assessment evidence and return structured JSON.\n"
        "<untrusted_evidence_data>\n"
        f"{json.dumps(ctx_15, ensure_ascii=False, sort_keys=True)}\n"
        "</untrusted_evidence_data>"
    )

    temperatures = [0.0, 0.3, 0.7, 1.0]
    temp_summary: List[Dict[str, Any]] = []
    temp_raw_runs: List[Dict[str, Any]] = []

    for temp in temperatures:
        runs = []
        for r in range(repeats):
            seed_val = 42 if temp == 0.0 else None
            print(f"[Exp 2A] temp={temp} run={r + 1}/{repeats}...")
            res = await _call_ollama_trial(
                base_url=base_url,
                model=model,
                user_prompt=prompt_15,
                valid_fids=valid_fids,
                temperature=temp,
                seed=seed_val,
                think=False,
                use_schema=True,
                timeout_s=timeout_s,
            )
            res["temperature"] = temp
            res["run"] = r + 1
            runs.append(res)
            temp_raw_runs.append(res)
            print(
                f"   -> status={res['status']} dec={res['recommended_decision']} risk={res['overall_risk']} "
                f"schema={res['schema_ok']} rejected={res['rejected_items']}/{res['cited_fids']} "
                f"latency={res['latency_ms']}ms comp_tok={res['completion_tokens']}"
            )

        latencies_s = [x["latency_ms"] / 1000.0 for x in runs]
        comp_toks = [x["completion_tokens"] for x in runs]
        total_cited = sum(x["cited_fids"] for x in runs)
        total_rejected = sum(x["rejected_items"] for x in runs)
        agg_hall_pct = round((total_rejected / total_cited) * 100.0, 2) if total_cited > 0 else 0.0

        temp_summary.append({
            "temperature": temp,
            "repeats": repeats,
            "schema_compliance_pct": round((sum(1 for x in runs if x["schema_ok"]) / repeats) * 100.0, 2),
            "decision_consistency_pct": _mode_consistency_pct([x["recommended_decision"] for x in runs]),
            "risk_consistency_pct": _mode_consistency_pct([x["overall_risk"] for x in runs]),
            "total_cited_fids": total_cited,
            "total_rejected_fids": total_rejected,
            "raw_hallucination_rate_pct": agg_hall_pct,
            "raw_grounding_acc_pct": round(100.0 - agg_hall_pct, 2),
            "post_validator_grounding_acc_pct": 100.0 if any(x["schema_ok"] for x in runs) else 0.0,
            "mean_latency_s": round(statistics.mean(latencies_s), 2),
            "std_latency_s": round(statistics.stdev(latencies_s), 2) if len(latencies_s) > 1 else 0.0,
            "mean_prompt_tokens": round(statistics.mean([x["prompt_tokens"] for x in runs]), 1),
            "mean_completion_tokens": round(statistics.mean(comp_toks), 1),
            "modal_decision": Counter([x["recommended_decision"] for x in runs]).most_common(1)[0][0],
        })

    # ==========================================================================
    # Experiment 2B: Context Size Sweep (Top-5, Top-15, Top-25, Top-40, Legacy 40)
    # ==========================================================================
    context_configs = [
        {"label": "Top-5 (Compact)", "max_findings": 5, "compact_diff": True, "trim_fields": True},
        {"label": "Top-15 (SEMAR Default)", "max_findings": 15, "compact_diff": True, "trim_fields": True},
        {"label": "Top-25 (Compact)", "max_findings": 25, "compact_diff": True, "trim_fields": True},
        {"label": "Top-40 (Compact)", "max_findings": 40, "compact_diff": True, "trim_fields": True},
        {"label": "Top-40 (Unoptimized)", "max_findings": 40, "compact_diff": False, "trim_fields": False},
    ]
    context_summary: List[Dict[str, Any]] = []

    for cfg in context_configs:
        ctx = _build_custom_context(
            doc,
            max_findings=cfg["max_findings"],
            compact_diff=cfg["compact_diff"],
            trim_fields=cfg["trim_fields"],
        )
        prompt_str = (
            "Analyze the following firmware security assessment evidence and return structured JSON.\n"
            "<untrusted_evidence_data>\n"
            f"{json.dumps(ctx, ensure_ascii=False, sort_keys=True)}\n"
            "</untrusted_evidence_data>"
        )
        included_fids = {f["fid"] for f in ctx.get("findings") or []}
        key_cov_pct = round((len(included_fids & key_fids) / len(key_fids)) * 100.0, 2) if key_fids else 100.0

        print(f"[Exp 2B] {cfg['label']} | chars={len(prompt_str)} | key_cov={key_cov_pct}%...")
        res = await _call_ollama_trial(
            base_url=base_url,
            model=model,
            user_prompt=prompt_str,
            valid_fids=valid_fids,
            temperature=0.0,
            seed=42,
            think=False,
            use_schema=True,
            timeout_s=timeout_s,
        )
        context_summary.append({
            "label": cfg["label"],
            "max_findings": cfg["max_findings"],
            "compact_diff": cfg["compact_diff"],
            "key_findings_coverage_pct": key_cov_pct,
            "prompt_chars": res["prompt_chars"],
            "prompt_tokens": res["prompt_tokens"],
            "completion_tokens": res["completion_tokens"],
            "latency_s": round(res["latency_ms"] / 1000.0, 2),
            "status": res["status"],
            "error": res["error"],
            "schema_ok": res["schema_ok"],
            "grounding_ok": res["grounding_ok"],
            "rejected_items": res["rejected_items"],
            "cited_fids": res["cited_fids"],
            "triage_count": res["triage_count"],
            "mitigations_count": res["mitigations_count"],
            "recommended_decision": res["recommended_decision"],
        })
        print(
            f"   -> status={res['status']} latency={res['latency_ms']/1000:.2f}s "
            f"p_tok={res['prompt_tokens']} c_tok={res['completion_tokens']} dec={res['recommended_decision']}"
        )

    # ==========================================================================
    # Experiment 2C: Decoding Mode Comparison (think=False/True, Schema On/Off)
    # ==========================================================================
    mode_configs = [
        {"label": "SEMAR Default\n(think=False, Schema=ON)", "think": False, "use_schema": True},
        {"label": "Extended Thinking\n(think=True, Schema=ON)", "think": True, "use_schema": True},
        {"label": "Unconstrained\n(think=False, Schema=OFF)", "think": False, "use_schema": False},
    ]
    mode_summary: List[Dict[str, Any]] = []

    for mcfg in mode_configs:
        print(f"[Exp 2C] {mcfg['label'].replace(chr(10), ' ')}...")
        res = await _call_ollama_trial(
            base_url=base_url,
            model=model,
            user_prompt=prompt_15,
            valid_fids=valid_fids,
            temperature=0.0,
            seed=42,
            think=mcfg["think"],
            use_schema=mcfg["use_schema"],
            timeout_s=timeout_s,
        )
        mode_summary.append({
            "label": mcfg["label"],
            "think": mcfg["think"],
            "use_schema": mcfg["use_schema"],
            "status": res["status"],
            "error": res["error"],
            "schema_ok": res["schema_ok"],
            "grounding_ok": res["grounding_ok"],
            "cited_fids": res["cited_fids"],
            "rejected_items": res["rejected_items"],
            "hallucination_rate_pct": res["hallucination_rate_pct"],
            "latency_s": round(res["latency_ms"] / 1000.0, 2),
            "prompt_tokens": res["prompt_tokens"],
            "completion_tokens": res["completion_tokens"],
            "recommended_decision": res["recommended_decision"],
            "triage_count": res["triage_count"],
        })
        print(
            f"   -> status={res['status']} schema_ok={res['schema_ok']} grounding_ok={res['grounding_ok']} "
            f"latency={res['latency_ms']/1000:.2f}s c_tok={res['completion_tokens']}"
        )

    return {
        "model": model,
        "base_url": base_url,
        "target_version": target_ver,
        "repeats": repeats,
        "timeout_s": timeout_s,
        "experiment_2a_temperature": temp_summary,
        "experiment_2a_raw_runs": temp_raw_runs,
        "experiment_2b_context_size": context_summary,
        "experiment_2c_decoding_modes": mode_summary,
    }


def write_outputs(data: Dict[str, Any], out_dir: str = DEFAULT_OUT_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "qwen3_evaluation_stats.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # CSVs
    def _dump_csv(filename: str, rows: List[Dict[str, Any]]) -> str:
        path = os.path.join(out_dir, filename)
        if not rows:
            return path
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    csv_t = _dump_csv("qwen3_temperature_summary.csv", data["experiment_2a_temperature"])
    csv_c = _dump_csv("qwen3_context_summary.csv", data["experiment_2b_context_size"])
    csv_m = _dump_csv("qwen3_modes_summary.csv", data["experiment_2c_decoding_modes"])

    # LaTeX Tables
    tex_path = os.path.join(out_dir, "qwen3_latex_tables.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("% Evaluation 2A: Temperature Sensitivity on qwen3:8b\n")
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write("\\caption{Temperature Sensitivity, Grounding, and Consistency of Qwen3:8B ($K=" + str(data["repeats"]) + "$ Runs)}\n")
        f.write("\\label{tab:qwen3-temp}\n")
        f.write("\\begin{tabular}{ccccccc}\n\\hline\n")
        f.write("Temp. & Schema(\\%) & Dec. Consist.(\\%) & Risk Consist.(\\%) & Raw Halluc.(\\%) & Post-Val.(\\%) & Latency (s) \\\\\n\\hline\n")
        for r in data["experiment_2a_temperature"]:
            f.write(
                f"{r['temperature']:.1f} & {r['schema_compliance_pct']:.1f} & {r['decision_consistency_pct']:.1f} & "
                f"{r['risk_consistency_pct']:.1f} & {r['raw_hallucination_rate_pct']:.1f} & "
                f"{r['post_validator_grounding_acc_pct']:.1f} & {r['mean_latency_s']:.2f} $\\pm$ {r['std_latency_s']:.2f} \\\\\n"
            )
        f.write("\\hline\n\\end{tabular}\n\\end{table}\n\n")

        f.write("% Evaluation 2B: Context Size Sweep on qwen3:8b\n")
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write("\\caption{Prompt Context Size vs. Inference Latency and Coverage on Qwen3:8B}\n")
        f.write("\\label{tab:qwen3-context}\n")
        f.write("\\begin{tabular}{lrrrrrl}\n\\hline\n")
        f.write("Configuration & Key Cov.(\\%) & Chars & Prompt Tok. & Comp. Tok. & Latency (s) & Status \\\\\n\\hline\n")
        for r in data["experiment_2b_context_size"]:
            f.write(
                f"{r['label']} & {r['key_findings_coverage_pct']:.1f} & {r['prompt_chars']} & "
                f"{r['prompt_tokens']} & {r['completion_tokens']} & {r['latency_s']:.2f} & {r['status']} \\\\\n"
            )
        f.write("\\hline\n\\end{tabular}\n\\end{table}\n")

    # Markdown Report
    md_path = os.path.join(out_dir, "qwen3_evaluation_report.md")
    lines = [f"# Evaluation 2: Qwen3:8B Sensitivity, Hallucination & Consistency Report\n"]
    lines.append(f"- **Model:** `{data['model']}` | **Server:** `{data['base_url']}` | **Target Build:** `{data['target_version']}`\n")

    lines.append("\n## Experiment 2A: Temperature Sensitivity (`K=" + str(data["repeats"]) + "` runs/setting)\n")
    lines.append("| Temp | Schema OK (%) | Decision Consistency (%) | Risk Consistency (%) | Cited / Rejected FIDs | Raw Hallucination (%) | Post-Validator Grounding (%) | Latency (s) | Comp. Tokens |")
    lines.append("| ---: | ---: | ---: | ---: | :---: | ---: | ---: | :---: | ---: |")
    for r in data["experiment_2a_temperature"]:
        lines.append(
            f"| {r['temperature']:.1f} | {r['schema_compliance_pct']}% | {r['decision_consistency_pct']}% | "
            f"{r['risk_consistency_pct']}% | {r['total_cited_fids']} / {r['total_rejected_fids']} | "
            f"{r['raw_hallucination_rate_pct']}% | {r['post_validator_grounding_acc_pct']}% | "
            f"{r['mean_latency_s']} ± {r['std_latency_s']} | {r['mean_completion_tokens']} |"
        )

    lines.append("\n## Experiment 2B: Prompt Context Size Sweep (`Top-K` Findings)\n")
    lines.append("| Configuration | Key Coverage (%) | Prompt Chars | Prompt Tokens | Comp. Tokens | Latency (s) | Status | Decision |")
    lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | :---: | :---: |")
    for r in data["experiment_2b_context_size"]:
        lines.append(
            f"| {r['label']} | {r['key_findings_coverage_pct']}% | {r['prompt_chars']} | {r['prompt_tokens']} | "
            f"{r['completion_tokens']} | {r['latency_s']} | {r['status']} | {r['recommended_decision']} |"
        )

    lines.append("\n## Experiment 2C: Decoding Modes (`think` & `JSON Schema`)\n")
    lines.append("| Mode | Schema OK | Grounding OK | Rejected / Cited | Latency (s) | Comp. Tokens | Status | Decision |")
    lines.append("| :--- | :---: | :---: | :---: | ---: | ---: | :---: | :---: |")
    for r in data["experiment_2c_decoding_modes"]:
        lbl = r["label"].replace("\n", " ")
        lines.append(
            f"| {lbl} | {r['schema_ok']} | {r['grounding_ok']} | {r['rejected_items']} / {r['cited_fids']} | "
            f"{r['latency_s']} | {r['completion_tokens']} | {r['status']} | {r['recommended_decision']} |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nSaved Evaluation 2 outputs in {os.path.abspath(out_dir)}:")
    for p in (json_path, csv_t, csv_c, csv_m, tex_path, md_path):
        print(f" - {p}")
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Qwen3:8B parameter sensitivity & grounding evaluation.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    data = asyncio.get_event_loop().run_until_complete(
        run_benchmark(model=args.model, repeats=args.repeats, timeout_s=args.timeout)
    )
    write_outputs(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
