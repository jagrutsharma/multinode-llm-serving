<!--
Images to attach when posting (LinkedIn supports multiple, shown as a carousel):
1. ../03-aws-eks/dashboard/scaling/dual-gpu-concurrent-util.png — nvidia-smi polled with timestamps on two
   separate GPU nodes, both showing non-zero utilization at the same moment
2. ../03-aws-eks/dashboard/inf-req-resp.png — real curl request/response from the deployed model
-->

Last post ended with "next up: the same setup, real GPUs." Here's that.

Moved the Ray Serve setup off my laptop. Onto a real AWS EKS cluster, GPU-backed nodes this time. Getting the GPU to actually do the work was straightforward — CUDA image, float16 weights, `.to("cuda")`.

The harder part was a gap in the infrastructure itself. EKS auto-installs the NVIDIA device plugin when it sees a GPU instance. Handy. But it doesn't limit that plugin to GPU nodes only. It also landed on my CPU-only head node. No GPU there, so it crash-looped for hours. That slowly filled up the node's disk. Eventually it blocked all scheduling on that node.

After fixing that, I scaled to 2 GPU workers on 2 separate EC2 instances. I checked whether the load actually split across both, not just that both pods existed. It did — 3 requests went to one replica, 2 to the other. I also captured both GPUs computing at the same moment, with timestamps.

Also put a small chat UI on top, so I could try it without typing curl commands.

Everything runs cleanly now, on real cloud hardware.

Full writeup: https://github.com/jagrutsharma/multinode-llm-serving/blob/main/03-aws-eks/README.md

#LLMInference #Kubernetes #KubeRay #RayServe #AWS #GPU
