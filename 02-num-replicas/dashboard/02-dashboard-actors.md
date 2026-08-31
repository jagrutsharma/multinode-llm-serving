# Ray Dashboard — Actors tab (internal actor breakdown, 2 replicas)

## What we're looking at

`TOTAL x494, ALIVE x6, DEAD x488`. The 6 alive actors:

| Class | PID | IP |
|---|---|---|
| `ProxyActor` | 221 | `10.42.0.11` (worker `lg5dz`) |
| `ServeReplica:llm_app:QwenChat` (`kuff2ut9`) | 104 | `10.42.0.11` (worker `lg5dz`) |
| `ProxyActor` | 1534 | `10.42.2.6` (worker `rz8f6`) |
| `ServeReplica:llm_app:QwenChat` (`5w8o2lk7`) | 1470 | `10.42.2.6` (worker `rz8f6`) |
| `ProxyActor` | 455 | `10.42.1.7` (head) |
| `ServeController` | 407 | `10.42.1.7` (head) |

## Significance

- **`ALIVE x6` is exactly the expected composition** for this setup: 3 `ProxyActor`s (one per node — head +
  2 workers), 2 `ServeReplica` actors (`kuff2ut9` and `5w8o2lk7`, one per worker), and 1 `ServeController`
  (always on the head). This is the concrete, actor-level confirmation that both replicas are real, distinct,
  running processes on the two different worker nodes — not two logical replicas sharing one process.
- **`DEAD x488` is a notably large number**, almost certainly accumulated churn from everything this cluster
  went through during debugging: multiple failed replica-init attempts during the OOM/`DEPLOY_FAILED` cycle
  (each crashed attempt registers as a dead actor rather than being erased), plus a full pod recycle after the
  Mac restart. This investigation didn't trace the exact breakdown of what all 488 are, so treat this as
  "high but apparently benign churn" rather than a diagnosed root cause — cluster health elsewhere (Serve
  status, replica health, resource usage) shows no adverse effect from it. Worth keeping an eye on if this
  cluster stays up for a long time, since GCS retains this history and it could add unbounded memory overhead
  on a sufficiently long-lived cluster.
