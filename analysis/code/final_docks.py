"""Would moving docks between campus stations help, and which ones?

Usage: python final_docks.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16] [--moves 12]

In the morning the campus as a whole keeps docks free while single stations are full (final_city.py: Engineering
55% of the time between 09:00 and 11:00, the Gymnasium with its 63 docks 15%). Citi Bike moved docks between
stations on the advice of a model of expected unmet demand and found that each added dock saved about 1.5 empty or
full events a day (Freund et al., "Analytics and Bikes"). This script asks the same question of the eight campus
stations with the birth-death chain of the planner.

For every held-out teaching day and every campus station, the chain is run through the day in three-hour windows,
each started from the logged stock at its first snapshot (the operator's trucks act between windows as they did),
with the station's rates per 10-minute slot (rates_slots.csv). Every step adds the expected rentals refused at an
empty station and the expected returns refused at a full one. This is repeated for capacities from the real one
minus MAX_DELTA to plus MAX_DELTA. A greedy search then moves one dock at a time from the station where losing it
costs least to the station where gaining it saves most, as long as the total of refused rentals and returns falls,
up to --moves docks (the discrete gradient method of the Citi Bike study).

The chain's rates are fitted with the censoring at a full rack taken into account, so refused returns are part of
the model. On campus the chain finds full stations less often than the logger does (Sec. 3.7 of the report), so
the counts of refused returns, and what extra docks save, are likely too low. A refused rider is counted once; in
reality the rider rides on to another station.

Writes docks_station.csv (each station's refused rentals and returns per teaching day, by capacity),
docks_greedy.csv (the moves in order with the totals after each) and docks_pairs.csv (moving k docks from the
Gymnasium to Engineering, k = 1..10, by period of the day).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP  # noqa: E402

DATA, RATES, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIT_END, TEST_END = ARG("--fit-end", "2026-10-29"), ARG("--test-end", "2026-11-16")
MOVES = int(ARG("--moves", 12))
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
MAX_DELTA = 12
WINDOWS = [(36, 54), (54, 72), (72, 90), (90, 108), (108, 126), (126, 138)]      # 06:00-09:00, ..., 21:00-23:00, in 10-minute slots
PERIODS = {"09:00-11:00": (54, 66), "17:00-20:00": (102, 120), "day": (36, 138)}
DONOR, TAKER = "501209069", "501209051"                                           # the Gymnasium, Engineering

st = load_stations(DATA)
camp = [s for s in CAMPUS if s in set(st.sno)]
cap0 = {s: int(st.set_index("sno").capacity[s]) for s in camp}
slots = pd.read_csv(RATES / "rates_slots.csv", dtype={"sno": str})
hourly = pd.read_csv(RATES / "rates.csv", dtype={"sno": str})
hourly = hourly[hourly.offday == 0]


def rates_at(sno, slot):
    r = slots[(slots.sno == sno) & (slots.slot == slot)]
    if len(r):
        return float(r.lam_r.iloc[0]), float(r.lam_q.iloc[0])
    h = hourly[(hourly.sno == sno) & (hourly.hod == slot // 6)]
    return (float(h.lam_r.iloc[0]), float(h.lam_q.iloc[0])) if len(h) else (0.0, 0.0)


def step_tables(lam_r, lam_q, c):
    """One 10-minute step at capacity c: transition matrix, expected refused rentals and refused returns by stock."""
    a, b = lam_r * STEP / 60, lam_q * STEP / 60
    M = int(max(a, b) + 8 * math.sqrt(max(a, b)) + 20) + c
    r = np.arange(M + 1)
    pr, pq = poisson.pmf(r, a), poisson.pmf(r, b)
    K = np.zeros((c + 1, c + 1)); ur = np.zeros(c + 1); uq = np.zeros(c + 1)
    for i in range(c + 1):
        prc = pr[:i + 1].copy(); prc[i] = pr[i:].sum()
        pqc = pq[:c - i + 1].copy(); pqc[c - i] = pq[c - i:].sum()
        K[i] = np.convolve(pqc, prc[::-1])
        ur[i] = ((r[i + 1:] - i) * pr[i + 1:]).sum()
        f = c - i
        uq[i] = ((r[f + 1:] - f) * pq[f + 1:]).sum()
    return K, ur, uq


df = load_logger(DATA)
df = df[df.sno.isin(camp) & (df.age <= 20) & df.bikes.notna()].copy()
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS and FIT_END < d <= TEST_END)
stock = {(d, s, sl): b for d, s, sl, b in zip(dstr, df.sno, df.slot, df.bikes)}

tables = {}
rows = []
for s in camp:
    for delta in range(-MAX_DELTA, MAX_DELTA + 1):
        c = cap0[s] + delta
        if c < 4:
            continue
        for slot in range(36, 138):
            if (s, slot, c) not in tables:
                tables[(s, slot, c)] = step_tables(*rates_at(s, slot), c)
        for day in days:
            for w0, w1 in WINDOWS:
                b0 = stock.get((day, s, w0))
                if b0 is None:
                    continue
                P = np.zeros(c + 1); P[int(min(max(b0, 0), c))] = 1.0
                for slot in range(w0, w1):
                    K, ur, uq = tables[(s, slot, c)]
                    rows.append((s, delta, c, day, slot, float(P @ ur), float(P @ uq), float(P[c]), float(P[0])))
                    P = P @ K
    print(s, CAMPUS[s], "done", flush=True)

res = pd.DataFrame(rows, columns=["sno", "delta", "cap", "day", "slot", "lost_rent", "lost_return", "p_full", "p_empty"])
nd = res.day.nunique()


def per_day(sel):
    g = sel.groupby(["sno", "delta", "cap"])[["lost_rent", "lost_return"]].sum() / nd
    g["lost"] = g.lost_rent + g.lost_return
    return g.reset_index()


station = []
for name, (a, z) in PERIODS.items():
    g = per_day(res[(res.slot >= a) & (res.slot < z)])
    full = res[(res.slot >= a) & (res.slot < z)].groupby(["sno", "delta"]).p_full.mean().rename("chain_full_share").reset_index()
    g = g.merge(full, on=["sno", "delta"]); g["period"] = name; g["station"] = g.sno.map(CAMPUS)
    station.append(g)
station = pd.concat(station)
station.round(4).to_csv(OUT / "docks_station.csv", index=False)

day_tab = station[station.period == "day"].set_index(["sno", "delta"]).lost
cur = {s: 0 for s in camp}
total = lambda d: sum(day_tab[(s, d[s])] for s in camp)
greedy = [{"move": 0, "from": "", "to": "", "lost_per_day": total(cur), **{CAMPUS[s]: cap0[s] + cur[s] for s in camp}}]
for m in range(1, MOVES + 1):
    best = None
    for give in camp:
        if (give, cur[give] - 1) not in day_tab.index:
            continue
        for take in camp:
            if take == give or (take, cur[take] + 1) not in day_tab.index:
                continue
            gain = day_tab[(give, cur[give] - 1)] - day_tab[(give, cur[give])] + day_tab[(take, cur[take] + 1)] - day_tab[(take, cur[take])]
            if best is None or gain < best[0]:
                best = (gain, give, take)
    if best is None or best[0] >= -1e-6:
        break
    cur[best[1]] -= 1; cur[best[2]] += 1
    greedy.append({"move": m, "from": CAMPUS[best[1]], "to": CAMPUS[best[2]], "lost_per_day": total(cur), **{CAMPUS[s]: cap0[s] + cur[s] for s in camp}})
greedy = pd.DataFrame(greedy)
greedy.round(3).to_csv(OUT / "docks_greedy.csv", index=False)

pairs = []
for k in range(0, 11):
    row = {"k": k}
    for name in PERIODS:
        t = station[station.period == name].set_index(["sno", "delta"])
        row[f"lost_{name}"] = t.lost[(DONOR, -k)] + t.lost[(TAKER, k)]
        row[f"return_{name}"] = t.lost_return[(DONOR, -k)] + t.lost_return[(TAKER, k)]
        row[f"rent_{name}"] = t.lost_rent[(DONOR, -k)] + t.lost_rent[(TAKER, k)]
        row[f"taker_full_{name}"] = t.chain_full_share[(TAKER, k)]
        row[f"donor_full_{name}"] = t.chain_full_share[(DONOR, -k)]
    pairs.append(row)
pairs = pd.DataFrame(pairs)
pairs.round(4).to_csv(OUT / "docks_pairs.csv", index=False)
json.dump({"days": days, "fit_end": FIT_END, "windows": WINDOWS, "periods": PERIODS, "donor": DONOR, "taker": TAKER, "capacities": {CAMPUS[s]: cap0[s] for s in camp}}, open(OUT / "docks_setup.json", "w"), indent=1)
pd.set_option("display.width", 250)
print(len(days), "held-out teaching days")
print(station[station.delta == 0].round(3).to_string(index=False))
print(greedy.round(2).to_string(index=False))
print(pairs.round(3).to_string(index=False))
