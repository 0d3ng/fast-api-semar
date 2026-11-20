"""Plot publication-grade Matplotlib charts (PNG 300 DPI) for Evaluation 2 (Qwen3:8B Sensitivity).

Edit labels, titles, and colors in `CHART_CONFIG` below, then run:
    python -m app.scripts.plot_qwen3_sensitivity_charts
    python -m app.scripts.plot_qwen3_sensitivity_charts --refresh   # Re-run live Ollama benchmark
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
        "matplotlib is required. Install with: pip install matplotlib"
    ) from exc

from app.scripts.eval_qwen3_sensitivity import (
    DEFAULT_MODEL,
    DEFAULT_OUT_DIR,
    run_benchmark,
    write_outputs,
)

# ==============================================================================
# EDITABLE LABELS, TITLES & STYLING CONFIG (Ubah label/warna di sini)
# ==============================================================================
CHART_CONFIG: Dict[str, Any] = {
    "dpi": 300,
    "font_family": "sans-serif",
    "font_sans": ["DejaVu Sans", "Arial", "Helvetica"],

    "fig4": {
        "title_a": "(a) Consistency & Grounding Accuracy vs. Temperature",
        "xlabel_a": "Sampling Temperature (Qwen3:8B)",
        "ylabel_a": "Percentage (%)",
        "legend_dec_consist": "Decision Consistency (%)",
        "legend_risk_consist": "Risk Rating Consistency (%)",
        "legend_ground": "FID Grounding Accuracy (%)",

        "title_b": "(b) Inference Latency & Output Length vs. Temperature",
        "xlabel_b": "Sampling Temperature (Qwen3:8B)",
        "ylabel_b_left": "Mean Inference Latency (s)",
        "ylabel_b_right": "Mean Completion Tokens",
        "legend_latency": "Mean Latency ± SD (s)",
        "legend_tokens": "Completion Tokens",
    },

    "fig5": {
        "title_a": "(a) Prompt Context Size vs. Latency & Key Coverage",
        "ylabel_a_left": "Inference Latency (s)",
        "ylabel_a_right": "Key Findings Coverage (%)",
        "legend_latency": "Inference Latency (s)",
        "legend_coverage": "Key Priority Coverage (%)",

        "title_b": "(b) Decoding Mode Impact (Thinking & JSON Schema)",
        "ylabel_b": "Inference Latency (s)",
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
        "xtick.labelsize": 9.0,
        "ytick.labelsize": 9.2,
        "legend.fontsize": 8.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def render_charts(data: Dict[str, Any], out_dir: str) -> None:
    _apply_style()
    os.makedirs(out_dir, exist_ok=True)
    dpi = CHART_CONFIG["dpi"]

    # ==========================================================================
    # Figure 4: Temperature Sensitivity (Consistency, Grounding & Latency)
    # ==========================================================================
    c4 = CHART_CONFIG["fig4"]
    t_rows = data["experiment_2a_temperature"]
    t_labels = [f"T={r['temperature']:.1f}" for r in t_rows]
    x = np.arange(len(t_rows))
    w = 0.25

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 4.5))

    dec_c = [r["decision_consistency_pct"] for r in t_rows]
    risk_c = [r["risk_consistency_pct"] for r in t_rows]
    ground_a = [r["raw_grounding_acc_pct"] for r in t_rows]

    b1 = ax1.bar(x - w, dec_c, width=w, color="#2563eb", edgecolor="#1e3a8a", label=c4["legend_dec_consist"], zorder=3)
    b2 = ax1.bar(x, risk_c, width=w, color="#f59e0b", edgecolor="#b45309", label=c4["legend_risk_consist"], zorder=3)
    b3 = ax1.bar(x + w, ground_a, width=w, color="#16a34a", edgecolor="#14532d", label=c4["legend_ground"], zorder=3)

    ax1.set_xticks(x)
    ax1.set_xticklabels(t_labels)
    ax1.set_xlabel(c4["xlabel_a"])
    ax1.set_ylabel(c4["ylabel_a"])
    ax1.set_ylim(0, 122)
    # ax1.set_title(c4["title_a"])
    ax1.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax1.legend(loc="lower left", frameon=True)

    for bars in (b1, b2, b3):
        for bar in bars:
            v = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, v + 1.8, f"{v:.0f}%", ha="center", va="bottom", fontsize=7.2, fontweight="bold")

    # Panel (b): Latency & Completion Tokens
    lat_m = [r["mean_latency_s"] for r in t_rows]
    lat_s = [r["std_latency_s"] for r in t_rows]
    toks = [r["mean_completion_tokens"] for r in t_rows]

    bars_lat = ax2.bar(x, lat_m, yerr=lat_s, capsize=4, width=0.45, color="#60a5fa", edgecolor="#1d4ed8", label=c4["legend_latency"], zorder=3)
    ax2.set_xticks(x)
    ax2.set_xticklabels(t_labels)
    ax2.set_xlabel(c4["xlabel_b"])
    ax2.set_ylabel(c4["ylabel_b_left"], color="#1d4ed8")
    ax2.set_ylim(0, max([m + s for m, s in zip(lat_m, lat_s)] + [10]) * 1.35)
    # ax2.set_title(c4["title_b"])
    ax2.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, m, s in zip(bars_lat, lat_m, lat_s):
        ax2.text(bar.get_x() + bar.get_width() / 2, m + s + 2.2, f"{m:.1f}s", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1e3a8a")

    ax2_r = ax2.twinx()
    ax2_r.spines["top"].set_visible(False)
    ax2_r.plot(x, toks, color="#dc2626", marker="s", lw=2, markersize=6, label=c4["legend_tokens"], zorder=5)
    ax2_r.set_ylabel(c4["ylabel_b_right"], color="#b91c1c")
    ax2_r.set_ylim(0, max(toks + [200]) * 1.35)

    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2_r.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig4_qwen3_temperature_sensitivity.png"), dpi=dpi)
    plt.close(fig)

    # ==========================================================================
    # Figure 5: Prompt Context Size Sweep & Decoding Mode Impact
    # ==========================================================================
    c5 = CHART_CONFIG["fig5"]
    c_rows = data["experiment_2b_context_size"]
    m_rows = data["experiment_2c_decoding_modes"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.6))

    c_labels = [r["label"].replace(" (", "\n(") for r in c_rows]
    xc = np.arange(len(c_rows))
    c_lat = [r["latency_s"] for r in c_rows]
    c_cov = [r["key_findings_coverage_pct"] for r in c_rows]
    c_colors = ["#16a34a" if "Default" in r["label"] else ("#ef4444" if r["status"] != "ok" else "#64748b") for r in c_rows]

    bars_c = ax1.bar(xc, c_lat, width=0.52, color=c_colors, edgecolor="#1e293b", label=c5["legend_latency"], zorder=3)
    ax1.set_xticks(xc)
    ax1.set_xticklabels(c_labels, fontsize=8.2)
    ax1.set_ylabel(c5["ylabel_a_left"])
    ax1.set_ylim(0, max(c_lat + [15]) * 1.42)
    ax1.set_title(c5["title_a"])
    ax1.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, r in zip(bars_c, c_rows):
        v = r["latency_s"]
        if r["status"] != "ok":
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                v * 0.55,
                f"{v:.1f}s\nTIMEOUT",
                ha="center",
                va="center",
                fontsize=8.2,
                fontweight="bold",
                color="white",
                zorder=6,
            )
        else:
            dec = r.get("recommended_decision") or ""
            sub = "\n(PASS - Missed!)" if (dec == "PASS" and r["key_findings_coverage_pct"] < 100) else f"\n({dec})"
            sub_col = "#b45309" if "Missed" in sub else "#0f172a"
            ax1.text(bar.get_x() + bar.get_width() / 2, v + 2.0, f"{v:.1f}s{sub}", ha="center", va="bottom", fontsize=7.6, fontweight="bold", color=sub_col)

    ax1_r = ax1.twinx()
    ax1_r.spines["top"].set_visible(False)
    ax1_r.plot(xc, c_cov, color="#f59e0b", marker="o", lw=2, markersize=6, label=c5["legend_coverage"], zorder=5)
    ax1_r.set_ylabel(c5["ylabel_a_right"], color="#b45309")
    ax1_r.set_ylim(0, 122)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_r.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True, fontsize=8.2)

    # Panel (b): Decoding Modes
    xm = np.arange(len(m_rows))
    m_labels = [r["label"] for r in m_rows]
    m_lat = [r["latency_s"] for r in m_rows]
    m_colors = ["#16a34a" if (r["schema_ok"] and r["grounding_ok"] and not r["think"]) else ("#f59e0b" if r["schema_ok"] else "#ef4444") for r in m_rows]

    bars_m = ax2.bar(xm, m_lat, width=0.48, color=m_colors, edgecolor="#1e293b", zorder=3)
    ax2.set_xticks(xm)
    ax2.set_xticklabels(m_labels, fontsize=8.4)
    ax2.set_ylabel(c5["ylabel_b"])
    ax2.set_ylim(0, max(m_lat + [15]) * 1.35)
    ax2.set_title(c5["title_b"])
    ax2.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)

    for bar, r in zip(bars_m, m_rows):
        v = r["latency_s"]
        badge = "Schema OK\nGrounding OK" if (r["schema_ok"] and r["grounding_ok"]) else ("Schema OK\nFiltered" if r["schema_ok"] else "SCHEMA FAIL")
        if r["status"] == "error":
            badge = "TIMEOUT"
        b_col = "#15803d" if (r["schema_ok"] and r["grounding_ok"]) else "#b91c1c"
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            v + max(m_lat + [15]) * 0.03,
            f"{v:.1f}s ({r['completion_tokens']} tok)\n{badge}",
            ha="center",
            va="bottom",
            fontsize=8.0,
            fontweight="bold",
            color=b_col,
        )

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig5_qwen3_context_and_mode.png"), dpi=dpi)
    plt.close(fig)

    print(f"Generated Evaluation 2 charts in {os.path.abspath(out_dir)}:")
    print(" -", os.path.join(out_dir, "fig4_qwen3_temperature_sensitivity.png"))
    print(" -", os.path.join(out_dir, "fig5_qwen3_context_and_mode.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Evaluation 2 Matplotlib charts for Qwen3:8B.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--refresh", action="store_true", help="Re-run Ollama benchmark before plotting")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    stats_path = os.path.join(args.out_dir, "qwen3_evaluation_stats.json")
    if args.refresh or not os.path.exists(stats_path):
        data = asyncio.get_event_loop().run_until_complete(
            run_benchmark(model=args.model, repeats=args.repeats)
        )
        write_outputs(data, out_dir=args.out_dir)
    else:
        with open(stats_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    render_charts(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
