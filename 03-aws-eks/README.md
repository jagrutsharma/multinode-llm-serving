# Phase 3: AWS EKS (planned)

[← back to project overview](../README.md)

Deploy the same multi-node LLM serving workload (KubeRay + Ray Serve) to a real AWS EKS cluster, moving off
the local CPU-only k3d lab from [phase 1](../01-single-replica/README.md) onto GPU-backed nodes.

## Status

Partially unblocked — GPU instance quota approved at a lower limit than requested.

- `All G and VT Spot Instance Requests` (EC2, us-east-1) — requested 24, **approved 8** (partial approval,
  2026-08-31). 8 vCPUs is enough for a small number of GPU Spot instances depending on instance type chosen
  (e.g. one `g4dn.2xlarge` or two `g4dn.xlarge`) — enough to start phase 3 with a single-GPU-node RayCluster.
  Can appeal with a more detailed use case if more capacity is needed later.
- `Running On-Demand G and VT instances` (EC2) — quota 24, requested 2026-08-31, status: case opened (no
  update yet)
