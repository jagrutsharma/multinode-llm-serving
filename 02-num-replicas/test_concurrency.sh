#!/usr/bin/env bash
#
# Fires 5 requests at the /generate endpoint, staggered 200ms apart, to check whether
# Ray Serve actually spreads load across both QwenChat replicas or piles everything onto one.
#
# Why staggered and not all-at-once: firing all requests in the same instant lets them all see
# an identical "every replica is idle" snapshot from Serve's router before it refreshes, so they
# can all get routed to the same replica. A small stagger gives the router time to notice a
# replica has become busy before dispatching the next request.
#
# How to read the result: durations that split into rough tiers (some near the solo baseline,
# some ~2x, some ~3x) indicate real load-spreading across replicas. Durations that form one
# steadily increasing staircase indicate everything landed on a single replica.
#
# For ground truth on which replica handled which request, check the Ray dashboard
# (kubectl port-forward svc/rayservice-sample-head-svc 8265:8265, then Serve -> QwenChat ->
# each replica -> Logs) and compare POST /generate completions per replica ID.

set -u

LOCAL_PORT=8100
OUT_DIR=$(mktemp -d)
echo "Writing per-request output to: $OUT_DIR"

# Open tunnel from local port 8100 to RayService's head service on port 8000 (the Serve HTTP Proxy)
# & at the end puts this in background. This prevents blocking of the script
kubectl port-forward svc/rayservice-sample-head-svc "${LOCAL_PORT}:8000" > "${OUT_DIR}/port-forward.log" 2>&1 &

# PID of the process I just put in background. We need this to explicitly kill this tunnel later.
PF_PID=$!

# Give the tunnel a moment to complete being established before attempting to use it.
sleep 3

# Counter for naming each request's output files uniquely so we can read the responses
i=0
# Empty array to collect the PID of each request's sub-shell
PIDS=()

# Feed the 5 prompt lines into the loop, one at a time
# Each line can be referenced via $p for one iteration
# works in both bash and zsh
while IFS= read -r p; do
  # (...) is a subshell - a self-contained block of commands
  (
    # get the unix timestamp (seconds) - before invocation
    start=$(date +%s)
    # actual request, -s flag for silent, -m 120 caps it at 120 seconds so that it doesn't block everything
    curl -s -m 120 -X POST -H "Content-Type: application/json" \
      "http://localhost:${LOCAL_PORT}/generate" -d "{\"prompt\": \"$p\", \"max_new_tokens\": 40}" \
      > "${OUT_DIR}/req${i}_body.json"
    # get the uniq timestamp (seconds) - after response
    end=$(date +%s)
    # print summary for user to see the progress
    echo "req${i} start=$start end=$end duration=$((end - start))s prompt=\"$p\""
    # below > redirects whole of sub-shell to its own log file
    # The & at end backgrounds this subshell, so the loop doesn't wait for request N to finish before firing N+1
  ) > "${OUT_DIR}/req${i}.log" 2>&1 &
  # records this subshell's PID into our array
  PIDS+=($!)
  # staggers each request launch by 200 ms. This is the key.
  # This gap gives Ray Serve's internal router just enough time to notice a replica has become busy
  # before the next request is dispatched.
  sleep 0.2
  # increment counter
  i=$((i + 1))
done <<'EOF'
What is Kubernetes?
What is Ray?
What is Docker?
What is Python?
What is a container?
EOF

# Wait only on the tracked request PIDs -- NOT a bare `wait`, which would also wait on
# PF_PID (the port-forward), since that process never exits on its own.
wait "${PIDS[@]}"

echo
# Print each request's one-line summary in order, then clean up the tunnel
echo "=== Results ==="
for j in 0 1 2 3 4; do
  cat "${OUT_DIR}/req${j}.log"
done

kill "$PF_PID" 2>/dev/null