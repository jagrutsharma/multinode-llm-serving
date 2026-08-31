# Phase 2: multiple replicas on local k3d

[← back to project overview](../README.md)

Phase 1 ran a single `QwenChat` replica. This phase changes exactly one thing in `ray-service-sample.yaml`:

```yaml
deployments:
  - name: QwenChat
    num_replicas: 2
```

That one-line change turned into a much longer debugging story than expected, because it surfaces several
non-obvious things about how Ray's scheduler, Serve's deployment controller, and Kubernetes readiness probes
interact. This README documents the whole arc — the point isn't "here's a clean recipe," it's "here's what
actually broke and why," since that's the more useful thing to have written down.

Everything here assumes phase 1's cluster (`raylab`, KubeRay operator, the `multinode-llm-serving/ray-qwen`
image) is already set up — see [phase 1's README](../01-single-replica/README.md) if starting fresh. Run
commands from inside this directory.

## Attempt 1: OOM — `num_replicas: 2` alone isn't enough

Applying the manifest with just `num_replicas: 2` bumped (no `memory` declared yet) produced this in
`kubectl get rayservice rayservice-sample -o yaml`:

```
QwenChat: status UPSCALING
message: "A replica failed to start with exception... OutOfMemoryError:
  Memory on the node ... was 3.96GB / 4.00GB (98.9%), which exceeds the
  memory usage threshold of 0.95. Ray killed this worker..."
```

**What actually happened, and why the autoscaler didn't just add a second worker:** the second replica tried
to start on the *same* existing worker pod, not a new one. `ray_actor_options` only declared `num_cpus: 1` —
no `memory` resource. The worker's container CPU limit is `2`, so with one replica already using 1 CPU,
there was CPU headroom for a second `num_cpus: 1` replica on that same node — so Ray's scheduler placed it
there instead of triggering the in-tree autoscaler to provision a new worker. Memory was never part of that
placement decision, because it was never declared as a resource requirement. Two ~2.2GB model instances got
crammed onto one `4Gi`-limited worker, and the second one got OOM-killed mid-startup.

**The gotcha worth remembering:** *Ray's memory resource, like CPU, is a scheduling hint based on what an
actor declares, not what it actually uses.* If you don't declare `memory` in `ray_actor_options`, the
scheduler has no idea a replica needs 2+ GB and will happily co-locate it with other memory-heavy actors
purely based on CPU headroom, until the OS-level memory monitor steps in after the fact and kills something.

## Attempt 2: still failing after adding `memory:` — a deadlock, not a config error

The fix looked obvious: declare the real memory cost.

```yaml
ray_actor_options:
  num_cpus: 1
  memory: 2500000000   # ~2.5GB — observed actual usage was 2.2GB
```

Re-applying still failed with the *same* OOM error, and after 6 retries the deployment settled into a
terminal state:

```
QwenChat: status DEPLOY_FAILED
message: "The deployment failed to start 6 times in a row..."
```

**Why the fix didn't immediately work:** the *already-running* replica had been scheduled under the *old*
config, before `memory` existed in `ray_actor_options`. Ray tracks resource reservations based on what an
actor declared *at the moment it was scheduled* — not its real-time actual usage. So that old replica was
still occupying ~2.2GB of real RAM while showing a **0-byte declared memory reservation** to the scheduler.
When the new, correctly-configured replica tried to start, the scheduler saw "1 of 2 CPUs used, ~0 of ~4GB
memory reserved" — looked wide open — and placed it on the same node anyway. Only the real OS memory monitor
noticed the actual overcommit and killed it, same as before.

**`DEPLOY_FAILED` doesn't self-heal.** Ray Serve's deployment controller gives up retrying after enough
consecutive failures. Deleting the stuck worker pod (`kubectl delete pod ...`) didn't fix it either — KubeRay
recreated a fresh pod, but it sat `0/1 NotReady` indefinitely. That turned out to be a **second, related
deadlock**: the worker's readiness probe requires *both* the raylet *and* Serve's `/-/healthz` to report
success, and `/-/healthz` can't report success while the deployment is `DEPLOY_FAILED`. So: Serve won't retry
on its own, and the new pod can't prove healthy until Serve does.

**The actual fix** — force a clean reschedule by stepping the deployment down and back up:

```bash
# 1. Step down to a known-good state
#    (num_replicas: 1 in ray-service-sample.yaml)
kubectl apply -f ray-service-sample.yaml
kubectl get rayservice   # wait for SERVICE STATUS: Running, NUM SERVE ENDPOINTS: 1

# 2. Step back up
#    (num_replicas: 2 in ray-service-sample.yaml)
kubectl apply -f ray-service-sample.yaml
kubectl get pods -o wide -w   # watch for a genuinely NEW second worker pod this time
```

This works because step 1 lets the surviving replica reschedule fresh *with* the memory declaration already
in effect — no more stale zero-reservation actor. Once that's true, step 2's second replica correctly finds
"no room" on the existing node (its real remaining memory, ~1.1-1.5GB, is less than the 2.5GB needed) and the
autoscaler finally provisions a real second worker.

**Sizing rule of thumb for `ray_actor_options.memory`:** pick a value such that
`replicas-per-node × memory ≈ worker's memory limit`, roughly `4Gi worker ÷ (2.5GB/replica) ≈ 1 replica/node`
after accounting for ~0.4-0.5GB of Ray's own per-node overhead (raylet, dashboard agent, etc.). If your
declared value is too low relative to real usage, you're back to attempt 1's silent overcommit.

## Confirming the fix

```bash
kubectl get pods -o wide
kubectl get rayservice
```
Expect two distinct worker pods on two different nodes, `QwenChat: HEALTHY`, `SERVICE STATUS: Running`. See
`dashboard/02-dashboard-serve.md`, `dashboard/02-dashboard-cluster.md`, and `dashboard/02-dashboard-actors.md`
for the actual screenshots and what each field means once healthy.

## Debugging technique: replica logs without `kubectl exec`

`kubectl exec` is the Kubernetes equivalent of `docker exec` — it runs a command (or opens an interactive
shell) *inside* an already-running container, in its real filesystem and process namespace, e.g.
`kubectl exec -it <pod> -- bash`. The natural way to inspect a Serve replica's log file (which lives inside
the pod at a path like `/tmp/ray/session_latest/logs/serve/replica_....log`) would be
`kubectl exec <pod> -- cat <path>`.

`kubectl exec` access is often restricted in shared, sandboxed, or permission-locked environments, since it
grants arbitrary command execution inside a live pod — a much broader capability than read-only inspection
commands like `kubectl get`/`describe`/`logs`. If you don't have `exec` access to a cluster for this or any
other reason, the Ray dashboard exposes the same log data over its own REST API — the same API its web UI
calls when you click a replica's "Logs" link. Since reaching the dashboard only needs a normal
`kubectl port-forward` (not `exec`), this gets you the
identical log content with no shell into the pod required:

```bash
kubectl port-forward svc/rayservice-sample-head-svc 8265:8265 &
curl -s http://localhost:8265/api/serve/applications/ | python3 -c "
import json,sys
d=json.load(sys.stdin)
for app in d.get('applications', {}).values():
    for dep in app.get('deployments', {}).values():
        for r in dep.get('replicas', []):
            print(r['replica_id'], r['node_id'], r['log_file_path'])
"
# then, per replica:
curl -s "http://localhost:8265/api/v0/logs/file?node_id=<node_id>&filename=<log_file_path, no leading slash>&lines=50"
```
Note the `filename` must **not** have a leading slash, or the API returns "file not found" even though the
path looks otherwise correct.

## Testing concurrency: a misleading first result

The obvious test — fire 2 requests at once — gave a confusing result:

```bash
time (
  curl -s -X POST ... -d '{"prompt": "What is Kubernetes?", ...}' &
  curl -s -X POST ... -d '{"prompt": "What is Ray?", ...}' &
  wait
)
# real 0m53.959s
```

53.9s for 2 "concurrent" requests, when a single request alone takes ~13-15s. Pulling each replica's actual
Serve logs (via the technique above) showed **both requests landed on the same replica**, run sequentially —
the second replica sat completely idle the whole time. `num_replicas: 2` provided zero benefit for this
specific test.

**Why:** Ray Serve's router doesn't synchronously check real-time in-flight-request counts on every dispatch —
it works off a periodically-refreshed snapshot of each replica's queue depth. Two requests arriving within
single-digit milliseconds of each other (exactly what `curl ... & curl ... & wait` produces) can both see an
identical "everything's idle" snapshot before it refreshes, and both get routed to the same replica by the
same tie-break. See `ARCHITECTURE.md` for the full sequence diagram of this failure mode.

## The fix: stagger requests, and prove it with logs

`test_concurrency.sh` fires 5 requests 200ms apart instead of simultaneously — enough time for the router's
snapshot to refresh between dispatches:

```bash
./test_concurrency.sh
```

Expect output like:
```
req0 duration=17s   req1 duration=18s
req2 duration=33s   req3 duration=33s
req4 duration=48s
```

The tiered pattern (two near the solo baseline, two near double, one near triple) is the signature of real
load-spreading. Ground truth, cross-checked against each replica's own logs via the dashboard, confirmed a
genuine **3-2 split**: replica `2gv623qw` handled req0/req2/req4, replica `owydolf4` handled req1/req3 — see
`dashboard/02-dashboard-concurrency-test.md` for the exact log lines. Full request-flow diagrams for both the
failure mode and the fix are in `ARCHITECTURE.md`.

## Other gotchas hit along the way

- **A bare `wait` waits on every backgrounded job in the shell, not just the ones you care about.** My first
  two attempts at the concurrency test hung for minutes because `wait` (no arguments) was also waiting on the
  long-lived `kubectl port-forward` process, which never exits on its own. Fix: track PIDs explicitly
  (`PIDS+=($!)`) and `wait "${PIDS[@]}"`.
- **zsh doesn't support bash's `${!array[@]}` array-index syntax.** The default shell on modern Macs is zsh;
  a script using that syntax fails with `bad substitution`. `test_concurrency.sh` uses a `while read` loop
  over a heredoc instead, which works in both.
- **A confusing kubelet event message**: `Readiness probe failed: success` looks contradictory, but makes
  sense once you see the probe itself — it's a shell command chaining two checks with `&&`
  (`wget .../local_raylet_healthz | grep success && wget .../-/healthz | grep success`). The event text shows
  the output of whichever `grep` matched, even though the overall command's exit code (from the *second*,
  failing check) is what actually failed the probe.
- **k3d/Mac restart resilience (a pleasant surprise, not a gotcha):** after a full Mac restart, starting
  Docker Desktop was the only manual step needed — the k3d node containers, the RayCluster's state, and the
  locally-built `ray-qwen` image all persisted and came back up on their own, with Kubernetes restarting the
  actual Ray pods automatically once the node containers were live again.
