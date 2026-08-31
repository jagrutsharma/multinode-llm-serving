# Ray Dashboard — Cluster tab (node resource usage)

## What we're looking at

The Cluster tab's node list, showing both Ray nodes as `ALIVE`:

| Host / Worker | State | CPU | Memory |
|---|---|---|---|
| `rayservice-sample-rm54x-head-slq2h` (Head) | ALIVE | 15.7% | 1.71GB / 2.00GB (85.5%) |
| `rayservice-sample-rm54x-small-group-worker-z69qv` | ALIVE | 2.5% | 2.86GB / 4.00GB (71.6%) |

Both nodes also show `Disk(root): 38.20GB/58.37GB (69.0%)`.

## Significance

- **Head memory at 85.5% of its 2Gi limit** — this is notably tight, *especially* since the head isn't running
  the model at all (that's the point of `headGroupSpec.rayStartParams.num-cpus: "0"` in
  `ray-service-sample.yaml`, which keeps the CPU-hungry `QwenChat` replica off the head). This memory is pure
  Ray overhead: GCS, the dashboard process, the autoscaler sidecar, and the Serve controller/proxy actors. This
  was flagged as a watch-item earlier in the project — if the head pod ever gets `OOMKilled` or the dashboard
  becomes unresponsive, bumping `headGroupSpec`'s container memory limit from `2Gi` to `3Gi` is the fix.
- **Worker memory at 71.6% of its 4Gi limit (2.86GB used)** — this is where the actual Qwen2.5-0.5B-Instruct
  model lives. ~2.86GB is consistent with a ~500M-parameter model loaded in `float32` (as configured via
  `torch_dtype=torch.float32` in `serve_llm.py`) plus the Python/PyTorch/Transformers runtime overhead. There's
  comfortable headroom here (4Gi limit set specifically for this reason when the manifest was upgraded from the
  original 2Gi fruit-app worker sizing).
- **Low CPU usage (15.7% / 2.5%)** reflects that no inference request was in flight at the moment of this
  screenshot — CPU spikes to near 100% on the worker's single allotted core during an active `/generate`
  request (see the ~13-15 second latencies in the inference-requests screenshot).
- **Shared disk usage (69% on both)** isn't two separate disks — both node-containers share the same underlying
  Docker Desktop VM disk, so this number is really "how full is the shared k3d Docker volume," not a per-node
  metric.
