# multinode-llm-serving

A local playground for multi-node LLM serving on Kubernetes using [KubeRay](https://github.com/ray-project/kuberay)
and [Ray Serve](https://docs.ray.io/en/latest/serve/index.html). It runs a `RayService` across a multi-node
[k3d](https://k3d.io/) cluster so you can develop and debug distributed serving deployments (head + worker
autoscaling, Serve app rollout, etc.) without needing real cloud infrastructure.

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

## Local k3d setup

1. **Create the cluster** (one control-plane node + 2 agent nodes, with the dashboard and Serve ports mapped
   through the k3d load balancer):

   ```bash
   ./create_cluster.sh
   ```

   This creates a cluster named `raylab` and maps host ports `8265` (Ray dashboard) and `8000` (Serve HTTP) to
   the k3d load balancer container (`k3d-raylab-serverlb`). In practice the RayService's head service is
   `ClusterIP`, so use `kubectl port-forward` (step 5) to actually reach the dashboard/Serve HTTP — the
   load-balancer port mapping alone doesn't route to it.

2. **Install the KubeRay operator** (tested with chart `kuberay-operator-1.7.0`):

   ```bash
   helm repo add kuberay https://ray-project.github.io/kuberay-helm/
   helm repo update
   helm install kuberay-operator kuberay/kuberay-operator --namespace kuberay-operator --create-namespace
   kubectl get pods -n kuberay-operator   # wait for 1/1 Running
   ```

3. **Deploy the sample RayService:**

   ```bash
   kubectl apply -f ray-service-sample.yaml
   ```

4. **Check status** until `SERVICE STATUS` is `Running` and `NUM SERVE ENDPOINTS` is non-zero:

   ```bash
   kubectl get rayservice
   kubectl get pods -o wide
   ```

5. **Access the dashboard and Serve endpoint** via the stable head service (survives RayCluster upgrades):

   ```bash
   kubectl port-forward svc/rayservice-sample-head-svc 8265:8265   # dashboard, http://localhost:8265
   kubectl port-forward svc/rayservice-sample-head-svc 8000:8000   # Serve HTTP
   ```

   Check registered routes, then hit the sample fruit app:

   ```bash
   curl -s http://localhost:8000/-/routes
   # {"/fruit":"fruit_app"}

   curl -X POST -H "Content-Type: application/json" http://localhost:8000/fruit/ -d '["MANGO", 2]'
   # 6

   curl -X POST -H "Content-Type: application/json" http://localhost:8000/fruit/ -d '["PEAR", 2]'
   # 8
   ```

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
list if you bump the Ray version and make sure the `-aarch64` counterpart exists.

Separately, if your Serve deployments need more CPU/memory than a single static worker provides, make sure
`enableInTreeAutoscaling: true` is set on the `RayCluster` spec — without it, `minReplicas`/`maxReplicas` on a
worker group are ignored and the cluster stays pinned at its static `replicas` count, which can leave a
deployment stuck in `UPDATING` waiting for resources that will never appear. In this repo's sample, the
`fruit_app`'s `PearStand` deployment needed a second worker; enabling autoscaling let KubeRay add it
automatically.
