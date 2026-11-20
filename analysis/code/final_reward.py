"""Does the operator's NT$5 voucher pay at the right time? The rule of today against a predictive one, on campus.

Usage: python final_reward.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16]

The voucher (友愛騎乘券, nationwide since 1 July 2026) pays a rider who returns a bike to an empty station, or borrows
from a full one, at that moment. On campus the evening shortage follows the bells: the stations empty after 17:00,
so a rider who brings a bike back at 16:30, when it would serve a student leaving class at 17:05, is not paid. A
predictive rule would pay where the chain gives the station at least an even chance (THETA) of running empty within
the next PRED_MIN minutes; demo_state.py writes the same chance for the page ("reward" in docs/state.json).

For the eight campus stations on the held-out teaching days (chain rates fitted up to --fit-end, per 10-minute
slot) the script computes, from the logged stock at every snapshot:

  timing     per half hour from 14:00 to 20:00: the share of station-time that is empty, the returns expected at
             campus stations (the chain's return rate), and how many of them each rule would pay
  value      the rentals refused later that one more bike at that station and minute avoids (the backward pass
             of the chain over the next 2 hours, as in the route planner); the mean over the returns each rule pays
  warning    for every time a station ran empty between 15:00 and 20:00 after having bikes, how many minutes before
             the predictive rule first flagged it (within the hour before), and how often a flag was followed by an
             empty station in the logger within PRED_MIN minutes
  what-if    the chain run from the logged stock at 15:00 to 20:00 with returns raised by a share ALPHA in the states
             that each rule pays (today's rule: an empty station; the predictive rule also a station the chain
             expects to empty within PRED_MIN minutes). The data already contain the response to today's rule, so
             the comparison adds the predictive part alone. The response share is not known; 25%, 50% and 100%
             are shown. Vouchers count every paid return, also the ones that would have happened anyway.
  morning    the same for borrowing at a full station between 08:00 and 11:00, against returns refused there.

Writes reward_timing.csv, reward_value.csv, reward_warning.csv, reward_whatif.csv and reward_setup.json.
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
PRED_MIN, THETA, H_VALUE = 40, 0.5, 120           # the predictive rule's horizon and threshold; horizon of a bike's value
ALPHAS = [0.25, 0.5, 1.0]
K_PRED, K_VAL = PRED_MIN // STEP, H_VALUE // STEP
EVE, MORN = (84, 120), (48, 66)                   # 14:00-20:00, 08:00-11:00 in 10-minute slots
WHATIF_EVE, WHATIF_MORN = (90, 120), (48, 66)     # 15:00-20:00, 08:00-11:00

st = load_stations(DATA)
camp = [s for s in CAMPUS if s in set(st.sno)]
cap0 = {s: int(st.set_index("sno").capacity[s]) for s in camp}
slots = pd.read_csv(RATES / "rates_slots.csv", dtype={"sno": str})
hourly = pd.read_csv(RATES / "rates.csv", dtype={"sno": str}); hourly = hourly[hourly.offday == 0]
SL = {(r.sno, r.slot): (r.lam_r, r.lam_q) for r in slots.itertuples()}
HR = {(r.sno, r.hod): (r.lam_r, r.lam_q) for r in hourly.itertuples()}
rates = lambda s, slot: SL.get((s, slot)) or HR.get((s, slot // 6), (0.0, 0.0))
_k = {}


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


def hit(s, t, c, target, k):
    """P(the station reaches stock `target` within k steps from slot t), for every starting stock (target absorbing)."""
    h = (np.arange(c + 1) == target).astype(float)
    for step in range(k - 1, -1, -1):
        K = kern(*rates(s, t + step), c)[0]
        h = np.where(np.arange(c + 1) == target, 1.0, K @ h)
    return h


def values(s, t0, t1, c, kind):
    """V[t](i): expected refused rentals ('rent') or returns ('return') from slot t to t1 with stock i at t."""
    V = {t1: np.zeros(c + 1)}
    for t in range(t1 - 1, t0 - 1, -1):
        K, ur, uq = kern(*rates(s, t), c)
        V[t] = (ur if kind == "rent" else uq) + K @ V[t + 1]
    return V


df = load_logger(DATA)
df = df[df.sno.isin(camp) & (df.age <= 20) & df.bikes.notna()].copy()
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS and FIT_END < d <= TEST_END)
stock = {(d, s, sl): int(b) for d, s, sl, b in zip(dstr, df.sno, df.slot, df.bikes)}

# eligibility tables, per station and slot, over the starting stock
P_EMPTY = {(s, t): hit(s, t, cap0[s], 0, K_PRED) for s in camp for t in range(*EVE)}
P_FULL = {(s, t): hit(s, t, cap0[s], cap0[s], K_PRED) for s in camp for t in range(*MORN)}
# the value of one more bike at slot t over the next two hours, for every stock (rates do not depend on the day)
VAL = {}
for s in camp:
    for t in range(*EVE):
        Vt = values(s, t, min(t + K_VAL, 138), cap0[s], "rent")[t]
        VAL[(s, t)] = np.append(Vt[:-1] - Vt[1:], 0.0)

# ---------------------------------------------------------------- timing, value and warning, from the logged stock
rows, warn = [], []
for d in days:
    for s in camp:
        c = cap0[s]
        for t in range(*EVE):
            b = stock.get((d, s, t))
            if b is None:
                continue
            b = min(max(b, 0), c)
            lam_q = rates(s, t)[1]
            exp_ret = lam_q * STEP / 60                                   # returns expected in this slot
            val = float(VAL[(s, t)][b])                                   # refused rentals one more bike avoids
            pe = float(P_EMPTY[(s, t)][b])
            now_rule = b == 0
            pred_rule = now_rule or pe >= THETA
            later = [stock.get((d, s, t + k)) for k in range(1, K_PRED + 1)]
            emptied = any(x is not None and x == 0 for x in later)
            rows.append((d, s, t, b, exp_ret, val, pe, now_rule, pred_rule, emptied))
        # every time the station ran empty after having bikes, 15:00-20:00: how early did the predictive rule flag it?
        for t in range(90, 120):
            b, b0 = stock.get((d, s, t)), stock.get((d, s, t - 1))
            if b is None or b0 is None or not (b == 0 and b0 > 0):
                continue
            lead = 0
            for k in range(6, 0, -1):                                     # the hour before, earliest first
                x = stock.get((d, s, t - k))
                if x is not None and x > 0 and P_EMPTY.get((s, t - k)) is not None and P_EMPTY[(s, t - k)][min(x, c)] >= THETA:
                    lead = 10 * k; break
            warn.append((d, s, t, lead))
R = pd.DataFrame(rows, columns=["day", "sno", "slot", "bikes", "exp_returns", "value", "p_empty40", "pays_now", "pays_pred", "emptied40"])
W = pd.DataFrame(warn, columns=["day", "sno", "slot", "lead_min"])
nd = len(days)
R["half"] = (R.slot // 3) * 30                                            # minutes from midnight, half hours
tim = R.groupby("half").apply(lambda g: pd.Series({
    "empty_share": float((g.bikes == 0).mean()),
    "returns_per_day": float(g.exp_returns.sum() / nd),
    "paid_now_per_day": float(g.exp_returns[g.pays_now].sum() / nd),
    "paid_pred_per_day": float(g.exp_returns[g.pays_pred].sum() / nd),
    "value_mean": float(g.value.mean()),
    "value_of_paid_now": float(np.average(g.value[g.pays_now], weights=g.exp_returns[g.pays_now])) if g.pays_now.any() and g.exp_returns[g.pays_now].sum() > 0 else np.nan,
    "value_of_paid_pred": float(np.average(g.value[g.pays_pred], weights=g.exp_returns[g.pays_pred])) if g.pays_pred.any() and g.exp_returns[g.pays_pred].sum() > 0 else np.nan})).reset_index()
tim.insert(0, "time", tim.half.map(lambda m: f"{m // 60:02d}:{m % 60:02d}"))
tim.drop(columns="half").to_csv(OUT / "reward_timing.csv", index=False)

pre = R[R.slot < 102]                                                     # before 17:00
val = pd.DataFrame([
    {"rule": rule, "window": win, "returns_paid_per_day": float(g.exp_returns[g[col]].sum() / nd), "returns_all_per_day": float(g.exp_returns.sum() / nd),
     "value_per_paid_return": float(np.average(g.value[g[col]], weights=g.exp_returns[g[col]])) if g.exp_returns[g[col]].sum() > 0 else np.nan,
     "value_per_return_unpaid": float(np.average(g.value[~g[col]], weights=g.exp_returns[~g[col]])) if g.exp_returns[~g[col]].sum() > 0 else np.nan}
    for rule, col in (("today: empty now", "pays_now"), ("predictive: empty now or within 40 min", "pays_pred"))
    for win, g in (("14:00-17:00", pre), ("17:00-20:00", R[R.slot >= 102]), ("14:00-20:00", R))])
val.to_csv(OUT / "reward_value.csv", index=False)

flag = R[R.pays_pred & ~R.pays_now]                                       # flagged by the prediction while bikes remain
warn_sum = pd.DataFrame([{"empty_events": int(len(W)), "flagged_before": float((W.lead_min > 0).mean()), "lead_mean_min": float(W.lead_min[W.lead_min > 0].mean()),
                          "lead_median_min": float(W.lead_min[W.lead_min > 0].median()), "flags_with_bikes": int(len(flag)),
                          "flag_then_empty_share": float(flag.emptied40.mean()), "base_empty40_share_with_bikes": float(R[R.bikes > 0].emptied40.mean())}])
warn_sum.to_csv(OUT / "reward_warning.csv", index=False)

# ---------------------------------------------------------------- what-if: raise returns (rentals) where a rule pays


def run(window, kind, rule, alpha):
    """Expected refused rentals (evening) or returns (morning) per teaching day, and vouchers paid per day."""
    lost = paid = 0.0
    for d in days:
        for s in camp:
            c = cap0[s]; b0 = stock.get((d, s, window[0]))
            if b0 is None:
                continue
            P = np.zeros(c + 1); P[min(max(b0, 0), c)] = 1.0
            for t in range(*window):
                lr, lq = rates(s, t)
                if kind == "rent":
                    now = np.arange(c + 1) == 0
                    pays = now | (P_EMPTY[(s, t)] >= THETA) if rule == "pred" else now
                    extra = pays & ~now if rule == "pred" else np.zeros(c + 1, bool)      # today's rule is in the data
                    K0, u0, _ = kern(lr, lq, c); K1, u1, _ = kern(lr, lq * (1 + alpha), c)
                    exp_ret = np.where(extra, lq * (1 + alpha), lq) * STEP / 60
                else:
                    full = np.arange(c + 1) == c
                    pays = full | (P_FULL[(s, t)] >= THETA) if rule == "pred" else full
                    extra = pays & ~full if rule == "pred" else np.zeros(c + 1, bool)
                    K0, _, u0 = kern(lr, lq, c); K1, _, u1 = kern(lr * (1 + alpha), lq, c)
                    exp_ret = np.where(extra, lr * (1 + alpha), lr) * STEP / 60
                K = np.where(extra[:, None], K1, K0); u = np.where(extra, u1, u0)
                lost += float(P @ u); paid += float(P @ (exp_ret * pays))
                P = P @ K
    return lost / len(days), paid / len(days)


wi = []
for kind, window, label in (("rent", WHATIF_EVE, "evening 15:00-20:00, refused rentals"), ("return", WHATIF_MORN, "morning 08:00-11:00, refused returns")):
    base, paid0 = run(window, kind, "now", 0.0)
    wi.append({"window": label, "rule": "today", "alpha": 0.0, "lost_per_day": base, "cut": 0.0, "vouchers_per_day": paid0, "extra_vouchers_per_day": 0.0, "lost_avoided_per_100_extra_vouchers": np.nan})
    for a in ALPHAS:
        v, p = run(window, kind, "pred", a)
        wi.append({"window": label, "rule": "predictive", "alpha": a, "lost_per_day": v, "cut": 1 - v / base, "vouchers_per_day": p, "extra_vouchers_per_day": p - paid0,
                   "lost_avoided_per_100_extra_vouchers": 100 * (base - v) / (p - paid0) if p > paid0 else np.nan})
WI = pd.DataFrame(wi)
WI.to_csv(OUT / "reward_whatif.csv", index=False)
json.dump({"fit_end": FIT_END, "test_days": days, "stations": [CAMPUS[s] for s in camp], "pred_min": PRED_MIN, "theta": THETA, "value_horizon_min": H_VALUE,
           "alphas": ALPHAS, "rows": int(len(R))}, open(OUT / "reward_setup.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 220)
print(tim.drop(columns="half").round(3).to_string(index=False))
print(val.round(3).to_string(index=False))
print(warn_sum.round(3).to_string(index=False))
print(WI.round(3).to_string(index=False))
