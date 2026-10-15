"""Ablation: does the class timetable help? Train the inventory-only model with and without the bell
features and compare on the rows where anticipation matters (weekday campus rows 0-30 min before a bell).

Usage: python ablation_bells.py NTU_DIR OUT_DIR
"""
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss

sys.path.insert(0, str(Path(__file__).parent))
from features import NTU_BELLS, NTU_SEMESTERS, INV_FEATS, BELL_FEATS, build  # noqa: E402

NTU = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
TRAIN_END, VAL_START, TEST_START = "2025-03-31", "2025-03-10", "2025-04-01"
MAJORS = ["12:10", "15:10", "17:20"]
SEED = 7
panel = pd.read_parquet(NTU / "panel_10min.parquet")
stations = pd.read_csv(NTU / "ntu_stations.csv", dtype={"sno": str})
X = build(panel, stations, NTU_BELLS, MAJORS, NTU_SEMESTERS)
X["campus"] = X.sno.map(dict(zip(stations.sno, stations.campus))).astype(np.int8)
train = X[X.date <= TRAIN_END]; test = X[X.date >= TEST_START]
tr = train[train.date < VAL_START].sample(frac=0.4, random_state=SEED); va = train[train.date >= VAL_START]
params = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_data_in_leaf=200, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, num_threads=2, verbose=-1, seed=SEED)
NOBELL = [f for f in INV_FEATS if f not in BELL_FEATS]
subsets = {
    "all": lambda d: np.ones(len(d), bool),
    "campus_weekday": lambda d: (d.campus.values == 1) & (d.offday.values == 0),
    "prebell_campus": lambda d: (d.campus.values == 1) & (d.offday.values == 0) & (d.to_major.values <= 30) & (d.bikes.values > 0),
    "prebell_campus_stocked": lambda d: (d.campus.values == 1) & (d.offday.values == 0) & (d.to_major.values <= 30) & (d.fill.values >= 0.3),
}
rows = []
for h in (30, 60):
    y = f"y{h}"
    trh, vah, teh = tr.dropna(subset=[y]), va.dropna(subset=[y]), test.dropna(subset=[y])
    for name, feats in (("with_bells", INV_FEATS), ("no_bells", NOBELL)):
        dtr = lgb.Dataset(trh[feats], trh[y], free_raw_data=False); dva = lgb.Dataset(vah[feats], vah[y], reference=dtr)
        bst = lgb.train(params, dtr, 2000, valid_sets=[dva], callbacks=[lgb.early_stopping(50, verbose=False)])
        p = bst.predict(teh[feats], num_iteration=bst.best_iteration)
        bst.save_model(str(OUT / f"lgb_{name}_{h}.txt"), num_iteration=bst.best_iteration)
        for sub, fn in subsets.items():
            m = fn(teh)
            yy, pp = teh[y].values[m], np.clip(p[m], 1e-6, 1 - 1e-6)
            rows.append({"h": h, "model": name, "subset": sub, "n": int(m.sum()), "pos_rate": float(yy.mean()),
                         "auc": float(roc_auc_score(yy, pp)), "brier": float(brier_score_loss(yy, pp))})
            print(rows[-1])
pd.DataFrame(rows).to_csv(OUT / "ablation_bells.csv", index=False)
