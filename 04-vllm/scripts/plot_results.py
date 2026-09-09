#!/usr/bin/env python3
"""
Reads results_hf.json and results_vllm.json (output of benchmark.py) and produces two
charts: throughput vs concurrency (the main comparison) and average latency vs
concurrency (supporting evidence). Concurrency levels double each step (1,2,4,8,16), so
the x-axis uses a log2 scale -- otherwise the low end visually compresses into nothing.

Usage:
  python plot_results.py --hf results_hf.json --vllm results_vllm.json --out-dir .
"""
import argparse
import json

import matplotlib.pyplot as plt


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def plot_throughput(hf: dict, vllm: dict, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for data, label, color, marker in [(hf, "HF Transformers", "#d62728", "o"), (vllm, "vLLM", "#1f77b4", "s")]:
        levels = [r["concurrency"] for r in data["results"]]
        throughput = [r["throughput_req_per_s"] for r in data["results"]]
        ax.plot(levels, throughput, label=label, color=color, marker=marker, linewidth=2, markersize=7)

    ax.set_xscale("log", base=2)
    all_levels = sorted({r["concurrency"] for r in hf["results"] + vllm["results"]})
    ax.set_xticks(all_levels)
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("Concurrent requests")
    ax.set_ylabel("Throughput (requests/sec)")
    ax.set_title("Throughput vs concurrency: HF Transformers vs vLLM\nQwen2.5-0.5B-Instruct, single T4 GPU")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Wrote {out_path}")


def plot_latency(hf: dict, vllm: dict, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for data, label, color, marker in [(hf, "HF Transformers", "#d62728", "o"), (vllm, "vLLM", "#1f77b4", "s")]:
        levels = [r["concurrency"] for r in data["results"]]
        latency = [r["latency_avg_s"] for r in data["results"]]
        ax.plot(levels, latency, label=label, color=color, marker=marker, linewidth=2, markersize=7)

    ax.set_xscale("log", base=2)
    all_levels = sorted({r["concurrency"] for r in hf["results"] + vllm["results"]})
    ax.set_xticks(all_levels)
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("Concurrent requests")
    ax.set_ylabel("Average latency per request (s)")
    ax.set_title("Latency under load: HF Transformers vs vLLM\nQwen2.5-0.5B-Instruct, single T4 GPU")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Wrote {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hf", required=True, help="Path to results_hf.json")
    parser.add_argument("--vllm", required=True, help="Path to results_vllm.json")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    hf = load(args.hf)
    vllm = load(args.vllm)

    plot_throughput(hf, vllm, f"{args.out_dir}/throughput_comparison.png")
    plot_latency(hf, vllm, f"{args.out_dir}/latency_comparison.png")


if __name__ == "__main__":
    main()
