"""What the planner expects and recommends at NSYSU, by time of day (final report).

Usage: python final_planner.py REPLAY_DIR OUT_DIR [REPLAY_DIR_HOURLY]

REPLAY_DIR holds replay_YYYY-MM-DD.json files written by demo_state.py --replay for teaching weekdays: for every
10-minute snapshot the expected unmet rentals of the next 90 minutes without a truck (the birth-death chain) and
the one-truck plan of the route search with the value it expects to recover. Kaohsiung publishes no trip records,
so these are the planner's own expectations, not replayed outcomes; the chain behind them is tested separately
(final_forecast.py). REPLAY_DIR_HOURLY, if given, holds the same days planned with hourly rates only.

Writes planner_by_slot.csv (per time of day: expected unmet, plan value, bikes moved, share delivered to campus),
planner_stations.csv (how often each station is a pick-up or a drop-off) and planner_summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REP, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
HOURLY = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def load(folder):
    rows, stops = [], []
    for f in sorted(folder.glob("replay_*.json")):
        r = json.load(open(f))
        st = r["stations"]
        grp = np.array([s["group"] for s in st])
        corridor = np.isin(grp, ["campus", "gateway"])
        for sl in r["slots"]:
            u = np.array([x if x is not None else 0.0 for x in sl["unmet"]])
            val = sum(p["value"] for p in sl["plans"])
            drop = sum(x["d"] for p in sl["plans"] for x in p["stops"] if x["d"] > 0)
            drop_c = sum(x["d"] for p in sl["plans"] for x in p["stops"] if x["d"] > 0 and grp[x["i"]] == "campus")
            pick_c = sum(-x["d"] for p in sl["plans"] for x in p["stops"] if x["d"] < 0 and grp[x["i"]] == "campus")
            rows.append({"date": r["date"], "t_min": sl["t_min"], "unmet": float(u.sum()), "unmet_corridor": float(u[corridor].sum()), "unmet_campus": float(u[grp == "campus"].sum()),
                         "value": val, "has_plan": int(val > 0), "bikes_dropped": drop, "dropped_campus": drop_c, "picked_campus": pick_c,
                         "minutes": sum(p["minutes"] for p in sl["plans"]), "n_stops": sum(len(p["stops"]) for p in sl["plans"])})
            for p in sl["plans"]:
                for x in p["stops"]:
                    stops.append({"date": r["date"], "t_min": sl["t_min"], "sno": st[x["i"]]["sno"], "name": st[x["i"]]["name_en"], "group": grp[x["i"]], "d": x["d"]})
    return pd.DataFrame(rows), pd.DataFrame(stops)


d, stops = load(REP)
g = d.groupby("t_min")
by = pd.DataFrame({"days": g.size(), "unmet_mean": g.unmet.mean(), "unmet_p25": g.unmet.quantile(0.25), "unmet_p75": g.unmet.quantile(0.75),
                   "unmet_corridor_mean": g.unmet_corridor.mean(), "unmet_campus_mean": g.unmet_campus.mean(),
                   "value_mean": g.value.mean(), "value_p25": g.value.quantile(0.25), "value_p75": g.value.quantile(0.75), "plan_share": g.has_plan.mean(),
                   "bikes_dropped": g.bikes_dropped.mean(), "dropped_campus": g.dropped_campus.mean(), "picked_campus": g.picked_campus.mean()}).reset_index()
by = by[by.days >= 0.6 * by.days.max()]
by.to_csv(OUT / "planner_by_slot.csv", index=False)
stn = stops.assign(drop=stops.d.clip(lower=0), pick=(-stops.d).clip(lower=0)).groupby(["sno", "name", "group"]).agg(drop_stops=("drop", lambda x: int((x > 0).sum())), bikes_dropped=("drop", "sum"),
                                                                                                                pick_stops=("pick", lambda x: int((x > 0).sum())), bikes_picked=("pick", "sum")).reset_index()
stn.sort_values("bikes_dropped", ascending=False).to_csv(OUT / "planner_stations.csv", index=False)


def window(a, b, frame=d):
    w = frame[(frame.t_min >= a) & (frame.t_min < b)]
    return {"slots": int(len(w)), "unmet_mean": round(float(w.unmet.mean()), 1), "value_mean": round(float(w.value.mean()), 1), "plan_share": round(float(w.has_plan.mean()), 3),
            "value_over_unmet": round(float(w.value.sum() / w.unmet.sum()), 4), "bikes_dropped_mean": round(float(w.bikes_dropped.mean()), 1),
            "campus_share_of_drops": round(float(w.dropped_campus.sum() / max(w.bikes_dropped.sum(), 1)), 3), "campus_pickups_mean": round(float(w.picked_campus.mean()), 1),
            "minutes_mean": round(float(w.minutes[w.has_plan == 1].mean()), 1) if w.has_plan.any() else None}


peak = by.loc[by.unmet_mean.idxmax()]
summary = {"days": int(d.date.nunique()), "first": d.date.min(), "last": d.date.max(), "slots": int(len(d)),
           "all_day": window(360, 1380), "before_noon_bell_1100_1200": window(660, 720), "afternoon_1500_1730": window(900, 1050), "evening_1730_2000": window(1050, 1200), "morning_0700_0900": window(420, 540),
           "unmet_peak_time": f"{int(peak.t_min) // 60:02d}:{int(peak.t_min) % 60:02d}", "unmet_peak": round(float(peak.unmet_mean), 1),
           "value_peak_time": f"{int(by.loc[by.value_mean.idxmax()].t_min) // 60:02d}:{int(by.loc[by.value_mean.idxmax()].t_min) % 60:02d}", "value_peak": round(float(by.value_mean.max()), 1),
           "top_dropoffs": stn.sort_values("bikes_dropped", ascending=False).head(5)[["name", "group", "drop_stops", "bikes_dropped"]].to_dict("records"),
           "top_pickups": stn.sort_values("bikes_picked", ascending=False).head(5)[["name", "group", "pick_stops", "bikes_picked"]].to_dict("records"),
           "campus_share_of_all_drops": round(float(d.dropped_campus.sum() / d.bikes_dropped.sum()), 3)}
if HOURLY and HOURLY.exists():
    dh, _ = load(HOURLY)
    common = set(d.date) & set(dh.date)
    summary["hourly_rates"] = {"days": len(common), "all_day": window(360, 1380, dh[dh.date.isin(common)]), "before_noon_bell_1100_1200": window(660, 720, dh[dh.date.isin(common)]),
                               "afternoon_1500_1730": window(900, 1050, dh[dh.date.isin(common)])}
json.dump(summary, open(OUT / "planner_summary.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1, ensure_ascii=False))
