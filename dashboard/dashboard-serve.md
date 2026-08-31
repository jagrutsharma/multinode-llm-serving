# Ray Dashboard — Serve tab (`llm_app` overview)

## What we're looking at

The top-level Serve tab, showing the overall health of the Ray Serve deployment on the `rayservice-sample`
cluster:

- **Controller status: HEALTHY** — the Serve controller (runs on the head node) is up and managing the
  deployment lifecycle.
- **Proxy status: HEALTHY x 2** — one HTTP proxy actor per Ray node (head + the one worker), both healthy.
- **Application status: RUNNING x 1** — the single application, `llm_app`.

Below that, the Applications/Deployments table shows:

- **`llm_app`** — status `RUNNING`, route prefix `/generate`, last deployed `2026/08/30 19:29:48`.
- **`QwenChat`** (the deployment inside `llm_app`) — status `HEALTHY`, `1` replica, same deploy timestamp.

## Significance

This is the single best "is everything okay" screen for Ray Serve. Each piece maps directly to something in
`ray-service-sample.yaml` / `llm_app/serve_llm.py`:

- The route prefix `/generate` matches `route_prefix: /generate` in `serveConfigV2`.
- `1` replica matches `num_replicas: 1` under the `QwenChat` deployment config.
- **Proxy HEALTHY x 2, not x 1** is a direct consequence of `headGroupSpec.rayStartParams.num-cpus: "0"` in the
  manifest: even though that setting keeps the `QwenChat` model replica off the head node (it requests
  `num_cpus: 1`, which the head can't offer), the lightweight HTTP proxy actors still run on *every* node
  (head + worker) since they need ~0 CPU. This is exactly why `curl`-ing the head service's `/generate` route
  still works — the head's proxy receives the request and forwards it internally to the replica running on the
  worker.
- `HEALTHY` on both `llm_app` and `QwenChat` confirms the model loaded successfully and Serve considers it
  ready to take traffic — if the model had failed to load (e.g. an OOM or a bad Hugging Face model name), this
  screen would show `UNHEALTHY` or `DEPLOY_FAILED` with a status message explaining why.
