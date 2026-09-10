#!/usr/bin/env bash
# Creates the raylab-eks cluster (head-cpu + gpu-worker node groups) from eksctl-cluster.yaml.
eksctl create cluster -f eksctl-cluster.yaml