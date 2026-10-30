"""Live demo state for NSYSU: stockout probabilities and the pre-bell truck plan from the latest snapshot.

Usage: python demo_state.py DATA_DIR RESULTS_DIR OUT_JSON [--trucks K] [--horizon MIN] [--at "YYYY-MM-DD HH:MM"]
       python demo_state.py DATA_DIR RESULTS_DIR OUT_JSON --replay YYYY-MM-DD [--trucks K]

Runs after every logger snapshot (see .github/workflows/logger.yml). For the latest 10-minute slot it
  1. builds the inventory-only features of features.py from the last hour of snapshots and scores
     P(empty within 30 min) and P(empty within 60 min) with the NTU models (zero-shot, Sec. 2.5);
  2. prices every station with the birth-death chain of the planner using the NSYSU rates of
     nsysu_rates.py (expected unmet rentals over the horizon without any truck);
  3. plans one route per truck with the route search of route_planner.py (Sec. 2.6.3), the same
     settings as the NTU replay (H = 90 min, beta = 0.25, up to 6 stops, Q = 20).
Writes OUT_JSON for the demo page (docs/index.html): the stations with their probabilities, today's stock
history since 06:00, the plan and the totals. --at scores a past slot; --replay writes every slot of one day
(06:00-22:50) in a compact form so the page can scrub through the day.
"""
import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from features import INV_FEATS, NSYSU_BELLS, NSYSU_SEMESTERS, TW_HOLIDAYS, _bell_minutes, _to_since, neighbors  # noqa: E402
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import ChainValues, RoutePlanner  # noqa: E402

DATA, RESULTS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
K = ARG("--trucks", 1, int)
HORIZON = ARG("--horizon", 90, int)
AT = ARG("--at", None, str)
REPLAY = ARG("--replay", None, str)
TZ = timezone(timedelta(hours=8))
MAJORS = ["12:00", "16:00", "17:00"]
Q, SPEED_KMH, STOP_MIN, PER_BIKE_MIN = 20, 15.0, 3.0, 0.1
BETA, STOPS, ITERS = 0.25, 6, 400
SEM_START = pd.Timestamp(NSYSU_SEMESTERS[0][0])
BELLS, MAJ = _bell_minutes(NSYSU_BELLS, MAJORS)
BELL_MIN = sorted(int(b[:2]) * 60 + int(b[3:]) for b in NSYSU_BELLS)
WINDOW = (6 * 60, 23 * 60)        # the predictor and the planner cover 06:00-23:00
DAY_START = 6 * 60                # history shown on the page starts here

t0 = time.time()
st = load_stations(DATA)
st = st[st.logged == 1].rename(columns={"lat": "latitude", "lng": "longitude"}).reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
NB = neighbors(st, k=5)
lat, lng = st.latitude.values, st.longitude.values
p_ = math.pi / 180
DIST_KM = 6371 * np.hypot((lng[:, None] - lng[None, :]) * p_ * math.cos(lat.mean() * p_), (lat[:, None] - lat[None, :]) * p_) * 1.3
TRAVEL_MIN = DIST_KM / SPEED_KMH * 60
EXCLUDED = (st.district == "旗津區").values      # a truck reaches Qijin only through the harbour tunnel; straight-line times do not model it
GROUPS = np.where(st.sno.isin(CAMPUS), "campus", np.where(st.sno.isin(GATEWAY), "gateway", "other"))
M30 = lgb.Booster(model_file=str(RESULTS / "model" / "lgb_inv_30.txt"))
M60 = lgb.Booster(model_file=str(RESULTS / "model" / "lgb_inv_60.txt"))
rates = pd.read_csv(RESULTS / "nsysu" / "rates" / "rates.csv", dtype={"sno": str})
prior = pd.read_csv(RESULTS / "nsysu" / "rates" / "rates_prior.csv")
_values = {}


def chain_values(offday):
    if offday not in _values:
        R = np.zeros((N, 24)); Qr = np.zeros((N, 24))
        for row in prior[prior.offday == offday].itertuples():
            R[:, row.hod] = row.pr; Qr[:, row.hod] = row.pq
        for row in rates[(rates.offday == offday) & rates.sno.isin(sidx)].itertuples():
            R[sidx[row.sno], row.hod] = row.lam_r; Qr[sidx[row.sno], row.hod] = row.lam_q
        _values[offday] = ChainValues(R, Qr, CAP, HORIZON, Q)
    return _values[offday]


def load_days(days):
    df = load_logger(DATA, days=days)
    df = df[df.sno.isin(sidx)].copy()
    df["ts"] = pd.to_datetime(df.date) + pd.to_timedelta(df.slot * 10, unit="m")
    return df


def compute(df, ts, trucks=K, with_history=True):
    """State at 10-minute slot ts (pd.Timestamp, naive local time) from the snapshots in df."""
    d = df[df.ts <= ts]
    ts_last = d.ts.max()
    hist_ts = [ts_last - pd.Timedelta(minutes=10 * k) for k in range(6, -1, -1)]
    wb = d.pivot_table(index="ts", columns="sno", values="bikes").reindex(columns=st.sno)
    wd = d.pivot_table(index="ts", columns="sno", values="docks").reindex(columns=st.sno)
    hb = wb.reindex(hist_ts).ffill(); hd = wd.reindex(hist_ts).ffill()
    bikes_now, docks_now = hb.iloc[-1].values, hd.iloc[-1].values
    observed = ~np.isnan(bikes_now)
    bikes = np.where(observed, bikes_now, 0).astype(int)
    docks = np.where(observed, docks_now, CAP - bikes).astype(int)
    hist = np.nan_to_num(hb.values[:-1], nan=0.0)
    age = d[d.ts == ts_last].set_index("sno").age.reindex(st.sno).values
    status = d[d.ts == ts_last].set_index("sno").status.reindex(st.sno).values

    t_min = ts_last.hour * 60 + ts_last.minute
    date = ts_last.normalize()
    dstr = date.strftime("%Y-%m-%d")
    offday = int(date.dayofweek >= 5 or dstr in TW_HOLIDAYS or dstr in HOLIDAYS)
    in_sem = int(pd.Timestamp(NSYSU_SEMESTERS[0][0]) <= date <= pd.Timestamp(NSYSU_SEMESTERS[0][1]))
    f = pd.DataFrame({
        "hour": np.full(N, t_min / 60, np.float32), "dow": np.full(N, date.dayofweek, np.int8), "offday": np.full(N, offday, np.int8),
        "sem_week": np.full(N, (date - SEM_START).days // 7 if in_sem else -1, np.float32), "in_sem": np.full(N, in_sem, np.int8)})
    tb, sb = _to_since(np.array([t_min]), BELLS); tm, sm = _to_since(np.array([t_min]), MAJ)
    f["to_bell"], f["since_bell"], f["to_major"], f["since_major"] = tb[0], sb[0], tm[0], sm[0]
    f["bikes"] = bikes.astype(np.float32); f["docks"] = docks.astype(np.float32); f["total"] = CAP.astype(np.float32)
    f["fill"] = bikes / np.maximum(CAP, 1)
    f["d10"] = bikes - hist[-1]; f["d30"] = bikes - hist[-3]; f["d60"] = bikes - hist[-6]
    f["min60"] = np.min(np.vstack([hist, bikes]), axis=0)
    f["empty_now"] = (bikes == 0).astype(np.float32)
    f["empty_min60"] = (np.vstack([hist[-5:], bikes]) == 0).sum(axis=0) * 10.0
    f["nb3_bikes"] = bikes[NB[:, :3]].sum(axis=1); f["nb3_empty"] = (bikes[NB[:, :3]] == 0).sum(axis=1)
    f["nb5_fill"] = (bikes / np.maximum(CAP, 1))[NB[:, :5]].mean(axis=1)
    X = f[INV_FEATS]
    p30, p60 = M30.predict(X), M60.predict(X)

    in_window = WINDOW[0] <= t_min < WINDOW[1]
    plans, unmet = [], np.zeros(N)
    if in_window:
        values = chain_values(offday)
        planner = RoutePlanner(TRAVEL_MIN, Q, STOP_MIN, 1.0, HORIZON, beta=BETA, max_stops=STOPS, iters=ITERS)
        B = values.benefit(t_min, bikes)
        unmet = values.last_unmet.astype(float)
        rng = np.random.default_rng(int(ts_last.timestamp()) // 600)
        claimed = ~observed | EXCLUDED
        for k in range(trucks):
            stops = planner.plan(B, bikes, CAP, None, 0, claimed, rng)
            if not stops:
                break
            t, prev, km, load, out = 0.0, None, 0.0, 0, []
            for s, dd, _ in stops:
                leg = TRAVEL_MIN[prev, s] if prev is not None else 5.0
                km += DIST_KM[prev, s] if prev is not None else 0.0
                t += leg
                load += -dd if dd < 0 else -dd                  # bikes on the truck after this stop
                out.append({"i": int(s), "d": int(dd), "eta": round(t, 1), "load": int(load)})
                t += STOP_MIN + abs(dd) * PER_BIKE_MIN
                prev = s
                claimed[s] = True
            planner.beta = 0.0
            v = planner.evaluate([s for s, _, _ in stops])
            planner.beta = BETA
            plans.append({"truck": k + 1, "stops": out, "value": round(float(v), 1), "minutes": round(t, 1), "km": round(km, 1)})
    nxt = [b for b in BELL_MIN if b > t_min]
    next_bell = None if offday or not nxt else {"time": f"{nxt[0] // 60:02d}:{nxt[0] % 60:02d}", "minutes": int(nxt[0] - t_min)}
    totals = {"observed": int(observed.sum()), "bikes": int(bikes[observed].sum()), "empty_now": int((bikes[observed] == 0).sum()),
              "p30_over_half": int((p30[observed] >= 0.5).sum()),
              "expected_unmet": round(float(unmet[observed].sum()), 1) if in_window else None,
              "plan_value": round(sum(p["value"] for p in plans), 1) if plans else 0.0}
    out = {"snapshot_at": ts_last.strftime("%Y-%m-%d %H:%M"), "t_min": int(t_min), "offday": offday, "in_semester": in_sem, "in_window": in_window,
           "next_bell": next_bell, "totals": totals, "plans": plans,
           "bikes": [int(b) if o else None for b, o in zip(bikes, observed)], "docks": [int(x) if o else None for x, o in zip(docks, observed)],
           "status": [None if np.isnan(x) else int(x) for x in status], "age": [None if np.isnan(x) else int(x) for x in age],
           "p30": [round(float(x), 3) if o else None for x, o in zip(p30, observed)], "p60": [round(float(x), 3) if o else None for x, o in zip(p60, observed)],
           "unmet": [round(float(x), 2) if (o and in_window) else None for x, o in zip(unmet, observed)]}
    if with_history:
        grid = pd.date_range(date + pd.Timedelta(minutes=DAY_START), ts_last, freq="10min")
        h = wb.reindex(grid)
        out["history"] = {"from": f"{DAY_START // 60:02d}:{DAY_START % 60:02d}", "step": 10,
                          "bikes": [[None if np.isnan(v) else int(v) for v in h[s].values] for s in st.sno]}
    return out


def station_list():
    return [{"sno": st.sno[i], "name": st.name_tw[i], "name_en": st.name_en[i], "lat": round(float(lat[i]), 6), "lng": round(float(lng[i]), 6),
             "cap": int(CAP[i]), "group": GROUPS[i], "excluded": bool(EXCLUDED[i])} for i in range(N)]


META = {"horizon_min": HORIZON, "bells": NSYSU_BELLS, "major_bells": MAJORS, "window": ["06:00", "23:00"],
        "settings": {"Q": Q, "speed_kmh": SPEED_KMH, "stop_min": STOP_MIN, "per_bike_min": PER_BIKE_MIN, "beta": BETA, "max_stops": STOPS, "iters": ITERS,
                     "predictor": "NTU inventory-only LightGBM, zero-shot", "rates": "chain MLE on the logger (nsysu_rates.py)",
                     "excluded": "Qijin district (harbour tunnel detour)"}}

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if REPLAY:
        day = pd.Timestamp(REPLAY)
        df = load_days([REPLAY])
        slots = []
        for m in range(DAY_START, 23 * 60, 10):
            ts = day + pd.Timedelta(minutes=m)
            if not (df.ts <= ts).any():
                continue
            s = compute(df, ts, with_history=False)
            if s["snapshot_at"] != ts.strftime("%Y-%m-%d %H:%M"):
                continue                                  # no snapshot for this slot
            slots.append({k: s[k] for k in ("snapshot_at", "t_min", "next_bell", "totals", "plans", "bikes", "p30", "p60", "unmet")})
            print(f"{s['snapshot_at']} unmet {s['totals']['expected_unmet']} plan {s['totals']['plan_value']}", flush=True)
        dstr = day.strftime("%Y-%m-%d")
        replay = dict(META, generated_at=datetime.now(TZ).isoformat(timespec="seconds"), date=REPLAY, trucks=K,
                      offday=int(day.dayofweek >= 5 or dstr in TW_HOLIDAYS or dstr in HOLIDAYS), stations=station_list(), slots=slots)
        json.dump(replay, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print(f"replay {REPLAY}: {len(slots)} slots in {time.time() - t0:.0f}s")
    else:
        now = datetime.strptime(AT, "%Y-%m-%d %H:%M").replace(tzinfo=TZ) if AT else datetime.now(TZ)
        days = sorted({(now - timedelta(days=1)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")})
        df = load_days(days)
        ts = pd.Timestamp(now.replace(tzinfo=None)).floor("10min")
        s = compute(df, ts)
        state = dict(META, generated_at=datetime.now(TZ).isoformat(timespec="seconds"), trucks=K, stations=station_list(), **s)
        json.dump(state, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        t = state["totals"]
        print(f"{state['snapshot_at']} observed {t['observed']}/{N}, empty {t['empty_now']}, p30>=0.5: {t['p30_over_half']}, "
              f"expected unmet {t['expected_unmet']}, plan value {t['plan_value']} ({len(state['plans'])} trucks) in {time.time() - t0:.1f}s")
