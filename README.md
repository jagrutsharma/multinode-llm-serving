# multinode-llm-serving

A local playground for multi-node LLM serving on Kubernetes using [KubeRay](https://github.com/ray-project/kuberay)
and [Ray Serve](https://docs.ray.io/en/latest/serve/index.html). It runs a `RayService` across a multi-node
[k3d](https://k3d.io/) cluster so you can develop and debug distributed serving deployments (head + worker
autoscaling, Serve app rollout, real-model inference, etc.) without needing real cloud infrastructure or a GPU.

The current `ray-service-sample.yaml` serves **Qwen2.5-0.5B-Instruct** (a small, CPU-friendly instruction-tuned
LLM) via a custom Ray Serve deployment in `llm_app/serve_llm.py`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for a diagram of the request flow (client → proxy → model replica) and
why it's routed the way it is.

## Prerequisites

Confirmed working with:

- Docker Desktop (Docker 29.1.5)
- `kubectl` client v1.31.0+
- [k3d](https://k3d.io/) v5.9.0
- `helm` v4.2.4

If `k3d` or `helm` aren't installed yet:

```bash
brew install k3d
brew install helm
```

## 1. Create the k3d cluster

```bash
./create_cluster.sh
```

This creates a cluster named `raylab` (one control-plane node + 2 agent nodes) and maps host ports `8265`
(Ray dashboard) and `8000` (Serve HTTP) to the k3d load balancer container (`k3d-raylab-serverlb`).

That mapping alone won't get you to the dashboard/Serve HTTP, though — it's worth understanding why. k3d's
load balancer does raw TCP-level port forwarding: it takes a connection on host port 8000 and forwards it to
port 8000 on the underlying node containers' network namespace, with no awareness of Kubernetes Services or
Pods. For that to reach anything, some process needs to actually be bound to port 8000 on the node itself —
which is what a `NodePort` or `hostNetwork` Service does. `rayservice-sample-head-svc` is a `ClusterIP`
Service, which is a virtual, cluster-internal-only address that `kube-proxy` intercepts via iptables/ipvs
rules for traffic *originating inside* the pod network — it never binds a real port on the node's host
network. So the load balancer's forwarded connection has nowhere to land; you'll see it accept the TCP
connection and then return nothing (`curl: (52) Empty reply from server`). Use `kubectl port-forward` instead
(see step 5) — it tunnels through the Kubernetes API server directly to a specific Pod, bypassing node
networking (and the load balancer) entirely.

Also note: since port `8000` on your host is already claimed by that load-balancer mapping, `kubectl port-forward`
on `8000` will fail with "address already in use" — forward to a different local port instead (e.g. `8090`).

## 2. Install the KubeRay operator

Tested with chart `kuberay-operator-1.7.0`:

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update
helm install kuberay-operator kuberay/kuberay-operator --namespace kuberay-operator --create-namespace
kubectl get pods -n kuberay-operator   # wait for 1/1 Running
```

This also installs the CRDs (`RayCluster`, `RayService`, `RayJob`, `RayCronJob` under the `ray.io` API group)
that make `kubectl get rayservice` etc. work — they aren't built into Kubernetes.

## 3. Build the custom Ray + Qwen image

`ray-service-sample.yaml` references a custom image (`multinode-llm-serving/ray-qwen:2.44.0-aarch64`) built from
the `Dockerfile` at the repo root. It starts from the official `rayproject/ray:2.44.0-aarch64` base image, installs
`torch`/`transformers`, and bakes in the Qwen2.5-0.5B-Instruct weights at build time (so pods don't need network
access to Hugging Face Hub at startup) plus the `llm_app/serve_llm.py` app code.

Build it (natively, for your host's arm64 architecture — no `--platform` flag needed):

```bash
docker build -t multinode-llm-serving/ray-qwen:2.44.0-aarch64 .
```

This downloads a few GB (torch + transformers + model weights) the first time and produces an image of a
few GB. Then import it into the k3d cluster — k3d nodes can't see your local Docker image cache otherwise:

```bash
k3d image import multinode-llm-serving/ray-qwen:2.44.0-aarch64 -c raylab
```

Re-run both commands any time you change `llm_app/serve_llm.py` or the `Dockerfile`.

## 4. Deploy the RayService

```bash
kubectl apply -f ray-service-sample.yaml
```

Key things this manifest does, beyond a minimal RayService:

- `enableInTreeAutoscaling: true` — without this, `minReplicas`/`maxReplicas` on `workerGroupSpecs` are ignored
  and the cluster stays pinned at its static `replicas` count, which can leave a Serve deployment stuck in
  `UPDATING` forever waiting for resources that will never appear.
- `headGroupSpec.rayStartParams.num-cpus: "0"` — tells Ray the head node has zero schedulable CPUs, so the
  `QwenChat` deployment replica (which requests `num_cpus: 1`) can't land on the head. The head is already busy
  running GCS, the dashboard, and the autoscaler; the Serve HTTP proxy still runs there fine since it needs ~0 CPU,
  which is how requests hitting the head service still reach the replica running on a worker.
- Worker `resources.limits: {cpu: "2", memory: "4Gi"}` — sized for the model; bumped up from the original
  2Gi/1cpu fruit-app example specifically to fit Qwen2.5-0.5B in float32.

Watch it come up. Any change to the manifest above triggers KubeRay's zero-downtime upgrade: it spins up a
**complete second RayCluster** alongside the existing one, waits for it (and its Serve app) to become healthy,
switches traffic over, then deletes the old cluster. During that window both clusters' pods run simultaneously,
so the node pool briefly needs roughly double the steady-state resource footprint.

```bash
kubectl get pods -o wide -w
kubectl get rayservice   # wait for SERVICE STATUS: Running, NUM SERVE ENDPOINTS non-zero
```

## 5. Talk to the model

Port-forward the stable head service (survives RayCluster upgrades) — using `8090` locally since `8000` is
already taken by the k3d load-balancer mapping from step 1:

```bash
kubectl port-forward svc/rayservice-sample-head-svc 8090:8000   # Serve HTTP
kubectl port-forward svc/rayservice-sample-head-svc 8265:8265   # dashboard, http://localhost:8265
```

Check registered routes, then prompt the model:

```bash
curl -s http://localhost:8090/-/routes
# {"/generate":"llm_app"}

curl -X POST -H "Content-Type: application/json" \
  http://localhost:8090/generate \
  -d '{"prompt": "What is Ray Serve in one sentence?", "max_new_tokens": 60}'
# {"response":"Ray Serve is an open-source framework for building scalable and efficient
#  machine learning models using Ray, a distributed computing system designed to handle
#  large-scale data processing tasks."}
```

## Local development setup

The Ray Serve app code (`llm_app/serve_llm.py`) imports `ray`, `torch`, and `transformers`, so point your editor
at a real interpreter with those installed rather than relying on the packages baked into the Docker image:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

In PyCharm: `Settings → Project: multinode-llm-serving → Python Interpreter → Add Interpreter → Add Local
Interpreter → Virtualenv Environment → Existing environment`, pointing at `.venv/bin/python`.

## The arm64 / `-aarch64` gotcha

On Apple Silicon (or any arm64 host), **do not use the plain `rayproject/ray:<version>` tags** — they are
amd64-only. Docker will silently pull and run the amd64 image under QEMU emulation, and the emulated binary
segfaults on startup (`qemu: uncaught target signal 11 (Segmentation fault)`), which manifests as the Ray head
pod crash-looping and worker pods stuck forever at `Init:0/1` (they're waiting on a head that never comes up).

Always pin the architecture-specific tag instead, e.g.:

```yaml
image: rayproject/ray:2.44.0-aarch64
```

Ray publishes native `-aarch64` builds for every version/variant on Docker Hub — check `rayproject/ray`'s tag
list if you bump the Ray version and make sure the `-aarch64` counterpart exists. This also applies to any custom
image you build on top of it (like this repo's `Dockerfile`) — build natively on your arm64 machine rather than
cross-compiling, and it'll inherit the correct architecture automatically.

## Troubleshooting

**k3d nodes share one resource pool — they aren't independent machines.** `kubectl describe nodes` reports the
same `Allocatable` CPU/memory for `k3d-raylab-server-0`, `k3d-raylab-agent-0`, and `k3d-raylab-agent-1` (on this
setup, ~16.5GB memory / 10 CPUs each) because all three are just containers backed by the *same* Docker Desktop
VM, not separate machines each with their own dedicated resources. That number is the whole shared host pool,
not per-node capacity. This matters once you're running multiple worker replicas — don't assume each worker
gets its own 16.5GB; they're all drawing from one shared pot, and Docker Desktop's own VM memory limit is the
real ceiling.

**Head pod memory runs close to its limit even without the model on it.** In testing, the head pod sat around
85% of its `2Gi` memory limit (see `dashboard/dashboard-cluster.md`) purely from GCS, the dashboard, the
autoscaler sidecar, and the Serve controller/proxy — before the `QwenChat` model replica is even in the
picture, since `num-cpus: "0"` keeps it off the head entirely. This hasn't caused an OOM, but there's little
slack. If the head pod restarts or the dashboard becomes unresponsive, bump `headGroupSpec`'s container memory
limit from `2Gi` to `3Gi` in `ray-service-sample.yaml`.

**`git push` fails with `HTTP 400` / "unexpected disconnect while reading sideband packet".** This showed up
pushing this repo to GitHub and is unrelated to repo size (the whole repo is ~1MB) — it looks like chunked
transfer-encoding getting interrupted somewhere on the network path (proxy/VPN), not an auth or permissions
issue. Retrying with a larger, non-chunked post buffer and HTTP/1.1 for that one push resolved it:

```bash
git -c http.postBuffer=157286400 -c http.version=HTTP/1.1 push origin main
```

This only affects that single invocation — it doesn't change your persisted git config.
