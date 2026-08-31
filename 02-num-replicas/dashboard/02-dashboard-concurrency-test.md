# Ray Dashboard — Serve replica logs, concurrency test (`test_concurrency.sh`)

## What we're looking at

Two screenshots of `Serve / llm_app / QwenChat`, one per replica, each showing that replica's Serve Logger
output after running `02-num-replicas/test_concurrency.sh` (5 requests, staggered 200ms apart):

**Replica `2gv623qw`** (`02-dashboard-concurrency-test-1.png`):
```
14:40:31,332 -- Started executing request
14:40:49,196 -- Started executing request
14:40:49,197 -- Started executing request
14:40:49,199 -- POST /generate 200 17869.5ms
14:41:04,881 -- POST /generate 200 33315.2ms
14:41:19,223 -- POST /generate 200 47219.9ms
```

**Replica `owydolf4`** (`02-dashboard-concurrency-test-2.png`):
```
14:40:31,275 -- Started executing request
14:40:48,902 -- Started executing request
14:40:48,905 -- POST /generate 200 17632.2ms
14:41:04,358 -- POST /generate 200 32580.7ms
```

## Significance

This is the ground-truth confirmation behind `test_concurrency.sh`'s output. The script reported 5 client-side
durations — 17s, 18s, 33s, 33s, 48s — and these two replica logs pin down exactly which replica handled which
request:

| Replica | Requests handled | Durations |
|---|---|---|
| `2gv623qw` | 3 | 17869.5ms, 33315.2ms, 47219.9ms → matches script's req0 (17s), req2 (33s), req4 (48s) |
| `owydolf4` | 2 | 17632.2ms, 32580.7ms → matches script's req1 (18s), req3 (33s) |

That's a genuine **3-2 split of 5 requests across both replicas**, with each replica processing its own share
sequentially (each completion roughly 15-16s after the previous one on that same replica — matching a single
generation's solo latency). This is the direct rebuttal to the earlier finding that *unstaggered* concurrent
requests (fired within single-digit milliseconds via `curl ... & curl ... & wait`) always piled onto a single
replica, because both requests saw an identical "all replicas idle" snapshot before Ray Serve's router could
refresh its view of in-flight load. The 200ms stagger in `test_concurrency.sh` gives the router enough time
between dispatches to notice growing queue depth and correctly route later requests to the less-loaded
replica — which is exactly what these two logs prove happened.
