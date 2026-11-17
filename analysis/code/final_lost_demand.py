"""Riders who never found a bike: how much demand do the NTU trip records miss? (final report)

Usage: python final_lost_demand.py NTU_DIR SIM_DIR OUT_JSON

The replay simulator of the midterm counts unmet rentals among recorded rentals only. A rental that never
happened because the station was empty is not in the records, so the replay cannot serve it. This script sizes
that missing demand on the replayed days from tables already built: for every station-hour between 06:00 and
23:00, the censoring-corrected rate of Eq. (3) (demand/rates.csv, fitted on the training period) times the
share of the hour the station stood empty (hourly.parquet). It is an estimate under the Poisson-rate model, not
a count, and it describes the days as they happened, with the operator's trucks at work.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NTU, SIM, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(Path(__file__).parent))
from features import TW_HOLIDAYS  # noqa: E402

days = sorted(pd.read_csv(SIM / "k1" / "sim_daily.csv").date.unique())           # the 28 replayed weekdays
h = pd.read_parquet(NTU / "hourly.parquet")
h["date"] = h.hour.dt.strftime("%Y-%m-%d"); h["hod"] = h.hour.dt.hour
h = h[h.date.isin(days) & (h.hod >= 6) & (h.hod < 23)]
r = pd.read_csv(NTU / "demand" / "rates.csv", dtype={"sno": str})
r = r[r.offday == 0][["sno", "hod", "lam_cens", "campus"]]
m = h.merge(r, on=["sno", "hod"], how="left")
m["lost"] = m.lam_cens * (1 - m.exposure.fillna(1.0))
per_day = m.groupby("date").agg(rentals=("rentals", "sum"), lost=("lost", "sum"))
campus = m[m.campus == 1].groupby("date").agg(rentals=("rentals", "sum"), lost=("lost", "sum"))
by_hod = m.groupby("hod").lost.sum() / len(days)
sim = pd.read_csv(SIM / "k1" / "sim_daily.csv")
none = sim[sim.policy == "none"].set_index("date")
out = {"days": len(days), "rentals_per_day_recorded": round(float(per_day.rentals.mean()), 0), "lost_per_day_estimated": round(float(per_day.lost.mean()), 0),
       "lost_share_of_recorded": round(float(per_day.lost.sum() / per_day.rentals.sum()), 4),
       "campus_rentals_per_day": round(float(campus.rentals.mean()), 0), "campus_lost_per_day": round(float(campus.lost.mean()), 0),
       "campus_lost_share_of_recorded": round(float(campus.lost.sum() / campus.rentals.sum()), 4),
       "campus_share_of_lost": round(float(campus.lost.sum() / per_day.lost.sum()), 3),
       "lost_17_22_share": round(float(by_hod.loc[17:21].sum() / by_hod.sum()), 3), "lost_peak_hod": int(by_hod.idxmax()), "lost_peak_per_day": round(float(by_hod.max()), 0),
       "replay_rentals_per_day": round(float(none.rentals.mean()), 0), "replay_unmet_no_truck_per_day": round(float(none.unmet.mean()), 0),
       "empty_station_hours_share": round(float((1 - m.exposure.fillna(1.0)).mean()), 4)}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps(out, indent=1))
print(by_hod.round(0).to_string())
