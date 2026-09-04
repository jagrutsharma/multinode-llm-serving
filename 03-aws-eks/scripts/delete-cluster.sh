#!/usr/bin/env bash
# Delete the cluster (avoid excess costs!)
eksctl delete cluster -f eksctl-cluster.yaml
