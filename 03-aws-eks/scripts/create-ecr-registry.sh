#!/usr/bin/env bash
# One-time setup: creates the ECR repository the GPU image gets pushed to.
aws ecr create-repository --repository-name multinode-llm-serving/ray-qwen-gpu --region us-east-1