<!--
Images to attach when posting (LinkedIn supports multiple, shown as a carousel):
1. linkedin-phase1-phase2-architecture.png (this folder) — request-flow architecture diagram
2. ../02-num-replicas/dashboard/02-dashboard-serve.png — real screenshot, healthy 2-replica Serve tab
-->

A chunk of this year's Ray Summit was about scaling LLM serving across nodes. That's what pushed me to stop reading about it and build a small version myself — Kubernetes, KubeRay, Ray Serve. No GPU required to start.

The interesting part wasn't getting it running. It was scaling it.

Changed one line — `num_replicas: 2`. It turned into a distributed-systems debugging investigation. Ray's scheduler reasons about declared resource requests, not actual usage. Replicas kept getting overcommitted onto the same node. The deployment wedged into a failure state that pod restarts alone couldn't fix. The broader lesson: a scheduler only knows what you tell it, not what's actually happening on the box. That gap is easy to introduce and easy to miss.

Once fixed, a concurrency test told me the second replica wasn't helping at all. I didn't trust that number. I pulled the actual per-replica logs instead of reasoning from timing alone, and traced the cause to Ray Serve's request router — its view of each replica's load doesn't refresh instantly, so near-simultaneous requests can pile onto one replica by coincidence.

All of it runs cleanly now: two replicas, real load-balancing, verified end to end.

Full writeup, including the sizing rule of thumb this led to: https://github.com/jagrutsharma/multinode-llm-serving/blob/main/02-num-replicas/README.md

Next up: the same setup, real GPUs.

#LLMInference #Kubernetes #KubeRay #RayServe #DistributedSystems
