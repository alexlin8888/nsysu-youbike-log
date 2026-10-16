"""Horizon sweep (30/60/90/120 min) on the NTU panel: the direct classifiers against the Poisson
roll-out that the proposal described, plus a logistic-regression baseline and a stacked model.

Usage: python horizon_sweep.py NTU_DIR MODEL_DIR OUT_DIR [--frac 0.4]

Poisson roll-out (proposal Sec. 2.3-2.4). Rental and return rates per station x off-day x hour are
estimated on the training period with the censoring correction (rate = events / exposure, exposure =
share of 10-min slots with bikes > 0 for rentals, docks > 0 for returns). Inventory is rolled forward
in 10-minute steps as a birth-death chain with net change ~ Skellam(returns, rentals), clipped to
[0, capacity], with the empty state absorbing. P(empty within h) is read off the chain exactly; a
Monte-Carlo sampler with the same dynamics is run on a subset to confirm the two agree.

Models evaluated on the same test rows (rows with an observed current inventory):
  persistence, seasonal, mc_naive (uncorrected rates), mc_cens (corrected rates), logistic,
  lgb_inv, lgb_full (30/60 loaded from MODEL_DIR, 90/120 trained here with identical settings),
  lgb_full_mc (lgb_full features + the roll-out probability as one extra feature).
Writes sweep_metrics.csv, sweep_pred_{h}.parquet, sweep_setup.json, rates_train.csv.
"""
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from features import FULL_FEATS, INV_FEATS, NTU_BELLS, NTU_SEMESTERS, TW_HOLIDAYS, build  # noqa: E402

NTU = Path(sys.argv[1]); MODELS = Path(sys.argv[2]); OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
FRAC = float(sys.argv[sys.argv.index("--frac") + 1]) if "--frac" in sys.argv else 0.4
TRAIN_END, VAL_START, TEST_START = "2025-03-31", "2025-03-10", "2025-04-01"
MAJORS = ["12:10", "15:10", "17:20"]
HORIZONS = (30, 60, 90, 120)
RUN = tuple(int(x) for x in sys.argv[sys.argv.index("--run") + 1].split(",")) if "--run" in sys.argv else HORIZONS
SEED = 7
STEP_MIN = 10
PRIOR_HOURS = 3          # shrinkage weight (in hours of exposure) toward the hour-of-day mean across stations
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_data_in_leaf=200, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, num_threads=2, verbose=-1, seed=SEED)


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    tot = 0.0
    for b in range(bins):
        m = idx == b
        if m.sum():
            tot += m.mean() * abs(y[m].mean() - p[m].mean())
    return tot


def metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "pos_rate": float(y.mean()), "brier": float(brier_score_loss(y, p)),
            "auc": float(roc_auc_score(y, p)) if 0 < y.mean() < 1 else np.nan,
            "logloss": float(log_loss(y, p)), "ece": float(ece(y, p))}


t0 = time.time()
panel = pd.read_parquet(NTU / "panel_10min.parquet")
stations = pd.read_csv(NTU / "ntu_stations.csv", dtype={"sno": str})
flows = pd.read_parquet(NTU / "flows_hourly.parquet")
X = build(panel, stations, NTU_BELLS, MAJORS, NTU_SEMESTERS, flows=flows, train_end=TRAIN_END, horizons=HORIZONS)
X["campus"] = X.sno.map(dict(zip(stations.sno, stations.campus))).astype(np.int8)
print(f"features built: {X.shape} in {time.time() - t0:.0f}s")

# ---------------------------------------------------------------- rates on the training period
sidx = {s: i for i, s in enumerate(stations.sno)}
pt = panel[(panel.ts <= pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1)) & panel.sno.isin(sidx)].copy()
pt["hour"] = pt.ts.dt.floor("h")
pt["bp"] = (pt.bikes > 0).astype(float); pt["dp"] = (pt.docks > 0).astype(float)
pt["na"] = (pt.bikes.isna() | pt.docks.isna()).astype(float)
hr = pt.groupby(["sno", "hour"]).agg(bp=("bp", "sum"), dp=("dp", "sum"), na=("na", "sum"), n=("bp", "size")).reset_index()
hr = hr[(hr.na == 0) & (hr.n == 6)]
hr["exp_r"] = hr.bp / hr.n; hr["exp_q"] = hr.dp / hr.n
hr = hr.merge(flows, on=["sno", "hour"], how="left").fillna({"rentals": 0, "returns": 0})
del pt
hr["hod"] = hr.hour.dt.hour
hr["offday"] = ((hr.hour.dt.dayofweek >= 5) | hr.hour.dt.strftime("%Y-%m-%d").isin(TW_HOLIDAYS)).astype(int)
cell = hr.groupby(["sno", "offday", "hod"]).agg(hours=("rentals", "size"), R=("rentals", "sum"), Q=("returns", "sum"),
                                                Er=("exp_r", "sum"), Eq=("exp_q", "sum")).reset_index()
cell["lam_r_naive"] = cell.R / cell.hours
cell["lam_q_naive"] = cell.Q / cell.hours
prior = cell.groupby(["offday", "hod"]).agg(pr=("lam_r_naive", "mean"), pq=("lam_q_naive", "mean"))
cell = cell.join(prior, on=["offday", "hod"])
cell["lam_r_cens"] = (cell.R + PRIOR_HOURS * cell.pr) / (cell.Er + PRIOR_HOURS)
cell["lam_q_cens"] = (cell.Q + PRIOR_HOURS * cell.pq) / (cell.Eq + PRIOR_HOURS)
cell["lam_r_naive_s"] = (cell.R + PRIOR_HOURS * cell.pr) / (cell.hours + PRIOR_HOURS)   # same shrinkage, no correction
cell["lam_q_naive_s"] = (cell.Q + PRIOR_HOURS * cell.pq) / (cell.hours + PRIOR_HOURS)
cell.to_csv(OUT / "rates_train.csv", index=False)
cap = X.groupby("si").total.max().astype(int)                       # station capacity for the chain
CMAX = int(cap.max())
print(f"rate cells {len(cell)}, capacity max {CMAX}, training station-hours {len(hr)}")


def kernel(lam_r, lam_q, C, absorbing=True):
    """One 10-minute transition matrix on states 0..C. From state i, rentals ~ Poisson(a) censored at i
    (no bike, no rental) and returns ~ Poisson(b) censored at C - i (no dock, no return). With
    absorbing=True state 0 is absorbing (the station has been empty); the first step of a roll-out uses
    absorbing=False so that a station that is empty now can still be refilled."""
    a, b = lam_r * STEP_MIN / 60, lam_q * STEP_MIN / 60
    M = max(int(max(a, b) + 8 * np.sqrt(max(a, b)) + 20), C + 1)   # Poisson support cut where the tail mass is negligible
    pr, pq = poisson.pmf(np.arange(M + 1), a), poisson.pmf(np.arange(M + 1), b)
    K = np.zeros((C + 1, C + 1))
    for i in range(C + 1):
        if i == 0 and absorbing:
            K[0, 0] = 1.0
            continue
        prc = pr[:i + 1].copy(); prc[i] = pr[i:].sum()              # min(rentals, i)
        pqc = pq[:C - i + 1].copy(); pqc[C - i] = pq[C - i:].sum()  # min(returns, C - i)
        K[i] = np.convolve(pqc, prc[::-1])                          # index = i + returns - rentals
    return K


NS = len(sidx)
CAP = cap.reindex(range(NS)).values.astype(int)


def gid(si, off, slot):
    return (si * 2 + off) * 144 + slot


def rollout(rate_r, rate_q, tag):
    """Exact absorption probabilities, array [group, horizon, start state] with group = (station, offday, slot)."""
    lut_r = {(r.sno, r.offday, r.hod): getattr(r, rate_r) for r in cell.itertuples()}
    lut_q = {(r.sno, r.offday, r.hod): getattr(r, rate_q) for r in cell.itertuples()}
    kmax = max(HORIZONS) // STEP_MIN
    ks = [h // STEP_MIN for h in HORIZONS]
    res = np.full((NS * 2 * 144, len(HORIZONS), CMAX + 1), np.nan, dtype=np.float32)
    t1 = time.time()
    for s, i in sidx.items():
        C = CAP[i]
        for off in (0, 1):
            Ks, K1 = {}, {}
            for hod in range(24):
                lr = lut_r.get((s, off, hod), prior.loc[(off, hod), "pr"])
                lq = lut_q.get((s, off, hod), prior.loc[(off, hod), "pq"])
                Ks[hod] = kernel(lr, lq, C)
                K1[hod] = kernel(lr, lq, C, absorbing=False)
            for slot in range(36, 138):
                V = K1[(slot // 6) % 24]                       # first step: an empty station may be refilled
                for j in range(2, kmax + 1):
                    V = V @ Ks[((slot + j - 1) // 6) % 24]
                    if j in ks:
                        res[gid(i, off, slot), ks.index(j), :C + 1] = V[:, 0]
    print(f"{tag}: roll-out table in {time.time() - t1:.0f}s")
    return res


def lookup(res, df):
    g = gid(df.si.values, df.offday.values.astype(int), df.slot.values.astype(int))
    b0 = np.minimum(df.bikes.values, CAP[df.si.values]).astype(int)
    return res[g, :, b0]


def mc_sample(df, res_tag_rates, n_samples=400, seed=SEED):
    """Monte-Carlo version of the same dynamics (sampling), for a subset of rows: returns P(empty within h)."""
    rate_r, rate_q = res_tag_rates
    lut_r = {(r.sno, r.offday, r.hod): getattr(r, rate_r) for r in cell.itertuples()}
    lut_q = {(r.sno, r.offday, r.hod): getattr(r, rate_q) for r in cell.itertuples()}
    rng = np.random.default_rng(seed)
    kmax = max(HORIZONS) // STEP_MIN
    out = np.zeros((len(df), len(HORIZONS)))
    for n, r in enumerate(df.itertuples()):
        C = int(CAP[r.si]); b = np.full(n_samples, min(int(r.bikes), C)); hit = np.zeros(n_samples, bool)
        for j in range(1, kmax + 1):
            hod = ((r.slot + j - 1) // 6) % 24
            lr = lut_r.get((r.sno, r.offday, hod), prior.loc[(r.offday, hod), "pr"])
            lq = lut_q.get((r.sno, r.offday, hod), prior.loc[(r.offday, hod), "pq"])
            rent = np.minimum(rng.poisson(lr / 6, n_samples), b)        # no bike, no rental
            ret = np.minimum(rng.poisson(lq / 6, n_samples), C - b)     # no dock, no return
            b = b + ret - rent
            hit |= b == 0                                               # sticky: empty at any step boundary
            if j * STEP_MIN in HORIZONS:
                out[n, HORIZONS.index(j * STEP_MIN)] = hit.mean()
    return out


# ---------------------------------------------------------------- splits
train = X[X.date <= TRAIN_END]
test = X[(X.date >= TEST_START) & X.bikes.notna() & X.total.notna()]
val_mask = train.date >= VAL_START
tr = train[~val_mask].sample(frac=FRAC, random_state=SEED) if FRAC < 1 else train[~val_mask]
va = train[val_mask]
n_test_all = int((X.date >= TEST_START).sum())
print(f"train {len(tr)} val {len(va)} test {len(test)} (test rows with observed inventory; {n_test_all} total)")
import gc
del X, train, panel, hr
gc.collect()

res_cens = rollout("lam_r_cens", "lam_q_cens", "roll-out, corrected rates")
res_naive = rollout("lam_r_naive_s", "lam_q_naive_s", "roll-out, naive rates")
P_cens = lookup(res_cens, test)
P_naive = lookup(res_naive, test)
# the training rows also need the roll-out probability for the stacked model
trm = tr[tr.bikes.notna()]; vam = va[va.bikes.notna()]
P_cens_tr = lookup(res_cens, trm); P_cens_va = lookup(res_cens, vam)

# Monte-Carlo check on a random subset
sub = test.sample(n=3000, random_state=SEED)
t1 = time.time()
P_mc = mc_sample(sub, ("lam_r_cens", "lam_q_cens"))
P_ex = lookup(res_cens, sub)
mc_check = {f"h{h}": {"mean_abs_diff": float(np.abs(P_mc[:, k] - P_ex[:, k]).mean()),
                     "max_abs_diff": float(np.abs(P_mc[:, k] - P_ex[:, k]).max()),
                     "corr": float(np.corrcoef(P_mc[:, k], P_ex[:, k])[0, 1])} for k, h in enumerate(HORIZONS)}
print(f"MC check ({len(sub)} rows x 400 samples, {time.time() - t1:.0f}s):", json.dumps(mc_check))

subsets = {
    "all": lambda d: np.ones(len(d), bool),
    "campus": lambda d: d.campus.values == 1,
    "classend": lambda d: (d.offday.values == 0) & (d.since_major.values <= 40) & (d.campus.values == 1),
    "weekday_day": lambda d: (d.offday.values == 0) & (d.hour.values >= 8) & (d.hour.values < 20),
}
NUM = [f for f in INV_FEATS if f not in ("hour", "dow")]


def logistic_design(d):
    """numeric inventory features + one-hot hour-of-day and day-of-week."""
    Z = d[NUM].copy()
    for hh in range(6, 23):
        Z[f"h{hh}"] = (d.hour.values.astype(int) == hh).astype(np.float32)
    for dd in range(7):
        Z[f"dow{dd}"] = (d.dow.values == dd).astype(np.float32)
    return Z


results, trees = [], {}
if (OUT / "sweep_setup.json").exists():
    trees = json.load(open(OUT / "sweep_setup.json")).get("trees", {})
for k, h in enumerate(HORIZONS):
    y = f"y{h}"
    if h not in RUN:
        if not (OUT / f"sweep_pred_{h}.parquet").exists():
            continue
        saved = pd.read_parquet(OUT / f"sweep_pred_{h}.parquet")
        for model in [c for c in saved.columns if c not in ("sno", "ts", "si", "campus", "offday", "slot", "hour", "since_major", "bikes", "total", y)]:
            for subn, fn in subsets.items():
                m = fn(saved)
                r = metrics(saved[y].values[m], saved[model].values[m].astype(float)); r.update({"h": h, "model": model, "subset": subn})
                results.append(r)
        print(f"h={h}: metrics recomputed from saved predictions")
        del saved
        continue
    trh, vah, teh = trm.dropna(subset=[y]), vam.dropna(subset=[y]), test.dropna(subset=[y])
    trh_all, vah_all = tr.dropna(subset=[y]), va.dropna(subset=[y])     # as in train_predictor.py (NaN inventory kept)
    mtr, mva, mte = trm[y].notna().values, vam[y].notna().values, test[y].notna().values
    preds = {"persistence": teh.empty_now.values.astype(float)}
    key_tr = pd.Series(list(zip(trh.si, trh.offday, trh.slot)), index=trh.index)
    seas = trh[y].groupby(key_tr).mean()
    key_te = pd.Series(list(zip(teh.si, teh.offday, teh.slot)), index=teh.index)
    preds["seasonal"] = key_te.map(seas).fillna(trh[y].mean()).values
    preds["mc_naive"] = P_naive[mte, k]
    preds["mc_cens"] = P_cens[mte, k]
    # the same roll-out after isotonic calibration on the validation rows (recalibrates, keeps the ranking)
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(P_cens_va[mva, k], vah[y].values)
    preds["mc_cens_cal"] = iso.predict(P_cens[mte, k])
    # logistic regression
    t1 = time.time()
    lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=300))
    lr.fit(logistic_design(trh), trh[y])
    preds["logistic"] = lr.predict_proba(logistic_design(teh))[:, 1]
    print(f"h={h} logistic fitted in {time.time() - t1:.0f}s")
    # gradient boosting
    for name, feats in (("inv", INV_FEATS), ("full", FULL_FEATS + ["si"])):
        f = MODELS / f"lgb_{name}_{h}.txt"
        cat = ["si"] if "si" in feats else []
        if f.exists():
            bst = lgb.Booster(model_file=str(f))
            print(f"h={h} {name}: loaded {bst.num_trees()} trees")
        else:
            dtr = lgb.Dataset(trh_all[feats], trh_all[y], categorical_feature=cat, free_raw_data=False)
            dva = lgb.Dataset(vah_all[feats], vah_all[y], categorical_feature=cat, reference=dtr)
            t1 = time.time()
            bst = lgb.train(PARAMS, dtr, num_boost_round=2000, valid_sets=[dva], callbacks=[lgb.early_stopping(50, verbose=False)])
            bst.save_model(str(f), num_iteration=bst.best_iteration)
            print(f"h={h} {name}: trained {bst.best_iteration} trees in {time.time() - t1:.0f}s")
        preds[f"lgb_{name}"] = bst.predict(teh[feats], num_iteration=bst.best_iteration or None)
        trees[f"lgb_{name}_{h}"] = int(bst.num_trees())
    # stacked: full features + roll-out probability
    feats = FULL_FEATS + ["si", "p_mc"]
    trs, vas, tes = trh[FULL_FEATS + ["si"]].copy(), vah[FULL_FEATS + ["si"]].copy(), teh[FULL_FEATS + ["si"]].copy()
    trs["p_mc"] = P_cens_tr[mtr, k]; vas["p_mc"] = P_cens_va[mva, k]; tes["p_mc"] = P_cens[mte, k]
    dtr = lgb.Dataset(trs, trh[y], categorical_feature=["si"], free_raw_data=False)
    dva = lgb.Dataset(vas, vah[y], categorical_feature=["si"], reference=dtr)
    t1 = time.time()
    bst = lgb.train(PARAMS, dtr, num_boost_round=2000, valid_sets=[dva], callbacks=[lgb.early_stopping(50, verbose=False)])
    bst.save_model(str(OUT / f"lgb_full_mc_{h}.txt"), num_iteration=bst.best_iteration)
    preds["lgb_full_mc"] = bst.predict(tes, num_iteration=bst.best_iteration)
    trees[f"lgb_full_mc_{h}"] = int(bst.best_iteration)
    imp = pd.Series(bst.feature_importance("gain"), index=feats)
    print(f"h={h} full+mc: {bst.best_iteration} trees in {time.time() - t1:.0f}s; p_mc gain share {imp['p_mc'] / imp.sum():.3f}")
    for model, p in preds.items():
        for subn, fn in subsets.items():
            m = fn(teh)
            if m.sum() < 1000:
                continue
            r = metrics(teh[y].values[m], np.asarray(p)[m]); r.update({"h": h, "model": model, "subset": subn})
            results.append(r)
            print(f"h={h:>3} {model:<12} {subn:<12} n={r['n']:>8} pos={r['pos_rate']:.3f} brier={r['brier']:.4f} auc={r['auc']:.3f} ece={r['ece']:.4f}")
    out = teh[["sno", "ts", "si", "campus", "offday", "slot", "hour", "since_major", "bikes", "total", y]].copy()
    for model, p in preds.items():
        out[model] = np.asarray(p, dtype=np.float32)
    out.to_parquet(OUT / f"sweep_pred_{h}.parquet", index=False)
    del trh, vah, teh, trh_all, vah_all, preds, out, trs, vas, tes, dtr, dva, bst, lr
    gc.collect()

pd.DataFrame(results).to_csv(OUT / "sweep_metrics.csv", index=False)
json.dump({"train_end": TRAIN_END, "val_start": VAL_START, "test_start": TEST_START, "frac": FRAC, "horizons": HORIZONS,
           "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(test)), "n_test_all_rows": n_test_all,
           "n_rate_cells": int(len(cell)), "prior_hours": PRIOR_HOURS, "capacity_max": CMAX, "trees": trees,
           "mc_check": mc_check, "mc_samples": 400, "mc_rows": int(len(sub))},
          open(OUT / "sweep_setup.json", "w"), indent=1)
print(f"done in {time.time() - t0:.0f}s")
