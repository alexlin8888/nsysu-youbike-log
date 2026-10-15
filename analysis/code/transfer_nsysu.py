"""NTU -> NSYSU transfer experiment for the inventory-only stockout predictor.

Usage: python transfer_nsysu.py LOGGER_DATA_DIR NTU_MODEL_DIR OUT_DIR
Builds the NSYSU 10-minute panel from the logger, computes the same inventory/time features as for NTU,
then compares: persistence, NSYSU seasonal baseline, NTU model zero-shot, NTU model fine-tuned on NSYSU
training days, and an NSYSU-only model. Writes transfer_metrics.csv, transfer_reliability.csv, setup json.
"""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss

sys.path.insert(0, str(Path(__file__).parent))
from features import NSYSU_BELLS, NSYSU_SEMESTERS, INV_FEATS, build  # noqa: E402
from nsysu_data import CAMPUS, GATEWAY, load_logger, load_stations  # noqa: E402

DATA = Path(sys.argv[1]); MODELS = Path(sys.argv[2]); OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
TRAIN_DAYS = ["2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07"]
VAL_DAYS = ["2026-10-08", "2026-10-09"]
TEST_DAYS = ["2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"]
MAJORS = ["12:00", "16:00", "17:00"]
SEED = 7


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    tot, rows = 0.0, []
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


# ---------- NSYSU panel on a complete 10-minute grid ----------
df = load_logger(DATA)
st = load_stations(DATA)
st = st[st.logged == 1].rename(columns={"lat": "latitude", "lng": "longitude"}).reset_index(drop=True)
df["ts"] = pd.to_datetime(df.date) + pd.to_timedelta(df.slot * 10, unit="m")
grid = pd.date_range(df.ts.min().normalize(), df.ts.max().normalize() + pd.Timedelta(days=1), freq="10min", inclusive="left")
full = pd.MultiIndex.from_product([st.sno, grid], names=["sno", "ts"]).to_frame(index=False)
panel = full.merge(df[["sno", "ts", "bikes", "docks"]], on=["sno", "ts"], how="left")
panel["total"] = panel.sno.map(dict(zip(st.sno, st.capacity))).astype(float)
X = build(panel, st, NSYSU_BELLS, MAJORS, NSYSU_SEMESTERS)
X["date_s"] = X.date.dt.strftime("%Y-%m-%d")
X["area"] = X.sno.isin(list(CAMPUS) + list(GATEWAY)).astype(np.int8)
X["campus"] = X.sno.isin(CAMPUS).astype(np.int8)
print(f"NSYSU features: {X.shape}; y30 rate {X.y30.mean():.3f}, y60 rate {X.y60.mean():.3f}")

tr = X[X.date_s.isin(TRAIN_DAYS)]
va = X[X.date_s.isin(VAL_DAYS)]
te = X[X.date_s.isin(TEST_DAYS)]
subsets = {
    "all309": lambda d: np.ones(len(d), bool),
    "area19": lambda d: d.area.values == 1,
    "campus8": lambda d: d.campus.values == 1,
    "classend_campus": lambda d: (d.offday.values == 0) & (d.since_major.values <= 40) & (d.campus.values == 1),
}
params = dict(objective="binary", learning_rate=0.05, num_leaves=31, min_data_in_leaf=100, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, num_threads=2, verbose=-1, seed=SEED)
results, reliab = [], []
for h in (30, 60):
    y = f"y{h}"
    trh, vah, teh = tr.dropna(subset=[y] + INV_FEATS), va.dropna(subset=[y] + INV_FEATS), te.dropna(subset=[y] + INV_FEATS)
    preds = {"persistence": teh.empty_now.values.astype(float)}
    key_tr = pd.Series(list(zip(trh.si, trh.offday, trh.slot)), index=trh.index)
    seas = trh[y].groupby(key_tr).mean()
    key_te = pd.Series(list(zip(teh.si, teh.offday, teh.slot)), index=teh.index)
    preds["seasonal_nsysu"] = key_te.map(seas).fillna(trh[y].mean()).values
    ntu = lgb.Booster(model_file=str(MODELS / f"lgb_inv_{h}.txt"))
    preds["ntu_zero_shot"] = ntu.predict(teh[INV_FEATS])
    dtr = lgb.Dataset(trh[INV_FEATS], trh[y], free_raw_data=False)
    dva = lgb.Dataset(vah[INV_FEATS], vah[y], reference=dtr)
    ft = lgb.train({**params, "learning_rate": 0.02}, dtr, num_boost_round=600, valid_sets=[dva], init_model=ntu,
                   callbacks=[lgb.early_stopping(50, verbose=False)])
    preds["ntu_finetuned"] = ft.predict(teh[INV_FEATS], num_iteration=ft.best_iteration)
    dtr2 = lgb.Dataset(trh[INV_FEATS], trh[y], free_raw_data=False)
    dva2 = lgb.Dataset(vah[INV_FEATS], vah[y], reference=dtr2)
    own = lgb.train(params, dtr2, num_boost_round=2000, valid_sets=[dva2], callbacks=[lgb.early_stopping(50, verbose=False)])
    preds["nsysu_only"] = own.predict(teh[INV_FEATS], num_iteration=own.best_iteration)
    print(f"h={h}: fine-tune added {ft.best_iteration - ntu.num_trees()} trees; nsysu-only {own.best_iteration} trees")
    ft.save_model(str(OUT / f"lgb_inv_{h}_finetuned_nsysu.txt"), num_iteration=ft.best_iteration)
    for model, p in preds.items():
        for sub, fn in subsets.items():
            m = fn(teh)
            if m.sum() < 300:
                continue
            r = metrics(teh[y].values[m], np.asarray(p)[m]); r.update({"h": h, "model": model, "subset": sub})
            results.append(r)
            print(f"h={h:>2} {model:<15} {sub:<16} n={r['n']:>7} pos={r['pos_rate']:.3f} brier={r['brier']:.4f} auc={r['auc']:.3f} ece={r['ece']:.4f}")
        m = subsets["area19"](teh)
        _, rows = ece(teh[y].values[m], np.clip(np.asarray(p)[m], 1e-6, 1 - 1e-6))
        reliab += [{"h": h, "model": model, "bin": b, "n": n, "p_mean": pm, "y_mean": ym} for b, n, pm, ym in rows]
    out = teh[["sno", "ts", "area", "campus", "offday", "slot", "bikes", "total", y]].copy()
    for model, p in preds.items():
        out[model] = np.asarray(p, dtype=np.float32)
    out.to_parquet(OUT / f"nsysu_test_pred_{h}.parquet", index=False)

pd.DataFrame(results).to_csv(OUT / "transfer_metrics.csv", index=False)
pd.DataFrame(reliab).to_csv(OUT / "transfer_reliability.csv", index=False)
json.dump({"train_days": TRAIN_DAYS, "val_days": VAL_DAYS, "test_days": TEST_DAYS, "n_train": int(len(tr)),
           "n_val": int(len(va)), "n_test": int(len(te)), "stations": int(X.si.nunique()), "features": INV_FEATS},
          open(OUT / "transfer_setup.json", "w"), indent=1)
print("done")
