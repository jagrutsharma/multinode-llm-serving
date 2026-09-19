#!/usr/bin/env python3
"""
Bar chart of the illustrative prefill-vs-decode cost breakdown from the "Why decode
dominates the cost of LLM inference" section of README.md. Numbers are hardcoded from
that worked example (not read from a results file), since they're a worked calculation,
not a benchmark result.

Usage:
  python plot_cost_breakdown.py --out-dir .
"""
import argparse

import matplotlib.pyplot as plt

PREFILL_COST = 0.06
DECODE_COST = 1.11


def plot_cost_breakdown(out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))

    labels = ["Prefill", "Decode"]
    costs = [PREFILL_COST, DECODE_COST]
    colors = ["#1f77b4", "#d62728"]

    bars = ax.bar(labels, costs, color=colors, width=0.5)
    for bar, cost in zip(bars, costs):
        ax.text(bar.get_x() + bar.get_width() / 2, cost, f"${cost:.2f}",
                 ha="center", va="bottom", fontsize=12, fontweight="bold")

    total = PREFILL_COST + DECODE_COST
    decode_pct = DECODE_COST / total * 100
    ax.text(1, DECODE_COST / 2, f"~{decode_pct:.0f}% of\ntotal cost",
             ha="center", va="center", fontsize=11, color="white", fontweight="bold")

    ax.set_ylabel("Cost ($)")
    ax.set_title(
        "Cost breakdown: prefill vs decode (illustrative)\n"
        "$2/hr GPU · 1,000 requests · 100 in / 200 out tokens each"
    )
    ax.set_ylim(0, DECODE_COST * 1.2)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Wrote {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    plot_cost_breakdown(f"{args.out_dir}/cost_breakdown.png")


if __name__ == "__main__":
    main()
