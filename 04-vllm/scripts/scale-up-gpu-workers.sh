#!/usr/bin/env bash
# Grows the gpu-worker node group to 2 nodes -- manual, since no Karpenter/Cluster
# Autoscaler is installed to do this automatically.
eksctl scale nodegroup --cluster raylab-eks --name gpu-worker --nodes 2
