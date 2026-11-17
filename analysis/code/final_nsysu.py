"""Class-end stockouts at NSYSU over the whole logging period, for the final report.

Usage: python final_nsysu.py DATA_DIR OUT_DIR [--first 2026-10-02] [--last 2026-11-16]

nsysu_analysis.py measured the pattern on the eight complete teaching weekdays of 2-14 Oct. This script repeats
its headline numbers on every teaching weekday logged so far and adds the logger's own record. Days are no longer
all complete (the YouBike API refused some runners for hours), so every number uses the snapshots that exist:
  - a campus total counts only when at least 7 of the 8 campus stations reported in that slot;
  - bell drops are paired within a day (stock 20 or 40 minutes after the bell minus stock 10 minutes before it);
  - stockout episodes are counted on days with at least 95% of the 07:00-23:00 snapshots.
23 Oct 2026 is left out: YouBike closed every Kaohsiung station that day.

Writes final_nsysu_summary.json, final_nsysu_days.csv (one row per teaching weekday), final_nsysu_weeks.csv and
final_logger_coverage.csv (snapshots per day and why any are missing).
"""
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, HOLIDAYS, load_logger, load_stations  # noqa: E402

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIRST, LAST = ARG("--first", "2026-10-02"), ARG("--last", "2026-11-16")
KRT = ["501209026", "501209023"]
CLOSED = {"2026-10-23"}
warnings.simplefilter("ignore")

df = load_logger(DATA)
df = df[df.date.between(FIRST, LAST)]
st = load_stations(DATA).set_index("sno")
all_days = sorted(df.date.unique())
teach = [d for d in all_days if pd.Timestamp(d).dayofweek < 5 and d not in HOLIDAYS and d not in CLOSED]


def totals(snos, need):
    """(day x 144) total bikes over snos; NaN where fewer than `need` of them reported."""
    d = df[df.sno.isin(snos) & df.bikes.notna()]
    g = d.groupby(["date", "slot"]).bikes.agg(["sum", "size"])
    g = g["sum"].where(g["size"] >= need)
    return g.unstack("slot").reindex(index=all_days, columns=range(144))


campus = totals(list(CAMPUS), 7)
krt = totals(KRT, 2)
c_emp = df[df.sno.isin(CAMPUS) & df.bikes.notna()].assign(e=lambda z: z.bikes == 0).groupby(["date", "slot"]).e.agg(["mean", "size"])
c_emp = c_emp["mean"].where(c_emp["size"] >= 7).unstack("slot").reindex(index=all_days, columns=range(144))
S = lambda hhmm: int(hhmm[:2]) * 6 + int(hhmm[3:]) // 10

# ---------- one row per teaching weekday ----------
rows = []
for d in teach:
    c = campus.loc[d]
    rows.append({"date": d, "dow": pd.Timestamp(d).day_name()[:3], "week": int((pd.Timestamp(d) - pd.Timestamp("2026-09-07")).days // 7 + 1),
                 "slots_06_23": int(df[(df.date == d) & (df.slot >= 36) & (df.slot < 138)].slot.nunique()),
                 "campus_10": c[S("10:00")], "campus_12": c[S("12:00")], "campus_17": c[S("17:00")], "campus_18": c[S("18:00")],
                 "drop_12_20": c[S("12:20")] - c[S("11:50")], "pct_12_20": (c[S("12:20")] - c[S("11:50")]) / c[S("11:50")] if c[S("11:50")] else np.nan,
                 "drop_16_40": c[S("16:40")] - c[S("15:50")], "drop_17_40": c[S("17:40")] - c[S("16:50")],
                 "campus_empty_share_18": c_emp.loc[d][S("18:00")], "krt_10": krt.loc[d][S("10:00")], "krt_18": krt.loc[d][S("18:00")]})
days = pd.DataFrame(rows)
days.to_csv(OUT / "final_nsysu_days.csv", index=False)
weeks = days.groupby("week").agg(days=("date", "size"), first=("date", "min"), campus_10=("campus_10", "mean"), campus_18=("campus_18", "mean"),
                                 drop_12_20=("drop_12_20", "mean"), pct_12_20=("pct_12_20", "mean"), drop_16_40=("drop_16_40", "mean"), drop_17_40=("drop_17_40", "mean")).reset_index()
weeks.to_csv(OUT / "final_nsysu_weeks.csv", index=False)

# ---------- stockout episodes at campus stations, on days with (nearly) complete snapshots ----------
full_days = [d for d in teach if days.set_index("date").loc[d, "slots_06_23"] >= 97]
eps = []
for (date, sno), g in df[df.sno.isin(CAMPUS) & df.date.isin(full_days)].groupby(["date", "sno"]):
    e = (g.set_index("slot").reindex(range(144)).bikes == 0).values
    s = 0
    while s < 144:
        if e[s]:
            t = s
            while t < 144 and e[t]:
                t += 1
            if 42 <= s < 138:
                eps.append({"date": date, "sno": sno, "start_slot": s, "minutes": (t - s) * 10})
            s = t
        else:
            s += 1
eps = pd.DataFrame(eps)

# ---------- the logger's own record ----------
cov = []
errs = {}
elog = DATA / "errors.log"
if elog.exists():
    for line in elog.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\d{4}-\d\d-\d\d)T", line)
        if m:
            errs[m.group(1)] = errs.get(m.group(1), 0) + 1
for d in all_days:
    n = int(df[df.date == d].slot.nunique())
    cov.append({"date": d, "snapshots": n, "missing": 144 - n, "failed_fetches": errs.get(d, 0), "closed": d in CLOSED})
cov = pd.DataFrame(cov)
cov.to_csv(OUT / "final_logger_coverage.csv", index=False)

m = lambda col: round(float(days[col].mean()), 1)
summary = {
    "first": FIRST, "last": LAST, "logged_days": len(all_days), "teaching_weekdays": len(teach), "teaching_weekdays_full": len(full_days),
    "offdays_in_range": sorted(set(HOLIDAYS) & set(all_days)), "closed_days": sorted(CLOSED & set(all_days)),
    "campus_bikes_10": m("campus_10"), "campus_bikes_12": m("campus_12"), "campus_bikes_17": m("campus_17"), "campus_bikes_18": m("campus_18"),
    "campus_bikes_18_median": round(float(days.campus_18.median()), 1), "campus_bikes_18_max": round(float(days.campus_18.max()), 1),
    "campus_empty_share_18": round(float(days.campus_empty_share_18.mean()), 3),
    "bell_12_drop_20min": m("drop_12_20"), "bell_12_pct_20min": round(float(days.pct_12_20.mean()), 3),
    "bell_12_drop_20min_min": round(float(days.drop_12_20.max()), 1), "bell_12_drop_20min_max": round(float(days.drop_12_20.min()), 1),
    "bell_12_days": int(days.drop_12_20.notna().sum()), "bell_12_days_with_drop_over_30": int((days.drop_12_20 <= -30).sum()),
    "bell_16_drop_40min": m("drop_16_40"), "bell_17_drop_40min": m("drop_17_40"),
    "krt_bikes_10": m("krt_10"), "krt_bikes_18": m("krt_18"),
    "episodes_n": int(len(eps)), "episodes_per_station_day": round(len(eps) / (8 * len(full_days)), 2),
    "episode_median_min": float(eps.minutes.median()), "episode_p90_min": float(eps.minutes.quantile(0.9)),
    "campus_station_minutes_empty_per_weekday": round(float(eps.minutes.sum() / len(full_days)), 0),
    "snapshots_expected": int(144 * len(all_days)), "snapshots_logged": int(cov.snapshots.sum()),
    "snapshot_coverage": round(float(cov.snapshots.sum() / (144 * len(all_days))), 4),
    "snapshots_lost_to_refused_fetches": int(cov.failed_fetches.sum()), "station_slots": int(len(df)),
    "days_with_all_144": int((cov.snapshots == 144).sum()),
}
json.dump(summary, open(OUT / "final_nsysu_summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))
print(weeks.round(1).to_string(index=False))
print(days[["date", "dow", "slots_06_23", "campus_10", "campus_18", "drop_12_20", "drop_16_40", "drop_17_40"]].round(0).to_string(index=False))
