# Ray Dashboard — Serve tab (`llm_app` overview, 2 replicas)

## What we're looking at

The Serve tab after fixing the OOM/`DEPLOY_FAILED` deadlock and successfully running with `num_replicas: 2`:

- **Controller status: HEALTHY**
- **Proxy status: HEALTHY x 3** — one proxy per Ray node. Up from phase 1's `x 2` because this setup now has
  3 nodes total (1 head + 2 workers) instead of 2.
- **Application status: RUNNING x 1**

The `llm_app` / `QwenChat` table shows `QwenChat` as `HEALTHY` with **2 replicas** — confirming the fix actually
worked: both replicas are up and serving, not stuck retrying.

## Significance

This is the payoff screen for the whole phase-2 debugging arc (OOM → `DEPLOY_FAILED` deadlock → memory-aware
`ray_actor_options` fix → clean restart). Getting `QwenChat: HEALTHY` with `2` replicas here means:

- Both replicas successfully loaded the Qwen2.5-0.5B-Instruct model without OOM-killing each other.
- Ray Serve is not retrying or reporting any deployment errors.
- The proxy count (`x3`) directly reflects the worker group actually having 2 workers now, which only happened
  because the autoscaler could correctly recognize the second replica needed a new node once its `memory`
  resource was declared accurately (see the root-cause writeup in `02-num-replicas/README.md`).
