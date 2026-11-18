"""The campus by the measures a city would use.

Usage: python final_city.py DATA_DIR OUT_DIR [--first 2026-10-02] [--last 2026-11-16]

Operators and cities report one availability figure per day and city. Taipei's is the share of the time between
06:00 and 24:00 in which a station has at least one bike, averaged over stations. This script computes the same
figure from the logger for all logged stations, the eight campus stations and the eleven gateway stations, on the
teaching weekdays of the period, together with the same share for free docks and for the two hard periods
(see_bike.csv). A daily city-wide average looks ordinary at NSYSU; the table shows the three hours it hides.

It also asks whether the campus runs out of docks in the morning or only single stations do (campus_docks.csv, one
row per station plus one for the campus as a whole, 09:00-11:00): the share of snapshots in which a station is
full, the free docks left on the whole campus, and how many of the eight stations are full at once.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger  # noqa: E402

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIRST, LAST = ARG("--first", "2026-10-02"), ARG("--last", "2026-11-16")
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
PERIODS = {"06-24": (36, 144), "17-20": (102, 120), "09-11": (54, 66)}
OUT.mkdir(parents=True, exist_ok=True)

df = load_logger(DATA)
df = df[(df.age <= 20) & df.weekday & ~df.date.isin(OFFDAYS) & (df.date >= FIRST) & (df.date <= LAST)]
days = df.date.nunique()

see = []
for name, ids in (("all logged", None), ("campus", CAMPUS), ("gateway", GATEWAY)):
    g = df if ids is None else df[df.sno.isin(ids)]
    for per, (a, z) in PERIODS.items():
        x = g[(g.slot >= a) & (g.slot < z) & g.bikes.notna() & g.docks.notna()]
        ps = x.assign(b=x.bikes >= 1, k=x.docks >= 1).groupby("sno")[["b", "k"]].mean()
        see.append({"stations": name, "period": per, "n_stations": len(ps), "days": days, "see_bike": ps.b.mean(), "see_dock": ps.k.mean()})
see = pd.DataFrame(see); see.round(4).to_csv(OUT / "see_bike.csv", index=False)

a, z = PERIODS["09-11"]
c = df[df.sno.isin(CAMPUS) & (df.slot >= a) & (df.slot < z) & df.bikes.notna() & df.docks.notna()]
rows = [{"station": CAMPUS[s], "sno": s, "docks": int((g.bikes + g.docks).median()), "full_share": (g.docks == 0).mean()} for s, g in c.groupby("sno")]
w = c.groupby(["date", "slot"]).agg(n=("bikes", "count"), bikes=("bikes", "sum"), free=("docks", "sum"), full=("docks", lambda v: int((v == 0).sum())))
w = w[w.n == len(CAMPUS)]                                           # snapshots that cover all eight stations
rows.append({"station": "campus as a whole", "sno": "", "docks": int((w.bikes + w.free).median()), "full_share": (w.free == 0).mean(), "free_docks_mean": w.free.mean(),
             "free_docks_10_or_fewer": (w.free <= 10).mean(), "one_or_more_full": (w.full >= 1).mean(), "stations_full_mean": w.full.mean(), "fill_mean": (w.bikes / (w.bikes + w.free)).mean(),
             "snapshots": len(w)})
docks = pd.DataFrame(rows); docks.round(4).to_csv(OUT / "campus_docks.csv", index=False)
pd.set_option("display.width", 220)
print(days, "teaching weekdays"); print(see.round(3).to_string(index=False)); print(docks.round(3).to_string(index=False))
