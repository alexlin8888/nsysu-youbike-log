"""Does the app's advice get a student a bike, or a dock? A check against what really happened (final report).

Usage: python final_rider.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16] [--avail avail_oof.npz]

Six weeks of logging show three moments when YouBike fails around the campus on teaching days:
  leave   17:00-19:50  the campus stations have no bikes (each is empty 30-70% of the time)
  dock    09:00-10:50  the campus stations have no free dock (College of Engineering: 80% of the 09:00 hour)
  arrive  08:30-10:50  the stations at the foot of the campus (KRT exits, Linhai Rd.) have no bikes
For every 10 minutes of these windows on every test day, the script puts a rider at each station of the group
concerned, lets each strategy choose a station from what a phone showed LEAD minutes earlier, and then looks up in
the logger whether that station really had a bike (or a free dock) when the rider got there.

Strategies:
  nearest   go to the station in front of you, as most people do
  countsK   what a live-count app allows: the nearest station that has at least K bikes (docks) at the moment of
            looking (K = 1, 2, 3, 5, 8; a larger K is the cautious rider's rule of thumb)
  chainT    the nearest station whose chance of still having a bike (dock) at the minute the rider arrives is at least
            T (0.6 .. 0.95); if none reaches it, the station with the highest chance. The chance comes from the
            birth-death chain run from the snapshot to the arrival time. This is the rule of the page, with T = 0.9
            for a bike and 0.95 for a dock.
  stackT    the same rule with the chance from the stacked model of final_avail.py (chain + learned correction,
            out-of-fold); only with --avail.
Each family trades success against extra walking, so the comparison is between the curves, not single points.

RATES_DIR holds chain rates fitted up to --fit-end, so every test day is new to the model. Walking time is the
page's own (straight line x 1.25 at 80 m/min, at least one minute). The logger has a snapshot every 10 minutes, so
"had a bike on arrival" is interpolated between the two snapshots around the arrival minute.

Writes hard_hours.csv (how often each window leaves a station with nothing, over every teaching weekday logged),
rider_cases.csv, rider_summary.csv (success rate, extra walking and paired day-bootstrap intervals),
rider_by_time.csv and rider_setup.json.
"""
import json
import math
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
THETAS = [0.6, 0.7, 0.8, 0.9, 0.95]
COUNTS = [1, 2, 3, 5, 8]
AVAIL = ARG("--avail", None)
SEED = 11
HM = lambda s: int(s[:2]) * 60 + int(s[3:])
# name: (group of starting points, what the rider needs, first and last minute, minutes of looking ahead,
#        minutes between the reference time and reaching the first station, search radius in km)
SCENARIOS = {
    "leave": ("campus", "bike", HM("17:00"), HM("19:50"), 10, 5, 2.0),
    "leave_rest_of_day": ("campus", "bike", HM("07:00"), HM("16:50"), 10, 5, 2.0),
    "dock": ("campus", "dock", HM("09:00"), HM("10:50"), 10, 0, 0.6),
    "dock_rest_of_day": ("campus", "dock", HM("11:00"), HM("21:50"), 10, 0, 0.6),
    "arrive": ("gateway", "bike", HM("08:30"), HM("10:50"), 10, 2, 1.0),
}

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
lat, lng = np.radians(st.lat.values), np.radians(st.lng.values)
KM = 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((lat[:, None] - lat[None, :]) / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin((lng[:, None] - lng[None, :]) / 2) ** 2))
WALK = np.maximum(1, np.round(KM * 1.25 * 1000 / 80)).astype(int)       # minutes, as on the page
PLACES = {"campus": [sidx[s] for s in CAMPUS if s in sidx], "gateway": [sidx[s] for s in GATEWAY if s in sidx]}

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

# How bad are the three windows? Share of station snapshots with nothing to borrow (no free dock) on every teaching
# weekday logged up to TEST_END, with the lowest and the highest station of the group, and the rest of the day for scale.
hard = []
dd = df[dstr.isin([d for d in days if "2026-10-02" <= d <= TEST_END])]                # the first full day of logging onwards
for name, (grp, need, first, last, _, _, _) in SCENARIOS.items():
    g = dd[dd.i.isin(PLACES[grp]) & (dd.slot >= first // STEP) & (dd.slot <= last // STEP)]
    miss = (g.bikes if need == "bike" else g.docks) == 0
    per = miss.groupby(g.i).mean()
    hard.append({"window": name, "stations": grp, "lacking": need, "from": f"{first // 60:02d}:{first % 60:02d}", "to": f"{(last + STEP) // 60:02d}:{(last + STEP) % 60:02d}", "days": int(g.date.nunique()),
                 "snapshots": int(len(g)), "share": float(miss.mean()), "lowest_station": float(per.min()), "highest_station": float(per.max()), "highest_station_sno": st.sno[int(per.idxmax())]})
pd.DataFrame(hard).to_csv(OUT / "hard_hours.csv", index=False)
print(pd.DataFrame(hard).round(3).to_string(index=False), flush=True)


STACK = {}                                                     # day -> {"bike": (144, 10, N), "dock": ...} out-of-fold chances after k steps
if AVAIL:
    z = np.load(AVAIL)
    zdays = [str(d) for d in z["days"]]; meta = z["meta"]
    for need in ("bike", "dock"):
        p = z[f"{need}_stacked"].astype(np.float32)
        for di, d in enumerate(zdays):
            m = meta[:, 0] == di
            a = STACK.setdefault(d, {}).setdefault(need, np.full((144, 10, N), np.nan, np.float32))
            a[meta[m, 1], meta[m, 2], meta[m, 3]] = p[m]


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


rows = []
for day in test_days:
    b, k = panel(day)
    forecasts = {}                                             # decision snapshot -> chance of a bike / of a dock after 1..8 steps
    for name, (grp, need, first, last, lead, delay, max_km) in SCENARIOS.items():
        x = b if need == "bike" else k
        for ref in range(first, last + 1, STEP):
            t = ((ref - lead) // STEP) * STEP                  # snapshot on the phone
            s0 = t // STEP
            known = ~np.isnan(b[s0]) & ~np.isnan(k[s0])
            if known.sum() < 50:
                continue
            now_b = np.where(known, b[s0], 0).astype(int)
            if t not in forecasts:
                P = np.zeros((N, chain.C + 1), np.float32); P[np.arange(N), np.clip(now_b, 0, CAP)] = 1.0
                pb = np.zeros((9, N)); pd_ = np.zeros((9, N)); pb[0] = now_b >= 1; pd_[0] = now_b < CAP
                for step in range(1, 9):
                    P = chain._fwd(t + STEP * (step - 1), P)
                    pb[step] = 1 - P[:, 0]; pd_[step] = 1 - P[np.arange(N), CAP]
                forecasts[t] = (pb, pd_)
            chance = forecasts[t][0 if need == "bike" else 1]
            chance2 = None
            if day in STACK:
                c2 = STACK[day][need][s0, :9]
                chance2 = np.where(np.isnan(c2), chance, c2); chance2[0] = chance[0]
            now = now_b if need == "bike" else np.where(known, k[s0], 0).astype(int)
            for o in PLACES[grp]:
                order = [j for j in np.argsort(WALK[o], kind="stable") if known[j] and KM[o, j] <= max_km]
                # a bike is needed when the rider has walked to the station; a dock when the ride ends, whichever station it ends at
                arrive = {j: ref + delay + (WALK[o, j] if need == "bike" else 0) for j in order}
                step_at = {j: min(8, max(1, math.ceil((arrive[j] - t) / STEP))) for j in order}
                pick = {"nearest": o}
                for kk in COUNTS:
                    pick[f"counts{kk}"] = next((j for j in order if now[j] >= kk), None) or next((j for j in order if now[j] >= 1), None)
                for label, ch in (("chain", chance), ("stack", chance2)):
                    if ch is None:
                        continue
                    for th in THETAS:
                        j = next((j for j in order if ch[step_at[j], j] >= th), None)
                        if j is None and order:
                            j = max(order, key=lambda j: ch[step_at[j], j])
                        pick[f"{label}{th}"] = j
                got = {s: (np.nan, 0, -1) if j is None else (had(x, j, arrive.get(j, ref + delay + (WALK[o, j] if need == "bike" else 0))), WALK[o, j] - WALK[o, o], j) for s, j in pick.items()}
                if any(np.isnan(v[0]) for v in got.values()):   # keep the comparison paired
                    continue
                for s, (ok, extra, j) in got.items():
                    rows.append((name, day, ref, o, s, j, ok, extra))
res = pd.DataFrame(rows, columns=["scenario", "day", "minute", "place", "strategy", "station", "ok", "extra_walk_min"])
res.to_csv(OUT / "rider_cases.csv", index=False)

rng = np.random.default_rng(SEED)
day_list = sorted(res.day.unique())
draws = rng.integers(0, len(day_list), size=(1000, len(day_list)))
summ = []
for name in SCENARIOS:
    sub = res[res.scenario == name]
    piv = sub.groupby(["strategy", "day"]).agg(ok=("ok", "sum"), n=("ok", "size"), extra=("extra_walk_min", "sum"))
    get = lambda s: piv.loc[s].reindex(day_list).fillna(0)
    rate = lambda p: p.ok.values[draws].sum(1) / np.maximum(p.n.values[draws].sum(1), 1)
    for s in sub.strategy.unique():
        p = get(s)
        row = {"scenario": name, "strategy": s, "cases": int(p.n.sum()), "success": p.ok.sum() / p.n.sum(), "lo": np.percentile(rate(p), 2.5), "hi": np.percentile(rate(p), 97.5),
               "extra_walk_min": p.extra.sum() / p.n.sum(), "moved_share": float((sub[sub.strategy == s].extra_walk_min > 0).mean())}
        for base in ("nearest", "counts1"):
            if s != base and not (base == "counts1" and s == "nearest"):
                d = rate(p) - rate(get(base))
                row.update({f"gain_vs_{base}": row["success"] - get(base).ok.sum() / get(base).n.sum(), f"gain_vs_{base}_lo": np.percentile(d, 2.5), f"gain_vs_{base}_hi": np.percentile(d, 97.5)})
        summ.append(row)
summ = pd.DataFrame(summ)
summ.to_csv(OUT / "rider_summary.csv", index=False)
byt = res.assign(hhmm=(res.minute // 30 * 30).map(lambda m: f"{m // 60:02d}:{m % 60:02d}")).groupby(["scenario", "hhmm", "strategy"]).agg(cases=("ok", "size"), success=("ok", "mean"), extra_walk_min=("extra_walk_min", "mean")).reset_index()
byt.to_csv(OUT / "rider_by_time.csv", index=False)
json.dump({"test_days": test_days, "scenarios": {k: {"start_points": v[0], "needs": v[1], "from": v[2], "to": v[3], "lead_min": v[4], "delay_min": v[5], "max_km": v[6]} for k, v in SCENARIOS.items()},
           "thetas": THETAS, "campus": [st.sno[o] for o in PLACES["campus"]], "gateway": [st.sno[o] for o in PLACES["gateway"]]}, open(OUT / "rider_setup.json", "w"), indent=1)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
show = summ[summ.scenario.isin(["leave", "dock", "arrive"])][["scenario", "strategy", "cases", "success", "lo", "hi", "extra_walk_min", "moved_share", "gain_vs_nearest", "gain_vs_counts1", "gain_vs_counts1_lo", "gain_vs_counts1_hi"]]
print(show.round(3).to_string(index=False))
print(summ[summ.scenario.str.contains("rest") & summ.strategy.isin(["nearest", "counts1", "counts3", "chain0.9", "chain0.95"])][["scenario", "strategy", "cases", "success", "extra_walk_min"]].round(3).to_string(index=False))
