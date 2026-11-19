"""Plot Matplotlib chart (PNG 300 DPI) for Evaluation 4: CI/CD Pipeline Overhead & Token Scaling.

Edit labels, titles, and colors in `CHART_CONFIG` below, then run:
    python -m app.scripts.plot_pipeline_overhead_charts
    python -m app.scripts.plot_pipeline_overhead_charts --refresh
"""

import argparse
import asyncio
import json
import os
from typing import Any, Dict

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit("matplotlib is required. Install with: pip install matplotlib") from exc

from app.scripts.eval_pipeline_overhead import DEFAULT_OUT_DIR, collect_overhead, write_outputs

# ==============================================================================
# EDITABLE LABELS, TITLES & STYLING CONFIG (Ubah label/warna di sini)
# ==============================================================================
CHART_CONFIG: Dict[str, Any] = {
    "dpi": 300,
    "font_family": "sans-serif",
    "font_sans": ["DejaVu Sans", "Arial", "Helvetica"],

    "fig8": {
        "title_a": "(a) End-to-End CI/CD Pipeline Time Breakdown",
        "xlabel_a": "Elapsed Execution Time (Seconds)",
        "legend_ci": "CI Build, 5 Security Scanners & ED25519 Sign",
        "legend_ingest": "SEMAR Evidence Ingest & Policy (< 2s)",
        "legend_ai": "Local Ollama LLM (Qwen3:8B)",

        "title_b": "(b) Qwen3:8B Inference Latency vs. Output Length",
        "xlabel_b": "Generated Completion Tokens",
        "ylabel_b": "Inference Latency (s)",
        "legend_clean": "Clean Release (PASS)",
        "legend_threat": "Threat Detected (REVIEW / BLOCKED)",
        "legend_fit": "Linear Fit",
    },
}


def _apply_style() -> None:
    plt.rcParams.update({
        "font.family": CHART_CONFIG["font_family"],
        "font.sans-serif": CHART_CONFIG["font_sans"],
        "font.size": 10,
        "axes.titlesize": 11.2,
        "axes.titleweight": "bold",
        "axes.labelsize": 9.8,
        "xtick.labelsize": 9.2,
        "ytick.labelsize": 9.2,
        "legend.fontsize": 8.4,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def render_charts(data: Dict[str, Any], out_dir: str) -> None:
    _apply_style()
    os.makedirs(out_dir, exist_ok=True)
    dpi = CHART_CONFIG["dpi"]
    c8 = CHART_CONFIG["fig8"]

    # Pick clean vs threat-injected real builds + baseline comparison (Traditional vs Clean vs Blocked)
    macros = data["macro_builds"]
    b227 = next((m for m in macros if m["short_version"] == "build227"), macros[-1])
    b228 = next((m for m in macros if m["short_version"] == "build228"), macros[-1])

    row_labels = [
        f"Traditional OTA\n(No Security Gate)",
        f"Clean Release (Build 227)\nDecision: {b227['final_decision']}",
        f"Threat Build (Build 228)\nDecision: {b228['final_decision']}",
    ]
    ci_vals = np.array([b228["ci_build_scan_upload_s"] * 0.78, b227["ci_build_scan_upload_s"], b228["ci_build_scan_upload_s"]])
    # Wait: use exact observed baseline build time (build227 vs build228); for Traditional OTA show b228 CI without security gate?
    # Better yet: show ALL 3 real builds directly (build225, build227 PASS, build228 BLOCKED) so 100% of bars are directly observed values!
    selected_builds = [m for m in macros if m["short_version"] in ("build225", "build227", "build228")]
    if len(selected_builds) < 2:
        selected_builds = macros

    row_labels = [
        f"{m['short_version'].replace('build', 'Build ')}\n({m['final_decision']})"
        for m in selected_builds
    ]
    ci_vals = np.array([m["ci_build_scan_upload_s"] or 0.0 for m in selected_builds])
    ing_vals = np.array([m["semar_ingest_s"] or 0.0 for m in selected_builds])
    ai_vals = np.array([m["ai_latency_s"] or 0.0 for m in selected_builds])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.6))
    y = np.arange(len(selected_builds))
    h = 0.48

    ax1.barh(y, ci_vals, height=h, color="#64748b", edgecolor="#334155", label=c8["legend_ci"], zorder=3)
    ax1.barh(y, ing_vals, left=ci_vals, height=h, color="#0ea5e9", edgecolor="#0369a1", label=c8["legend_ingest"], zorder=3)
    ax1.barh(y, ai_vals, left=ci_vals + ing_vals, height=h, color="#2563eb", edgecolor="#1e3a8a", label=c8["legend_ai"], zorder=3)

    ax1.set_yticks(y)
    ax1.set_yticklabels(row_labels, fontweight="bold")
    ax1.set_ylim(len(selected_builds) + 0.55, -0.55)
    ax1.set_xlabel(c8["xlabel_a"])
    ax1.set_title(c8["title_a"])
    ax1.set_xlim(0, max(ci_vals + ing_vals + ai_vals) * 1.32)
    ax1.grid(axis="x", linestyle="--", alpha=0.4, zorder=0)
    ax1.legend(loc="lower right", frameon=True, fontsize=8.0)

    for idx, m in enumerate(selected_builds):
        tot = m["total_e2e_s"] or 0.0
        ov = m["ai_gate_overhead_pct"] or 0.0
        ai_s = m["ai_latency_s"] or 0.0
        ax1.text(
            tot + 10, idx,
            f"Total: {tot:.0f}s\n(AI: {ai_s:.1f}s / {ov:.1f}%)",
            va="center", ha="left", fontsize=8.5, fontweight="bold",
            color="#15803d" if m["final_decision"] == "PASS" else "#1e3a8a",
        )

    # Panel (b): Token vs Latency Scaling Scatter + Linear Regression
    pts = data["scaling_points"]
    clean_x = [p["completion_tokens"] for p in pts if p["category"] == "Clean (PASS)"]
    clean_y = [p["latency_s"] for p in pts if p["category"] == "Clean (PASS)"]
    thr_x = [p["completion_tokens"] for p in pts if p["category"] != "Clean (PASS)"]
    thr_y = [p["latency_s"] for p in pts if p["category"] != "Clean (PASS)"]

    ax2.scatter(clean_x, clean_y, s=75, color="#16a34a", edgecolor="#14532d", marker="o", label=c8["legend_clean"], zorder=4)
    ax2.scatter(thr_x, thr_y, s=75, color="#dc2626", edgecolor="#7f1d1d", marker="^", label=c8["legend_threat"], zorder=4)

    all_x = np.array([p["completion_tokens"] for p in pts], dtype=float)
    all_y = np.array([p["latency_s"] for p in pts], dtype=float)
    slope, intercept = np.polyfit(all_x, all_y, 1)
    x_line = np.linspace(min(all_x) * 0.92, max(all_x) * 1.05, 50)
    y_line = slope * x_line + intercept
    sc = data["scaling_summary"]

    ax2.plot(
        x_line, y_line, linestyle="--", color="#1e293b", lw=1.6,
        label=f"{c8['legend_fit']} ($R^2={sc['r_squared']:.2f}$, {sc['effective_decode_tok_per_s']:.1f} tok/s)",
        zorder=3,
    )

    # Annotate key points (build227 & build228) cleanly
    for p in pts:
        if p["source"] in ("DB:build227", "DB:build228", "TC-01"):
            tag = p["source"].replace("DB:", "").replace("build", "Build ")
            if "228" in tag:
                dx, dy = (-24, 9)
            elif "TC-01" in tag:
                dx, dy = (-12, 9)
            else:
                dx, dy = (10, -4)
            ax2.annotate(tag, (p["completion_tokens"], p["latency_s"]), xytext=(dx, dy),
                         textcoords="offset points", fontsize=8.0, fontweight="bold", color="#334155")

    ax2.set_xlabel(c8["xlabel_b"])
    ax2.set_ylabel(c8["ylabel_b"])
    ax2.set_title(c8["title_b"])
    ax2.set_ylim(0, max(all_y) * 1.25)
    ax2.grid(True, linestyle="--", alpha=0.4, zorder=0)
    ax2.legend(loc="upper left", frameon=True, fontsize=8.2)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig8_pipeline_overhead.png"), dpi=dpi)
    plt.close(fig)

    print(f"Generated Evaluation 4 chart in {os.path.abspath(out_dir)}:")
    print(" -", os.path.join(out_dir, "fig8_pipeline_overhead.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Evaluation 4 CI/CD overhead chart.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--refresh", action="store_true", help="Re-run micro-benchmark & DB collection")
    parser.add_argument("--iters", type=int, default=100)
    args = parser.parse_args()

    stats_path = os.path.join(args.out_dir, "pipeline_overhead_stats.json")
    if args.refresh or not os.path.exists(stats_path):
        data = asyncio.get_event_loop().run_until_complete(collect_overhead(iters=args.iters))
        write_outputs(data, out_dir=args.out_dir)
    else:
        with open(stats_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    render_charts(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
