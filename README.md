# multinode-llm-serving

An experimentation project in multi-node LLM serving, moving from a local Kubernetes lab up to a real cloud deployment.
Each phase is a self-contained folder — its own README, manifests, and (where relevant) architecture notes and
dashboard walkthroughs — so you can browse or reproduce any phase independently.

## Phases

- **[`01-single-replica/`](01-single-replica/README.md)** — KubeRay + Ray Serve on a local k3d cluster (Apple
  Silicon, CPU-only), serving Qwen2.5-0.5B-Instruct with a single model replica. Covers cluster setup, building
  a custom Ray image with the model baked in, RayService configuration, and the arm64/autoscaling/networking
  gotchas hit along the way.
- **[`02-num-replicas/`](02-num-replicas/README.md)** — scaling the same setup to `num_replicas: 2`. A single
  config change surfaced a real debugging arc: an OOM caused by Ray's scheduler tracking *declared* rather
  than *actual* memory usage, a `DEPLOY_FAILED` deadlock, and a router-refresh nuance where naive concurrent
  requests can silently pile onto one replica instead of load-balancing across both.
- **[`03-aws-eks/`](03-aws-eks/README.md)** — *(planned)* the same
  workload deployed to a real AWS EKS cluster.

## Why folders instead of branches

Each phase is meant to remain browsable side by side on `main` rather than living on separate branches — the
phases build conceptually on each other but aren't meant to replace one another, so there's no "merge" step;
each folder is a standalone snapshot you can return to.
