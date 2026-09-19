<!--
Image to attach when posting:
1. ../04-vllm/dashboard/cost_breakdown.png — prefill $0.06 vs decode $1.11, decode ~95% of total cost
-->

# Why decode dominates the cost of LLM inference

*Published on LinkedIn: [add link after posting]*

Serving a request has two phases with very different economics:
- **Prefill** processes the whole prompt in one parallel pass — fast.
- **Decode** generates output one token at a time, streaming all the model weights per token — slow.

On a rented GPU, the hourly cost is fixed whether it's busy or idle. So cost tracks *time on the GPU* — and the slow phase dominates.

A quick illustrative example ($2/hr GPU, 1,000 requests, 100 in / 200 out tokens each — rough numbers to show the shape):
- Prefill: ~$0.06
- Decode: ~$1.11

Decode ends up ~95% of the cost — for two compounding reasons: more tokens (longer output), and slower per token (sequential vs. parallel). The slowness matters more than the length.

That's *why* nearly every serving optimization — continuous batching, paged attention, quantization, prefix caching — targets decode. Faster decode → more tokens per hour → lower cost per token, on the same hardware at the same price.

When I did measure it — vLLM vs. plain HuggingFace Transformers on the same GPU — vLLM hit ~27× decode throughput under concurrency. By this math, that's roughly a 96% cut in cost per token. Same GPU, same hourly rate; the optimization *is* the cost saving.

Full breakdown and calculations: https://github.com/jagrutsharma/multinode-llm-serving/blob/main/04-vllm/README.md#why-decode-dominates-the-cost-of-llm-inference

#LLMInference #GPU #vLLM #RayServe #MLInfra
