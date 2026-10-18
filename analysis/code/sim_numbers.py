"""Numbers for the report from the merged simulator runs: pooled reductions per policy and fleet size,
paired per-day differences with day-bootstrap intervals, truck-km and planner statistics.
Usage: python sim_numbers.py SIM_DIR OUT_JSON"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SIM, OUT = Path(sys.argv[1]), Path(sys.argv[2])
rng = np.random.default_rng(11)
res = {}
for k in (1, 3, 6):
    d = pd.read_csv(SIM / f"k{k}" / "sim_daily.csv")
    w = {m: d.pivot(index="date", columns="policy", values=m) for m in ("unmet", "empty_station_min", "truck_km", "bikes_moved")}
    nd = len(w["unmet"])
    idx = [rng.integers(0, nd, nd) for _ in range(2000)]
    r = {"days": nd}
    for pol in w["unmet"].columns:
        if pol == "none":
            continue
        r[pol] = {
            "unmet_red": 1 - w["unmet"][pol].sum() / w["unmet"]["none"].sum(),
            "empty_red": 1 - w["empty_station_min"][pol].sum() / w["empty_station_min"]["none"].sum(),
            "km": w["truck_km"][pol].mean(), "km_lo": w["truck_km"][pol].min(), "km_hi": w["truck_km"][pol].max(),
            "bikes": w["bikes_moved"][pol].mean()}
    for a, b in (("route", "prob"), ("route", "reactive"), ("route", "route1"), ("route1", "prob"), ("prob", "point")):
        if a not in w["unmet"] or b not in w["unmet"]:
            continue
        for m in ("unmet", "empty_station_min"):
            diff = (w[m][b] - w[m][a]) / w[m]["none"]            # points of the no-rebalancing total, per day
            bs = np.array([diff.values[i].mean() for i in idx])
            r[f"{a}-{b}:{m}"] = {"mean": diff.mean(), "lo": np.percentile(bs, 2.5), "hi": np.percentile(bs, 97.5),
                                 "days_better": float((diff > 0).mean())}
    rt = d[d.policy == "route"]
    if len(rt) and "v_final" in rt:
        r["route_stats"] = {"plan_ms": rt.plan_ms.mean(), "stops_per_route": rt.stops_per_route.mean(),
                            "routes": rt.routes.mean(), "sa_improved_share": rt.sa_improved.sum() / max(rt.searched.sum(), 1),
                            "sa_gain": rt.v_final.sum() / max(rt.v_greedy.sum(), 1e-9) - 1}
    res[k] = r
json.dump(res, open(OUT, "w"), indent=1, default=float)
for k, r in res.items():
    print(f"K={k} ({r['days']} days)")
    for pol in ("reactive", "point", "prob", "route1", "route", "operator"):
        if pol in r:
            x = r[pol]
            print(f"  {pol:9s} unmet {100 * x['unmet_red']:5.1f}%  empty {100 * x['empty_red']:5.1f}%  km {x['km']:6.1f} "
                  f"[{x['km_lo']:.0f}-{x['km_hi']:.0f}]  bikes {x['bikes']:6.0f}")
    for key, x in r.items():
        if ":" in key:
            print(f"  {key:32s} {100 * x['mean']:5.2f} [{100 * x['lo']:5.2f}, {100 * x['hi']:5.2f}]  days better {x['days_better']:.2f}")
    if "route_stats" in r:
        print("  route stats", {a: round(b, 3) for a, b in r["route_stats"].items()})
