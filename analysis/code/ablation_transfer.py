"""Zero-shot NTU->NSYSU with and without bell features (uses models saved by ablation_bells.py)."""
import sys
from pathlib import Path
import lightgbm as lgb, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss
sys.path.insert(0, str(Path(__file__).parent))
from features import NSYSU_BELLS, NSYSU_SEMESTERS, INV_FEATS, BELL_FEATS, build
from nsysu_data import CAMPUS, GATEWAY, load_logger, load_stations
DATA, MODELS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
TEST_DAYS = ["2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"]
df = load_logger(DATA); st = load_stations(DATA)
st = st[st.logged == 1].rename(columns={"lat": "latitude", "lng": "longitude"}).reset_index(drop=True)
df["ts"] = pd.to_datetime(df.date) + pd.to_timedelta(df.slot * 10, unit="m")
grid = pd.date_range(df.ts.min().normalize(), df.ts.max().normalize() + pd.Timedelta(days=1), freq="10min", inclusive="left")
full = pd.MultiIndex.from_product([st.sno, grid], names=["sno", "ts"]).to_frame(index=False)
panel = full.merge(df[["sno", "ts", "bikes", "docks"]], on=["sno", "ts"], how="left")
panel["total"] = panel.sno.map(dict(zip(st.sno, st.capacity))).astype(float)
X = build(panel, st, NSYSU_BELLS, ["12:00", "16:00", "17:00"], NSYSU_SEMESTERS)
X = X[X.date.dt.strftime("%Y-%m-%d").isin(TEST_DAYS)]
X["area"] = X.sno.isin(list(CAMPUS) + list(GATEWAY)); X["campus"] = X.sno.isin(CAMPUS)
NOBELL = [f for f in INV_FEATS if f not in BELL_FEATS]
rows = []
for h in (30, 60):
    y = f"y{h}"; te = X.dropna(subset=[y] + INV_FEATS)
    for name, feats in (("with_bells", INV_FEATS), ("no_bells", NOBELL)):
        bst = lgb.Booster(model_file=str(MODELS / f"lgb_{name}_{h}.txt"))
        p = np.clip(bst.predict(te[feats]), 1e-6, 1 - 1e-6)
        for sub, m in (("all309", np.ones(len(te), bool)), ("area19", te.area.values), ("campus8", te.campus.values),
                       ("prebell_campus", te.campus.values & (te.offday.values == 0) & (te.to_major.values <= 30) & (te.bikes.values > 0))):
            yy = te[y].values[m]
            rows.append({"h": h, "model": name, "subset": sub, "n": int(m.sum()), "pos_rate": float(yy.mean()),
                         "auc": float(roc_auc_score(yy, p[m])), "brier": float(brier_score_loss(yy, p[m]))})
            print(rows[-1])
pd.DataFrame(rows).to_csv(OUT / "ablation_transfer.csv", index=False)
