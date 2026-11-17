"""Rental and return rates at NSYSU from the logger alone (no trip records exist in Kaohsiung).

Usage: python nsysu_rates.py DATA_DIR OUT_DIR [--holdout N] [--workers W] [--until YYYY-MM-DD] [--slots] [--slot-prior H] [--tune-slots]

For every station, day type (teaching day / off-day) and hour of day, the 10-minute transitions
s -> s' of the logged stock are fitted by maximum likelihood to the birth-death chain of the planner
(route_planner.kernel1): rentals ~ Poisson(lam_r / 6) censored at the stock, returns ~ Poisson(lam_q / 6)
censored at the free docks. The chain handles the censoring at 0 and at capacity exactly, so the fitted
rates are not lower bounds like the gross 10-minute decreases. A Gamma prior with the weight of
PRIOR_HOURS hours of exposure shrinks every cell toward the hour-of-day mean across stations (the same
shrinkage as the NTU roll-out rates). Transitions the fitted chain gives probability < P_MOVE are treated
as truck moves and left out (two rounds).

Writes rates.csv (sno, offday, hod, lam_r, lam_q, n, n_moves, lam_r_gross, lam_q_gross) and, with
--holdout N, rates_holdout.csv: the log-likelihood per transition on the last N logged days for the chain
rates fitted on the earlier days against the gross-change rates and the hour-of-day prior.

--slots adds rates_slots.csv (sno, slot, lam_r, lam_q, n): for the 19 stations of the campus corridor on teaching
days, one pair of rates per 10-minute slot of the day instead of per hour. An hour's demand at a campus station is
not spread evenly: most of it falls in the 20 minutes after the bell, which an hourly rate averages away. Each
slot is fitted like an hourly cell, with that station's hourly rates as the prior (weight --slot-prior hours,
default 0.5). --tune-slots prints the held-out likelihood for several prior weights (last five teaching days of
the fitting window). --until restricts the fit to days up to that date.
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import kernel1  # noqa: E402

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
HOLDOUT = ARG("--holdout", 0, int)
WORKERS = ARG("--workers", 2, int)
UNTIL = ARG("--until", None, str)
SLOTS, TUNE_SLOTS = "--slots" in sys.argv, "--tune-slots" in sys.argv
SLOT_PRIOR = ARG("--slot-prior", 0.5, float)     # hours of pseudo-exposure at the station's hourly rate
SLOT_MIN_N = 5                                   # transitions a slot needs before it gets its own rate
HOURS = range(6, 23)            # 06:00-22:59, the window of the predictor and the planner
PRIOR_HOURS = 3.0
P_MOVE = 1e-5
MAX_AGE = 20                    # minutes; older station reports are dropped


def transitions(df, cap):
    """Observed 10-minute transitions (sno, offday, hod, s, s1) from consecutive snapshots of the same day."""
    df = df[(df.age <= MAX_AGE) & df.bikes.notna() & df.docks.notna()].copy()
    df["offday"] = (~df.weekday).astype(int)
    df = df.sort_values(["sno", "date", "slot"])
    nxt = df.groupby(["sno", "date"])[["slot", "bikes"]].shift(-1)
    ok = nxt.slot == df.slot + 1
    t = pd.DataFrame({"sno": df.sno[ok], "offday": df.offday[ok], "hod": (df.slot[ok] // 6).astype(int), "slot": df.slot[ok].astype(int),
                      "s": df.bikes[ok].astype(int), "s1": nxt.bikes[ok].astype(int), "date": df.date[ok]})
    c = t.sno.map(cap)
    t = t[(t.s <= c) & (t.s1 <= c) & t.hod.isin(HOURS)]
    return t.reset_index(drop=True)


def gross_rates(t):
    """Lower-bound rates from gross 10-minute changes: mean decrease and increase per hour, by cell."""
    d = t.s1 - t.s
    g = pd.DataFrame({"sno": t.sno, "offday": t.offday, "hod": t.hod, "dec": (-d).clip(lower=0), "inc": d.clip(lower=0)})
    g = g.groupby(["sno", "offday", "hod"]).agg(lam_r_gross=("dec", "mean"), lam_q_gross=("inc", "mean"), n=("dec", "size"))
    g[["lam_r_gross", "lam_q_gross"]] *= 6
    return g.reset_index()


def fit_cell(args):
    """Penalised MLE of (lam_r, lam_q) for one cell. args: (key, counts {(s, s1): n}, cap, prior_r, prior_q, prior_hours)."""
    key, counts, c, pr, pq, w = args
    pairs = np.array(list(counts.keys()), int)
    n = np.array(list(counts.values()), float)
    keep = np.ones(len(n), bool)
    x0 = np.log([max(pr, 0.05), max(pq, 0.05)])

    def nll(x, keep):
        lr, lq = np.exp(x)
        K = kernel1(lr, lq, c)
        p = np.maximum(K[pairs[keep, 0], pairs[keep, 1]], 1e-300)
        # Gamma prior = w hours of pseudo-observations at the prior rate (per-hour units)
        prior = w * (pr * np.log(lr) - lr + pq * np.log(lq) - lq)
        return -(np.sum(n[keep] * np.log(p)) + prior)

    for _ in range(3):
        res = minimize(nll, x0, args=(keep,), method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": 300})
        x0 = res.x
        lr, lq = np.exp(res.x)
        K = kernel1(lr, lq, c)
        p = K[pairs[:, 0], pairs[:, 1]]
        new_keep = p >= P_MOVE
        if np.array_equal(new_keep, keep):
            break
        keep = new_keep
    return key, float(lr), float(lq), int(n[keep].sum()), int(n[~keep].sum())


def fit_rates(t, cap, workers=2):
    g = gross_rates(t)
    prior = g.groupby(["offday", "hod"]).agg(pr=("lam_r_gross", "mean"), pq=("lam_q_gross", "mean"))
    grp = t.groupby(["sno", "offday", "hod"])
    jobs = []
    for key, sub in grp:
        counts = sub.groupby(["s", "s1"]).size().to_dict()
        pr, pq = prior.loc[(key[1], key[2])]
        jobs.append((key, counts, int(cap[key[0]]), float(pr), float(pq), PRIOR_HOURS))
    t0 = time.time()
    with Pool(workers) as pool:
        out = pool.map(fit_cell, jobs, chunksize=20)
    print(f"fitted {len(out)} cells in {time.time() - t0:.0f}s", flush=True)
    r = pd.DataFrame([{"sno": k[0], "offday": k[1], "hod": k[2], "lam_r": lr, "lam_q": lq, "n": n, "n_moves": nm}
                      for k, lr, lq, n, nm in out])
    r = r.merge(g, on=["sno", "offday", "hod"], how="left", suffixes=("", "_g")).drop(columns=["n_g"])
    return r, prior


def fit_slot_rates(t, cap, hourly, w, workers=2):
    """10-minute rates for the corridor stations on teaching days; prior = the station's own hourly rates."""
    corridor = set(CAMPUS) | set(GATEWAY)
    h = hourly[hourly.offday == 0].set_index(["sno", "hod"])
    jobs = []
    for (sno, slot), sub in t[(t.offday == 0) & t.sno.isin(corridor)].groupby(["sno", "slot"]):
        if len(sub) < SLOT_MIN_N or (sno, slot // 6) not in h.index:
            continue
        pr, pq = h.loc[(sno, slot // 6), ["lam_r", "lam_q"]]
        jobs.append(((sno, slot), sub.groupby(["s", "s1"]).size().to_dict(), int(cap[sno]), float(max(pr, 0.02)), float(max(pq, 0.02)), w))
    with Pool(workers) as pool:
        out = pool.map(fit_cell, jobs, chunksize=20)
    return pd.DataFrame([{"sno": k[0], "slot": k[1], "lam_r": lr, "lam_q": lq, "n": n, "n_moves": nm} for k, lr, lq, n, nm in out])


def loglik_slots(t, hourly, slots, cap):
    """Mean log-likelihood per teaching-day corridor transition: hourly rates against 10-minute rates."""
    corridor = set(CAMPUS) | set(GATEWAY)
    m = t[(t.offday == 0) & t.sno.isin(corridor)].merge(hourly[hourly.offday == 0][["sno", "hod", "lam_r", "lam_q"]], on=["sno", "hod"], how="inner")
    m = m.merge(slots[["sno", "slot", "lam_r", "lam_q"]].rename(columns={"lam_r": "sr", "lam_q": "sq"}), on=["sno", "slot"], how="left")
    m["sr"] = m.sr.fillna(m.lam_r); m["sq"] = m.sq.fillna(m.lam_q)
    out = {}
    for name, cr, cq in (("hourly", "lam_r", "lam_q"), ("slots", "sr", "sq")):
        ll = 0.0
        for (sno, lr, lq), sub in m.groupby(["sno", cr, cq]):
            K = kernel1(max(lr, 1e-3), max(lq, 1e-3), int(cap[sno]))
            ll += np.log(np.maximum(K[sub.s.values, sub.s1.values], 1e-12)).sum()
        out[name] = ll / len(m)
    return out, len(m)


def loglik(t, rates, cap, kind):
    """Mean log-likelihood per transition of t under rates (columns lam_r, lam_q or the gross columns)."""
    cols = {"chain": ("lam_r", "lam_q"), "gross": ("lam_r_gross", "lam_q_gross"), "prior": ("pr", "pq")}[kind]
    m = t.merge(rates, on=["sno", "offday", "hod"], how="left")
    ll, cnt = 0.0, 0
    for (sno, off, hod), sub in m.groupby(["sno", "offday", "hod"]):
        lr, lq = sub[cols[0]].iloc[0], sub[cols[1]].iloc[0]
        if np.isnan(lr) or np.isnan(lq):
            continue
        K = kernel1(max(lr, 1e-3), max(lq, 1e-3), int(cap[sno]))
        p = np.maximum(K[sub.s.values, sub.s1.values], 1e-12)
        ll += np.log(p).sum(); cnt += len(sub)
    return ll / cnt, cnt


if __name__ == "__main__":
    st = load_stations(DATA)
    st = st[st.logged == 1]
    cap = dict(zip(st.sno, st.capacity.astype(int)))
    df = load_logger(DATA)
    df = df[df.sno.isin(cap)]
    if UNTIL:
        df = df[df.date <= UNTIL]
    days = sorted(df.date.unique())
    t = transitions(df, cap)
    print(f"{len(days)} days {days[0]}..{days[-1]}, {len(t)} transitions, {t.sno.nunique()} stations", flush=True)
    if HOLDOUT:
        train_days, test_days = days[:-HOLDOUT], days[-HOLDOUT:]
        tr, te = t[t.date.isin(train_days)], t[t.date.isin(test_days)]
        r, prior = fit_rates(tr, cap, WORKERS)
        rp = r.merge(prior.reset_index(), on=["offday", "hod"])
        rows = []
        for kind in ("chain", "gross", "prior"):
            ll, n = loglik(te, rp, cap, kind)
            rows.append({"rates": kind, "test_days": len(test_days), "transitions": n, "loglik_per_transition": ll})
            print(f"holdout {kind}: {ll:.4f} per transition over {n}", flush=True)
        if SLOTS:
            ll, n = loglik_slots(te, r, fit_slot_rates(tr, cap, r, SLOT_PRIOR, WORKERS), cap)
            for kind, v in ll.items():
                rows.append({"rates": f"corridor teaching days, {kind}", "test_days": len(test_days), "transitions": n, "loglik_per_transition": v})
                print(f"holdout corridor, {kind}: {v:.4f} per transition over {n}", flush=True)
        pd.DataFrame(rows).to_csv(OUT / "rates_holdout.csv", index=False)
    if TUNE_SLOTS:
        teach = sorted(t[t.offday == 0].date.unique())
        val = teach[-5:]
        tr, va = t[~t.date.isin(val)], t[t.date.isin(val)]
        r, _ = fit_rates(tr, cap, WORKERS)
        rows = []
        for w in (0.25, 0.5, 1.0, 2.0, 4.0):
            ll, n = loglik_slots(va, r, fit_slot_rates(tr, cap, r, w, WORKERS), cap)
            rows.append({"slot_prior_hours": w, "val_days": len(val), "transitions": n, "loglik_hourly": ll["hourly"], "loglik_slots": ll["slots"]})
            print(f"slot prior {w} h: validation log-likelihood {ll['slots']:.4f} (hourly {ll['hourly']:.4f}) over {n} transitions on {val[0]}..{val[-1]}", flush=True)
        pd.DataFrame(rows).to_csv(OUT / "rates_slots_tuning.csv", index=False)
    r, prior = fit_rates(t, cap, WORKERS)
    r.to_csv(OUT / "rates.csv", index=False)
    prior.reset_index().to_csv(OUT / "rates_prior.csv", index=False)
    setup = {"days": [str(d) for d in days], "transitions": int(len(t)), "cells": int(len(r)), "prior_hours": PRIOR_HOURS,
             "p_move": P_MOVE, "hours": [HOURS.start, HOURS.stop - 1], "max_age_min": MAX_AGE, "moves_excluded": int(r.n_moves.sum()),
             "offdays": sorted(str(d) for d in t[t.offday == 1].date.unique())}
    if SLOTS:
        rs = fit_slot_rates(t, cap, r, SLOT_PRIOR, WORKERS)
        rs.to_csv(OUT / "rates_slots.csv", index=False)
        setup.update({"slot_cells": int(len(rs)), "slot_prior_hours": SLOT_PRIOR, "slot_min_transitions": SLOT_MIN_N, "slot_stations": int(rs.sno.nunique())})
        print(f"slot rates: {len(rs)} cells for {rs.sno.nunique()} stations", flush=True)
    json.dump(setup, open(OUT / "rates_setup.json", "w"), indent=1)
    print(r.describe().round(2).to_string())
