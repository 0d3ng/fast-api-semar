"""Plot publication-grade Matplotlib charts (PNG 300 DPI) for Evaluation 1.

Edit labels, titles, colors, and typography in `CHART_CONFIG` below, then run:
    python -m app.scripts.plot_filtering_charts
    python -m app.scripts.plot_filtering_charts --refresh   # Re-query MongoDB first
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
    raise SystemExit(
        "matplotlib is required to run this script. Install with: pip install matplotlib"
    ) from exc

from app.scripts.eval_filtering_effectiveness import (
    DEFAULT_OUT_DIR,
    collect_evaluation,
    write_outputs,
)

# ==============================================================================
# EDITABLE LABELS, TITLES & STYLING CONFIG (Ubah teks label/warna di sini)
# ==============================================================================
CHART_CONFIG: Dict[str, Any] = {
    "dpi": 300,
    "font_family": "sans-serif",
    "font_sans": ["DejaVu Sans", "Arial", "Helvetica"],
    "build_prefix_replace": ("build", "Build "),  # e.g. "build224" -> "Build 224"

    # --- Figure 1: Multi-Stage Filtering Funnel ---
    "fig1": {
        "title": "Multi-Stage Security Finding Filtering Funnel (Raw Output to OTA Gate)",
        "xlabel": "Number of Findings / Items",
        "baseline_build_match": "build224",
        "optimized_build_match": "build227",
        "legend_baseline": "Build 224 (Pre-Pruning / Initial Reachability)",
        "legend_optimized": "Build 227 (Full SEMAR Filtering + Baseline Reuse)",
        "stages": [
            "1. Raw Multi-Scanner\n(5 Tools)",
            "2. After Cross-Tool\nDeduplication",
            "3. Reachable on Target\n(sdkconfig & Arch)",
            "4. Actionable Non-Low\n(Severity >= Medium)",
            "5. LLM Prompt Context\n(Top-15 Priority)",
            "6. Unresolved Blockers\n(Crit/High + Unapproved)",
        ],
        "color_baseline": "#94a3b8",
        "edge_baseline": "#475569",
        "color_optimized": "#2563eb",
        "edge_optimized": "#1e40af",
    },

    # --- Figure 2: SBOM Pruning & False-Blocker Elimination ---
    "fig2": {
        "title_a": "(a) SBOM Component Pruning & Coverage",
        "ylabel_a_left": "Compiled SBOM Components",
        "ylabel_a_right": "SBOM Coverage (%)",
        "legend_cov": "SBOM Coverage (%)",
        "legend_thresh": "Policy Threshold (90%)",
        "prune_annotation": "-60.3%\n(189 -> 75)",

        "title_b": "(b) False-Blocker Elimination & Gate Outcome",
        "ylabel_b": "Critical & High Findings Count",
        "legend_crit_raw": "Raw Critical + High CVEs",
        "legend_crit_reach": "Reachable Critical + High",
        "gate_labels": {
            "BLOCKED": "BLOCKED",
            "REVIEW_REQUIRED": "REVIEW",
            "approved": "PASS\n(Human)",
            "auto_passed": "PASS\n(Auto)",
        },
    },

    # --- Figure 3: Prompt Size Compression & Unreachable FP Breakdown ---
    "fig3": {
        "title_a": "(a) LLM Prompt Compression (Fixes ReadTimeout)",
        "ylabel_a": "Prompt Size (x1,000 Characters)",
        "legend_legacy": "Unoptimized Prompt (Top-40 + Full Diff)",
        "legend_compact": "Compact Prompt (Top-15 + Summary Diff)",

        "title_b": "(b) Filtered False Positive Categories (Build 224)",
        "xlabel_b": "Filtered Unreachable CVEs (Build 224 Total = 21)",
        "fp_reasons": [
            "Bluetooth Disabled\n(CONFIG_BT_ENABLED=n)",
            "ARM Cortex-M MPU CVEs\n(FreeRTOS on Xtensa ESP32)",
            "Linux D-Bus CVE\n(wpa_supplicant on RTOS)",
        ],
        "fp_counts": [15, 5, 1],
        "fp_colors": ["#38bdf8", "#818cf8", "#fbbf24"],
    },
}


def _apply_style() -> None:
    plt.rcParams.update({
        "font.family": CHART_CONFIG["font_family"],
        "font.sans-serif": CHART_CONFIG["font_sans"],
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def _gate_badge(build: Dict[str, Any]):
    wf = build.get("workflow_state")
    dec = build.get("final_decision")
    badges = CHART_CONFIG["fig2"]["gate_labels"]
    if dec == "BLOCKED":
        return badges.get("BLOCKED", "BLOCKED"), "#b91c1c"
    if dec == "REVIEW_REQUIRED":
        return badges.get("REVIEW_REQUIRED", "REVIEW"), "#d97706"
    if wf == "auto_passed":
        return badges.get("auto_passed", "PASS\n(Auto)"), "#15803d"
    return badges.get("approved", "PASS\n(Human)"), "#0284c7"


def render_charts(data: Dict[str, Any], out_dir: str) -> None:
    _apply_style()
    os.makedirs(out_dir, exist_ok=True)
    dpi = CHART_CONFIG["dpi"]

    builds = data["builds"]
    old_p, new_p = CHART_CONFIG["build_prefix_replace"]
    labels = [b["version"].split("-")[-1].replace(old_p, new_p) for b in builds]
    x = np.arange(len(builds))

    # ==========================================================================
    # Figure 1: Multi-Stage Filtering Funnel
    # ==========================================================================
    c1 = CHART_CONFIG["fig1"]
    b_base = next((b for b in builds if c1["baseline_build_match"] in b["version"]), builds[0])
    b_opt = next((b for b in builds if c1["optimized_build_match"] in b["version"]), builds[-1])

    vals_base = [
        b_base["raw_findings_total"],
        b_base["unique_findings_total"],
        b_base["reachable_findings"],
        b_base["non_low_reachable"],
        b_base["prompt_findings_sent"],
        b_base["crit_high_reachable"],
    ]
    vals_opt = [
        b_opt["raw_findings_total"],
        b_opt["unique_findings_total"],
        b_opt["reachable_findings"],
        b_opt["non_low_reachable"],
        b_opt["prompt_findings_sent"],
        b_opt["crit_high_reachable"],
    ]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    y = np.arange(len(c1["stages"]))
    h = 0.36
    bars_base = ax.barh(y - h / 2, vals_base, height=h, color=c1["color_baseline"], edgecolor=c1["edge_baseline"], label=c1["legend_baseline"])
    bars_opt = ax.barh(y + h / 2, vals_opt, height=h, color=c1["color_optimized"], edgecolor=c1["edge_optimized"], label=c1["legend_optimized"])

    ax.set_yticks(y)
    ax.set_yticklabels(c1["stages"])
    ax.invert_yaxis()
    ax.set_xlabel(c1["xlabel"])
    ax.set_title(c1["title"])
    ax.set_xlim(0, max(vals_base + vals_opt) * 1.2)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", frameon=True)

    for bar, v in zip(bars_base, vals_base):
        ax.text(v + 5, bar.get_y() + bar.get_height() / 2, f"{v}", va="center", ha="left", fontsize=9, color="#334155")

    for idx, (bar, v) in enumerate(zip(bars_opt, vals_opt)):
        pct_drop = ((b_opt["raw_findings_total"] - v) / b_opt["raw_findings_total"]) * 100
        txt = f"{v}" if idx == 0 else f"{v}  (-{pct_drop:.1f}%)"
        color = "#15803d" if v == 0 else "#1e3a8a"
        ax.text(v + 5, bar.get_y() + bar.get_height() / 2, txt, va="center", ha="left", fontsize=9, fontweight="bold", color=color)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig1_filtering_funnel.png"), dpi=dpi)
    plt.close(fig)

    # ==========================================================================
    # Figure 2: SBOM Pruning & Critical/High False-Blocker Elimination
    # ==========================================================================
    c2 = CHART_CONFIG["fig2"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4))

    comps = [b["components"] for b in builds]
    covs = [b["sbom_coverage"] for b in builds]
    bar_colors = ["#94a3b8" if c > 100 else "#0ea5e9" for c in comps]
    b1 = ax1.bar(x, comps, width=0.52, color=bar_colors, edgecolor="#0369a1", zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel(c2["ylabel_a_left"])
    ax1.set_ylim(0, max(comps) * 1.22)
    ax1.set_title(c2["title_a"])
    ax1.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, c in zip(b1, comps):
        ax1.text(bar.get_x() + bar.get_width() / 2, c + 4, f"{c}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    if len(builds) >= 3:
        ax1.annotate(
            c2["prune_annotation"],
            xy=(2.0, 96),
            xytext=(2.85, 162),
            arrowprops=dict(arrowstyle="->", color="#0f766e", lw=1.6),
            fontsize=9,
            fontweight="bold",
            color="#0f766e",
            ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="#ccfbf1", ec="#0f766e", lw=0.9),
            zorder=6,
        )

    ax1_r = ax1.twinx()
    ax1_r.spines["top"].set_visible(False)
    ax1_r.plot(x, covs, color="#f59e0b", marker="o", lw=2, markersize=6, label=c2["legend_cov"], zorder=5)
    ax1_r.axhline(90.0, color="#dc2626", linestyle=":", lw=1.4, label=c2["legend_thresh"])
    ax1_r.set_ylabel(c2["ylabel_a_right"], color="#b45309")
    ax1_r.set_ylim(80, 102)
    ax1_r.legend(loc="lower left", fontsize=8.5, frameon=True)

    crit_raw = [b["crit_high_unique"] for b in builds]
    crit_reach = [b["crit_high_reachable"] for b in builds]
    w = 0.36
    br_raw = ax2.bar(x - w / 2, crit_raw, width=w, color="#fca5a5", edgecolor="#b91c1c", label=c2["legend_crit_raw"], zorder=3)
    br_rch = ax2.bar(x + w / 2, crit_reach, width=w, color="#16a34a", edgecolor="#14532d", label=c2["legend_crit_reach"], zorder=3)

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel(c2["ylabel_b"])
    ax2.set_ylim(0, max(crit_raw + [16]) + 4)
    ax2.set_title(c2["title_b"])
    ax2.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax2.legend(loc="upper right", frameon=True)

    for i, (r_bar, a_bar, rv, av) in enumerate(zip(br_raw, br_rch, crit_raw, crit_reach)):
        g_txt, g_col = _gate_badge(builds[i])
        ax2.text(r_bar.get_x() + r_bar.get_width() / 2, rv + 0.35, str(rv), ha="center", va="bottom", fontsize=9, color="#991b1b", fontweight="bold")
        ax2.text(a_bar.get_x() + a_bar.get_width() / 2, av + 0.35, str(av), ha="center", va="bottom", fontsize=9, color="#14532d", fontweight="bold")
        ax2.text(
            x[i], max(rv, av) + 2.3, g_txt, ha="center", va="bottom", fontsize=8, fontweight="bold",
            color=g_col, bbox=dict(boxstyle="round,pad=0.2", fc="#f8fafc", ec=g_col, lw=0.8),
        )

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig2_sbom_and_blockers.png"), dpi=dpi)
    plt.close(fig)

    # ==========================================================================
    # Figure 3: Prompt Compression & Filtered FP Categories
    # ==========================================================================
    c3 = CHART_CONFIG["fig3"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4))

    leg_chars = [b["legacy_prompt_chars"] / 1000.0 for b in builds]
    cmp_chars = [b["compact_prompt_chars"] / 1000.0 for b in builds]

    p1 = ax1.bar(x - w / 2, leg_chars, width=w, color="#f87171", edgecolor="#991b1b", label=c3["legend_legacy"], zorder=3)
    p2 = ax1.bar(x + w / 2, cmp_chars, width=w, color="#3b82f6", edgecolor="#1e3a8a", label=c3["legend_compact"], zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel(c3["ylabel_a"])
    ax1.set_ylim(0, max(leg_chars) * 1.35)
    ax1.set_title(c3["title_a"])
    ax1.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax1.legend(loc="upper right", frameon=True, fontsize=8.5)

    for bar, v in zip(p1, leg_chars):
        ax1.text(bar.get_x() + bar.get_width() / 2, v + 0.45, f"{v:.1f}k", ha="center", va="bottom", fontsize=8.5, color="#991b1b")
    for i, (bar, v) in enumerate(zip(p2, cmp_chars)):
        pct = builds[i]["prompt_char_compression_pct"]
        ax1.text(bar.get_x() + bar.get_width() / 2 + 0.04, v + 0.45, f"{v:.1f}k\n(-{pct:.0f}%)", ha="center", va="bottom", fontsize=7.8, fontweight="bold", color="#1e3a8a")

    reasons = c3["fp_reasons"]
    counts = c3["fp_counts"]
    y2 = np.arange(len(reasons))
    bars_fp = ax2.barh(y2, counts, height=0.5, color=c3["fp_colors"], edgecolor="#334155", zorder=3)
    ax2.set_yticks(y2)
    ax2.set_yticklabels(reasons)
    ax2.invert_yaxis()
    ax2.set_xlabel(c3["xlabel_b"])
    ax2.set_xlim(0, max(counts) * 1.37)
    ax2.set_title(c3["title_b"])
    ax2.grid(axis="x", linestyle="--", alpha=0.4, zorder=0)

    for bar, c in zip(bars_fp, counts):
        pct = (c / sum(counts)) * 100.0
        ax2.text(c + 0.4, bar.get_y() + bar.get_height() / 2, f"{c}  ({pct:.1f}%)", va="center", ha="left", fontsize=9.5, fontweight="bold")

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig3_prompt_compression_and_fp.png"), dpi=dpi)
    plt.close(fig)

    print(f"Generated charts in {os.path.abspath(out_dir)}:")
    for name in (
        "fig1_filtering_funnel.png",
        "fig2_sbom_and_blockers.png",
        "fig3_prompt_compression_and_fp.png",
    ):
        print(" -", os.path.join(out_dir, name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Matplotlib evaluation charts for SEMAR.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Output directory (default: logs/evaluation)")
    parser.add_argument("--refresh", action="store_true", help="Re-query MongoDB before plotting")
    args = parser.parse_args()

    stats_path = os.path.join(args.out_dir, "filtering_evaluation_stats.json")
    if args.refresh or not os.path.exists(stats_path):
        data = asyncio.get_event_loop().run_until_complete(collect_evaluation())
        write_outputs(data, out_dir=args.out_dir)
    else:
        with open(stats_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    render_charts(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
