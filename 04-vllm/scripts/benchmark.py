#!/usr/bin/env python3
"""
Concurrency-sweep benchmark comparing HF Transformers (phase 3) vs vLLM (phase 4)
serving the same model (Qwen2.5-0.5B-Instruct) on the same GPU hardware.

Fires increasing levels of truly concurrent requests (1, 2, 4, 8, 16 by default) at a
single endpoint and records per-level throughput (requests/sec) and per-request latency.
The point isn't single-request TTFT/TPOT -- it's how each engine's throughput and latency
behave as concurrent load increases, since that's where continuous batching (vLLM) should
diverge from HF's sequential-per-replica handling.

Two engines, two request/response contracts:
  --engine hf   -> phase 3's custom POST /generate
                   body: {"prompt": ..., "max_new_tokens": ...}
                   response: {"response": "..."}
  --engine vllm -> ray.serve.llm's OpenAI-compatible POST /v1/chat/completions
                   body: {"model": ..., "messages": [...], "max_tokens": ...}
                   response: .choices[0].message.content

Uses a pool of distinct prompts, cycled across requests -- not one repeated prompt --
since vLLM's automatic prefix caching would make identical repeated prompts unfairly
fast, which would measure caching, not concurrent-load handling.

A short warmup phase runs before the real sweep, since the first request to a freshly
started replica includes cold-start overhead (CUDA context init, etc.) that has nothing
to do with the engine's actual concurrent-load behavior.

Usage:
  python benchmark.py --engine hf   --url http://localhost:8000/generate            --out results_hf.json
  python benchmark.py --engine vllm --url http://localhost:8000/v1/chat/completions --out results_vllm.json
"""
import argparse
import asyncio
import json
import time

import aiohttp

PROMPTS = [
    "What is Kubernetes?",
    "What is Ray?",
    "What is Docker?",
    "What is Python?",
    "What is a container?",
    "What is a GPU?",
    "What is an API?",
    "What is a load balancer?",
    "What is a database index?",
    "What is a message queue?",
    "What is a reverse proxy?",
    "What is a CDN?",
    "What is DNS?",
    "What is TCP?",
    "What is a microservice?",
    "What is a container registry?",
]


def build_payload(engine: str, model: str, prompt: str, max_tokens: int) -> dict:
    if engine == "hf":
        return {"prompt": prompt, "max_new_tokens": max_tokens}
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }


def extract_text(engine: str, body: dict) -> str:
    if engine == "hf":
        return body.get("response", "")
    return body["choices"][0]["message"]["content"]


async def fire_one(session: aiohttp.ClientSession, url: str, payload: dict, engine: str) -> dict:
    start = time.monotonic()
    async with session.post(url, json=payload) as resp:
        status = resp.status
        body = await resp.json()
    end = time.monotonic()
    text = extract_text(engine, body) if status == 200 else ""
    return {"latency_s": end - start, "status": status, "response_chars": len(text)}


async def run_level(url: str, engine: str, model: str, concurrency: int, max_tokens: int) -> dict:
    async with aiohttp.ClientSession() as session:
        payloads = [
            build_payload(engine, model, PROMPTS[i % len(PROMPTS)], max_tokens)
            for i in range(concurrency)
        ]
        batch_start = time.monotonic()
        results = await asyncio.gather(*[fire_one(session, url, p, engine) for p in payloads])
        batch_duration = time.monotonic() - batch_start

    latencies = [r["latency_s"] for r in results]
    failures = [r for r in results if r["status"] != 200]
    return {
        "concurrency": concurrency,
        "batch_duration_s": batch_duration,
        "throughput_req_per_s": concurrency / batch_duration,
        "latency_avg_s": sum(latencies) / len(latencies),
        "latency_min_s": min(latencies),
        "latency_max_s": max(latencies),
        "failures": len(failures),
    }


async def warmup(url: str, engine: str, model: str, max_tokens: int, n: int) -> None:
    print(f"--- warmup ({n} sequential requests, discarded) ---")
    async with aiohttp.ClientSession() as session:
        for i in range(n):
            payload = build_payload(engine, model, PROMPTS[i % len(PROMPTS)], max_tokens)
            await fire_one(session, url, payload, engine)


async def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["hf", "vllm"], required=True)
    parser.add_argument("--url", required=True, help="Full endpoint URL")
    parser.add_argument("--model", default="qwen-0.5b", help="Model id (vLLM/OpenAI payload only)")
    parser.add_argument("--concurrency-levels", default="1,2,4,8,16")
    parser.add_argument("--max-tokens", type=int, default=50)
    parser.add_argument("--warmup-requests", type=int, default=2)
    parser.add_argument("--out", required=True, help="Path to write JSON results")
    args = parser.parse_args()

    await warmup(args.url, args.engine, args.model, args.max_tokens, args.warmup_requests)

    levels = [int(x) for x in args.concurrency_levels.split(",")]
    results = []
    for level in levels:
        print(f"--- concurrency={level} ---")
        r = await run_level(args.url, args.engine, args.model, level, args.max_tokens)
        print(r)
        results.append(r)

    with open(args.out, "w") as f:
        json.dump({"engine": args.engine, "results": results}, f, indent=2)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
