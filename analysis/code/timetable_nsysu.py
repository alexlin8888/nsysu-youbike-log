"""Does the course timetable help predict stockouts at NSYSU?

Usage: python timetable_nsysu.py LOGGER_DATA_DIR NTU_MODEL_DIR SESSIONS_CSV OUT_DIR

Leave-one-teaching-day-out comparison on the NSYSU logger panel (complete days 2-16 Oct 2026). For each of the
ten teaching days, models are trained on all other complete days (weekends and holidays included) and scored on
the held-out day. Every model also gets the station role (0 other, 1 gateway, 2 campus), so that the timetable
features are the only difference between paired sets. Feature sets (same LightGBM settings and trees for all):
  inv        the 22 inventory-only features (time, bell, state, neighbours; official NSYSU period ends) + role
  inv+tt     plus 5 timetable-intensity features from the course catalogue (timetable.intensity), set to zero
             outside the 19-station campus corridor (campus + gateway stations)
  ntu+inv    inv plus the NTU model's zero-shot probability as a feature
  ntu+inv+tt both
Reference: the NTU model zero-shot. Metrics: AUC and Brier per held-out day; paired day-level bootstrap for the
differences. Subsets: all 309 stations, the 8 campus stations, the 11 gateway stations, campus slots within 30 min
before a period end with at least 5 bikes on teaching days (well stocked before a bell: the case the bell features
could not predict at NTU), and gateway slots 07:00-10:00 on teaching days (morning arrivals).
Writes tt_metrics.csv, tt_daily.csv, tt_diff.csv, tt_importance.csv, tt_pred.parquet.
"""
import json
import os
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from features import INV_FEATS, NSYSU_BELLS, NSYSU_SEMESTERS, TW_HOLIDAYS, build  # noqa: E402
from nsysu_data import CAMPUS, GATEWAY, load_logger, load_stations  # noqa: E402
from timetable import intensity  # noqa: E402

DATA, MODELS, SESS, OUT = (Path(a) for a in sys.argv[1:5])
OUT.mkdir(parents=True, exist_ok=True)
MAJORS = ["12:00", "16:00", "17:00"]
TT = ["tt_out30", "tt_out60", "tt_outprev30", "tt_in30", "tt_now"]
COMPLETE = [f"2026-10-{d:02d}" for d in range(2, 17)]
TEACH = [d for d in COMPLETE if pd.Timestamp(d).dayofweek < 5 and d not in TW_HOLIDAYS]
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=31, min_data_in_leaf=100, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, num_threads=2, verbose=-1, seed=7)
ROUNDS = 250
B = 1000
if os.environ.get("TT_SMOKE"):                 # quick end-to-end check of the pipeline
    TEACH, ROUNDS, B = TEACH[:2], 10, 20
# TT_SPLIT=week: one fold instead of leave-one-day-out, training on 2-11 Oct and testing on the five teaching days
# of 12-16 Oct, so that every weekday has been seen exactly once before it is predicted
WEEK = os.environ.get("TT_SPLIT") == "week"
WEEK2 = [d for d in TEACH if d >= "2026-10-12"]
rng = np.random.default_rng(11)

# ---------------- panel and features (as transfer_nsysu.py) ----------------
df = load_logger(DATA)
st = load_stations(DATA)
st = st[st.logged == 1].rename(columns={"lat": "latitude", "lng": "longitude"}).reset_index(drop=True)
df["ts"] = pd.to_datetime(df.date) + pd.to_timedelta(df.slot * 10, unit="m")
grid = pd.date_range(df.ts.min().normalize(), df.ts.max().normalize() + pd.Timedelta(days=1), freq="10min", inclusive="left")
full = pd.MultiIndex.from_product([st.sno, grid], names=["sno", "ts"]).to_frame(index=False)
panel = full.merge(df[["sno", "ts", "bikes", "docks"]], on=["sno", "ts"], how="left")
panel["total"] = panel.sno.map(dict(zip(st.sno, st.capacity))).astype(float)
X = build(panel, st, NSYSU_BELLS, MAJORS, NSYSU_SEMESTERS, horizons=(30, 60))
X["date_s"] = X.date.dt.strftime("%Y-%m-%d")
X = X[X.date_s.isin(COMPLETE)].reset_index(drop=True)
X["campus"] = X.sno.isin(CAMPUS).astype(np.int8)
X["role"] = np.where(X.sno.isin(CAMPUS), 2, np.where(X.sno.isin(GATEWAY), 1, 0)).astype(np.int8)
holiday = X.date_s.isin(TW_HOLIDAYS).values
sess = pd.read_csv(SESS)
X[TT] = intensity(sess, X.ts, holiday).values * (X.role.values > 0)[:, None]
for h in (30, 60):
    ntu = lgb.Booster(model_file=str(MODELS / f"lgb_inv_{h}.txt"))
    X[f"p_ntu{h}"] = ntu.predict(X[INV_FEATS])
print(f"panel {X.shape}, teaching days {TEACH}")

subsets = {
    "all309": lambda d: np.ones(len(d), bool),
    "campus8": lambda d: d.campus.values == 1,
    "gateway11": lambda d: d.role.values == 1,
    "prebell_campus": lambda d: (d.campus.values == 1) & (d.to_bell.values <= 30) & (d.bikes.values >= 5) & (d.offday.values == 0),
    "morning_gateway": lambda d: (d.role.values == 1) & (d.ts.dt.hour.values >= 7) & (d.ts.dt.hour.values < 10) & (d.offday.values == 0),
}


def safe_auc(y, p):
    return roc_auc_score(y, p) if 0 < y.mean() < 1 else np.nan


rows, preds, imps = [], [], []
for h in (30, 60):
    y = f"y{h}"
    base = INV_FEATS + ["role"]
    sets = {"inv": base, "inv+tt": base + TT, "ntu+inv": base + [f"p_ntu{h}"], "ntu+inv+tt": base + [f"p_ntu{h}"] + TT}
    D = X.dropna(subset=[y] + INV_FEATS)
    for day in (["week2"] if WEEK else TEACH):
        if WEEK:
            tr, te = D[D.date_s <= "2026-10-11"], D[D.date_s.isin(WEEK2)]
        else:
            tr, te = D[D.date_s != day], D[D.date_s == day]
        out = te[["sno", "ts", "date_s", "campus", "role", "to_bell", "bikes", "offday", y]].copy()
        out["ntu_zero_shot"] = te[f"p_ntu{h}"].values
        for name, feats in sets.items():
            bst = lgb.train(PARAMS, lgb.Dataset(tr[feats], tr[y]), num_boost_round=ROUNDS)
            out[name] = bst.predict(te[feats])
            if name == "inv+tt":
                g = pd.Series(bst.feature_importance("gain"), index=feats)
                imps.append({"h": h, "day": day, **(g / g.sum()).to_dict()})
        out["h"] = h
        preds.append(out)
        print(f"h={h} {day}: test rows {len(te)}", flush=True)

P = pd.concat(preds, ignore_index=True)
P.to_parquet(OUT / "tt_pred.parquet", index=False)
MODELS_ = ["ntu_zero_shot", "inv", "inv+tt", "ntu+inv", "ntu+inv+tt"]
daily = []
for h in (30, 60):
    Ph = P[P.h == h]
    y = f"y{h}"
    for sub, fn in subsets.items():
        S = Ph[fn(Ph)]
        for m in MODELS_:
            yy, pp = S[y].values, np.clip(S[m].values, 1e-6, 1 - 1e-6)
            rows.append({"h": h, "subset": sub, "model": m, "n": len(S), "pos_rate": yy.mean(),
                         "auc": safe_auc(yy, pp), "brier": brier_score_loss(yy, pp)})
        for day, g in S.groupby("date_s"):
            for m in MODELS_:
                yy, pp = g[y].values, np.clip(g[m].values, 1e-6, 1 - 1e-6)
                daily.append({"h": h, "subset": sub, "day": day, "model": m, "n": len(g),
                              "auc": safe_auc(yy, pp), "brier": brier_score_loss(yy, pp)})
met = pd.DataFrame(rows); met.to_csv(OUT / "tt_metrics.csv", index=False)
dl = pd.DataFrame(daily); dl.to_csv(OUT / "tt_daily.csv", index=False)

# paired differences: pooled metric under day resampling (same draws for all models)
class WeightedAUC:
    """Pooled AUC under per-row weights, ties scored 1/2 (as in bootstrap_ci.py)."""

    def __init__(self, score, y):
        self.y = y.astype(float)
        _, self.g = np.unique(score, return_inverse=True)
        self.ng = self.g.max() + 1

    def __call__(self, w):
        wy = w * self.y
        wn = w - wy
        neg_g = np.bincount(self.g, weights=wn, minlength=self.ng)
        below = np.cumsum(neg_g) - neg_g
        return np.sum(wy * (below[self.g] + 0.5 * neg_g[self.g])) / (wy.sum() * wn.sum())


PAIRS = (("inv+tt", "inv"), ("ntu+inv+tt", "ntu+inv"), ("inv", "ntu_zero_shot"), ("inv+tt", "ntu_zero_shot"),
         ("ntu+inv", "ntu_zero_shot"))
diffs = []
for h in (30, 60):
    Ph = P[P.h == h]
    y = f"y{h}"
    for sub, fn in subsets.items():
        S = Ph[fn(Ph)].reset_index(drop=True)
        days, dinv = np.unique(S.date_s.values, return_inverse=True)
        nd = len(days)
        yv = S[y].values.astype(float)
        auc = {m: WeightedAUC(S[m].values, yv) for m in MODELS_}
        sq = {m: (np.clip(S[m].values, 1e-6, 1 - 1e-6) - yv) ** 2 for m in MODELS_}
        da = {m: [] for m in MODELS_}
        db = {m: [] for m in MODELS_}
        for _ in range(B):
            w = np.bincount(rng.integers(0, nd, nd), minlength=nd).astype(float)[dinv]
            if (w * yv).sum() == 0 or (w * (1 - yv)).sum() == 0:
                continue
            for m in MODELS_:
                da[m].append(auc[m](w))
                db[m].append(np.sum(w * sq[m]) / w.sum())
        da = {m: np.array(v) for m, v in da.items()}
        db = {m: np.array(v) for m, v in db.items()}
        one = np.ones(len(S))
        for a, b in PAIRS:
            ga, gb = dl[(dl.h == h) & (dl.subset == sub) & (dl.model == a)].set_index("day").auc, \
                dl[(dl.h == h) & (dl.subset == sub) & (dl.model == b)].set_index("day").auc
            diffs.append({"h": h, "subset": sub, "a": a, "b": b, "days": nd, "n": len(S), "pos_rate": yv.mean(),
                          "auc_a": auc[a](one), "auc_b": auc[b](one), "d_auc": auc[a](one) - auc[b](one),
                          "d_auc_lo": np.percentile(da[a] - da[b], 2.5), "d_auc_hi": np.percentile(da[a] - da[b], 97.5),
                          "d_brier": sq[a].mean() - sq[b].mean(),
                          "d_brier_lo": np.percentile(db[a] - db[b], 2.5), "d_brier_hi": np.percentile(db[a] - db[b], 97.5),
                          "days_a_better_auc": int((ga > gb).sum()), "days_compared": int((ga.notna() & gb.notna()).sum())})
        print(f"bootstrap h={h} {sub} done", flush=True)
df_ = pd.DataFrame(diffs); df_.to_csv(OUT / "tt_diff.csv", index=False)
pd.DataFrame(imps).to_csv(OUT / "tt_importance.csv", index=False)
pd.set_option("display.width", 200)
print(met.pivot_table(index=["h", "subset"], columns="model", values="auc").round(3).to_string())
print(met.pivot_table(index=["h", "subset"], columns="model", values="brier").round(4).to_string())
print(df_.round(4).to_string())
imp = pd.DataFrame(imps)
print("mean gain share of timetable features (inv+tt):", imp.groupby("h")[TT].mean().sum(axis=1).round(3).to_dict())
