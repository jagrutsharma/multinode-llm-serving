# Phase 3: AWS EKS (planned)

[← back to project overview](../README.md)

Deploy the same multi-node LLM serving workload (KubeRay + Ray Serve) to a real AWS EKS cluster, moving off
the local CPU-only k3d lab from [phase 1](../01-single-replica/README.md) onto GPU-backed nodes.

## Status

Unblocked — both GPU instance quota requests are now approved.

- `All G and VT Spot Instance Requests` (EC2, us-east-1) — requested 24, **approved 8** (partial approval,
  2026-08-31). Enough for a small number of GPU Spot instances depending on instance type chosen (e.g. one
  `g4dn.2xlarge` or two `g4dn.xlarge`). Can appeal with a more detailed use case if more Spot capacity is
  needed later.
- `Running On-Demand G and VT instances` (EC2, us-east-1) — requested 24, **approved 48** (full approval and
  then some, 2026-08-31). Comfortable room for a multi-GPU-node RayCluster on On-Demand — e.g. up to six
  `g5.2xlarge` (8 vCPU each), or fewer, larger instances if a bigger single-GPU-node is preferred.

Enough quota now to start building phase 3: a single-GPU-node RayCluster first (mirroring
[phase 1](../01-single-replica/README.md)), then a multi-GPU-node setup (mirroring
[phase 2](../02-num-replicas/README.md)) using the On-Demand headroom.
