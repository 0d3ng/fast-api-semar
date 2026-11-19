"""Evaluation 4: End-to-End CI/CD Pipeline & Backend Performance Overhead Analysis.

Combines:
  1. CPU micro-benchmark (N=100 iterations) of all deterministic SEMAR modules
     on real build227/build228 findings (milliseconds).
  2. Macro-benchmark from MongoDB timestamps (`ota_firmware_releases` and
     `ota_security_assessments`) for real builds (build225..build228).
  3. Token-vs-latency linear scaling & throughput analysis across live Qwen3:8B
     runs (`ai_security_analysis.jsonl` + MongoDB + qwen3_evaluation_stats.json).

Usage:
    python -m app.scripts.eval_pipeline_overhead
    python -m app.scripts.eval_pipeline_overhead --iters 100 --out-dir logs/evaluation
"""

import argparse
import asyncio
import copy
import csv
import json
import os
import statistics
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.ota_security_assessment_service import (
    _apply_review_baseline,
    _extract_review_baseline,
)
from app.services.security.ai_analyzer import _build_context_payload, validate_and_ground_output
from app.services.security.decision import merge_policy_and_ai
from app.services.security.enricher import apply_reachability
from app.services.security.normalizer import compute_diff
from app.services.security.policy_engine import evaluate_policy
from app.utils.db import db

DEFAULT_OUT_DIR = os.path.join("logs", "evaluation")
JST = timezone(timedelta(hours=9))


def _parse_version_start_utc(target_version: str) -> Optional[datetime]:
    """Parse YYYYMMDDTHHMM (Asia/Tokyo in build-ota.yml) from target_version to UTC datetime."""
    parts = str(target_version or "").split("-")
    for p in parts:
        if len(p) == 13 and "T" in p:
            try:
                dt_jst = datetime.strptime(p, "%Y%m%dT%H%M").replace(tzinfo=JST)
                return dt_jst.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                pass
    return None


def _run_micro_benchmark(doc: Dict[str, Any], prev_doc: Optional[Dict[str, Any]], approved_doc: Optional[Dict[str, Any]], iters: int = 100) -> Dict[str, Any]:
    """Time each deterministic backend stage over N iterations."""
    raw_findings = doc.get("findings") or []
    summary = doc.get("summary") or {}
    sdk_flags = (doc.get("source") or {}).get("sdkconfig_flags") or {}
    platform = doc.get("platform_type") or "esp32"

    ai_res = doc.get("ai_result") or {}
    sample_ai_json = json.dumps({
        "overall_risk": ai_res.get("overall_risk") or "low",
        "recommended_decision": ai_res.get("recommended_decision") or "PASS",
        "confidence": ai_res.get("confidence") or 0.5,
        "triage": ai_res.get("triage") or [],
        "correlations": ai_res.get("correlations") or [],
        "mitigations": ai_res.get("mitigations") or [],
        "summary": ai_res.get("summary") or "Clean.",
    })
    valid_fids = {f["fid"] for f in raw_findings if f.get("fid")}

    timings: Dict[str, List[float]] = {
        "reachability_filter": [],
        "baseline_inheritance": [],
        "policy_engine": [],
        "diff_computation": [],
        "prompt_context_build": [],
        "grounding_validator": [],
        "monotonic_merge": [],
    }

    for _ in range(iters):
        f_work = copy.deepcopy(raw_findings)

        t0 = time.perf_counter()
        apply_reachability(f_work, sdkconfig_flags=sdk_flags, platform_type=platform)
        timings["reachability_filter"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        fp_fids, app_fids = _extract_review_baseline([prev_doc, approved_doc])
        _apply_review_baseline(f_work, fp_fids, app_fids)
        timings["baseline_inheritance"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        pol = evaluate_policy(f_work, summary, profile="lab")
        timings["policy_engine"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        diff = compute_diff(f_work, prev_doc)
        timings["diff_computation"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        ctx = _build_context_payload(
            source_meta=doc.get("source") or {},
            findings=f_work,
            summary=summary,
            policy_result=pol,
            diff_vs_previous=diff,
        )
        json.dumps(ctx, ensure_ascii=False, sort_keys=True)
        timings["prompt_context_build"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        validate_and_ground_output(sample_ai_json, valid_fids)
        timings["grounding_validator"].append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        merge_policy_and_ai(pol.get("decision", "PASS"), ai_res.get("recommended_decision"))
        timings["monotonic_merge"].append((time.perf_counter() - t0) * 1000.0)

    stages_summary: List[Dict[str, Any]] = []
    total_mean_ms = 0.0
    for stage, vals in timings.items():
        m = statistics.mean(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        total_mean_ms += m
        stages_summary.append({
            "stage": stage,
            "mean_ms": round(m, 3),
            "std_ms": round(sd, 3),
            "p95_ms": round(float(np.percentile(vals, 95)), 3),
        })

    return {
        "target_version": doc.get("target_version"),
        "findings_count": len(raw_findings),
        "iterations": iters,
        "total_deterministic_mean_ms": round(total_mean_ms, 3),
        "stages": stages_summary,
    }


async def collect_overhead(iters: int = 100) -> Dict[str, Any]:
    """Gather micro-benchmark, CI macro-timings from MongoDB, and LLM scaling points."""
    docs = await db.ota_security_assessments.find({"deleted_at": None}).sort("inserted_at", 1).to_list(50)
    b227 = next((d for d in docs if "build227" in str(d.get("target_version"))), docs[-1])
    b228 = next((d for d in docs if "build228" in str(d.get("target_version"))), docs[-1])
    b225 = next((d for d in docs if "build225" in str(d.get("target_version"))), None)

    print(f"[Micro-Benchmark] Running N={iters} iterations on {b228.get('target_version')} ({len(b228.get('findings') or [])} findings)...")
    micro_b228 = _run_micro_benchmark(b228, b227, b225, iters=iters)
    print(f" -> Total deterministic SEMAR CPU time: {micro_b228['total_deterministic_mean_ms']:.2f} ms")

    # Macro timings from MongoDB builds with completed AI
    macro_builds: List[Dict[str, Any]] = []
    for d in docs:
        ai = d.get("ai_result") or {}
        if ai.get("status") != "completed":
            continue
        ver = d.get("target_version")
        rels = await db.ota_firmware_releases.find({"target_version": ver, "deleted_at": None}).sort("inserted_at", 1).to_list(5)
        start_utc = _parse_version_start_utc(ver)
        ass_ins = d.get("inserted_at")
        ass_upd = d.get("updated_at")

        # Estimate CI build + scanner + signing time until last release upload (minute precision on start_utc)
        last_rel_ins = rels[-1].get("inserted_at") if rels else ass_ins
        ci_build_scan_s = round((last_rel_ins - start_utc).total_seconds(), 2) if (start_utc and last_rel_ins) else None
        ingest_upload_s = round((ass_ins - last_rel_ins).total_seconds(), 2) if (ass_ins and last_rel_ins) else None
        ai_latency_s = round((ai.get("latency_ms") or 0) / 1000.0, 2)
        total_e2e_s = round((ci_build_scan_s or 0) + (ingest_upload_s or 0) + ai_latency_s, 2) if ci_build_scan_s is not None else None
        ai_overhead_pct = round(((ingest_upload_s or 0) + ai_latency_s) / total_e2e_s * 100.0, 2) if total_e2e_s else None

        toks = ai.get("tokens") or {}
        macro_builds.append({
            "version": ver,
            "short_version": str(ver).split("-")[-1],
            "final_decision": d.get("final_decision"),
            "workflow_state": d.get("workflow_state"),
            "ci_build_scan_upload_s": ci_build_scan_s,
            "semar_ingest_s": ingest_upload_s,
            "ai_latency_s": ai_latency_s,
            "total_e2e_s": total_e2e_s,
            "ai_gate_overhead_pct": ai_overhead_pct,
            "prompt_tokens": toks.get("prompt", 0),
            "completion_tokens": toks.get("completion", 0),
            "ai_decision": ai.get("recommended_decision"),
        })

    # Collect all unique live Qwen3:8B runs for token-vs-latency scaling analysis
    scaling_points: List[Dict[str, Any]] = []
    seen_keys = set()

    # From MongoDB builds (where initial AI ran cleanly without manual reanalyze overwrite latency mismatch)
    for mb in macro_builds:
        key = (mb["short_version"], mb["completion_tokens"], round(mb["ai_latency_s"], 1))
        seen_keys.add(key)
        scaling_points.append({
            "source": f"DB:{mb['short_version']}",
            "decision": mb["ai_decision"] or "PASS",
            "category": "Clean (PASS)" if mb["ai_decision"] == "PASS" else "Threat/Review",
            "prompt_tokens": mb["prompt_tokens"],
            "completion_tokens": mb["completion_tokens"],
            "latency_s": mb["ai_latency_s"],
        })

    # From logs/ai_security_analysis.jsonl (Stage 1 TC-01..TC-10)
    jsonl_path = os.path.join("logs", "ai_security_analysis.jsonl")
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    out = rec.get("output_result") or {}
                    inp = rec.get("input_parameters") or {}
                    ver = ((inp.get("release_context") or {}).get("target_version")) or ""
                    if not ver.startswith("tc-"):
                        continue
                    toks = out.get("tokens") or {}
                    comp_t = int(toks.get("completion") or 0)
                    prom_t = int(toks.get("prompt") or 0)
                    lat_s = round(float(out.get("latency_ms") or 0) / 1000.0, 2)
                    dec = out.get("recommended_decision") or "REVIEW_REQUIRED"
                    key = (ver, comp_t, round(lat_s, 1))
                    if comp_t > 0 and key not in seen_keys:
                        seen_keys.add(key)
                        scaling_points.append({
                            "source": ver.upper().replace("-VALIDATION", ""),
                            "decision": dec,
                            "category": "Clean (PASS)" if dec == "PASS" else "Threat/Review",
                            "prompt_tokens": prom_t,
                            "completion_tokens": comp_t,
                            "latency_s": lat_s,
                        })
                except Exception:
                    continue

    # Linear fit: latency_s = slope * completion_tokens + intercept
    x_tok = np.array([p["completion_tokens"] for p in scaling_points], dtype=float)
    y_lat = np.array([p["latency_s"] for p in scaling_points], dtype=float)
    slope, intercept = np.polyfit(x_tok, y_lat, 1)
    y_pred = slope * x_tok + intercept
    ss_res = float(np.sum((y_lat - y_pred) ** 2))
    ss_tot = float(np.sum((y_lat - np.mean(y_lat)) ** 2))
    r2 = round(1.0 - (ss_res / ss_tot), 4) if ss_tot > 0 else 0.0

    clean_pts = [p for p in scaling_points if p["decision"] == "PASS"]
    threat_pts = [p for p in scaling_points if p["decision"] != "PASS"]

    scaling_summary = {
        "n_points": len(scaling_points),
        "slope_ms_per_token": round(float(slope) * 1000.0, 2),
        "intercept_prefill_s": round(float(intercept), 2),
        "r_squared": r2,
        "effective_decode_tok_per_s": round(1.0 / float(slope), 2) if slope > 0 else 0.0,
        "clean_pass_mean_latency_s": round(statistics.mean([p["latency_s"] for p in clean_pts]), 2) if clean_pts else 0.0,
        "clean_pass_mean_comp_tokens": round(statistics.mean([p["completion_tokens"] for p in clean_pts]), 1) if clean_pts else 0.0,
        "threat_review_mean_latency_s": round(statistics.mean([p["latency_s"] for p in threat_pts]), 2) if threat_pts else 0.0,
        "threat_review_mean_comp_tokens": round(statistics.mean([p["completion_tokens"] for p in threat_pts]), 1) if threat_pts else 0.0,
    }

    return {
        "micro_benchmark": micro_b228,
        "macro_builds": macro_builds,
        "scaling_summary": scaling_summary,
        "scaling_points": scaling_points,
    }


def write_outputs(data: Dict[str, Any], out_dir: str = DEFAULT_OUT_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "pipeline_overhead_stats.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    csv_micro = os.path.join(out_dir, "pipeline_micro_benchmark.csv")
    with open(csv_micro, "w", newline="", encoding="utf-8") as f:
        rows = data["micro_benchmark"]["stages"]
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    csv_macro = os.path.join(out_dir, "pipeline_macro_builds.csv")
    with open(csv_macro, "w", newline="", encoding="utf-8") as f:
        rows = data["macro_builds"]
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    tex_path = os.path.join(out_dir, "pipeline_overhead_latex.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        mb = data["micro_benchmark"]
        f.write("% Evaluation 4A: Deterministic SEMAR Backend Micro-Benchmark\n")
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write(f"\\caption{{Deterministic SEMAR Backend Processing Time ({mb['findings_count']} Findings, $N={mb['iterations']}$ Runs)}}\n")
        f.write("\\label{tab:micro-overhead}\n")
        f.write("\\begin{tabular}{lrrr}\n\\hline\n")
        f.write("Pipeline Sub-Stage & Mean (ms) & Std (ms) & p95 (ms) \\\\\n\\hline\n")
        for s in mb["stages"]:
            f.write(f"{s['stage'].replace('_', ' ').title()} & {s['mean_ms']:.3f} & {s['std_ms']:.3f} & {s['p95_ms']:.3f} \\\\\n")
        f.write("\\hline\n")
        f.write(f"\\textbf{{Total Deterministic SEMAR}} & \\textbf{{{mb['total_deterministic_mean_ms']:.3f}}} & -- & -- \\\\\n")
        f.write("\\hline\n\\end{tabular}\n\\end{table}\n\n")

        f.write("% Evaluation 4B: End-to-End CI/CD Overhead Across Real Builds\n")
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write("\\caption{End-to-End CI/CD Pipeline Execution Breakdown Across Real ESP32 Builds}\n")
        f.write("\\label{tab:macro-overhead}\n")
        f.write("\\begin{tabular}{lcrrrrr}\n\\hline\n")
        f.write("Build & Gate Outcome & CI Build+Scan (s) & Ingest (s) & Qwen3:8B (s) & Total (s) & AI Overhead (\\%) \\\\\n\\hline\n")
        for m in data["macro_builds"]:
            f.write(
                f"{m['short_version']} & {m['final_decision']} & {m['ci_build_scan_upload_s']:.1f} & "
                f"{m['semar_ingest_s']:.2f} & {m['ai_latency_s']:.2f} & {m['total_e2e_s']:.1f} & {m['ai_gate_overhead_pct']:.1f} \\\\\n"
            )
        f.write("\\hline\n\\end{tabular}\n\\end{table}\n")

    md_path = os.path.join(out_dir, "pipeline_overhead_report.md")
    mb = data["micro_benchmark"]
    sc = data["scaling_summary"]
    lines = ["# Evaluation 4: End-to-End CI/CD & Performance Overhead Report\n"]
    lines.append(f"## 1. Deterministic Backend Micro-Benchmark (`{mb['target_version']}`, `{mb['findings_count']}` findings, `N={mb['iterations']}`)\n")
    lines.append("| Sub-Stage | Mean (ms) | Std (ms) | p95 (ms) |")
    lines.append("| :--- | ---: | ---: | ---: |")
    for s in mb["stages"]:
        lines.append(f"| {s['stage']} | {s['mean_ms']:.3f} | {s['std_ms']:.3f} | {s['p95_ms']:.3f} |")
    lines.append(f"| **Total Deterministic SEMAR** | **{mb['total_deterministic_mean_ms']:.3f} ms** | — | — |")

    lines.append("\n## 2. End-to-End Real CI/CD Pipeline Breakdown\n")
    lines.append("| Build | Final Gate | CI Build+Scan+Upload (s) | SEMAR Ingest (s) | Qwen3:8B Latency (s) | Total E2E (s) | AI Gate Overhead (%) | Tokens (P / C) |")
    lines.append("| :--- | :---: | ---: | ---: | ---: | ---: | ---: | :---: |")
    for m in data["macro_builds"]:
        lines.append(
            f"| {m['short_version']} | **{m['final_decision']}** | {m['ci_build_scan_upload_s']} | "
            f"{m['semar_ingest_s']} | {m['ai_latency_s']} | {m['total_e2e_s']} | **{m['ai_gate_overhead_pct']}%** | "
            f"{m['prompt_tokens']} / {m['completion_tokens']} |"
        )

    lines.append("\n## 3. Token-to-Latency Linear Scaling (`N=" + str(sc["n_points"]) + "` Qwen3:8B Runs)\n")
    lines.append(f"- **Linear Fit:** `latency_s = {sc['slope_ms_per_token'] / 1000.0:.4f} * completion_tokens + {sc['intercept_prefill_s']} s` ($R^2 = {sc['r_squared']}$)")
    lines.append(f"- **Effective Decode Speed:** `{sc['effective_decode_tok_per_s']} tokens/s`")
    lines.append(f"- **Clean `PASS` Runs Mean:** `{sc['clean_pass_mean_latency_s']} s` (`{sc['clean_pass_mean_comp_tokens']}` comp. tokens)")
    lines.append(f"- **Threat `REVIEW/BLOCKED` Runs Mean:** `{sc['threat_review_mean_latency_s']} s` (`{sc['threat_review_mean_comp_tokens']}` comp. tokens)")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nSaved Evaluation 4 outputs in {os.path.abspath(out_dir)}:")
    for p in (json_path, csv_micro, csv_macro, tex_path, md_path):
        print(f" - {p}")
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure SEMAR CI/CD & backend performance overhead.")
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    data = asyncio.get_event_loop().run_until_complete(collect_overhead(iters=args.iters))
    write_outputs(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
