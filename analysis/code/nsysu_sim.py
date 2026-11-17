"""Trucks at NSYSU: what the route search would save in the two hard periods of a teaching day (simulation).

Usage: python nsysu_sim.py DATA_DIR PLANNER_RATES_DIR WORLD_RATES_DIR OUT_DIR [--seeds 5] [--workers 2]
                           [--first 2026-10-30] [--last 2026-11-16]

Kaohsiung publishes no trip records, so a policy cannot be replayed on real trips as at NTU. This script does the
next best thing. Demand is drawn from the chain model itself: in every 10-minute step each station gets
Poisson(lam_r / 6) rental requests and Poisson(lam_q / 6) returns, with the rates of WORLD_RATES_DIR (fitted to the
later weeks only). A request at an empty station is an unmet rental; a return at a full station is a refused return.

Two shifts are simulated on every real teaching day of the period, each starting from the stock the logger
recorded at its first minute, so the simulation never drifts far from what happened:
  morning  07:00-11:00  the campus fills up and the stations at its foot run empty
  evening  15:00-20:00  the campus runs empty
The trucks plan with the route search of route_planner.py, exactly as the live page does, but with the rates of
PLANNER_RATES_DIR (fitted to the earlier weeks), so the planner does not know the rates that generate the demand.
A truck drives the first two stops of its route and plans again (capacity 20, 15 km/h on 1.3 x straight-line
distance, 4 min per stop). A stock change takes effect at the first 10-minute boundary after the truck arrives.

Policies: no truck; K trucks that deliver only to the 19 stations between campus and the metro ("campus"); K trucks
free to deliver to any of the 309 stations ("area"). All policies see the same random demand, so differences are
paired.

Writes sim_runs.csv (one row per day, seed, shift and policy), sim_summary.csv (shares avoided with day-bootstrap
intervals), sim_stock.csv (simulated against logged campus stock without trucks, a check on the demand model) and
sim_setup.json.
"""
import json
import math
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP, ChainValues, RoutePlanner, load_slot_rates  # noqa: E402

DATA, PLAN_RATES, WORLD_RATES, OUT = [Path(a) for a in sys.argv[1:5]]
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default, cast=str: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
SEEDS, WORKERS = ARG("--seeds", 5, int), ARG("--workers", 2, int)
FIRST, LAST = ARG("--first", "2026-10-30"), ARG("--last", "2026-11-16")
Q, SPEED_KMH, STOP_MIN, HANDLE_MIN, PER_BIKE_MIN = 20, 15.0, 3.0, 1.0, 0.1       # as in demo_state.py
BETA, STOPS, ITERS, HORIZON, DRIVE = 0.25, 6, 400, 90, 2
SHIFTS = {"morning": (42, 66, 48, 66), "evening": (90, 120, 102, 120)}            # first slot, end slot, and the slots that are scored
POLICIES = [("none", 0), ("campus", 1), ("campus", 2), ("campus", 3), ("area", 1), ("area", 3)]

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
lat, lng = st.lat.values, st.lng.values
p_ = math.pi / 180
DIST_KM = 6371 * np.hypot((lng[:, None] - lng[None, :]) * p_ * math.cos(lat.mean() * p_), (lat[:, None] - lat[None, :]) * p_) * 1.3
TRAVEL_MIN = DIST_KM / SPEED_KMH * 60
EXCLUDED = (st.district == "旗津區").values
IS_CAMPUS = st.sno.isin(CAMPUS).values; IS_GATE = st.sno.isin(GATEWAY).values; CORRIDOR = IS_CAMPUS | IS_GATE


def hourly(rates_dir):
    rates = pd.read_csv(rates_dir / "rates.csv", dtype={"sno": str}); prior = pd.read_csv(rates_dir / "rates_prior.csv")
    R = np.zeros((N, 24)); Qr = np.zeros((N, 24))
    for row in prior[prior.offday == 0].itertuples():
        R[:, row.hod] = row.pr; Qr[:, row.hod] = row.pq
    for row in rates[(rates.offday == 0) & rates.sno.isin(sidx)].itertuples():
        R[sidx[row.sno], row.hod] = row.lam_r; Qr[sidx[row.sno], row.hod] = row.lam_q
    return R, Qr, load_slot_rates(rates_dir / "rates_slots.csv", sidx)


def per_slot(rates_dir):
    """Rental and return rates per station and 10-minute slot of a teaching day, (N, 144) each."""
    R, Qr, slots = hourly(rates_dir)
    lr = np.repeat(R, 6, axis=1); lq = np.repeat(Qr, 6, axis=1)
    if slots is not None:
        idx, sr, sq = slots
        lr[idx] = np.where(np.isnan(sr), lr[idx], sr); lq[idx] = np.where(np.isnan(sq), lq[idx], sq)
    return lr, lq


df = load_logger(DATA)
df = df[df.sno.isin(sidx) & (df.age <= 20)].copy()
df["i"] = df.sno.map(sidx); dstr = df.date.astype(str).str.slice(0, 10)
DAYS = [d for d in sorted(dstr.unique()) if FIRST <= d <= LAST and pd.Timestamp(d).dayofweek < 5 and d not in HOLIDAYS and d != "2026-10-23"]


def logged(day):
    d = df[dstr == day]
    b = np.full((144, N), np.nan)
    b[d.slot.values, d.i.values] = d.bikes.values
    return b


START = {}                                                         # (day, shift) -> stock at the shift's first minute
for day in DAYS:
    b = logged(day)
    for shift, (s0, s1, _, _) in SHIFTS.items():
        if (~np.isnan(b[s0])).sum() >= 250 and (~np.isnan(b[s0:s1][:, IS_CAMPUS])).mean() > 0.9:   # the logger covered the shift
            START[(day, shift)] = b[s0]
LR, LQ = per_slot(WORLD_RATES)
_planner_values = None


def values():
    global _planner_values
    if _planner_values is None:
        R, Qr, slots = hourly(PLAN_RATES)
        _planner_values = ChainValues(R, Qr, CAP, HORIZON, Q, slots)
    return _planner_values


def run(day, shift, seed, policy, K, demand):
    s0, s1, m0, m1 = SHIFTS[shift]
    Dr, Dq = demand
    frozen = np.isnan(START[(day, shift)])
    bikes = np.where(frozen, 0, START[(day, shift)]).astype(int)
    planner = RoutePlanner(TRAVEL_MIN, Q, STOP_MIN, HANDLE_MIN, HORIZON, beta=BETA, max_stops=STOPS, iters=ITERS)
    prng = np.random.default_rng(seed)
    trucks = [{"free": s0 * STEP, "pos": None, "load": 0, "queue": []} for _ in range(K)]
    out = dict.fromkeys(["requests_campus", "unmet_campus", "requests_gateway", "unmet_gateway", "requests_other", "unmet_other", "returns_campus", "refused_campus",
                         "campus_empty_station_steps", "moved", "plans"], 0)
    out["drive_min"] = 0.0
    stock = np.zeros(s1 - s0)
    for s in range(s0, s1):
        t = s * STEP
        for tr in trucks:                                          # stops reached since the last boundary take effect now
            while tr["queue"] and tr["queue"][0][2] <= t:
                i, d, arr = tr["queue"].pop(0)
                if d > 0:
                    a = min(d, tr["load"], CAP[i] - bikes[i]); bikes[i] += a; tr["load"] -= a
                else:
                    a = min(-d, bikes[i], Q - tr["load"]); bikes[i] -= a; tr["load"] += a
                out["moved"] += a; tr["pos"] = i; tr["free"] = arr + STOP_MIN + a * PER_BIKE_MIN
        idle = [tr for tr in trucks if not tr["queue"] and tr["free"] <= t]
        if idle:
            B = values().benefit(t, bikes)
            if policy == "campus":
                B = B.copy(); B[~CORRIDOR, :, Q + 1:] = 0.0         # nothing to gain from a delivery outside the corridor
            claimed = frozen | EXCLUDED
            for tr in trucks:
                for i, _, _ in tr["queue"]:
                    claimed[i] = True
            for tr in idle:
                stops = planner.plan(B, bikes, CAP, tr["pos"], tr["load"], claimed, prng)[:DRIVE]
                out["plans"] += 1
                prev = tr["pos"]
                for i, d, off in stops:
                    tr["queue"].append((i, d, t + off)); claimed[i] = True
                    out["drive_min"] += 5.0 if prev is None else TRAVEL_MIN[prev, i]; prev = i
        r, q = np.where(frozen, 0, Dr[s - s0]), np.where(frozen, 0, Dq[s - s0])
        served = np.minimum(r, bikes); taken = np.minimum(q, CAP - bikes)
        if m0 <= s < m1:
            miss = r - served
            for name, m in (("campus", IS_CAMPUS), ("gateway", IS_GATE), ("other", ~CORRIDOR)):
                out["requests_" + name] += int(r[m].sum()); out["unmet_" + name] += int(miss[m].sum())
            out["returns_campus"] += int(q[IS_CAMPUS].sum()); out["refused_campus"] += int((q - taken)[IS_CAMPUS].sum())
            out["campus_empty_station_steps"] += int((bikes[IS_CAMPUS] == 0).sum())
        stock[s - s0] = bikes[IS_CAMPUS].sum()
        bikes = bikes - served + taken
    out.update({"day": day, "shift": shift, "seed": seed, "policy": policy, "trucks": K})
    return out, stock


def job(args):
    day, shift, seed = args
    s0, s1 = SHIFTS[shift][:2]
    rng = np.random.default_rng(1000 * seed + 10 * DAYS.index(day) + (shift == "evening"))
    demand = (rng.poisson(LR[:, s0:s1].T / 6), rng.poisson(LQ[:, s0:s1].T / 6))
    res, none = [], None
    for policy, K in POLICIES:
        o, stock = run(day, shift, seed, policy, K, demand)
        res.append(o)
        if policy == "none":
            none = stock
    return res, (day, shift, none)


if __name__ == "__main__":
    tasks = [(d, sh, s) for (d, sh) in START for s in range(SEEDS)]
    print(len(DAYS), "teaching days,", len(START), "shifts,", len(tasks), "simulated shifts", flush=True)
    runs, stocks = [], []
    with Pool(WORKERS) as pool:
        for n, (res, stk) in enumerate(pool.imap_unordered(job, tasks)):
            runs += res; stocks.append(stk)
            if (n + 1) % 10 == 0:
                print(n + 1, "/", len(tasks), flush=True)
    runs = pd.DataFrame(runs)
    runs["requests_corridor"] = runs.requests_campus + runs.requests_gateway; runs["unmet_corridor"] = runs.unmet_campus + runs.unmet_gateway
    runs.to_csv(OUT / "sim_runs.csv", index=False)
    # every policy against the no-truck run of the same day, shift and seed; intervals from a bootstrap over days
    rng = np.random.default_rng(7)
    rows = []
    for shift in SHIFTS:
        R = runs[runs["shift"] == shift]
        dlist = sorted(R.day.unique()); draws = rng.integers(0, len(dlist), size=(1000, len(dlist)))
        base = R[R.policy == "none"].groupby("day").sum(numeric_only=True).reindex(dlist)
        for (policy, K), g in R.groupby(["policy", "trucks"]):
            gd = g.groupby("day").sum(numeric_only=True).reindex(dlist)
            n_runs = len(g)
            row = {"shift": shift, "policy": policy, "trucks": K, "days": len(dlist), "moved_per_shift": g.moved.sum() / n_runs, "drive_min_per_shift": g.drive_min.sum() / n_runs}
            for col, den in (("unmet_campus", "requests_campus"), ("unmet_gateway", "requests_gateway"), ("unmet_corridor", "requests_corridor"), ("unmet_other", "requests_other"), ("refused_campus", "returns_campus")):
                row[col + "_per_shift"] = g[col].sum() / n_runs
                row[col + "_share"] = g[col].sum() / max(g[den].sum(), 1)
                if policy != "none":
                    cut = 1 - gd[col].values[draws].sum(1) / np.maximum(base[col].values[draws].sum(1), 1)
                    row[col + "_avoided"] = 1 - gd[col].sum() / max(base[col].sum(), 1); row[col + "_lo"] = np.percentile(cut, 2.5); row[col + "_hi"] = np.percentile(cut, 97.5)
            row["campus_empty_station_steps"] = g.campus_empty_station_steps.sum() / n_runs
            rows.append(row)
    summ = pd.DataFrame(rows); summ.to_csv(OUT / "sim_summary.csv", index=False)
    # the demand model against the logger: campus stock during each shift, simulated without trucks and as logged
    chk = []
    for shift, (s0, s1, _, _) in SHIFTS.items():
        sim = np.mean([s for _, sh, s in stocks if sh == shift], axis=0)
        log = np.nanmean([np.nansum(logged(d)[s0:s1][:, IS_CAMPUS], axis=1) for (d, sh) in START if sh == shift], axis=0)
        chk.append(pd.DataFrame({"shift": shift, "minute": np.arange(s0, s1) * STEP, "campus_bikes_simulated": sim, "campus_bikes_logged": log}))
    chk = pd.concat(chk); chk.to_csv(OUT / "sim_stock.csv", index=False)
    json.dump({"days": DAYS, "shifts": {k: {"from": v[0] * STEP, "to": v[1] * STEP, "scored_from": v[2] * STEP, "scored_to": v[3] * STEP, "days": sum(1 for (_, sh) in START if sh == k)} for k, v in SHIFTS.items()},
               "seeds": SEEDS, "policies": POLICIES, "Q": Q, "speed_kmh": SPEED_KMH, "stop_min": STOP_MIN + HANDLE_MIN, "beta": BETA, "horizon_min": HORIZON, "drive_stops": DRIVE,
               "stock_mae_sim_vs_logged": {sh: float((g.campus_bikes_simulated - g.campus_bikes_logged).abs().mean()) for sh, g in chk.groupby("shift")}}, open(OUT / "sim_setup.json", "w"), indent=1)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
    keep = ["shift", "policy", "trucks", "unmet_campus_per_shift", "unmet_campus_share", "unmet_campus_avoided", "unmet_campus_lo", "unmet_campus_hi", "unmet_gateway_share", "unmet_gateway_avoided",
            "refused_campus_share", "refused_campus_avoided", "unmet_other_avoided", "moved_per_shift", "drive_min_per_shift"]
    print(summ[keep].round(3).to_string(index=False))
    print(chk.iloc[::6].round(0).to_string(index=False))
