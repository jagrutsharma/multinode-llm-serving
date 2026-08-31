# Architecture: request flow

This diagram traces exactly what happens when you run:

```bash
kubectl port-forward svc/rayservice-sample-head-svc 8090:8000
curl -X POST -H "Content-Type: application/json" \
  http://localhost:8090/generate -d '{"prompt": "...", "max_new_tokens": 60}'
```

## Components

```mermaid
flowchart LR
    Client["Your machine<br/>(curl)"]

    subgraph K3D["k3d cluster: raylab"]
        PF["kubectl port-forward<br/>localhost:8090 → svc:8000"]
        SVC["Service<br/>rayservice-sample-head-svc<br/>(ClusterIP)"]

        subgraph HEAD["Head pod (num-cpus: 0)"]
            Proxy["ProxyActor<br/>SERVE_PROXY_ACTOR"]
            Controller["ServeController<br/>(deployment lifecycle only)"]
        end

        subgraph WORKER["Worker pod"]
            Proxy2["ProxyActor<br/>SERVE_PROXY_ACTOR"]
            Replica["ServeReplica<br/>llm_app:QwenChat<br/>(Qwen2.5-0.5B-Instruct loaded)"]
        end
    end

    Client -->|"POST /generate"| PF
    PF --> SVC
    SVC --> Proxy
    Proxy -->|"internal Ray RPC<br/>(route to replica)"| Replica
    Replica -->|"generated text"| Proxy
    Proxy -->|"200 OK JSON"| PF
    PF --> Client
```

## Sequence

```mermaid
sequenceDiagram
    participant C as curl (client)
    participant P as ProxyActor (head)
    participant R as ServeReplica: QwenChat (worker)

    C->>P: POST /generate {"prompt": "...", "max_new_tokens": 60}
    P->>R: forward request (Ray RPC)
    activate R
    Note over R: apply_chat_template()<br/>tokenizer.encode()<br/>model.generate() — CPU, greedy decode<br/>~13-15s for 60 tokens
    R-->>P: {"response": "..."}
    deactivate R
    P-->>C: 200 OK, JSON body
```

## Why the request lands on the worker, not the head

`ray-service-sample.yaml` sets `headGroupSpec.rayStartParams.num-cpus: "0"`. This tells Ray the head node has
zero schedulable CPUs, so the `QwenChat` deployment (which requests `ray_actor_options: {num_cpus: 1}`) can
never be placed there — it always lands on a worker, which has real CPU/memory headroom (`limits: {cpu: "2",
memory: "4Gi"}`) reserved for the model.

The `ProxyActor` is unaffected by that setting because it requests ~0 CPU — Ray Serve runs one proxy on
*every* node by default, head included. That's why the head's `rayservice-sample-head-svc` is still the right
thing to `port-forward` and `curl` against: its proxy is what actually receives the HTTP request and forwards
it internally to wherever the replica really lives.

See `dashboard/dashboard-actors.md` for the live actor listing this diagram is based on, and
`dashboard/dashboard-serve-inference-requests.md` for the real request-latency numbers observed.
