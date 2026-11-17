"""Fine-tune the NTU inventory-only stockout predictor on NSYSU data, for the live page.

Usage: python nsysu_finetune.py DATA_DIR NTU_MODEL_DIR OUT_DIR [--val-days 3] [--threads 2]

final_transfer.py showed that the zero-shot NTU model ranks stockouts at NSYSU as well as a local model but is less
well calibrated (ECE 0.028 against 0.003 after one week of local data). This script makes the model the page uses:
it continues boosting lgb_inv_30.txt and lgb_inv_60.txt at learning rate 0.02 on every logged day except the last
--val-days, which stop the boosting early. Writes lgb_inv_30_nsysu.txt, lgb_inv_60_nsysu.txt and finetune_setup.json
(zero-shot against fine-tuned on the validation days). demo_state.py uses the fine-tuned files when they exist.
"""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from features import INV_FEATS, NSYSU_BELLS, NSYSU_SEMESTERS, build  # noqa: E402
from nsysu_data import load_logger, load_stations  # noqa: E402

DATA, MODELS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
VAL_DAYS, THREADS = ARG("--val-days", 3, int), ARG("--threads", 2, int)
MAJORS = ["12:00", "16:00", "17:00"]


def ece(y, p, bins=10):
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    return float(sum((idx == b).mean() * abs(y[idx == b].mean() - p[idx == b].mean()) for b in range(bins) if (idx == b).any()))


df = load_logger(DATA)
st = load_stations(DATA)
st = st[st.logged == 1].rename(columns={"lat": "latitude", "lng": "longitude"}).reset_index(drop=True)
df = df[df.date != "2026-10-23"]                                     # every station was closed that day
df["ts"] = pd.to_datetime(df.date) + pd.to_timedelta(df.slot * 10, unit="m")
grid = pd.date_range(df.ts.min().normalize(), df.ts.max().normalize() + pd.Timedelta(days=1), freq="10min", inclusive="left")
full = pd.MultiIndex.from_product([st.sno, grid], names=["sno", "ts"]).to_frame(index=False)
panel = full.merge(df[["sno", "ts", "bikes", "docks"]], on=["sno", "ts"], how="left")
panel["total"] = panel.sno.map(dict(zip(st.sno, st.capacity))).astype(float)
X = build(panel, st, NSYSU_BELLS, MAJORS, NSYSU_SEMESTERS)
X["date_s"] = X.date.dt.strftime("%Y-%m-%d")
days = sorted(X.dropna(subset=["y30"] + INV_FEATS).date_s.unique())
val_days = days[-VAL_DAYS:]
setup = {"train_days": [days[0], days[-VAL_DAYS - 1]], "val_days": val_days, "learning_rate": 0.02}
params = dict(objective="binary", learning_rate=0.02, num_leaves=31, min_data_in_leaf=100, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
              lambda_l2=1.0, num_threads=THREADS, verbose=-1, seed=7)
for h in (30, 60):
    y = f"y{h}"
    D = X.dropna(subset=[y] + INV_FEATS)
    tr, va = D[~D.date_s.isin(val_days)], D[D.date_s.isin(val_days)]
    ntu = lgb.Booster(model_file=str(MODELS / f"lgb_inv_{h}.txt"))
    dtr = lgb.Dataset(tr[INV_FEATS], tr[y], free_raw_data=False)
    ft = lgb.train(params, dtr, num_boost_round=800, valid_sets=[lgb.Dataset(va[INV_FEATS], va[y], reference=dtr)], init_model=ntu,
                   callbacks=[lgb.early_stopping(50, verbose=False)])
    ft.save_model(str(OUT / f"lgb_inv_{h}_nsysu.txt"), num_iteration=ft.best_iteration)
    yv = va[y].values
    p0 = ntu.predict(va[INV_FEATS], num_threads=THREADS); p1 = ft.predict(va[INV_FEATS], num_iteration=ft.best_iteration, num_threads=THREADS)
    setup[f"h{h}"] = {"rows_train": int(len(tr)), "rows_val": int(len(va)), "trees_added": int(ft.best_iteration - ntu.num_trees()),
                      "zero_shot": {"auc": float(roc_auc_score(yv, p0)), "brier": float(brier_score_loss(yv, p0)), "ece": ece(yv, p0)},
                      "fine_tuned": {"auc": float(roc_auc_score(yv, p1)), "brier": float(brier_score_loss(yv, p1)), "ece": ece(yv, p1)}}
    print(h, json.dumps(setup[f"h{h}"]), flush=True)
json.dump(setup, open(OUT / "finetune_setup.json", "w"), indent=1)
