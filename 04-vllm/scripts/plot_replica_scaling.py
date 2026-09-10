#!/usr/bin/env python3
"""
Reads results_vllm_1replica_extended.json and results_vllm_2replica_run2.json (output of
benchmark.py) and produces two charts: throughput vs concurrency and average latency vs
concurrency, comparing 1 vs 2 vLLM replicas. Concurrency levels double each step
(1,2,4,8,16,32,64,128,256), so the x-axis uses a log2 scale.

Usage:
  python plot_replica_scaling.py --one-replica results_vllm_1replica_extended.json \
      --two-replica results_vllm_2replica_run2.json --out-dir .
"""
import argparse
import json

import matplotlib.pyplot as plt


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def plot_metric(one: dict, two: dict, metric: str, ylabel: str, title: str, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for data, label, color, marker in [(one, "1 replica", "#d62728", "o"), (two, "2 replicas", "#1f77b4", "s")]:
        levels = [r["concurrency"] for r in data["results"]]
        values = [r[metric] for r in data["results"]]
        ax.plot(levels, values, label=label, color=color, marker=marker, linewidth=2, markersize=7)

    ax.set_xscale("log", base=2)
    all_levels = sorted({r["concurrency"] for r in one["results"] + two["results"]})
    ax.set_xticks(all_levels)
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("Concurrent requests")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Wrote {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--one-replica", required=True)
    parser.add_argument("--two-replica", required=True)
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    one = load(args.one_replica)
    two = load(args.two_replica)

    plot_metric(
        one, two, "throughput_req_per_s", "Throughput (requests/sec)",
        "Throughput vs concurrency: 1 vs 2 vLLM replicas\nQwen2.5-0.5B-Instruct, T4 GPUs",
        f"{args.out_dir}/replica_scaling_throughput.png",
    )
    plot_metric(
        one, two, "latency_avg_s", "Average latency per request (s)",
        "Latency under load: 1 vs 2 vLLM replicas\nQwen2.5-0.5B-Instruct, T4 GPUs",
        f"{args.out_dir}/replica_scaling_latency.png",
    )


if __name__ == "__main__":
    main()
