"""What would a policy change on campus? A first what-if with the birth-death chain (preliminary).

Usage: python final_policy.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16]

Information alone cannot help when every campus station is empty at once, so the question moves to what the school,
the city or the operator could change. For the eight campus stations on the held-out teaching days, the chain of
final_docks.py (rates per 10-minute slot, fitted up to --fit-end) is run from the logged stock at 16:00 to 20:00 for
rentals refused at an empty rack, and from 08:00 to 11:00 for returns refused at a full one, under these changes:

  evening (16:00-20:00, refused rentals)
    stagger_early  half of the classes ending at 17:00 and 18:00 end 10 minutes earlier: the rental rate of every slot
                   from 16:40 to 18:40 becomes the mean of its own and the next slot's (total demand unchanged)
    stagger_late   the same with half ending 10 minutes later
    reward_N       N more bikes ridden back to campus between 16:00 and 17:00 (a return reward such as the city's
                   NT$5 voucher, or Citi Bike's Bike Angels), spread over the stations by their evening outflow
    truck_20       a truck brings 20 bikes at 16:50, spread the same way (capacity caps what a station can take)
    truck_20x2     20 bikes at 16:50 and 20 more at 17:50
  morning (08:00-11:00, refused returns)
    docks_4        4 docks moved from the Gymnasium to Engineering (as in final_docks.py)
    ride_off_N     N more bikes taken off the full campus racks between 09:00 and 11:00 (the voucher pays for
                   borrowing at a full station)
    truck_out_20   a truck takes 20 bikes off campus at 09:00, from the stations by their morning inflow

The chain runs without the operator's own trucks inside a window, it finds full campus racks less often than the
logger does (report Sec. 3.7), and a refused rider is counted once, so the levels are rough; the comparison between
the changes is the point. Writes policy_summary.csv and policy_setup.json.
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
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
EVE, MORN = (96, 120), (48, 66)                   # 16:00-20:00, 08:00-11:00 in 10-minute slots
DONOR, TAKER = "501209069", "501209051"           # the Gymnasium, Engineering

st = load_stations(DATA)
camp = [s for s in CAMPUS if s in set(st.sno)]
cap0 = {s: int(st.set_index("sno").capacity[s]) for s in camp}
slots = pd.read_csv(RATES / "rates_slots.csv", dtype={"sno": str})
hourly = pd.read_csv(RATES / "rates.csv", dtype={"sno": str})
hourly = hourly[hourly.offday == 0]
SL = {(r.sno, r.slot): (r.lam_r, r.lam_q) for r in slots.itertuples()}
HR = {(r.sno, r.hod): (r.lam_r, r.lam_q) for r in hourly.itertuples()}


def base_rates(s, slot):
    return SL.get((s, slot)) or HR.get((s, slot // 6), (0.0, 0.0))


_cache = {}


def step_tables(lam_r, lam_q, c):
    key = (round(lam_r, 6), round(lam_q, 6), c)
    if key in _cache:
        return _cache[key]
    a, b = lam_r * STEP / 60, lam_q * STEP / 60
    M = int(max(a, b) + 8 * math.sqrt(max(a, b) + 1e-9) + 20) + c
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
    _cache[key] = (K, ur, uq)
    return _cache[key]


df = load_logger(DATA)
df = df[df.sno.isin(camp) & (df.age <= 20) & df.bikes.notna()].copy()
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS and FIT_END < d <= TEST_END)
stock = {(d, s, sl): b for d, s, sl, b in zip(dstr, df.sno, df.slot, df.bikes)}

# where the extra bikes go: evening by net outflow, morning by net inflow (rates in bikes per hour)
out_e = {s: max(0.0, sum(base_rates(s, k)[0] - base_rates(s, k)[1] for k in range(*EVE))) for s in camp}
in_m = {s: max(0.0, sum(base_rates(s, k)[1] - base_rates(s, k)[0] for k in range(54, 66))) for s in camp}
w_e = {s: out_e[s] / sum(out_e.values()) for s in camp}
w_m = {s: in_m[s] / sum(in_m.values()) for s in camp}


def split(total, w):
    """Whole bikes per station, largest remainders first."""
    raw = {s: total * w[s] for s in w}; got = {s: int(raw[s]) for s in w}
    for s in sorted(w, key=lambda s: raw[s] - got[s], reverse=True)[:total - sum(got.values())]:
        got[s] += 1
    return got


def run(window, metric, rates_fn, cap_fn=lambda s: cap0[s], shift_fn=None):
    """Expected refused rentals ('rent') or returns ('return') per teaching day on campus over the window."""
    total = 0.0
    for day in days:
        for s in camp:
            b0 = stock.get((day, s, window[0]))
            if b0 is None:
                continue
            c = cap_fn(s)
            P = np.zeros(c + 1); P[int(min(max(b0, 0), c))] = 1.0
            for slot in range(*window):
                if shift_fn:
                    k = shift_fn(s, slot)
                    if k:
                        Q = np.zeros(c + 1)
                        for i, p in enumerate(P):
                            Q[min(max(i + k, 0), c)] += p
                        P = Q
                K, ur, uq = step_tables(*rates_fn(s, slot), c)
                total += float(P @ (ur if metric == "rent" else uq))
                P = P @ K
    return total / len(days)


def stagger(direction):
    lo, hi = 100, 112                                   # 16:40-18:40
    def f(s, slot):
        r, q = base_rates(s, slot)
        if lo <= slot < hi:
            r2 = base_rates(s, slot + direction)[0]
            r = 0.5 * r + 0.5 * r2
        return r, q
    return f


def reward(n):
    extra = {s: n * w_e[s] for s in camp}               # bikes per hour over 16:00-17:00
    def f(s, slot):
        r, q = base_rates(s, slot)
        return (r, q + extra[s]) if 96 <= slot < 102 else (r, q)
    return f


def ride_off(n):
    extra = {s: n * w_m[s] / 2 for s in camp}           # bikes per hour over 09:00-11:00
    def f(s, slot):
        r, q = base_rates(s, slot)
        return (r + extra[s], q) if 54 <= slot < 66 else (r, q)
    return f


def trucks(plan):                                       # {slot: bikes}, + to bring, - to take
    per = {sl: split(abs(n), w_e if n > 0 else w_m) for sl, n in plan.items()}
    def f(s, slot):
        return (1 if plan[slot] > 0 else -1) * per[slot][s] if slot in plan else 0
    return f


rows = []
base_e = run(EVE, "rent", base_rates)
base_m = run(MORN, "return", base_rates)
for name, kw in [("stagger_early", dict(rates_fn=stagger(+1))), ("stagger_late", dict(rates_fn=stagger(-1))),
                 ("reward_20", dict(rates_fn=reward(20))), ("reward_40", dict(rates_fn=reward(40))),
                 ("truck_20", dict(rates_fn=base_rates, shift_fn=trucks({101: 20}))),
                 ("truck_20x2", dict(rates_fn=base_rates, shift_fn=trucks({101: 20, 107: 20}))),
                 ("stagger_early+truck_20", dict(rates_fn=stagger(+1), shift_fn=trucks({101: 20})))]:
    v = run(EVE, "rent", **kw)
    rows.append({"window": "evening 16:00-20:00", "measure": "refused rentals per teaching day", "change": name, "value": v, "baseline": base_e, "cut": 1 - v / base_e})
for name, kw in [("docks_4", dict(rates_fn=base_rates, cap_fn=lambda s: cap0[s] + (4 if s == TAKER else -4 if s == DONOR else 0))),
                 ("ride_off_20", dict(rates_fn=ride_off(20))), ("ride_off_40", dict(rates_fn=ride_off(40))),
                 ("truck_out_20", dict(rates_fn=base_rates, shift_fn=trucks({54: -20})))]:
    v = run(MORN, "return", **kw)
    rows.append({"window": "morning 08:00-11:00", "measure": "refused returns per teaching day", "change": name, "value": v, "baseline": base_m, "cut": 1 - v / base_m})
res = pd.DataFrame(rows)
res.to_csv(OUT / "policy_summary.csv", index=False)
json.dump({"fit_end": FIT_END, "test_days": days, "stations": [CAMPUS[s] for s in camp], "weights_evening": {CAMPUS[s]: round(w_e[s], 3) for s in camp},
           "weights_morning": {CAMPUS[s]: round(w_m[s], 3) for s in camp}, "baseline_evening": base_e, "baseline_morning": base_m},
          open(OUT / "policy_setup.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 200)
print(f"baseline: evening {base_e:.1f} refused rentals, morning {base_m:.1f} refused returns per teaching day ({len(days)} days)")
print(res[["window", "change", "value", "cut"]].round(3).to_string(index=False))
