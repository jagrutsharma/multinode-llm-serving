#!/usr/bin/env bash
# Builds the vLLM image for amd64 (explicit --platform, since Apple Silicon defaults
# to arm64) and pushes it to ECR.

echo "*** Building *** (tag it latest)"
docker build --platform linux/amd64 -t 722323574575.dkr.ecr.us-east-1.amazonaws.com/multinode-llm-serving/ray-qwen-vllm:latest .

echo "*** Pushing ***"
docker push 722323574575.dkr.ecr.us-east-1.amazonaws.com/multinode-llm-serving/ray-qwen-vllm:latest