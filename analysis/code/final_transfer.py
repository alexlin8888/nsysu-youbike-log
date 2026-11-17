"""How much local data does the NTU predictor need at NSYSU, and does the transfer hold up over time? (final report)

Usage: python final_transfer.py DATA_DIR NTU_MODEL_DIR OUT_DIR [--threads 1] [--boot 200]

The midterm compared zero-shot, fine-tuned and local-only models with six training days and six test days.
With six weeks logged this script answers the question the proposal asked ("how many weeks of local data"):
  test    3-16 Nov 2026 (14 days, never used for fitting)
  train   windows ending on 29 Oct and going back 1, 2, 3 or 4 weeks; 30-31 Oct are held out for early stopping
  models  the NTU inventory-only model as it is (zero-shot), the same model fine-tuned on the window, and a model
          trained on the window alone
It also scores the zero-shot model on every logging week since 2 Oct, to see whether its accuracy drifts.

Writes weeks_metrics.csv (h, model, weeks, subset: n, pos_rate, AUC, Brier, ECE), weeks_ci.csv (paired AUC
differences against zero-shot, 95% intervals from a bootstrap over test days), zero_shot_by_week.csv and
weeks_setup.json.
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
from nsysu_data import CAMPUS, GATEWAY, load_logger, load_stations  # noqa: E402

DATA, MODELS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
THREADS, BOOT = ARG("--threads", 1, int), ARG("--boot", 200, int)
MAJORS = ["12:00", "16:00", "17:00"]
TEST = pd.date_range("2026-11-03", "2026-11-16").strftime("%Y-%m-%d").tolist()
VAL = ["2026-10-30", "2026-10-31"]
TRAIN_END = "2026-10-29"
SEED = 7


def ece(y, p, bins=10):
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    return float(sum((idx == b).mean() * abs(y[idx == b].mean() - p[idx == b].mean()) for b in range(bins) if (idx == b).any()))


def metrics(y, p):
    return {"n": int(len(y)), "pos_rate": float(y.mean()), "auc": float(roc_auc_score(y, p)) if 0 < y.mean() < 1 else np.nan,
            "brier": float(brier_score_loss(y, p)), "ece": ece(y, np.clip(p, 0, 1))}


df = load_logger(DATA)
st = load_stations(DATA)
st = st[st.logged == 1].rename(columns={"lat": "latitude", "lng": "longitude"}).reset_index(drop=True)
df = df[df.date <= TEST[-1]]
df["ts"] = pd.to_datetime(df.date) + pd.to_timedelta(df.slot * 10, unit="m")
grid = pd.date_range(df.ts.min().normalize(), df.ts.max().normalize() + pd.Timedelta(days=1), freq="10min", inclusive="left")
full = pd.MultiIndex.from_product([st.sno, grid], names=["sno", "ts"]).to_frame(index=False)
panel = full.merge(df[["sno", "ts", "bikes", "docks"]], on=["sno", "ts"], how="left")
panel["total"] = panel.sno.map(dict(zip(st.sno, st.capacity))).astype(float)
X = build(panel, st, NSYSU_BELLS, MAJORS, NSYSU_SEMESTERS)
X["date_s"] = X.date.dt.strftime("%Y-%m-%d")
X["area"] = X.sno.isin(list(CAMPUS) + list(GATEWAY)).astype(np.int8)
X["campus"] = X.sno.isin(CAMPUS).astype(np.int8)
subsets = {"all309": lambda d: np.ones(len(d), bool), "corridor19": lambda d: d.area.values == 1, "campus8": lambda d: d.campus.values == 1}
params = dict(objective="binary", learning_rate=0.05, num_leaves=31, min_data_in_leaf=100, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, num_threads=THREADS, verbose=-1, seed=SEED)
rng = np.random.default_rng(SEED)
rows, cis, weekly = [], [], []
setup = {"test_days": TEST, "val_days": VAL, "train_end": TRAIN_END, "windows": {}}

for h in (30, 60):
    y = f"y{h}"
    D = X.dropna(subset=[y] + INV_FEATS)
    te, va = D[D.date_s.isin(TEST)], D[D.date_s.isin(VAL)]
    ntu = lgb.Booster(model_file=str(MODELS / f"lgb_inv_{h}.txt"))
    preds = {("zero_shot", 0): ntu.predict(te[INV_FEATS], num_threads=THREADS)}
    for k in (1, 2, 3, 4):
        first = (pd.Timestamp(TRAIN_END) - pd.Timedelta(days=7 * k - 1)).strftime("%Y-%m-%d")
        tr = D[(D.date_s >= first) & (D.date_s <= TRAIN_END)]
        setup["windows"][str(k)] = {"first": first, "last": TRAIN_END, "days_with_data": int(tr.date_s.nunique()), "rows": int(len(tr))}
        dtr = lgb.Dataset(tr[INV_FEATS], tr[y], free_raw_data=False)
        dva = lgb.Dataset(va[INV_FEATS], va[y], reference=dtr)
        ft = lgb.train({**params, "learning_rate": 0.02}, dtr, num_boost_round=600, valid_sets=[dva], init_model=ntu, callbacks=[lgb.early_stopping(50, verbose=False)])
        preds[("fine_tuned", k)] = ft.predict(te[INV_FEATS], num_iteration=ft.best_iteration, num_threads=THREADS)
        dtr2 = lgb.Dataset(tr[INV_FEATS], tr[y], free_raw_data=False)
        dva2 = lgb.Dataset(va[INV_FEATS], va[y], reference=dtr2)
        own = lgb.train(params, dtr2, num_boost_round=2000, valid_sets=[dva2], callbacks=[lgb.early_stopping(50, verbose=False)])
        preds[("local_only", k)] = own.predict(te[INV_FEATS], num_iteration=own.best_iteration, num_threads=THREADS)
        print(f"h={h} window {k} wk ({first}..{TRAIN_END}, {len(tr)} rows): fine-tune +{ft.best_iteration - ntu.num_trees()} trees, local-only {own.best_iteration} trees", flush=True)
    yv = te[y].values
    for (model, k), p in preds.items():
        for sub, fn in subsets.items():
            m = fn(te)
            r = metrics(yv[m], np.asarray(p)[m]); r.update({"h": h, "model": model, "weeks": k, "subset": sub}); rows.append(r)
    # paired AUC differences against zero-shot, bootstrap over test days
    day_idx = {d: np.flatnonzero(te.date_s.values == d) for d in sorted(te.date_s.unique())}
    dlist = list(day_idx)
    for sub in ("all309", "campus8"):
        m = subsets[sub](te)
        boots = {key: [] for key in preds}
        for _ in range(BOOT if h == 30 else 0):
            take = np.concatenate([day_idx[d] for d in rng.choice(dlist, len(dlist))])
            take = take[m[take]]
            for key, p in preds.items():
                boots[key].append(roc_auc_score(yv[take], np.asarray(p)[take]))
        if h == 30:
            z = np.array(boots[("zero_shot", 0)])
            for key, b in boots.items():
                b = np.array(b)
                cis.append({"h": h, "subset": sub, "model": key[0], "weeks": key[1], "auc_lo": float(np.percentile(b, 2.5)), "auc_hi": float(np.percentile(b, 97.5)),
                            "diff_vs_zero_shot_lo": float(np.percentile(b - z, 2.5)), "diff_vs_zero_shot_hi": float(np.percentile(b - z, 97.5))})
    # zero-shot by logging week (all days since 2 Oct)
    A = D[D.date_s >= "2026-10-02"]
    pa = ntu.predict(A[INV_FEATS], num_threads=THREADS)
    wk = np.asarray((A.date - pd.Timestamp("2026-09-07")).dt.days // 7 + 1)
    for w in sorted(set(wk)):
        for sub, fn in subsets.items():
            m = fn(A) & (wk == w)
            if m.sum() > 500 and 0 < A[y].values[m].mean() < 1:
                r = metrics(A[y].values[m], pa[m]); ds = pd.Series(np.asarray(A.date_s, dtype=object)[m])
                r.update({"h": h, "week": int(w), "subset": sub, "first_day": str(ds.min()), "days": int(ds.nunique())}); weekly.append(r)

met = pd.DataFrame(rows); met.to_csv(OUT / "weeks_metrics.csv", index=False)
pd.DataFrame(cis).to_csv(OUT / "weeks_ci.csv", index=False)
wkdf = pd.DataFrame(weekly); wkdf.to_csv(OUT / "zero_shot_by_week.csv", index=False)
json.dump(setup, open(OUT / "weeks_setup.json", "w"), indent=1)
pd.set_option("display.width", 220)
print(met[met.h == 30].pivot_table(index=["model", "weeks"], columns="subset", values=["auc", "brier", "ece"]).round(4).to_string())
print(pd.DataFrame(cis).round(4).to_string(index=False))
print(wkdf[(wkdf.h == 30)].pivot_table(index="week", columns="subset", values="auc").round(3).to_string())
