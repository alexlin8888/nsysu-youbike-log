"""What would a policy change on campus? The what-if grid behind the page's Policy tab and Sec. 3.10 of the report.

Usage: python final_policy.py DATA_DIR RATES_DIR OUT_DIR [PAGE_JSON] [--fit-end 2026-10-29] [--test-end 2026-11-16]

Information cannot help when every campus station is empty at once, so the question moves to what the school, the
city or the operator could change. For the eight campus stations on the held-out teaching days, the birth-death
chain (rates per 10-minute slot fitted up to --fit-end, as in final_docks.py) is run from the logged stock

  evening  15:00 to 20:00, counting rentals refused at an empty rack, under every combination of
    reward   the predictive voucher of final_reward.py (pay a return where the chain gives the station an even chance
             of running empty within 40 minutes) raising returns there by 0, 25, 50 or 100%; the response is not known
    truck    no truck, 20 bikes brought at 16:50, or 20 at 16:50 and 20 more at 17:50, spread over the stations by
             their evening outflow (a station takes what its free docks allow)
    stagger  all classes end at the bell, or half of those ending at 17:00 and 18:00 end 10 minutes earlier: the
             rental rate of every slot from 16:40 to 18:40 becomes the mean of its own and the next slot's
  morning  08:00 to 11:00, counting returns refused at a full rack, under every combination of
    reward   the predictive voucher for borrowing where the chain gives an even chance of the rack filling within 40
             minutes, raising rentals there by 0, 25, 50 or 100%
    truck    none, or 20 bikes taken off campus at 09:00 from the stations by their morning inflow
  (moving docks is left to final_docks.py: Engineering full 0.47 -> 0.20 of the morning, the campus day only -2.6%)

Today's voucher (pay at an empty or full rack) is in the data the rates were fitted on, so only the predictive part is
added. The chain runs without the operator's own trucks inside a window, so the levels are high; the cuts are the
result. Rewards count every paid return or rental, also those that would have happened anyway; "induced" counts only the
returns (morning: rentals) the reward adds, each one a ride that would not have been made.

The page pays the reward in ride time, 30 minutes per paid return or rental (one billing block of the Kaohsiung fare),
not in cash: REWARD_MIN below, and RIDE_MIN, the median ride from the Hamasen metro station to the campus buildings in
places.json, are written into the page file so that it can show hours of ride time and minutes of riding.

Writes policy_grid.csv and policy_setup.json, and with PAGE_JSON the file the page reads (docs/policy.json), which also
carries the timing and warning results of final_reward.py (run it first) and the truck simulation of nsysu_sim.py.
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP  # noqa: E402

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
DATA, RATES, OUT = Path(ARGS[0]), Path(ARGS[1]), Path(ARGS[2])
PAGE = Path(ARGS[3]) if len(ARGS) > 3 and ARGS[3].endswith(".json") else None
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIT_END, TEST_END = ARG("--fit-end", "2026-10-29"), ARG("--test-end", "2026-11-16")
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
EVE, MORN = (90, 120), (48, 66)                   # 15:00-20:00, 08:00-11:00 in 10-minute slots
K_PRED, THETA = 4, 0.5                            # the predictive voucher: an even chance within 40 minutes
REWARD_MIN = 30                                   # ride time paid per reward, in minutes
REWARDS = [0.0, 0.25, 0.5, 1.0]

st = load_stations(DATA)
camp = [s for s in CAMPUS if s in set(st.sno)]
cap0 = {s: int(st.set_index("sno").capacity[s]) for s in camp}
slots = pd.read_csv(RATES / "rates_slots.csv", dtype={"sno": str})
hourly = pd.read_csv(RATES / "rates.csv", dtype={"sno": str}); hourly = hourly[hourly.offday == 0]
SL = {(r.sno, r.slot): (r.lam_r, r.lam_q) for r in slots.itertuples()}
HR = {(r.sno, r.hod): (r.lam_r, r.lam_q) for r in hourly.itertuples()}
base_rates = lambda s, slot: SL.get((s, slot)) or HR.get((s, slot // 6), (0.0, 0.0))
_k, _h = {}, {}


def kern(lam_r, lam_q, c):
    """One 10-minute step at capacity c: transition matrix, expected refused rentals and refused returns by stock."""
    key = (round(lam_r, 6), round(lam_q, 6), c)
    if key not in _k:
        a, b = lam_r * STEP / 60, lam_q * STEP / 60
        M = int(max(a, b) + 8 * math.sqrt(max(a, b) + 1e-9) + 20) + c
        r = np.arange(M + 1); pr, pq = poisson.pmf(r, a), poisson.pmf(r, b)
        K = np.zeros((c + 1, c + 1)); ur = np.zeros(c + 1); uq = np.zeros(c + 1)
        for i in range(c + 1):
            prc = pr[:i + 1].copy(); prc[i] = pr[i:].sum()
            pqc = pq[:c - i + 1].copy(); pqc[c - i] = pq[c - i:].sum()
            K[i] = np.convolve(pqc, prc[::-1])
            ur[i] = ((r[i + 1:] - i) * pr[i + 1:]).sum(); uq[i] = ((r[c - i + 1:] - (c - i)) * pq[c - i + 1:]).sum()
        _k[key] = (K, ur, uq)
    return _k[key]


def hit(s, t, c, target, rates_fn):
    """P(stock reaches `target` within K_PRED steps from slot t), for every starting stock: what the voucher pays on."""
    key = (s, t, c, target, rates_fn.__name__)
    if key not in _h:
        h = (np.arange(c + 1) == target).astype(float)
        for step in range(K_PRED - 1, -1, -1):
            h = np.where(np.arange(c + 1) == target, 1.0, kern(*rates_fn(s, t + step), c)[0] @ h)
        _h[key] = h
    return _h[key]


df = load_logger(DATA)
df = df[df.sno.isin(camp) & (df.age <= 20) & df.bikes.notna()].copy()
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS and FIT_END < d <= TEST_END)
stock = {(d, s, sl): int(b) for d, s, sl, b in zip(dstr, df.sno, df.slot, df.bikes)}

out_e = {s: max(0.0, sum(base_rates(s, k)[0] - base_rates(s, k)[1] for k in range(96, 120))) for s in camp}   # 16:00-20:00
in_m = {s: max(0.0, sum(base_rates(s, k)[1] - base_rates(s, k)[0] for k in range(54, 66))) for s in camp}     # 09:00-11:00
w_e = {s: out_e[s] / sum(out_e.values()) for s in camp}
w_m = {s: in_m[s] / sum(in_m.values()) for s in camp}


def split(total, w):
    """Whole bikes per station, largest remainders first."""
    raw = {s: total * w[s] for s in w}; got = {s: int(raw[s]) for s in w}
    for s in sorted(w, key=lambda s: raw[s] - got[s], reverse=True)[:total - sum(got.values())]:
        got[s] += 1
    return got


def staggered(s, slot):
    """Half of the classes ending at 17:00 and 18:00 end 10 minutes earlier."""
    r, q = base_rates(s, slot)
    if 100 <= slot < 112:
        r = 0.5 * r + 0.5 * base_rates(s, slot + 1)[0]
    return r, q


def run(kind, reward, truck_plan, rates_fn=base_rates):
    """Expected refused rentals ('rent', evening) or returns ('return', morning), rewards paid and rides the reward adds, per teaching day."""
    window = EVE if kind == "rent" else MORN
    w = w_e if kind == "rent" else w_m
    per = {sl: split(abs(n), w) for sl, n in truck_plan.items()}
    lost = paid = induced = 0.0
    for d in days:
        for s in camp:
            c = cap0[s]; b0 = stock.get((d, s, window[0]))
            if b0 is None:
                continue
            P = np.zeros(c + 1); P[min(max(b0, 0), c)] = 1.0
            for t in range(*window):
                if t in truck_plan and per[t][s]:
                    k = per[t][s] * (1 if truck_plan[t] > 0 else -1)
                    Q = np.zeros(c + 1)
                    for i, p in enumerate(P):
                        Q[min(max(i + k, 0), c)] += p
                    P = Q
                lr, lq = rates_fn(s, t)
                if kind == "rent":
                    now = np.arange(c + 1) == 0
                    pays = now | (hit(s, t, c, 0, rates_fn) >= THETA) if reward > 0 else now     # no predictive voucher: today's rule
                    K0, u0, _ = kern(lr, lq, c); K1, u1, _ = kern(lr, lq * (1 + reward), c)
                    flow = np.where(pays & ~now, lq * (1 + reward), lq) * STEP / 60
                else:
                    now = np.arange(c + 1) == c
                    pays = now | (hit(s, t, c, c, rates_fn) >= THETA) if reward > 0 else now
                    K0, _, u0 = kern(lr, lq, c); K1, _, u1 = kern(lr * (1 + reward), lq, c)
                    flow = np.where(pays & ~now, lr * (1 + reward), lr) * STEP / 60
                extra = pays & ~now
                K = np.where(extra[:, None], K1, K0); u = np.where(extra, u1, u0)
                base_flow = (lq if kind == "rent" else lr) * STEP / 60
                lost += float(P @ u); paid += float(P @ (flow * pays)); induced += float(P @ np.where(extra, base_flow * reward, 0.0))
                P = P @ K
    return lost / len(days), paid / len(days), induced / len(days)


rows = []
for reward, truck, stagger in product(REWARDS, [0, 1, 2], [0, 1]):
    plan = {101: 20} if truck == 1 else {101: 20, 107: 20} if truck == 2 else {}
    lost, paid, more = run("rent", reward, plan, rates_fn=staggered if stagger else base_rates)
    rows.append({"window": "evening", "reward": reward, "truck": truck, "stagger": stagger, "docks": 0, "lost": lost, "vouchers": paid, "induced": more})
for reward, truck in product(REWARDS, [0, 1]):
    lost, paid, more = run("return", reward, {54: -20} if truck else {})
    rows.append({"window": "morning", "reward": reward, "truck": truck, "stagger": 0, "docks": 0, "lost": lost, "vouchers": paid, "induced": more})
G = pd.DataFrame(rows)
base = {w: float(G[(G.window == w) & (G.reward == 0) & (G.truck == 0) & (G.stagger == 0) & (G.docks == 0)].lost.iloc[0]) for w in ("evening", "morning")}
G["cut"] = 1 - G.lost / G.window.map(base)
G.to_csv(OUT / "policy_grid.csv", index=False)
setup = {"fit_end": FIT_END, "test_days": days, "stations": [CAMPUS[s] for s in camp], "evening": "15:00-20:00 refused rentals", "morning": "08:00-11:00 refused returns",
         "baseline": base, "weights_evening": {CAMPUS[s]: round(w_e[s], 3) for s in camp}, "weights_morning": {CAMPUS[s]: round(w_m[s], 3) for s in camp}}
json.dump(setup, open(OUT / "policy_setup.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 200)
print(G.round(3).to_string(index=False))

if PAGE:
    res = OUT.parent
    tim = pd.read_csv(res / "reward" / "reward_timing.csv")
    warn = pd.read_csv(res / "reward" / "reward_warning.csv").iloc[0]
    rv = pd.read_csv(res / "reward" / "reward_value.csv")
    day_rows = rv[rv.window == "14:00-20:00"]
    pred_row, now_row = day_rows[day_rows.rule.str.startswith("predictive")].iloc[0], day_rows[day_rows.rule.str.startswith("today")].iloc[0]
    # what one paid return is worth under each rule, and what a return the predictive rule leaves unpaid is worth
    worth, worth_now, worth_unpaid = float(pred_row.value_per_paid_return), float(now_row.value_per_paid_return), float(pred_row.value_per_return_unpaid)
    sim = pd.read_csv(res / "sim" / "sim_summary.csv")
    # minutes by bike from the Hamasen metro station to the campus buildings (the page's own path table)
    pl = json.load(open(PAGE.parent / "places.json"))
    a64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
    pos = {n: k for k, n in enumerate([x["id"] for x in pl["places"]] + pl["stations"])}
    campus_places = [x["id"] for x in pl["places"] if x.get("group") == "campus"]
    ride_min = float(np.median([a64.index(pl["ride"][pos["krt"]][pos[q]]) for q in campus_places]))
    ev = sim[(sim["shift"] == "evening") & (sim.policy == "campus")].sort_values("trucks")
    mo = sim[(sim["shift"] == "morning") & (sim.policy == "campus")].sort_values("trucks")
    page = {"made": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"), "days": len(days), "first": days[0], "last": days[-1],
            "reward_min": REWARD_MIN, "ride_min": ride_min,
            "evening": {"base": round(base["evening"], 1), "grid": [[r.reward, int(r.truck), int(r.stagger), round(r.lost, 1), round(r.vouchers, 1), round(r.induced, 1)] for r in G[G.window == "evening"].itertuples()]},
            "morning": {"base": round(base["morning"], 1), "grid": [[r.reward, int(r.truck), round(r.lost, 1), round(r.vouchers, 1), round(r.induced, 1)] for r in G[G.window == "morning"].itertuples()]},
            "timing": [[r.time, round(r.empty_share, 3), round(r.returns_per_day, 1), round(r.paid_now_per_day, 1), round(r.paid_pred_per_day, 1), round(r.value_mean, 2)] for r in tim.itertuples()],
            "warning": {"events": int(warn.empty_events), "flagged": round(float(warn.flagged_before), 3), "lead_median": int(warn.lead_median_min),
                        "precision": round(float(warn.flag_then_empty_share), 3), "base": round(float(warn.base_empty40_share_with_bikes), 3), "worth": round(worth, 2),
                        "worth_now": round(worth_now, 2), "worth_unpaid": round(worth_unpaid, 2)},
            "sim": {"evening": [round(float(x), 3) for x in ev.unmet_campus_avoided], "morning_refused": [round(float(x), 3) for x in mo.refused_campus_avoided]}}
    json.dump(page, open(PAGE, "w"), ensure_ascii=False, separators=(",", ":"))
    print("page file", PAGE, len(json.dumps(page)), "bytes")
