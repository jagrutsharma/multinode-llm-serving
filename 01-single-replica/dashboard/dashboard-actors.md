# Ray Dashboard — Actors tab (internal Serve actor breakdown)

## What we're looking at

The Actors tab lists every Ray actor in the cluster — 4 total, all `ALIVE`, all with `4h 35m` uptime and no
restarts:

| Class | Name | PID | IP |
|---|---|---|---|
| `ServeController` | `SERVE_CONTROLLER_ACTOR` | 407 | `10.42.1.7` (head) |
| `ProxyActor` | `SERVE_PROXY_ACTOR-22d64...` | 455 | `10.42.1.7` (head) |
| `ProxyActor` | `SERVE_PROXY_ACTOR-eb7af...` | 234 | `10.42.0.10` (worker) |
| `ServeReplica:llm_app:QwenChat` | `SERVE_REPLICA::llm_app#QwenChat#qu2ojxoi` | 178 | `10.42.0.10` (worker) |

## Significance

This is the actual set of Ray actors that make up everything shown on the Serve/Cluster tabs — it's the
mechanism behind the summary numbers seen elsewhere:

- **`SERVE_CONTROLLER_ACTOR`** — the single controller actor, always on the head node. Manages deployment
  state and drives the `HEALTHY`/`RUNNING` statuses shown on the Serve tab; doesn't touch inference traffic.
- **Two `ProxyActor`s, one per node** — this is the concrete actor-level reason the Serve tab showed
  "Proxy status: HEALTHY x 2." Every Ray node runs one, regardless of `num-cpus`, because proxies request ~0
  CPU. The head's proxy (`22d64...`) is the one that actually receives external HTTP traffic when you
  `port-forward` to `rayservice-sample-head-svc` and `curl /generate`.
- **`ServeReplica:llm_app:QwenChat`** (ID `qu2ojxoi`, matching the replica ID from the logs screenshot) — the
  one actor that actually holds the loaded Qwen2.5-0.5B-Instruct model in memory and runs `__call__` on each
  request. Note it's on `10.42.0.10` (the **worker**), not the head — direct confirmation that
  `headGroupSpec.rayStartParams.num-cpus: "0"` successfully forced this CPU-requesting actor off the head node.

**Full request path this implies:** `curl` → head's `ProxyActor` (`22d64...`) → routed internally to
`ServeReplica` (`qu2ojxoi`) on the worker → response flows back through the same proxy. This is the concrete,
actor-level version of the architecture decision made when sizing `ray-service-sample.yaml`: keep routing/proxy
infrastructure cheap and everywhere, keep the expensive model replica confined to worker nodes with real
resource headroom.
