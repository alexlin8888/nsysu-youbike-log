"""Train and evaluate the schedule-aware stockout predictor on the NTU panel.

Usage: python train_predictor.py NTU_DIR OUT_DIR [--frac 0.4]
Writes metrics.csv, reliability.csv, importance.csv, models lgb_{set}_{h}.txt, test_pred_{h}.parquet
"""
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

sys.path.insert(0, str(Path(__file__).parent))
from features import NTU_BELLS, NTU_SEMESTERS, FULL_FEATS, INV_FEATS, build  # noqa: E402

NTU = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
FRAC = float(sys.argv[sys.argv.index("--frac") + 1]) if "--frac" in sys.argv else 0.4
TRAIN_END, VAL_START, TEST_START = "2025-03-31", "2025-03-10", "2025-04-01"
MAJORS = ["12:10", "15:10", "17:20"]
SEED = 7


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    tot = 0.0
    rows = []
    for b in range(bins):
        m = idx == b
        if m.sum() == 0:
            rows.append((b, 0, np.nan, np.nan)); continue
        tot += m.mean() * abs(y[m].mean() - p[m].mean())
        rows.append((b, int(m.sum()), float(p[m].mean()), float(y[m].mean())))
    return tot, rows


def metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    e, _ = ece(y, p)
    return {"n": int(len(y)), "pos_rate": float(y.mean()), "brier": float(brier_score_loss(y, p)),
            "auc": float(roc_auc_score(y, p)) if 0 < y.mean() < 1 else np.nan,
            "logloss": float(log_loss(y, p)), "ece": float(e)}


t0 = time.time()
panel = pd.read_parquet(NTU / "panel_10min.parquet")
stations = pd.read_csv(NTU / "ntu_stations.csv", dtype={"sno": str})
flows = pd.read_parquet(NTU / "flows_hourly.parquet")
X = build(panel, stations, NTU_BELLS, MAJORS, NTU_SEMESTERS, flows=flows, train_end=TRAIN_END)
X["campus"] = X.sno.map(dict(zip(stations.sno, stations.campus))).astype(np.int8)
print(f"features built: {X.shape} in {time.time() - t0:.0f}s; label rates y30={X.y30.mean():.3f} y60={X.y60.mean():.3f}")

train = X[X.date <= TRAIN_END]
test = X[X.date >= TEST_START]
val_mask = train.date >= VAL_START
rng = np.random.default_rng(SEED)
tr = train[~val_mask]
tr = tr.sample(frac=FRAC, random_state=SEED) if FRAC < 1 else tr
va = train[val_mask]
print(f"train rows {len(tr)} (frac {FRAC}), val {len(va)}, test {len(test)}; "
      f"train dates {train.date.min().date()}..{train.date.max().date()}, test {test.date.min().date()}..{test.date.max().date()}")

results, reliab, imps = [], [], []
subsets = {
    "all": lambda d: np.ones(len(d), bool),
    "campus": lambda d: d.campus.values == 1,
    "classend": lambda d: (d.offday.values == 0) & (d.since_major.values <= 40) & (d.campus.values == 1),
    "weekday_day": lambda d: (d.offday.values == 0) & (d.hour.values >= 8) & (d.hour.values < 20),
}
for h in (30, 60):
    y = f"y{h}"
    trh, vah, teh = tr.dropna(subset=[y]), va.dropna(subset=[y]), test.dropna(subset=[y])
    preds = {}
    # baselines
    preds["persistence"] = teh.empty_now.values.astype(float)
    key_tr = pd.Series(list(zip(trh.si, trh.offday, trh.slot)), index=trh.index)
    seas = trh[y].groupby(key_tr).mean()
    key_te = pd.Series(list(zip(teh.si, teh.offday, teh.slot)), index=teh.index)
    preds["seasonal"] = key_te.map(seas).fillna(trh[y].mean()).values
    # gradient boosting, two feature sets
    for name, feats in (("inv", INV_FEATS), ("full", FULL_FEATS + ["si"])):
        cat = ["si"] if "si" in feats else []
        params = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_data_in_leaf=200,
                      feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
                      num_threads=2, verbose=-1, seed=SEED)
        dtr = lgb.Dataset(trh[feats], trh[y], categorical_feature=cat, free_raw_data=False)
        dva = lgb.Dataset(vah[feats], vah[y], categorical_feature=cat, reference=dtr)
        t1 = time.time()
        bst = lgb.train(params, dtr, num_boost_round=2000, valid_sets=[dva],
                        callbacks=[lgb.early_stopping(50, verbose=False)])
        preds[f"lgb_{name}"] = bst.predict(teh[feats], num_iteration=bst.best_iteration)
        bst.save_model(str(OUT / f"lgb_{name}_{h}.txt"), num_iteration=bst.best_iteration)
        imp = pd.DataFrame({"feature": feats, "gain": bst.feature_importance("gain"), "set": name, "h": h})
        imps.append(imp)
        print(f"h={h} {name}: {bst.best_iteration} trees, {time.time() - t1:.0f}s")
    for model, p in preds.items():
        for sub, fn in subsets.items():
            m = fn(teh)
            if m.sum() < 1000:
                continue
            r = metrics(teh[y].values[m], np.asarray(p)[m])
            r.update({"h": h, "model": model, "subset": sub})
            results.append(r)
            print(f"h={h:>2} {model:<12} {sub:<12} n={r['n']:>8} pos={r['pos_rate']:.3f} brier={r['brier']:.4f} auc={r['auc']:.3f} ece={r['ece']:.4f}")
        _, rows = ece(teh[y].values, np.clip(np.asarray(p), 1e-6, 1 - 1e-6))
        reliab += [{"h": h, "model": model, "bin": b, "n": n, "p_mean": pm, "y_mean": ym} for b, n, pm, ym in rows]
    out = teh[["sno", "ts", "si", "campus", "offday", "slot", "bikes", "total", y]].copy()
    for model, p in preds.items():
        out[model] = np.asarray(p, dtype=np.float32)
    out.to_parquet(OUT / f"test_pred_{h}.parquet", index=False)

pd.DataFrame(results).to_csv(OUT / "metrics.csv", index=False)
pd.DataFrame(reliab).to_csv(OUT / "reliability.csv", index=False)
pd.concat(imps).to_csv(OUT / "importance.csv", index=False)
json.dump({"train_end": TRAIN_END, "val_start": VAL_START, "test_start": TEST_START, "frac": FRAC,
           "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(test)),
           "n_stations": int(X.si.nunique()), "n_days": int(X.date.nunique()),
           "features_inv": INV_FEATS, "features_full": FULL_FEATS + ["si"]}, open(OUT / "setup.json", "w"), indent=1)
print(f"done in {time.time() - t0:.0f}s")
