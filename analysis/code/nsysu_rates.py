"""Rental and return rates at NSYSU from the logger alone (no trip records exist in Kaohsiung).

Usage: python nsysu_rates.py DATA_DIR OUT_DIR [--holdout N] [--workers W]

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
from nsysu_data import HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import kernel1  # noqa: E402

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
HOLDOUT = ARG("--holdout", 0, int)
WORKERS = ARG("--workers", 2, int)
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
    t = pd.DataFrame({"sno": df.sno[ok], "offday": df.offday[ok], "hod": (df.slot[ok] // 6).astype(int),
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
    """Penalised MLE of (lam_r, lam_q) for one cell. args: (key, counts {(s, s1): n}, cap, prior_r, prior_q)."""
    key, counts, c, pr, pq = args
    pairs = np.array(list(counts.keys()), int)
    n = np.array(list(counts.values()), float)
    keep = np.ones(len(n), bool)
    x0 = np.log([max(pr, 0.05), max(pq, 0.05)])

    def nll(x, keep):
        lr, lq = np.exp(x)
        K = kernel1(lr, lq, c)
        p = np.maximum(K[pairs[keep, 0], pairs[keep, 1]], 1e-300)
        # Gamma prior = PRIOR_HOURS hours of pseudo-observations at the prior rate (per-hour units)
        prior = PRIOR_HOURS * (pr * np.log(lr) - lr + pq * np.log(lq) - lq)
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
        jobs.append((key, counts, int(cap[key[0]]), float(pr), float(pq)))
    t0 = time.time()
    with Pool(workers) as pool:
        out = pool.map(fit_cell, jobs, chunksize=20)
    print(f"fitted {len(out)} cells in {time.time() - t0:.0f}s", flush=True)
    r = pd.DataFrame([{"sno": k[0], "offday": k[1], "hod": k[2], "lam_r": lr, "lam_q": lq, "n": n, "n_moves": nm}
                      for k, lr, lq, n, nm in out])
    r = r.merge(g, on=["sno", "offday", "hod"], how="left", suffixes=("", "_g")).drop(columns=["n_g"])
    return r, prior


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
        pd.DataFrame(rows).to_csv(OUT / "rates_holdout.csv", index=False)
    r, prior = fit_rates(t, cap, WORKERS)
    r.to_csv(OUT / "rates.csv", index=False)
    prior.reset_index().to_csv(OUT / "rates_prior.csv", index=False)
    json.dump({"days": [str(d) for d in days], "transitions": int(len(t)), "cells": int(len(r)), "prior_hours": PRIOR_HOURS,
               "p_move": P_MOVE, "hours": [HOURS.start, HOURS.stop - 1], "max_age_min": MAX_AGE,
               "moves_excluded": int(r.n_moves.sum())}, open(OUT / "rates_setup.json", "w"), indent=1)
    print(r.describe().round(2).to_string())
