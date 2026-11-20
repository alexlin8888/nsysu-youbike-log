"""How often is each word on the page right? The page's four station labels checked against what really happened.

Usage: python final_labels.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16]

The page sorts every station into four labels from the chance that it has a bike (a free dock) when the rider gets
there, the chance coming from the birth-death chain run from the latest count:

  bikes                     docks
  有車  chance >= 0.90       有空位  chance >= 0.95
  車不多 0.60 .. 0.90         空位不多 0.70 .. 0.95
  難借  below 0.60, bikes now 難還  below 0.70, docks now
  沒車  none now and below 0.60 停滿  none now and below 0.70

A label is worth a firm word only if it is right often enough. For every 10-minute snapshot from 07:00 to 21:50 on
the test days, every station of the campus corridor (the eight campus stations and the eleven at the foot of the
hill) and every arrival 1 to 30 minutes later, the script takes the chance the page would have shown (the count now,
then the chain's 10-minute steps, linear in between and rounded to 1/63 as in docs/state.json), gives the label, and
looks up in the logger whether the station had a bike (a dock) at the minute of arrival; between two snapshots the
outcome is weighted by time, as in final_rider.py. RATES_DIR holds rates fitted up to --fit-end, so every test day is
new to the chain.

Writes label_cases.csv (one row per label, kind, lead group and window), label_summary.csv (share right with a
day-bootstrap interval) and label_setup.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP, ChainValues, load_slot_rates  # noqa: E402

DATA, RATES, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIT_END, TEST_END = ARG("--fit-end", "2026-10-29"), ARG("--test-end", "2026-11-16")
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
SURE, MAYBE = {"bike": 0.90, "dock": 0.95}, {"bike": 0.60, "dock": 0.70}
LEADS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30]        # minutes from the count to the arrival
FIRST, LAST = 7 * 60, 21 * 60 + 50
SEED = 11
NAMES = {"bike": {"g": "有車", "y": "車不多", "r": "難借", "x": "沒車"}, "dock": {"g": "有空位", "y": "空位不多", "r": "難還", "x": "停滿"}}

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
CORRIDOR = [sidx[s] for s in list(CAMPUS) + list(GATEWAY) if s in sidx]
IS_CAMPUS = {sidx[s] for s in CAMPUS if s in sidx}

rates = pd.read_csv(RATES / "rates.csv", dtype={"sno": str})
prior = pd.read_csv(RATES / "rates_prior.csv")
R = np.zeros((N, 24)); Qr = np.zeros((N, 24))
for row in prior[prior.offday == 0].itertuples():
    R[:, row.hod] = row.pr; Qr[:, row.hod] = row.pq
for row in rates[(rates.offday == 0) & rates.sno.isin(sidx)].itertuples():
    R[sidx[row.sno], row.hod] = row.lam_r; Qr[sidx[row.sno], row.hod] = row.lam_q
chain = ChainValues(R, Qr, CAP, 90, 20, load_slot_rates(RATES / "rates_slots.csv", sidx))

df = load_logger(DATA)
df = df[df.sno.isin(sidx) & (df.age <= 20)].copy()
df["i"] = df.sno.map(sidx)
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS)
test_days = [d for d in days if FIT_END < d <= TEST_END]


def panel(day):
    d = df[dstr == day]
    b = np.full((144, N), np.nan); k = np.full((144, N), np.nan)
    b[d.slot.values, d.i.values] = d.bikes.values
    k[d.slot.values, d.i.values] = d.docks.values
    return b, k


def had(x, j, minute):
    """Share of the arrival minute's 10-minute interval, weighted by time, in which station j had what was needed."""
    s0, f = int(minute // STEP), (minute % STEP) / STEP
    if s0 >= 143:
        return np.nan
    x0, x1 = x[s0, j], x[s0 + 1, j]
    if np.isnan(x0) or (f > 0 and np.isnan(x1)):
        return np.nan
    return (1 - f) * float(x0 >= 1) + f * float(x1 >= 1)


def label(kind, c, now):
    if c >= SURE[kind]:
        return "g"
    if c >= MAYBE[kind]:
        return "y"
    return "x" if now == 0 else "r"


rows = []
for day in test_days:
    b, k = panel(day)
    for t in range(FIRST, LAST + 1, STEP):
        s0 = t // STEP
        known = ~np.isnan(b[s0]) & ~np.isnan(k[s0])
        if known.sum() < 50:
            continue
        now_b = np.where(known, b[s0], 0).astype(int)
        P = np.zeros((N, chain.C + 1), np.float32); P[np.arange(N), np.clip(now_b, 0, CAP)] = 1.0
        pb = np.zeros((4, N)); pk = np.zeros((4, N))
        for step in range(1, 4):
            P = chain._fwd(t + STEP * (step - 1), P)
            pb[step] = np.round((1 - P[:, 0]) * 63) / 63
            pk[step] = np.round((1 - P[np.arange(N), CAP]) * 63) / 63
        for kind, x, pr in (("bike", b, pb), ("dock", k, pk)):
            for j in CORRIDOR:
                if not known[j]:
                    continue
                now = int(x[s0, j])
                pr[0, j] = 1.0 if now >= 1 else 0.0
                for lead in LEADS:
                    q = lead / STEP; kk = int(q); f = q - kk
                    c = pr[kk, j] if f == 0 else (1 - f) * pr[kk, j] + f * pr[min(kk + 1, 3), j]
                    ok = had(x, j, t + lead)
                    if np.isnan(ok):
                        continue
                    window = "evening" if 17 * 60 <= t < 20 * 60 else "morning" if 8 * 60 + 30 <= t < 11 * 60 else "other"
                    rows.append((day, t, j, kind, lead, label(kind, c, now), c, ok, int(j in IS_CAMPUS), window))

res = pd.DataFrame(rows, columns=["day", "minute", "station", "kind", "lead", "label", "chance", "ok", "campus", "window"])
res["leads"] = np.where(res.lead <= 10, "1-10", "12-30")
cases = res.groupby(["kind", "label", "leads", "window"]).agg(cases=("ok", "size"), right=("ok", "mean"), mean_chance=("chance", "mean")).reset_index()
cases.to_csv(OUT / "label_cases.csv", index=False)

rng = np.random.default_rng(SEED)
day_list = sorted(res.day.unique())
draws = rng.integers(0, len(day_list), size=(1000, len(day_list)))
summ = []
for (kind, lab, leads), sub in list(res.groupby(["kind", "label", "leads"])) + [((kind, lab, "all"), sub) for (kind, lab), sub in res.groupby(["kind", "label"])]:
    per = sub.groupby("day").ok.agg(["sum", "size"]).reindex(day_list).fillna(0)
    rate = per["sum"].values[draws].sum(1) / np.maximum(per["size"].values[draws].sum(1), 1)
    summ.append({"kind": kind, "label": lab, "word": NAMES[kind][lab], "leads": leads, "cases": int(len(sub)), "share_of_kind": len(sub) / int((res.kind == kind).sum() if leads == "all" else ((res.kind == kind) & (res.leads == leads)).sum()),
                 "right": float(sub.ok.mean()), "lo": float(np.percentile(rate, 2.5)), "hi": float(np.percentile(rate, 97.5)), "mean_chance": float(sub.chance.mean()),
                 "evening_right": float(sub[sub.window == "evening"].ok.mean()) if (sub.window == "evening").any() else None,
                 "campus_right": float(sub[sub.campus == 1].ok.mean()) if (sub.campus == 1).any() else None})
summary = pd.DataFrame(summ).sort_values(["kind", "leads", "label"])
summary.to_csv(OUT / "label_summary.csv", index=False)
json.dump({"fit_end": FIT_END, "test_days": test_days, "stations": len(CORRIDOR), "from": "07:00", "to": "21:50", "leads_min": LEADS,
           "sure": SURE, "maybe": MAYBE, "rows": int(len(res))}, open(OUT / "label_setup.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 200)
print(summary.round(3).to_string(index=False))
