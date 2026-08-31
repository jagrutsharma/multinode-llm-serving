# Ray Dashboard — Cluster tab (node resource usage, 2 workers)

## What we're looking at

Node Statistics: `TOTAL x4, ALIVE x3, DEAD x1`. The Node List shows the 3 currently alive nodes:

| Host | State | CPU | Memory |
|---|---|---|---|
| `rayservice-sample-rm54x-head-slq2h` (Head) | ALIVE | 15.2% | 1.82GB / 2.00GB (90.9%) |
| `rayservice-sample-rm54x-small-group-worker-lg5dz` | ALIVE | 2.6% | 2.85GB / 4.00GB (71.3%) |
| `rayservice-sample-rm54x-small-group-worker-rz8f6` | ALIVE | 2.5% | 2.85GB / 4.00GB (71.3%) |

## Significance

- **`DEAD x1`** is a historical remnant, not a current problem: it's the original worker pod
  (`small-group-worker-z69qv`) that got deleted during the OOM debugging and replaced by `rz8f6`. Ray's GCS
  keeps a record of terminated nodes rather than erasing them, so this count will keep growing slightly over
  the life of a long-running cluster that's had any pod churn — it doesn't indicate anything currently broken.
- **Both workers at `2.85GB/4.00GB (71.3%)`** — nearly identical memory footprint on both, which is exactly
  what we'd expect now that each replica has an explicit `memory: 2500000000` resource request in
  `ray_actor_options`: two independent, equally-sized model instances, one per worker, each with headroom to
  spare within its `4Gi` container limit.
- **Head memory at `90.9%` (`1.82GB/2.00GB`)** — tighter than the `85.5%` observed in phase 1 with a single
  worker. This is the same known watch-item from phase 1 (GCS + dashboard + autoscaler overhead on the head,
  independent of the model, which stays off the head via `num-cpus: "0"`), just slightly worse here since the
  autoscaler now has two worker nodes to track instead of one. If this heads toward `100%`, bumping the head's
  memory limit to `3Gi` (as previously flagged) becomes the fix.
