"""Discrete-event replay simulator with one rebalancing truck, driven by real NTU trips.

Usage: python replay_sim.py NTU_DIR MODEL_DIR OUT_DIR [--days N] [--policies none,reactive,point,prob,operator]

Each simulated day (06:00-23:00) replays the recorded rentals at the 144 study-area stations: a rental is
served only if the station has a bike, otherwise it is counted as unmet and the trip disappears. Returns
of served trips arrive after the recorded duration; returns from outside the area arrive as recorded.
A full station redirects the return to the nearest station with a free dock. Policies decide, every
10 minutes while the truck is idle, one source->target move (greedy); the truck travels at 15 km/h on
1.3 x straight-line distance, with 3 min per stop + 6 s per bike handling, capacity 20.
"""
import heapq
import json
import math
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from features import NTU_BELLS, INV_FEATS, TW_HOLIDAYS, _bell_minutes, _to_since, neighbors  # noqa: E402

NTU = Path(sys.argv[1]); MODELS = Path(sys.argv[2]); OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
NDAYS = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 30
K = int(sys.argv[sys.argv.index("--trucks") + 1]) if "--trucks" in sys.argv else 1
POLICIES = sys.argv[sys.argv.index("--policies") + 1].split(",") if "--policies" in sys.argv else ["none", "reactive", "point", "prob", "operator"]
TRAIN_END = pd.Timestamp("2025-03-31")
T0, T1 = 6 * 60, 23 * 60                 # simulated window, minutes of day
Q, SPEED_KMH, STOP_MIN, PER_BIKE_MIN = 20, 15.0, 3.0, 0.1
HORIZON_MIN = 60
MAJORS = ["12:10", "15:10", "17:20"]
SEED = 11

# ---------------- static data ----------------
st = pd.read_csv(NTU / "ntu_stations.csv", dtype={"sno": str}).reset_index(drop=True)
N = len(st); sidx = {s: i for i, s in enumerate(st.sno)}
campus = st.campus.values.astype(bool)
lat, lng = st.latitude.values, st.longitude.values
p_ = math.pi / 180
DX = (lng[:, None] - lng[None, :]) * p_ * math.cos(lat.mean() * p_)
DY = (lat[:, None] - lat[None, :]) * p_
DIST_KM = 6371 * np.hypot(DX, DY) * 1.3
NB = neighbors(st, k=5)
hourly = pd.read_parquet(NTU / "hourly.parquet")
hourly = hourly[hourly.sno.isin(sidx)]
panel = pd.read_parquet(NTU / "panel_10min.parquet")
panel = panel[panel.sno.isin(sidx)]
cap_med = panel.groupby("sno").total.median()
CAP = np.array([cap_med.get(s, 20) for s in st.sno]).astype(int)

# censoring-corrected demand rates from the training period: station x offday x hour
h = hourly[(hourly.hour <= TRAIN_END + pd.Timedelta(days=1))].dropna(subset=["exposure"]).copy()
h["offday"] = ((h.hour.dt.dayofweek >= 5) | h.hour.dt.strftime("%Y-%m-%d").isin(TW_HOLIDAYS)).astype(int)
h["hod"] = h.hour.dt.hour
r = h.groupby(["sno", "offday", "hod"]).agg(rentals=("rentals", "sum"), exposure=("exposure", "sum"), n=("rentals", "size")).reset_index()
r["lam"] = r.rentals / r.exposure.replace(0, np.nan)
r["lam"] = r.lam.fillna(r.rentals / r.n)
RATES = np.zeros((N, 2, 24))
for row in r.itertuples():
    RATES[sidx[row.sno], row.offday, row.hod] = row.lam
BELLS, MAJ = _bell_minutes(NTU_BELLS, MAJORS)
BOOSTER = lgb.Booster(model_file=str(MODELS / "lgb_inv_60.txt"))

# inferred operator moves (for the replay-the-operator policy): station-hour residuals flagged as moves
mv = hourly[hourly.move == 1].dropna(subset=["resid"])
OPS = {}
for row in mv.itertuples():
    OPS.setdefault(row.hour.normalize(), []).append((row.hour.hour * 60, sidx[row.sno], int(round(row.resid))))


def load_day(date):
    """rentals and outside returns for one day, with minute-level timestamps drawn uniformly within the hour."""
    rng = np.random.default_rng(SEED + int(date.strftime("%Y%m%d")))
    t = pd.read_parquet(NTU / f"trips_{date.strftime('%Y%m')}.parquet")
    d0, d1 = date + pd.Timedelta(hours=6), date + pd.Timedelta(hours=23)
    rent = t[(t.rent_time >= d0) & (t.rent_time < d1) & t.rs.isin(sidx)].copy()
    rent["m"] = (rent.rent_time - date).dt.total_seconds() / 60 + rng.uniform(0, 60, len(rent))
    rent["i"] = rent.rs.map(sidx).astype(int)
    rent["j"] = rent.ts.map(sidx).fillna(-1).astype(int)
    rent["dur"] = rent.dur_min.clip(1, 240).fillna(10)
    rent = rent.sort_values("m")
    out = t[(t.return_time >= d0) & (t.return_time < d1) & t.ts.isin(sidx) & ~t.rs.isin(sidx)].copy()
    out["m"] = (out.return_time - date).dt.total_seconds() / 60 + rng.uniform(0, 60, len(out))
    out["j"] = out.ts.map(sidx).astype(int)
    init = panel[(panel.ts == date + pd.Timedelta(hours=6))].set_index("sno").bikes
    b0 = np.array([init.get(s, np.nan) for s in st.sno])
    med = panel[panel.ts.dt.hour == 6].groupby("sno").bikes.median()
    b0 = np.where(np.isnan(b0), [med.get(s, 5) for s in st.sno], b0)
    return rent[["m", "i", "j", "dur"]].to_numpy(), out[["m", "j"]].to_numpy(), np.clip(np.nan_to_num(b0), 0, CAP).astype(int)


# ---------------- policies: return (src, dst, k) or None ----------------
def choose(state, need, value, src_ok, pos):
    """Greedy one-move selection: maximise expected rentals saved per truck-minute.
    need[i]  bikes station i should receive (0 = no need); value[i] weight of a bike delivered there (P(empty) or 1)
    src_ok   boolean mask of stations allowed to give bikes; pos current truck position (station index or None)."""
    bikes, lam_h, claimed = state["bikes"], state["lam_h"], state["claimed"]
    surplus = bikes - lam_h - 2
    dsts = np.where((need > 0) & ~claimed)[0]
    srcs = np.where(src_ok & (surplus >= 3) & ~claimed)[0]
    if len(dsts) == 0 or len(srcs) == 0:
        return None
    dsts = dsts[np.argsort(-(value[dsts] * np.minimum(need[dsts], Q)))][:8]
    srcs = srcs[np.argsort(-surplus[srcs])][:12]
    best, best_score = None, 0.0
    for d in dsts:
        for s_ in srcs:
            k = int(min(Q, surplus[s_], CAP[d] - bikes[d], need[d]))
            if k < 3:
                continue
            t_travel = (DIST_KM[pos, s_] if pos is not None else 1.0) / SPEED_KMH * 60 + DIST_KM[s_, d] / SPEED_KMH * 60
            t_total = t_travel + 2 * STOP_MIN + k * PER_BIKE_MIN
            benefit = value[d] * min(k, max(lam_h[d], 1.0))
            score = benefit / t_total
            if score > best_score:
                best, best_score = (int(s_), int(d), k), score
    return best


def policy_reactive(state, pos):
    bikes, lam_h = state["bikes"], state["lam_h"]
    need = np.where(bikes == 0, np.maximum(5, np.ceil(lam_h)), 0)
    return choose(state, need, np.ones(N), np.ones(N, bool), pos)


def policy_point(state, pos):
    bikes, lam_h = state["bikes"], state["lam_h"]
    unmet = np.maximum(0, lam_h - bikes)              # point forecast of unmet rentals in the next hour
    need = np.where(unmet >= 2, np.ceil(unmet) + 2, 0)
    return choose(state, need, np.ones(N), unmet <= 0, pos)


def policy_prob(state, pos):
    bikes, lam_h, p = state["bikes"], state["lam_h"], state["p_empty"]
    need = np.where(p >= 0.3, np.maximum(5, np.ceil(lam_h - bikes) + 3), 0)
    return choose(state, need, p, p <= 0.2, pos)


POLICY = {"none": None, "reactive": policy_reactive, "point": policy_point, "prob": policy_prob, "operator": "operator"}


def features_now(t_min, bikes, hist, date):
    """inventory-only features for all stations at minute t_min of the simulated day."""
    dow = date.dayofweek
    offday = int(dow >= 5 or date.strftime("%Y-%m-%d") in TW_HOLIDAYS)
    sem_start = pd.Timestamp("2025-02-17")
    f = pd.DataFrame({
        "hour": np.full(N, t_min / 60, np.float32), "dow": np.full(N, dow, np.int8), "offday": np.full(N, offday, np.int8),
        "sem_week": np.full(N, (date - sem_start).days // 7, np.float32), "in_sem": np.full(N, 1, np.int8),
    })
    tb, sb = _to_since(np.array([t_min]), BELLS); tm, sm = _to_since(np.array([t_min]), MAJ)
    f["to_bell"], f["since_bell"], f["to_major"], f["since_major"] = tb[0], sb[0], tm[0], sm[0]
    f["bikes"] = bikes.astype(np.float32); f["docks"] = (CAP - bikes).astype(np.float32); f["total"] = CAP.astype(np.float32)
    f["fill"] = bikes / np.maximum(CAP, 1)
    f["d10"] = bikes - hist[-1]; f["d30"] = bikes - hist[-3]; f["d60"] = bikes - hist[-6]
    f["min60"] = np.min(np.vstack([hist[-6:], bikes]), axis=0)
    f["empty_now"] = (bikes == 0).astype(np.float32)
    f["empty_min60"] = (np.vstack([hist[-5:], bikes]) == 0).sum(axis=0) * 10.0
    f["nb3_bikes"] = bikes[NB[:, :3]].sum(axis=1); f["nb3_empty"] = (bikes[NB[:, :3]] == 0).sum(axis=1)
    f["nb5_fill"] = (bikes / np.maximum(CAP, 1))[NB[:, :5]].mean(axis=1)
    return f[INV_FEATS]


def run_day(date, policy_name, rent, outret, b0):
    bikes = b0.copy()
    hist = [bikes.copy() for _ in range(6)]
    empty_since = np.where(bikes == 0, T0, -1.0)
    unmet = np.zeros(N, int); served = np.zeros(N, int); redirected = 0
    empty_min = np.zeros(N); truck_km = 0.0; moved = 0; n_moves = 0
    offday = int(date.dayofweek >= 5 or date.strftime("%Y-%m-%d") in TW_HOLIDAYS)
    ev = []                                   # (minute, kind, a, b): kind 0 rental, 1 return, 2 truck arrival
    for m, i, j, dur in rent:
        heapq.heappush(ev, (float(m), 0, int(i), (int(j), float(dur))))
    for m, j in outret:
        heapq.heappush(ev, (float(m), 1, int(j), None))
    ops = sorted(OPS.get(date, [])) if policy_name == "operator" else []
    for m, i, k in ops:
        heapq.heappush(ev, (float(m) + 1.0, 3, i, k))
    pol = POLICY[policy_name]
    trucks = [{"pos": None, "load": 0, "busy": False} for _ in range(K)]
    next_decision = T0
    while ev:
        m, kind, a, b = heapq.heappop(ev)
        if m >= T1:
            break
        # decisions at 10-minute boundaries
        while next_decision <= m:
            td = next_decision
            if td > T0:
                emp = bikes == 0
                empty_min[emp] += 10
            hist.append(bikes.copy()); hist = hist[-7:]
            if callable(pol):
                idle = [ti for ti, tr in enumerate(trucks) if not tr["busy"]]
                if idle:
                    lam_h = RATES[:, offday, int(td // 60) % 24]
                    state = {"bikes": bikes, "lam_h": lam_h, "claimed": np.zeros(N, bool)}
                    if policy_name == "prob":
                        state["p_empty"] = BOOSTER.predict(features_now(td, bikes, hist, date))
                    for ti in idle:
                        plan = pol(state, trucks[ti]["pos"])
                        if plan is None:
                            break
                        src, dst, k = plan
                        state["claimed"][[src, dst]] = True
                        pos = trucks[ti]["pos"]
                        t_src = td + (DIST_KM[pos, src] / SPEED_KMH * 60 if pos is not None else 5.0)
                        t_dst = t_src + STOP_MIN + k * PER_BIKE_MIN + DIST_KM[src, dst] / SPEED_KMH * 60
                        truck_km += (DIST_KM[pos, src] if pos is not None else 0) + DIST_KM[src, dst]
                        heapq.heappush(ev, (t_src, 2, src, (ti, -k)))
                        heapq.heappush(ev, (t_dst + STOP_MIN + k * PER_BIKE_MIN, 2, dst, (ti, +k)))
                        trucks[ti]["busy"] = True
                        n_moves += 1
            next_decision += 10
        if kind == 0:                          # rental at station a
            if bikes[a] > 0:
                bikes[a] -= 1; served[a] += 1
                if bikes[a] == 0:
                    empty_since[a] = m
                j, dur = b
                if j >= 0:
                    heapq.heappush(ev, (m + dur, 1, j, None))
            else:
                unmet[a] += 1
        elif kind == 1:                        # return at station a
            if bikes[a] < CAP[a]:
                if bikes[a] == 0:
                    empty_since[a] = -1
                bikes[a] += 1
            else:
                order = np.argsort(DIST_KM[a])
                for jj in order[1:]:
                    if bikes[jj] < CAP[jj]:
                        if bikes[jj] == 0:
                            empty_since[jj] = -1
                        bikes[jj] += 1; redirected += 1
                        break
        elif kind == 2:                        # truck arrives: b = (truck id, -k load / +k unload)
            ti, kk = b
            tr = trucks[ti]
            if kk < 0:
                k = min(-kk, int(bikes[a]))
                bikes[a] -= k; tr["load"] += k
                if bikes[a] == 0:
                    empty_since[a] = m
            else:
                k = min(tr["load"], int(CAP[a] - bikes[a]))
                if bikes[a] == 0 and k > 0:
                    empty_since[a] = -1
                bikes[a] += k; tr["load"] -= k; moved += k
                tr["pos"] = a
                tr["busy"] = False
        elif kind == 3:                        # inferred operator move
            k = int(np.clip(b, -bikes[a], CAP[a] - bikes[a]))
            if bikes[a] == 0 and k > 0:
                empty_since[a] = -1
                bikes[a] += k
            elif bikes[a] + k == 0 and k < 0:
                bikes[a] += k; empty_since[a] = m
            else:
                bikes[a] += k
            moved += abs(k); n_moves += 1
    day_min = (T1 - T0)
    return {"date": date.strftime("%Y-%m-%d"), "policy": policy_name, "rentals": int(len(rent)),
            "served": int(served.sum()), "unmet": int(unmet.sum()), "unmet_campus": int(unmet[campus].sum()),
            "empty_station_min": float(empty_min.sum()), "empty_station_min_campus": float(empty_min[campus].sum()),
            "redirected_returns": int(redirected), "truck_km": round(float(truck_km), 1), "bikes_moved": int(moved),
            "moves": int(n_moves), "trucks": K}


if __name__ == "__main__":
    # candidate days: in-semester weekdays of the test period with good snapshot coverage
    q = panel[(panel.ts >= "2025-04-01") & (panel.ts <= "2025-06-13")]
    cov = q.groupby(q.ts.dt.normalize()).bikes.apply(lambda x: 1 - x.isna().mean())
    days = [d for d, c in cov.items() if c >= 0.95 and d.dayofweek < 5 and d.strftime("%Y-%m-%d") not in TW_HOLIDAYS]
    days = days[:NDAYS]
    print(f"{len(days)} simulation days: {days[0].date()} .. {days[-1].date()}; policies {POLICIES}")
    rows = []
    t0 = time.time()
    for d in days:
        rent, outret, b0 = load_day(d)
        for pol in POLICIES:
            rows.append(run_day(d, pol, rent, outret, b0))
        last = rows[-len(POLICIES):]
        print(f"{d.date()} rentals={last[0]['rentals']} " + " ".join(f"{r['policy']}:unmet={r['unmet']}/{r['unmet_campus']} km={r['truck_km']}" for r in last) + f"  ({time.time() - t0:.0f}s)")
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "sim_daily.csv", index=False)
    summ = res.groupby("policy").agg(days=("date", "nunique"), rentals=("rentals", "mean"), unmet=("unmet", "mean"),
                                     unmet_campus=("unmet_campus", "mean"), empty_station_min=("empty_station_min", "mean"),
                                     empty_campus_min=("empty_station_min_campus", "mean"), truck_km=("truck_km", "mean"),
                                     bikes_moved=("bikes_moved", "mean"), moves=("moves", "mean")).round(1)
    base = summ.loc["none", "unmet"] if "none" in summ.index else np.nan
    summ["unmet_reduction"] = (1 - summ.unmet / base).round(3)
    summ.to_csv(OUT / "sim_summary.csv")
    print(summ.to_string())
    json.dump({"days": [d.strftime("%Y-%m-%d") for d in days], "Q": Q, "trucks": K, "speed_kmh": SPEED_KMH, "stop_min": STOP_MIN,
               "per_bike_min": PER_BIKE_MIN, "horizon_min": HORIZON_MIN, "window": [T0, T1]}, open(OUT / "sim_setup.json", "w"), indent=1)
