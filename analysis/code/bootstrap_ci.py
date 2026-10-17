"""Block-bootstrap confidence intervals for the predictor comparisons and the replay simulator.

Usage: python bootstrap_ci.py SWEEP_DIR TRANSFER_DIR SIM_ROOT OUT_DIR [--B 250]

NTU sweep:   blocks = test days; pooled AUC / Brier recomputed under day resampling (same draws for all
             models, so paired differences are valid). Subsets all / campus.
NSYSU:       blocks = station-days (only 6 test days); same procedure.
Simulator:   paired per-day differences between policies, percentile CI over day resampling.
Writes ci_predictor.csv, ci_transfer.csv, ci_sim.csv (--sim-only: ci_sim.csv; --transfer-only: ci_transfer.csv).
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

SWEEP, TRANS, SIM, OUT = (Path(a) for a in sys.argv[1:5]); OUT.mkdir(parents=True, exist_ok=True)
B = int(sys.argv[sys.argv.index("--B") + 1]) if "--B" in sys.argv else 250
SEED = 11


class WeightedAUC:
    """Pooled AUC under per-row weights, with ties scored 1/2; precomputes the score grouping once."""

    def __init__(self, score, y):
        self.y = y.astype(float)
        _, self.g = np.unique(score, return_inverse=True)
        self.ng = self.g.max() + 1

    def __call__(self, w):
        wy = w * self.y
        wn = w - wy
        neg_g = np.bincount(self.g, weights=wn, minlength=self.ng)
        below = np.cumsum(neg_g) - neg_g
        num = np.sum(wy * (below[self.g] + 0.5 * neg_g[self.g]))
        return num / (wy.sum() * wn.sum())


def block_bootstrap(df, y, models, block, rng, B):
    """Returns dict model -> (auc_samples, brier_samples) under block resampling; and point estimates."""
    blocks, binv = np.unique(block, return_inverse=True)
    nb = len(blocks)
    yv = df[y].values.astype(float)
    aucs = {m: WeightedAUC(df[m].values, yv) for m in models}
    sq = {m: (np.clip(df[m].values, 1e-6, 1 - 1e-6) - yv) ** 2 for m in models}
    out = {m: (np.zeros(B), np.zeros(B)) for m in models}
    ones = np.ones(len(df))
    point = {m: (aucs[m](ones), sq[m].mean()) for m in models}
    for b in range(B):
        cnt = np.bincount(rng.integers(0, nb, nb), minlength=nb).astype(float)
        w = cnt[binv]
        ws = w.sum()
        for m in models:
            out[m][0][b] = aucs[m](w)
            out[m][1][b] = np.sum(w * sq[m]) / ws
    return point, out


def summarize(point, samp, models, ref, tag):
    rows = []
    for m in models:
        a, br = samp[m]
        row = {**tag, "model": m, "auc": point[m][0], "auc_lo": np.percentile(a, 2.5), "auc_hi": np.percentile(a, 97.5),
               "brier": point[m][1], "brier_lo": np.percentile(br, 2.5), "brier_hi": np.percentile(br, 97.5)}
        if m != ref:
            da, db = a - samp[ref][0], br - samp[ref][1]
            row.update({"ref": ref, "d_auc": point[m][0] - point[ref][0], "d_auc_lo": np.percentile(da, 2.5), "d_auc_hi": np.percentile(da, 97.5),
                        "d_brier": point[m][1] - point[ref][1], "d_brier_lo": np.percentile(db, 2.5), "d_brier_hi": np.percentile(db, 97.5)})
        rows.append(row)
    return rows


rng = np.random.default_rng(SEED)
t0 = time.time()
SIM_ONLY = "--sim-only" in sys.argv
TRANS_ONLY = "--transfer-only" in sys.argv          # recompute ci_transfer.csv only
# ---------------------------------------------------------------- NTU sweep
rows = []
for h in (30, 60, 90, 120) if not (SIM_ONLY or TRANS_ONLY) else ():
    f = SWEEP / f"sweep_pred_{h}.parquet"
    if not f.exists():
        continue
    d = pd.read_parquet(f)
    y = f"y{h}"
    models = [c for c in ("persistence", "seasonal", "mc_naive", "mc_cens", "mc_cens_cal", "logistic", "lgb_inv", "lgb_full", "lgb_full_mc") if c in d]
    day = d.ts.dt.normalize().values
    for sub, m in (("all", np.ones(len(d), bool)), ("campus", d.campus.values == 1)):
        dd, blk = d[m], day[m]
        point, samp = block_bootstrap(dd, y, models, blk, rng, B)
        rows += summarize(point, samp, models, "lgb_inv", {"h": h, "subset": sub, "n": len(dd), "blocks": int(pd.Series(blk).nunique())})
        print(f"NTU h={h} {sub}: {len(dd)} rows, {time.time() - t0:.0f}s")
if not (SIM_ONLY or TRANS_ONLY):
    pd.DataFrame(rows).to_csv(OUT / "ci_predictor.csv", index=False)

# ---------------------------------------------------------------- NSYSU transfer
rows = []
for h in (30, 60) if not SIM_ONLY else ():
    f = TRANS / f"nsysu_test_pred_{h}.parquet"
    if not f.exists():
        continue
    d = pd.read_parquet(f)
    y = f"y{h}"
    models = [c for c in ("persistence", "seasonal_nsysu", "ntu_zero_shot", "ntu_finetuned", "nsysu_only") if c in d]
    blk_all = (d.sno.astype(str) + "_" + d.ts.dt.strftime("%Y-%m-%d")).values
    for sub, m in (("all309", np.ones(len(d), bool)), ("campus8", d.campus.values == 1)):
        dd, blk = d[m], blk_all[m]
        point, samp = block_bootstrap(dd, y, models, blk, rng, B)
        rows += summarize(point, samp, models, "ntu_zero_shot", {"h": h, "subset": sub, "n": len(dd), "blocks": int(pd.Series(blk).nunique())})
        print(f"NSYSU h={h} {sub}: {len(dd)} rows, {time.time() - t0:.0f}s")
if not SIM_ONLY:
    pd.DataFrame(rows).to_csv(OUT / "ci_transfer.csv", index=False)

# ---------------------------------------------------------------- simulator
rows = []
for k in (1, 3, 6) if not TRANS_ONLY else ():
    f = SIM / f"k{k}" / "sim_daily.csv"
    if not f.exists():
        continue
    d = pd.read_csv(f)
    if "policy" not in d or "unmet" not in d:
        print("sim_daily columns:", list(d.columns)); break
    wide = d.pivot(index="date", columns="policy", values="unmet")
    base = wide["none"] if "none" in wide else None
    nd = len(wide)
    for pol in wide.columns:
        if pol == "none" or base is None:
            continue
        red = 1 - wide[pol] / base                       # per-day relative reduction
        samp = np.array([red.values[rng.integers(0, nd, nd)].mean() for _ in range(B * 4)])
        pooled = 1 - wide[pol].sum() / base.sum()
        pooled_s = np.array([1 - wide[pol].values[idx].sum() / base.values[idx].sum()
                             for idx in (rng.integers(0, nd, nd) for _ in range(B * 4))])
        rows.append({"K": k, "policy": pol, "days": nd, "reduction_pooled": pooled, "pooled_lo": np.percentile(pooled_s, 2.5),
                     "pooled_hi": np.percentile(pooled_s, 97.5), "reduction_daily_mean": red.mean(), "daily_sd": red.std(),
                     "daily_lo": np.percentile(samp, 2.5), "daily_hi": np.percentile(samp, 97.5),
                     "unmet_mean": wide[pol].mean(), "unmet_sd": wide[pol].std()})
    # paired policy differences (share of the no-rebalancing unmet rentals / empty minutes)
    wide_e = d.pivot(index="date", columns="policy", values="empty_station_min")
    for a, b_ in (("prob", "reactive"), ("prob", "point"), ("reactive", "point")):
        if a not in wide or b_ not in wide:
            continue
        for metric, w_ in (("unmet", wide), ("empty_min", wide_e)):
            diff = (w_[b_] - w_[a]) / w_["none"]
            samp = np.array([diff.values[rng.integers(0, nd, nd)].mean() for _ in range(B * 4)])
            rows.append({"K": k, "policy": f"{a}_minus_{b_}_{metric}", "days": nd, "reduction_pooled": diff.mean(),
                         "pooled_lo": np.percentile(samp, 2.5), "pooled_hi": np.percentile(samp, 97.5),
                         "reduction_daily_mean": diff.mean(), "daily_sd": diff.std(), "daily_lo": np.percentile(samp, 2.5),
                         "daily_hi": np.percentile(samp, 97.5), "unmet_mean": np.nan, "unmet_sd": np.nan,
                         "share_days_first_better": float((diff > 0).mean())})
if not TRANS_ONLY:
    pd.DataFrame(rows).to_csv(OUT / "ci_sim.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string())
print(f"done in {time.time() - t0:.0f}s")
