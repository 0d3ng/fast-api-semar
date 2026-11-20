"""Plot Matplotlib charts (PNG 300 DPI) for Evaluation 3 Stage 1 (Threat Validation & Ablation).

Edit labels, titles, and colors in `CHART_CONFIG` below, then run:
    python -m app.scripts.plot_threat_validation_charts
    python -m app.scripts.plot_threat_validation_charts --refresh
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
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
except ImportError as exc:
    raise SystemExit("matplotlib is required. Install with: pip install matplotlib") from exc

from app.scripts.eval_threat_validation import (
    DEFAULT_MODEL,
    DEFAULT_OUT_DIR,
    run_validation,
    write_outputs,
)

# ==============================================================================
# EDITABLE LABELS, TITLES & STYLING CONFIG (Ubah teks label/warna di sini)
# ==============================================================================
CHART_CONFIG: Dict[str, Any] = {
    "dpi": 300,
    "font_family": "sans-serif",
    "font_sans": ["DejaVu Sans", "Arial", "Helvetica"],

    "method_labels": {
        "naive_scanner": "Naive Raw\nScanner",
        "rule_only": "Rule-Only\nPolicy",
        "ai_only": "Pure AI-Only\n(Qwen3:8B)",
        "semar_hybrid": "Proposed SEMAR\nHybrid Gate",
    },

    "fig6": {
        "title": "Ablation Study: Threat Detection, Accuracy & False Alarm Rate (10 Scenarios)",
        "ylabel": "Percentage (%)",
        "legend_acc": "Exact 3-Class Accuracy (%)",
        "legend_recall": "Threat Detection / Recall (%)",
        "legend_fpr": "False Alarm / FPR (%)",
    },

    "fig7": {
        "title": "Scenario-by-Scenario Gate Decision Matrix (Green = Correct, Red = Error)",
        "col_headers": ["Ground Truth", "Naive Scanner", "Rule-Only Policy", "Pure AI-Only", "SEMAR Hybrid"],
        "short_decision": {
            "PASS": "PASS",
            "REVIEW_REQUIRED": "REVIEW",
            "BLOCKED": "BLOCK",
        },
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
        "xtick.labelsize": 9.2,
        "ytick.labelsize": 9.2,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def render_charts(data: Dict[str, Any], out_dir: str) -> None:
    _apply_style()
    os.makedirs(out_dir, exist_ok=True)
    dpi = CHART_CONFIG["dpi"]

    # ==========================================================================
    # Figure 6: Ablation Comparison Bar Chart
    # ==========================================================================
    c6 = CHART_CONFIG["fig6"]
    metrics = data["method_metrics"]
    m_labels = [CHART_CONFIG["method_labels"][m["method"]] for m in metrics]
    x = np.arange(len(metrics))
    w = 0.25

    acc_3 = [m["exact_3class_accuracy_pct"] for m in metrics]
    recall = [m["threat_detection_recall_pct"] for m in metrics]
    fpr = [m["false_alarm_fpr_pct"] for m in metrics]

    fig, ax = plt.subplots(figsize=(9.8, 4.7))
    b1 = ax.bar(x - w, acc_3, width=w, color="#2563eb", edgecolor="#1e3a8a", label=c6["legend_acc"], zorder=3)
    b2 = ax.bar(x, recall, width=w, color="#16a34a", edgecolor="#14532d", label=c6["legend_recall"], zorder=3)
    b3 = ax.bar(x + w, fpr, width=w, color="#ef4444", edgecolor="#991b1b", label=c6["legend_fpr"], zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(m_labels, fontweight="bold")
    ax.set_ylabel(c6["ylabel"])
    ax.set_ylim(0, 120)
    # ax.set_title(c6["title"])
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=True)

    for bars in (b1, b2, b3):
        for bar in bars:
            v = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.8, f"{v:.0f}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig6_ablation_comparison.png"), dpi=dpi)
    plt.close(fig)

    # ==========================================================================
    # Figure 7: Decision Matrix Grid (10 Scenarios x 4 Methods)
    # ==========================================================================
    c7 = CHART_CONFIG["fig7"]
    scenarios = data["scenarios"]
    row_labels = [f"{r['tc_id']}: {r['name']}" for r in scenarios]
    col_keys = ["ground_truth", "naive_scanner", "rule_only", "ai_only", "semar_hybrid"]

    grid_vals = np.zeros((len(scenarios), len(col_keys)), dtype=int)
    text_grid = []

    for i, r in enumerate(scenarios):
        gt = r["ground_truth"]
        gt_unsafe = gt != "PASS"
        row_texts = []
        for j, k in enumerate(col_keys):
            val = r[k]
            row_texts.append(c7["short_decision"].get(val, val))
            if k == "ground_truth":
                grid_vals[i, j] = 0  # Neutral slate
            elif val == gt:
                grid_vals[i, j] = 1  # Exact match (Green)
            elif (val != "PASS") == gt_unsafe:
                grid_vals[i, j] = 2  # Same safety hold, wrong severity tier (Amber)
            else:
                grid_vals[i, j] = 3  # Critical gate error: Missed threat or false block (Red)
        text_grid.append(row_texts)

    # Color map: 0=neutral, 1=green, 2=amber, 3=red
    cmap = ListedColormap(["#e2e8f0", "#bbf7d0", "#fde68a", "#fecaca"])
    text_colors = {0: "#1e293b", 1: "#14532d", 2: "#92400e", 3: "#991b1b"}

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.imshow(grid_vals, cmap=cmap, aspect="auto", vmin=0, vmax=3)

    ax.set_xticks(np.arange(len(col_keys)))
    ax.set_xticklabels(c7["col_headers"], fontweight="bold")
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(scenarios)))
    ax.set_yticklabels(row_labels, fontsize=9.2)

    # Draw cell gridlines
    ax.set_xticks(np.arange(-0.5, len(col_keys), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(scenarios), 1), minor=True)
    ax.grid(which="minor", color="#64748b", linestyle="-", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False, top=False)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#475569")

    for i in range(len(scenarios)):
        for j in range(len(col_keys)):
            code = grid_vals[i, j]
            mark = " ✓" if code == 1 else (" !" if code == 2 else (" ✗" if code == 3 else ""))
            ax.text(
                j, i, text_grid[i][j] + mark,
                ha="center", va="center",
                fontsize=9.0, fontweight="bold",
                color=text_colors[code],
            )

    # ax.set_title(c7["title"], pad=24)
    legend_handles = [
        Patch(facecolor="#e2e8f0", edgecolor="#64748b", label="Ground Truth Reference"),
        Patch(facecolor="#bbf7d0", edgecolor="#14532d", label="Exact Match (✓)"),
        Patch(facecolor="#fde68a", edgecolor="#92400e", label="Held/Blocked, Severity Mismatch (!)"),
        Patch(facecolor="#fecaca", edgecolor="#991b1b", label="Wrong Decision: Threat Escaped / False Alarm (✗)"),
    ]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=2, frameon=True, fontsize=8.6)

    plt.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig7_threat_validation_matrix.png"), dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    print(f"Generated Threat Validation charts in {os.path.abspath(out_dir)}:")
    print(" -", os.path.join(out_dir, "fig6_ablation_comparison.png"))
    print(" -", os.path.join(out_dir, "fig7_threat_validation_matrix.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Stage 1 Threat Validation charts.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--refresh", action="store_true", help="Re-run live validation scenarios")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    stats_path = os.path.join(args.out_dir, "threat_validation_stats.json")
    if args.refresh or not os.path.exists(stats_path):
        data = asyncio.get_event_loop().run_until_complete(run_validation(model=args.model))
        write_outputs(data, out_dir=args.out_dir)
    else:
        with open(stats_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    render_charts(data, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
