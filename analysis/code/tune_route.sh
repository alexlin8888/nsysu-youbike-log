#!/bin/bash
# Tune the route planner on the 16 validation weekdays (10-31 Mar 2025) with 3 trucks; the test days are not used.
# Pass 1: horizon x beta x commit (0 = drive the whole route, 2 = plan again after two stops).
# Pass 2: larger time costs beta at a 90-minute horizon.
# Usage: bash tune_route.sh NTU_DIR MODEL_DIR OUT_DIR
NTU=$1; MODEL=$2; OUT=$3
SIM="$(dirname "$0")/replay_sim.py"
mkdir -p "$OUT"
run() {   # horizon beta commit
  D="$OUT/h$1_b$2_c$3"; POL=route; [ "$3" = "0" ] && POL=route1,route
  python3 "$SIM" "$NTU" "$MODEL" "$D" --period val --days 30 --trucks 3 --workers 2 \
    --policies "$POL" --horizon $1 --beta $2 --stops 6 --iters 400 --commit $3 > "$D.log" 2>&1
  echo "$D $(grep -E '^route' "$D/sim_summary.csv" | tr '\n' ' ')"
}
for H in 60 90 120; do for B in 0 0.05; do for C in 0 2; do run $H $B $C; done; done; done
for B in 0.1 0.25 0.5; do for C in 0 2; do run 90 $B $C; done; done
python3 "$SIM" "$NTU" "$MODEL" "$OUT/none" --period val --days 30 --trucks 3 --workers 2 --policies none > "$OUT/none.log" 2>&1
