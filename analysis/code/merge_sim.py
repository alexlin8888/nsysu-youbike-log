"""Merge the earlier policy runs (SIM_OLD/k{K}/sim_daily.csv) with the route-search runs (SIM_NEW/k{K}/...)
into SIM_OUT/k{K}/sim_daily.csv and print the pooled reductions per fleet size.
Usage: python merge_sim.py SIM_OLD SIM_NEW SIM_OUT"""
import sys
from pathlib import Path

import pandas as pd

old, new, out = (Path(a) for a in sys.argv[1:4])
for k in (1, 3, 6):
    a = pd.read_csv(old / f"k{k}" / "sim_daily.csv")
    b = pd.read_csv(new / f"k{k}" / "sim_daily.csv")
    assert set(a.date) == set(b.date), "different days"
    d = pd.concat([a[~a.policy.isin(b.policy)], b], ignore_index=True)
    (out / f"k{k}").mkdir(parents=True, exist_ok=True)
    d.to_csv(out / f"k{k}" / "sim_daily.csv", index=False)
    g = d.groupby("policy")[["unmet", "empty_station_min", "truck_km", "bikes_moved"]].sum()
    g["unmet_red"] = 1 - g.unmet / g.loc["none", "unmet"]
    g["empty_red"] = 1 - g.empty_station_min / g.loc["none", "empty_station_min"]
    nd = d.date.nunique()
    g[["truck_km", "bikes_moved"]] = g[["truck_km", "bikes_moved"]] / nd
    print(f"K={k}, {nd} days\n" + g[["unmet_red", "empty_red", "truck_km", "bikes_moved"]].round(3).to_string())
