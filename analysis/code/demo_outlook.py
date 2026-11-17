"""What a usual day looks like around the campus, for the demo page: when is it hard to borrow, when is it hard to return?

Usage: python demo_outlook.py DATA_DIR OUT_JSON

From every logged day, for teaching weekdays and for days off separately, the share of station snapshots with no
bike and with no free dock in each half hour from 06:00 to 23:00, for the eight campus stations and for the eleven
stations at the foot of the campus. The page draws these as the "usual day" strip, so a student can see at a glance
that the campus is hard to leave by bike between 17:00 and 19:30 and hard to return to between 09:00 and 10:30.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger  # noqa: E402

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
CLOSED = {"2026-10-23"}                       # every Kaohsiung station was out of service
df = load_logger(DATA)
df = df[df.bikes.notna() & df.docks.notna() & (df.slot >= 36) & (df.slot < 138)].copy()
df["d"] = df.date.astype(str).str.slice(0, 10)
df = df[~df.d.isin(CLOSED)]
df["off"] = (pd.to_datetime(df.d).dt.dayofweek >= 5) | df.d.isin(HOLIDAYS)
df["bucket"] = (df.slot - 36) // 3
df["no_bike"] = df.bikes == 0; df["no_dock"] = df.docks == 0
out = {"generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"), "from": "06:00", "step_min": 30,
       "days": {"teaching": int(df[~df.off].d.nunique()), "off": int(df[df.off].d.nunique())}}
for kind, off in (("teaching", False), ("off", True)):
    out[kind] = {}
    for name, group in (("campus", CAMPUS), ("gateway", GATEWAY)):
        g = df[(df.off == off) & df.sno.isin(group)].groupby("bucket")[["no_bike", "no_dock"]].mean().reindex(range(34)).fillna(0)
        out[kind][name] = {"no_bike": [round(float(x), 2) for x in g.no_bike], "no_dock": [round(float(x), 2) for x in g.no_dock]}
OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print("outlook:", out["days"], "campus no bike at 17:30 on teaching days:", out["teaching"]["campus"]["no_bike"][23])
