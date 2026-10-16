"""Feature construction for the schedule-aware stockout predictor.

Works for both campuses: the NTU 10-minute panel (with hourly trip flows) and the NSYSU logger
panel (inventory only). Every row = one station x one 10-minute slot.

Feature groups
  time      hour, dow, weekend/holiday flag, semester week, in-semester flag
  bell      minutes to the next period end and since the last one (campus timetable)
  state     bikes, free docks, capacity, fill ratio, changes over the last 10/30/60 min,
            minutes empty in the last hour, empty-now flag
  neighbor  bikes and empty count at the k nearest stations
  flow      (NTU only) rentals/returns in the last complete hours, same hour last week,
            station mean rentals for this hour-of-week (computed on the training period)
Labels
  y30, y60  station is empty at some point within the next 30 / 60 minutes
"""
import math

import numpy as np
import pandas as pd

NTU_BELLS = ["09:00", "10:00", "11:10", "12:10", "13:10", "14:10", "15:10", "16:20", "17:20", "18:20", "19:15", "20:10"]
NSYSU_BELLS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:10", "20:10", "21:10"]
TW_HOLIDAYS = {  # national holidays and make-up days inside the data windows
    "2024-09-17", "2024-10-10", "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-02-28", "2025-04-03", "2025-04-04", "2025-05-01", "2025-05-30", "2025-05-31",
    "2026-10-09", "2026-10-10",
}
# semester calendars: (start, end) of teaching weeks
NTU_SEMESTERS = [("2024-09-02", "2025-01-10"), ("2025-02-17", "2025-06-13")]
NSYSU_SEMESTERS = [("2026-09-07", "2027-01-15")]

STATE_FEATS = ["bikes", "docks", "total", "fill", "d10", "d30", "d60", "min60", "empty_now", "empty_min60"]
TIME_FEATS = ["hour", "dow", "offday", "sem_week", "in_sem"]
BELL_FEATS = ["to_bell", "since_bell", "to_major", "since_major"]
NEIGH_FEATS = ["nb3_bikes", "nb3_empty", "nb5_fill"]
FLOW_FEATS = ["rent_h1", "rent_h2", "ret_h1", "ret_h2", "rent_lw", "rent_how_mean"]
INV_FEATS = TIME_FEATS + BELL_FEATS + STATE_FEATS + NEIGH_FEATS          # transferable set
FULL_FEATS = INV_FEATS + FLOW_FEATS                                   # NTU set (+ station id as categorical)


def _bell_minutes(bells, majors):
    b = np.array([int(x[:2]) * 60 + int(x[3:]) for x in bells])
    m = np.array([int(x[:2]) * 60 + int(x[3:]) for x in majors])
    return np.sort(b), np.sort(m)


def _to_since(minute_of_day, b):
    """minutes to the next bell and since the previous bell for an array of minute-of-day values."""
    idx = np.searchsorted(b, minute_of_day, side="right")
    nxt = np.where(idx < len(b), b[np.minimum(idx, len(b) - 1)] - minute_of_day, 24 * 60 - minute_of_day + b[0])
    prv = np.where(idx > 0, minute_of_day - b[np.maximum(idx - 1, 0)], minute_of_day + 24 * 60 - b[-1])
    return np.minimum(nxt, 240).astype(np.float32), np.minimum(prv, 240).astype(np.float32)


def neighbors(stations, k=5):
    """index of the k nearest other stations for each station (by sno order)."""
    lat, lng = stations.latitude.values, stations.longitude.values
    p = math.pi / 180
    dx = (lng[:, None] - lng[None, :]) * p * np.cos(lat.mean() * p)
    dy = (lat[:, None] - lat[None, :]) * p
    d = np.hypot(dx, dy)
    np.fill_diagonal(d, np.inf)
    return np.argsort(d, axis=1)[:, :k]


def build(panel, stations, bells, majors, semesters, flows=None, train_end=None, slots=(36, 138), horizons=(30, 60)):
    """panel: columns sno, ts (10-min), bikes, docks, total. stations: sno, latitude, longitude.
    Returns a feature frame restricted to slots in [slots[0], slots[1]); labels y{h} for h in horizons (minutes)."""
    st = stations.reset_index(drop=True)
    sidx = {s: i for i, s in enumerate(st.sno)}
    p = panel[panel.sno.isin(sidx)].copy()
    p["si"] = p.sno.map(sidx).astype(np.int32)
    p = p.sort_values(["si", "ts"]).reset_index(drop=True)
    p["date"] = p.ts.dt.normalize()
    p["slot"] = (p.ts.dt.hour * 6 + p.ts.dt.minute // 10).astype(np.int16)

    # ---- state features (per station shifts; the panel is a complete regular grid per station) ----
    g = p.groupby("si").bikes
    p["d10"] = p.bikes - g.shift(1)
    p["d30"] = p.bikes - g.shift(3)
    p["d60"] = p.bikes - g.shift(6)
    p["min60"] = g.transform(lambda x: x.rolling(6, min_periods=1).min())
    emp = (p.bikes == 0).astype(np.float32)
    p["empty_now"] = emp
    p["empty_min60"] = emp.groupby(p.si).transform(lambda x: x.rolling(6, min_periods=1).sum()) * 10
    p["fill"] = p.bikes / p.total.replace(0, np.nan)
    # labels: empty at any point within the next h/10 slots (NaN if any of those slots is unobserved)
    kmax = max(horizons) // 10
    fut = pd.concat([g.shift(-k) for k in range(1, kmax + 1)], axis=1)
    fut.columns = range(1, kmax + 1)
    for h in horizons:
        k = h // 10
        f = fut.loc[:, 1:k]
        p[f"y{h}"] = (f.min(axis=1) == 0).astype(np.float32)
        p.loc[f.isna().any(axis=1), f"y{h}"] = np.nan

    # ---- time features ----
    p["hour"] = (p.ts.dt.hour + p.ts.dt.minute / 60).astype(np.float32)
    p["dow"] = p.ts.dt.dayofweek.astype(np.int8)
    dstr = p.date.dt.strftime("%Y-%m-%d")
    p["offday"] = ((p.dow >= 5) | dstr.isin(TW_HOLIDAYS)).astype(np.int8)
    p["sem_week"] = -1.0
    p["in_sem"] = 0
    for s0, s1 in semesters:
        m = (p.date >= s0) & (p.date <= s1)
        p.loc[m, "sem_week"] = ((p.date[m] - pd.Timestamp(s0)).dt.days // 7).astype(float)
        p.loc[m, "in_sem"] = 1
    # ---- bell features ----
    b, mj = _bell_minutes(bells, majors)
    mod = (p.ts.dt.hour * 60 + p.ts.dt.minute).values
    p["to_bell"], p["since_bell"] = _to_since(mod, b)
    p["to_major"], p["since_major"] = _to_since(mod, mj)

    # ---- neighbor features ----
    nb = neighbors(st, k=5)
    wide = p.pivot(index="ts", columns="si", values="bikes").sort_index()
    widef = p.pivot(index="ts", columns="si", values="fill").sort_index()
    W, Wf = wide.values, widef.values
    nb3 = np.stack([np.nansum(W[:, nb[i, :3]], axis=1) for i in range(len(st))], axis=1)
    nb3e = np.stack([np.nansum(W[:, nb[i, :3]] == 0, axis=1) for i in range(len(st))], axis=1)
    nb5f = np.stack([np.nanmean(Wf[:, nb[i, :5]], axis=1) for i in range(len(st))], axis=1)
    key = pd.MultiIndex.from_arrays([p.ts, p.si])
    tsi = {t: i for i, t in enumerate(wide.index)}
    ri = p.ts.map(tsi).values
    p["nb3_bikes"] = nb3[ri, p.si.values].astype(np.float32)
    p["nb3_empty"] = nb3e[ri, p.si.values].astype(np.float32)
    p["nb5_fill"] = nb5f[ri, p.si.values].astype(np.float32)

    # ---- flow features (NTU) ----
    if flows is not None:
        f = flows.copy()
        f["si"] = f.sno.map(sidx)
        f = f.dropna(subset=["si"])
        f["si"] = f.si.astype(np.int32)
        fw = f.pivot_table(index="hour", columns="si", values=["rentals", "returns"], fill_value=0)
        hours = pd.date_range(p.ts.min().floor("h") - pd.Timedelta(days=8), p.ts.max().ceil("h"), freq="h")
        fw = fw.reindex(hours, fill_value=0)
        R, Q = fw["rentals"].reindex(columns=range(len(st)), fill_value=0).values, fw["returns"].reindex(columns=range(len(st)), fill_value=0).values
        hidx = {h: i for i, h in enumerate(hours)}
        hcur = p.ts.dt.floor("h").map(hidx).values
        si = p.si.values
        p["rent_h1"] = R[hcur - 1, si].astype(np.float32)
        p["rent_h2"] = R[hcur - 2, si].astype(np.float32)
        p["ret_h1"] = Q[hcur - 1, si].astype(np.float32)
        p["ret_h2"] = Q[hcur - 2, si].astype(np.float32)
        p["rent_lw"] = R[hcur - 168, si].astype(np.float32)          # same hour, last week
        # mean rentals per station x hour-of-week, training period only
        hw = p.ts.dt.dayofweek * 24 + p.ts.dt.hour
        cur = pd.Series(R[hcur, si], index=p.index)
        tr = p.date <= pd.Timestamp(train_end) if train_end is not None else pd.Series(True, index=p.index)
        mean_how = cur[tr].groupby([p.si[tr], hw[tr]]).mean()
        p["rent_how_mean"] = pd.Series(list(zip(p.si, hw))).map(mean_how).fillna(cur.mean()).values.astype(np.float32)
        for c in FLOW_FEATS:
            p[c] = p[c].astype(np.float32)

    p = p[(p.slot >= slots[0]) & (p.slot < slots[1])]
    for c in STATE_FEATS + NEIGH_FEATS:
        p[c] = p[c].astype(np.float32)
    return p.reset_index(drop=True)
