# Phase 3: AWS EKS (planned)

[← back to project overview](../README.md)

Deploy the same multi-node LLM serving workload (KubeRay + Ray Serve) to a real AWS EKS cluster, moving off
the local CPU-only k3d lab from [phase 1](../01-single-replica/README.md) onto GPU-backed nodes.

## Status

Blocked on GPU instance quota approval.

- Requested `All G and VT Spot Instance Requests` (EC2) — quota 24, requested 2026-08-31, status: case opened
- Requested `Running On-Demand G and VT instances` (EC2) — quota 24, requested 2026-08-31, status: case opened
