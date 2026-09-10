<!--
Images to attach when posting (LinkedIn supports multiple, shown as a carousel):
1. ../04-vllm/dashboard/throughput_comparison.png — HF flat ~0.6 req/s vs vLLM scaling to 16.8 req/s at concurrency 16
2. ../04-vllm/dashboard/scaling/replica_scaling_throughput.png — 1 vs 2 vLLM replicas, lines overlap then split hard past concurrency 16
3. ../04-vllm/dashboard/cluster-gpu-allocated.png — Ray dashboard showing the GPU at 86% utilization during active generation
-->

Continuing from the EKS post: same model, same GPU hardware, one thing changed — swapped HuggingFace Transformers for vLLM, using Ray's own `ray.serve.llm` module.

Getting it deployed took three real bugs, three different categories of mistake: a config field verified against "latest" docs instead of the actual pinned version (it didn't exist yet in that release), asking for the same GPU twice without realizing vLLM already reserves one internally, and trusting vLLM's default numeric precision on a GPU generation that doesn't support it.

The comparison itself is the real story. I expected a modest gap — a 0.5B model seemed too small for batching to matter much. It wasn't modest. At 16 concurrent requests, vLLM delivered ~27x the throughput of plain Transformers, latency flat under a second while the old setup's climbed past 13. Counterintuitively, the small model seemed to benefit *more* from batching, not less — likely because fixed per-request overhead dominates more when the model's own compute cost is tiny. Plausible, not confirmed — would need profiling to actually verify.

Scaled to 2 GPU workers next, pushing the concurrency sweep up to 256 — confirmed a second replica genuinely extends the ceiling a single replica saturates at, not just idle redundancy.

Also found a real gap in eksctl itself along the way — the auto-installed NVIDIA device plugin has no way to restrict itself to GPU-only nodes, so it can crash-loop its way into taking down an unrelated node. Filed it upstream.

Full writeup: https://github.com/jagrutsharma/multinode-llm-serving/blob/main/04-vllm/README.md

Next up: same setup, a meaningfully bigger model — testing whether this batching advantage holds, shrinks, or grows once the model's own compute time actually dominates.

#LLMInference #Kubernetes #KubeRay #RayServe #vLLM #AWS #GPU
