# Architecture: request flow with 2 replicas

Phase 1 ran a single `QwenChat` replica on a single worker, so every request had exactly one place to go.
Phase 2 runs `num_replicas: 2` across 2 worker pods, which introduces something phase 1 never had to deal
with: a **router** that has to decide, per request, which replica should handle it. This document covers that
decision and a surprising nuance in how it behaves under different request timing.

## Components

```mermaid
flowchart LR
    Client["Your machine<br/>(curl / test_concurrency.sh)"]

    subgraph K3D["k3d cluster: raylab"]
        PF["kubectl port-forward<br/>localhost:PORT → svc:8000"]
        SVC["Service<br/>rayservice-sample-head-svc<br/>(ClusterIP)"]

        subgraph HEAD["Head pod (num-cpus: 0)"]
            Proxy["ProxyActor<br/>+ request router"]
            Controller["ServeController<br/>(deployment lifecycle only)"]
        end

        subgraph WORKER1["Worker pod 1"]
            Proxy1["ProxyActor"]
            ReplicaA["ServeReplica A<br/>llm_app:QwenChat<br/>(Qwen2.5-0.5B-Instruct)"]
        end

        subgraph WORKER2["Worker pod 2"]
            Proxy2["ProxyActor"]
            ReplicaB["ServeReplica B<br/>llm_app:QwenChat<br/>(Qwen2.5-0.5B-Instruct)"]
        end
    end

    Client -->|"POST /generate"| PF
    PF --> SVC
    SVC --> Proxy
    Proxy -->|"router picks least-loaded replica"| ReplicaA
    Proxy -.->|"or"| ReplicaB
    ReplicaA -->|"generated text"| Proxy
    ReplicaB -.->|"generated text"| Proxy
    Proxy -->|"200 OK JSON"| PF
    PF --> Client
```

Same as phase 1: `headGroupSpec.rayStartParams.num-cpus: "0"` keeps both `QwenChat` replicas off the head
(each requests `num_cpus: 1`, which the head can't offer), so they always land on worker nodes. The head's
`ProxyActor` still receives every external request (that's what `rayservice-sample-head-svc` routes to) and
is responsible for picking *which* replica actually handles it — that routing decision is the new piece in
this phase.

## The router's blind spot: near-simultaneous requests pile onto one replica

Ray Serve's router doesn't synchronously check real-time in-flight-request counts on every single dispatch —
it works off a periodically-refreshed local snapshot of each replica's queue depth. Two requests arriving
within single-digit milliseconds of each other can both see the *same stale snapshot* ("both replicas idle")
and both get routed to the same replica, before that snapshot updates to reflect the first one now being busy.

This is exactly what happened testing with plain `curl ... & curl ... & wait` (no stagger):

```mermaid
sequenceDiagram
    participant C as curl (2 requests, ~6ms apart)
    participant P as ProxyActor (head)
    participant RA as ServeReplica A (worker 1)
    participant RB as ServeReplica B (worker 2)

    C->>P: POST /generate (req1)
    C->>P: POST /generate (req2, +6ms)
    Note over P: Cached queue-length snapshot shows<br/>BOTH replicas idle (not yet refreshed)
    P->>RA: route req1 (tie-break)
    P->>RA: route req2 (same stale snapshot, same tie-break)
    Note over RB: Never receives a request — sits idle
    activate RA
    RA-->>P: req1 response (~25s)
    RA-->>P: req2 response (~48s, queued behind req1)
    deactivate RA
```

Both requests completed successfully, but sequentially, on a single replica — `num_replicas: 2` provided zero
concurrency benefit for this specific request pattern, even though a second, fully idle replica existed the
whole time.

## Staggering fixes it: `test_concurrency.sh`'s real 3-2 split

`02-num-replicas/test_concurrency.sh` fires 5 requests 200ms apart instead of simultaneously. That gap is
enough for the router's snapshot to refresh between dispatches and correctly notice growing load, spreading
requests across both replicas:

```mermaid
sequenceDiagram
    participant C as test_concurrency.sh (5 requests, 200ms apart)
    participant P as ProxyActor (head)
    participant RA as ServeReplica 2gv623qw (worker 1)
    participant RB as ServeReplica owydolf4 (worker 2)

    C->>P: req0 (t=0ms)
    P->>RA: route req0
    C->>P: req1 (t=200ms)
    Note over P: snapshot now reflects RA busy
    P->>RB: route req1
    C->>P: req2 (t=400ms)
    P->>RA: route req2 (queued behind req0)
    C->>P: req3 (t=600ms)
    P->>RB: route req3 (queued behind req1)
    C->>P: req4 (t=800ms)
    P->>RA: route req4 (queued behind req0, req2)
    RA-->>C: req0 done (~17s)
    RB-->>C: req1 done (~18s)
    RA-->>C: req2 done (~33s)
    RB-->>C: req3 done (~33s)
    RA-->>C: req4 done (~47s)
```

Ground truth for this exact run (from each replica's own Serve logs, not just inference from client timing) is
in `dashboard/02-dashboard-concurrency-test.md` — replica `2gv623qw` handled req0/req2/req4, replica
`owydolf4` handled req1/req3, a genuine 3-2 split.

## Why this matters

`num_replicas: 2` alone doesn't guarantee concurrent request handling — it depends on *how* requests arrive.
A burst of near-simultaneous requests can accidentally defeat load balancing due to the router's refresh
cadence, while requests arriving even slightly spread out (as most real traffic naturally is) get properly
distributed. This is worth knowing before concluding "adding replicas didn't help" from a naive benchmark —
the benchmark's request pattern matters as much as the replica count.
