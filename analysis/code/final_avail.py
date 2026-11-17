"""Will this station still have a bike (a free dock) k x 10 minutes from now? Chain alone against chain + learning.

Usage: python final_avail.py DATA_DIR RATES_DIR OUT_DIR [--first 2026-10-30] [--last 2026-11-16] [--threads 2] [--save-model DIR]

The page tells a rider whether a station will still have a bike, or a free dock, when the rider gets there. The
birth-death chain answers that from the current stock and the fitted rates, but it treats every station on its
own: it does not know that a station fills faster when the one next to it is full, or drains faster when its
neighbours are empty. This script measures what a correction learned from data adds.

For every snapshot (06:00-21:50) of the days after the rates were fitted, every station and k = 1..9:
  chain     P(stock >= 1) and P(free docks >= 1) after k steps of the chain (rates in RATES_DIR, fitted earlier)
  isotonic  the chain's probability passed through an isotonic map
  stacked   LightGBM on the chain's outputs plus what the chain cannot see: stock and docks now, their change over
            the last 10 and 30 minutes, the state of the five nearest stations (bikes, how many are empty or full),
            the chain's probability at the three nearest stations, time of day, day type and k
The days are split in two blocks; isotonic and stacked models fitted on one block are scored on the other, so every
row is scored by a model that never saw its day (and by rates that never saw either block).

Writes avail_metrics.csv (need, method, subset, horizon: AUC, Brier, ECE), avail_importance.csv and, for
final_rider.py, avail_oof.npz with the out-of-fold probabilities (day, slot, k, station). With --save-model it also
fits both models on all the days and writes avail_bike.txt and avail_dock.txt for demo_state.py.
"""
import json
import sys
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP, ChainValues, load_slot_rates  # noqa: E402

DATA, RATES, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default, cast=str: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
FIRST, LAST, THREADS = ARG("--first", "2026-10-30"), ARG("--last", "2026-11-16"), ARG("--threads", 2, int)
SAVE = ARG("--save-model", None)
OFFDAYS = set(HOLIDAYS)
KMAX = 9
SLOTS = range(36, 132)             # snapshots 06:00 .. 21:50
SEED = 3
FEATS = ["k", "minute", "offday", "campus", "gateway", "cap", "bikes", "docks", "d10", "d30", "nb_bikes", "nb_empty", "nb_full",
         "c_bike", "c_dock", "c_mean", "nb_c_bike", "nb_c_dock"]
warnings.simplefilter("ignore")


def setup(data, rates_dir):
    """Stations, neighbours and one chain per day type."""
    st = load_stations(data)
    st = st[st.logged == 1].reset_index(drop=True)
    n = len(st); sidx = {s: i for i, s in enumerate(st.sno)}; cap = st.capacity.values.astype(int)
    lat, lng = np.radians(st.lat.values), np.radians(st.lng.values)
    km = 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((lat[:, None] - lat[None, :]) / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin((lng[:, None] - lng[None, :]) / 2) ** 2))
    nb = np.argsort(km + np.eye(n) * 1e6, axis=1)[:, :5]
    rates = pd.read_csv(rates_dir / "rates.csv", dtype={"sno": str}); prior = pd.read_csv(rates_dir / "rates_prior.csv")
    chains = {}
    for off in (0, 1):
        R = np.zeros((n, 24)); Q = np.zeros((n, 24))
        for row in prior[prior.offday == off].itertuples():
            R[:, row.hod] = row.pr; Q[:, row.hod] = row.pq
        for row in rates[(rates.offday == off) & rates.sno.isin(sidx)].itertuples():
            R[sidx[row.sno], row.hod] = row.lam_r; Q[sidx[row.sno], row.hod] = row.lam_q
        chains[off] = ChainValues(R, Q, cap, 90, 20, load_slot_rates(rates_dir / "rates_slots.csv", sidx) if off == 0 else None)
    return st, sidx, cap, km, nb, chains


def chain_steps(chain, t_min, bikes, cap, kmax=KMAX):
    """P(bike), P(dock) and expected bikes after 1..kmax steps, each (kmax, N)."""
    n = len(cap)
    P = np.zeros((n, chain.C + 1), np.float32); P[np.arange(n), np.clip(bikes, 0, cap)] = 1.0
    lev = np.arange(chain.C + 1)[None, :]
    pb = np.zeros((kmax, n), np.float32); pk = np.zeros((kmax, n), np.float32); eb = np.zeros((kmax, n), np.float32)
    for k in range(kmax):
        P = chain._fwd(t_min + STEP * k, P)
        pb[k] = 1 - P[:, 0]; pk[k] = 1 - P[np.arange(n), cap]; eb[k] = (P * lev).sum(1)
    return pb, pk, eb


def features(bikes, docks, b10, b30, minute, offday, cap, nb, grp, pb, pk, eb):
    """Feature block (kmax * N, len(FEATS)) for one snapshot; NaN where the station's past is unknown."""
    n = len(cap); kmax = pb.shape[0]
    base = np.column_stack([np.full(n, minute), np.full(n, offday), grp == 1, grp == 2, cap, bikes, docks, bikes - b10, bikes - b30,
                            np.nanmean(bikes[nb], axis=1), np.nansum(bikes[nb] == 0, axis=1), np.nansum(docks[nb] == 0, axis=1)]).astype(np.float32)
    out = np.empty((kmax, n, len(FEATS)), np.float32)
    for k in range(kmax):
        out[k, :, 0] = k + 1
        out[k, :, 1:13] = base
        out[k, :, 13] = pb[k]; out[k, :, 14] = pk[k]; out[k, :, 15] = eb[k]
        out[k, :, 16] = pb[k][nb[:, :3]].mean(1); out[k, :, 17] = pk[k][nb[:, :3]].mean(1)
    return out.reshape(kmax * n, len(FEATS))


def ece(y, p, bins=10):
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    return float(sum((idx == b).mean() * abs(y[idx == b].mean() - p[idx == b].mean()) for b in range(bins) if (idx == b).any()))


if __name__ == "__main__":
    st, sidx, CAP, KM, NB, chains = setup(DATA, RATES)
    N = len(st)
    grp = np.where(st.sno.isin(CAMPUS), 1, np.where(st.sno.isin(GATEWAY), 2, 0))
    df = load_logger(DATA)
    df = df[df.sno.isin(sidx) & (df.age <= 20)].copy()
    df["i"] = df.sno.map(sidx); dstr = df.date.astype(str).str.slice(0, 10)
    days = [d for d in sorted(dstr.unique()) if FIRST <= d <= LAST and d != "2026-10-23"]
    X, YB, YK, META = [], [], [], []
    for di, day in enumerate(days):
        d = df[dstr == day]
        b = np.full((144, N), np.nan); kk = np.full((144, N), np.nan)
        b[d.slot.values, d.i.values] = d.bikes.values; kk[d.slot.values, d.i.values] = d.docks.values
        off = int(pd.Timestamp(day).dayofweek >= 5 or day in OFFDAYS)
        for s in SLOTS:
            known = ~np.isnan(b[s]) & ~np.isnan(kk[s])
            if known.sum() < 50:
                continue
            now = np.where(known, b[s], 0).astype(int)
            pb, pk, eb = chain_steps(chains[off], s * STEP, now, CAP)
            bikes = np.where(known, b[s], np.nan); docks = np.where(known, kk[s], np.nan)
            f = features(bikes, docks, b[s - 1], b[s - 3], s * STEP, off, CAP, NB, grp, pb, pk, eb)
            tgt = np.arange(1, KMAX + 1) + s
            ok = tgt <= 143
            yb = np.full((KMAX, N), np.nan); yk = np.full((KMAX, N), np.nan)
            yb[ok] = np.where(np.isnan(b[tgt[ok]]), np.nan, b[tgt[ok]] >= 1); yk[ok] = np.where(np.isnan(kk[tgt[ok]]), np.nan, kk[tgt[ok]] >= 1)
            yb[:, ~known] = np.nan; yk[:, ~known] = np.nan
            X.append(f); YB.append(yb.reshape(-1)); YK.append(yk.reshape(-1))
            META.append(np.column_stack([np.full(KMAX * N, di), np.full(KMAX * N, s), np.repeat(np.arange(1, KMAX + 1), N), np.tile(np.arange(N), KMAX)]))
        print(day, "off" if off else "teaching", len(X), flush=True)
    X = np.concatenate(X); YB = np.concatenate(YB); YK = np.concatenate(YK); META = np.concatenate(META).astype(np.int32)
    half = len(days) // 2
    fold = (META[:, 0] >= half).astype(int)                       # block 0: first half of the days, block 1: the rest
    params = dict(objective="binary", learning_rate=0.06, num_leaves=31, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.7, bagging_freq=1,
                  lambda_l2=1.0, num_threads=THREADS, verbose=-1, seed=SEED)
    rng = np.random.default_rng(SEED)
    oof = {"bike": {}, "dock": {}}; imp = []
    for need, Y, col in (("bike", YB, FEATS.index("c_bike")), ("dock", YK, FEATS.index("c_dock"))):
        have = ~np.isnan(Y)
        p_iso = np.full(len(Y), np.nan, np.float32); p_stk = np.full(len(Y), np.nan, np.float32)
        for f in (0, 1):
            tr = have & (fold != f); te = fold == f
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(X[tr, col], Y[tr])
            p_iso[te] = iso.predict(X[te, col])
            sub = np.flatnonzero(tr); sub = rng.choice(sub, min(len(sub), 900_000), replace=False)
            cut = int(len(sub) * 0.85)
            m = lgb.train(params, lgb.Dataset(X[sub[:cut]], Y[sub[:cut]], feature_name=FEATS), num_boost_round=600,
                          valid_sets=[lgb.Dataset(X[sub[cut:]], Y[sub[cut:]], feature_name=FEATS)], callbacks=[lgb.early_stopping(40, verbose=False)])
            p_stk[te] = m.predict(X[te], num_iteration=m.best_iteration, num_threads=THREADS)
            g = m.feature_importance("gain"); imp.append(pd.DataFrame({"need": need, "fold": f, "feature": FEATS, "gain_share": g / g.sum()}))
            print(need, "fold", f, "trees", m.best_iteration, flush=True)
        oof[need] = {"chain": X[:, col].copy(), "isotonic": p_iso, "stacked": p_stk, "y": Y}
    # ---------- metrics on teaching days ----------
    teach = np.array([int(pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS) for d in days])[META[:, 0]] == 1
    g = grp[META[:, 3]]
    subsets = {"all309": np.ones(len(g), bool), "corridor19": g > 0, "campus8": g == 1, "gateway11": g == 2}
    rows = []
    for need in ("bike", "dock"):
        y = oof[need]["y"]
        for sub, ms in subsets.items():
            for hz, mk in (("10-30 min", META[:, 2] <= 3), ("40-90 min", META[:, 2] >= 4)):
                m = ms & mk & teach & ~np.isnan(y)
                if m.sum() < 500 or y[m].min() == y[m].max():
                    continue
                for method in ("chain", "isotonic", "stacked"):
                    p = np.clip(oof[need][method][m], 0, 1)
                    rows.append({"need": need, "subset": sub, "horizon": hz, "method": method, "n": int(m.sum()), "unavailable_rate": float(1 - y[m].mean()),
                                 "auc": float(roc_auc_score(y[m], p)), "brier": float(brier_score_loss(y[m], p)), "ece": ece(y[m], p)})
    met = pd.DataFrame(rows); met.to_csv(OUT / "avail_metrics.csv", index=False)
    pd.concat(imp).groupby(["need", "feature"]).gain_share.mean().reset_index().sort_values(["need", "gain_share"], ascending=[True, False]).to_csv(OUT / "avail_importance.csv", index=False)
    np.savez_compressed(OUT / "avail_oof.npz", days=np.array(days), meta=META, **{f"{need}_{meth}": oof[need][meth].astype(np.float16) for need in oof for meth in ("chain", "isotonic", "stacked")})
    json.dump({"days": days, "block_0": days[:half], "block_1": days[half:], "features": FEATS, "rows": int(len(X)), "kmax": KMAX}, open(OUT / "avail_setup.json", "w"), indent=1)
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
    print(met.pivot_table(index=["need", "subset", "horizon"], columns="method", values=["auc", "brier", "ece"]).round(4).to_string())
    if SAVE:
        Path(SAVE).mkdir(parents=True, exist_ok=True)
        for need, Y in (("bike", YB), ("dock", YK)):
            sub = np.flatnonzero(~np.isnan(Y)); sub = rng.choice(sub, min(len(sub), 1_500_000), replace=False); cut = int(len(sub) * 0.9)
            m = lgb.train(params, lgb.Dataset(X[sub[:cut]], Y[sub[:cut]], feature_name=FEATS), num_boost_round=600,
                          valid_sets=[lgb.Dataset(X[sub[cut:]], Y[sub[cut:]], feature_name=FEATS)], callbacks=[lgb.early_stopping(40, verbose=False)])
            m.save_model(str(Path(SAVE) / f"avail_{need}.txt"), num_iteration=m.best_iteration)
            print("saved", need, m.best_iteration)
