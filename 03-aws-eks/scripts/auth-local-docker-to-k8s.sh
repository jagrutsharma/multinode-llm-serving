#!/usr/bin/env bash
# Authenticates the local Docker daemon to ECR so `docker push` can reach the registry.
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 722323574575.dkr.ecr.us-east-1.amazonaws.com