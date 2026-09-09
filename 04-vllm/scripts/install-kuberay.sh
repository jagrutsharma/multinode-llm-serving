#!/usr/bin/env bash

# Install KubeRay operator
helm install kuberay-operator kuberay/kuberay-operator --namespace kuberay-operator --create-namespace