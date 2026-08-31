# Ray Dashboard — Serve tab (`QwenChat` replica detail + logs)

## What we're looking at

Drilling into `Serve / llm_app / QwenChat`, this shows the single running replica (`qu2ojxoi`, status
`RUNNING`, started `2026/08/30 19:29:52`) and its live "Serve Logger" output:

```
1 INFO 2026-08-30 19:29:56,621 llm_app_QwenChat qu2ojxoi -- Started initializing replica.
2 INFO 2026-08-30 19:30:00,455 llm_app_QwenChat qu2ojxoi -- Finished initializing replica.
3 INFO 2026-08-30 19:40:22,264 llm_app_QwenChat qu2ojxoi -- Started executing request to method '__call__'.
4 INFO 2026-08-30 19:40:35,234 llm_app_QwenChat qu2ojxoi daae1cbd-... -- POST /generate 200 12987.1ms
5 INFO 2026-08-30 23:55:02,929 llm_app_QwenChat qu2ojxoi -- Started executing request to method '__call__'.
6 INFO 2026-08-30 23:55:18,156 llm_app_QwenChat qu2ojxoi bb14885a-... -- POST /generate 200 15230.5ms
7 INFO 2026-08-30 23:55:45,287 llm_app_QwenChat qu2ojxoi -- Started executing request to method '__call__'.
8 INFO 2026-08-30 23:55:58,147 llm_app_QwenChat qu2ojxoi 260e5a1a-... -- POST /generate 200 12860.9ms
```

## Significance

- **Lines 1-2: replica init took ~4 seconds** (19:29:56 → 19:30:00). This is the `QwenChat.__init__` from
  `llm_app/serve_llm.py` loading the tokenizer and model weights — fast specifically because the Dockerfile
  bakes the Qwen2.5-0.5B-Instruct weights into the image at build time, so there's no Hugging Face Hub download
  happening at pod startup.
- **Lines 3-4: the first real test request** — the "What is Ray Serve in one sentence?" curl from earlier in
  the session — took **12987.1ms (~13s)** end to end and returned `200`.
- **Lines 5-8: two more requests**, made later while reviewing the dashboard, took ~15.2s and ~12.9s
  respectively.
- **This latency (~13-15 seconds per request) is the real cost of CPU-only LLM inference**: greedy decoding
  (`do_sample=False`) of up to `max_new_tokens: 60` on a single CPU core (`ray_actor_options.num_cpus: 1`), with
  no batching. This is the direct trade-off for running a real ~500M-parameter instruction-tuned model without
  a GPU.
- **Requests 6 and 7 don't overlap** — the second request only starts (`23:55:45`) after the first fully
  finishes (`23:55:18`). With `num_replicas: 1`, there's only one actor to route to, so Ray Serve queues
  requests rather than running them concurrently. Bumping `num_replicas` to 2 (with `enableInTreeAutoscaling:
  true` and `maxReplicas: 2` already set on the worker group) would let a second worker come up to host a
  second replica, enabling real concurrent request handling — the same autoscaling pattern that added a second
  worker for the `PearStand` deployment in the original fruit-app example.
