#!/bin/bash
# Route planner on the 28 test weekdays with the setting chosen on the validation days
# (horizon 90 min, beta 0.25 unmet rentals per truck-minute, plan again after 2 stops).
# Usage: bash run_route_test.sh NTU_DIR MODEL_DIR OUT_DIR
NTU=$1; MODEL=$2; OUT=$3
for K in 1 3 6; do
  python3 "$(dirname "$0")/replay_sim.py" "$NTU" "$MODEL" "$OUT/k$K" --period test --days 30 --trucks $K --workers 2 \
    --policies route1,route --horizon 90 --beta 0.25 --stops 6 --iters 400 --commit 2 > "$OUT/k$K.log" 2>&1
  echo "K=$K $(grep -E '^route' "$OUT/k$K/sim_summary.csv" | tr '\n' ' ')"
done
