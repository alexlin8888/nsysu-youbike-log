"""Checks on the operator-move inference and the censoring-corrected rates (NTU).

Usage: python validate_moves.py NTU_DIR OUT_DIR
Writes moves_sensitivity.csv (threshold x window grid), moves_checks.json, rate_validation.csv.

Checks
  1. bike conservation: per day, stock change = net trips + inferred moves + unexplained residual;
     the unexplained part (residuals in unflagged windows) should be small and unbiased.
  2. threshold / window sensitivity of the move flag (|window residual| >= T bikes, T in 3/5/8,
     windows 1 h / 3 h / 6 h): share flagged, bikes moved per day, timing before bells.
  3. 10-minute jumps: a truck visit shows up as a large jump between consecutive snapshots that trips
     cannot produce; flagged windows should contain such jumps far more often than unflagged ones.
  4. rates: on test-period station-hours that start with plenty of bikes (so demand is observed in
     full), actual rentals should match the corrected training-period rate, not the naive one.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from features import TW_HOLIDAYS  # noqa: E402

NTU = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
TRAIN_END, TEST_START = "2025-03-31", "2025-04-01"
h = pd.read_parquet(NTU / "hourly.parquet")
st = pd.read_csv(NTU / "ntu_stations.csv", dtype={"sno": str})
h = h.merge(st[["sno", "campus"]], on="sno")
h["date"] = h.hour.dt.normalize()
h["hod"] = h.hour.dt.hour
h["offday"] = ((h.hour.dt.dayofweek >= 5) | h.date.dt.strftime("%Y-%m-%d").isin(TW_HOLIDAYS)).astype(int)
ok = h.dropna(subset=["stock0", "stock1", "exposure"]).copy()     # same rows as ntu_demand.py
ndays = ok.date.nunique()
checks = {"station_hours": int(len(ok)), "days": int(ndays)}

# ---------------------------------------------------------------- 1. conservation
flag = ok.move == 1
ok["mv"] = np.where(flag, ok.resid, 0.0)
ok["noise"] = np.where(flag, 0.0, ok.resid)
daily = ok.groupby("date").agg(stock_change=("delta", "sum"), net_trips=("returns", "sum"), rentals=("rentals", "sum"),
                               mv=("mv", "sum"), noise=("noise", "sum"),
                               drop=("mv", lambda x: x[x > 0].sum()), pick=("mv", lambda x: -x[x < 0].sum()))
daily["net_trips"] = daily.net_trips - daily.rentals
checks["per_day"] = {k: round(float(daily[k].mean()), 1) for k in ("stock_change", "net_trips", "mv", "noise", "drop", "pick", "rentals")}
checks["noise_resid_mean"] = round(float(ok.loc[~flag, "resid"].mean()), 3)
checks["noise_resid_sd"] = round(float(ok.loc[~flag, "resid"].std()), 3)
checks["noise_abs_q90"] = round(float(ok.loc[~flag, "resid"].abs().quantile(0.9)), 2)
checks["noise_share_of_abs_resid"] = round(float(ok.noise.abs().sum() / ok.resid.abs().sum()), 3)
print("conservation per day:", checks["per_day"])

# ---------------------------------------------------------------- 2. threshold / window sensitivity
rows = []
for win_h in (1, 3, 6):
    w = ok.copy()
    w["win"] = w.hour.dt.floor(f"{win_h}h")
    wr = w.groupby(["sno", "win"]).resid.sum().rename("wres").reset_index()
    w = w.merge(wr, on=["sno", "win"], how="left")
    for T in (3, 5, 8):
        m = w.wres.abs() >= T
        mv = np.where(m, w.resid, 0.0)
        quiet = w[~m]
        r2q = 1 - ((quiet.delta - (quiet.returns - quiet.rentals)) ** 2).sum() / ((quiet.delta - quiet.delta.mean()) ** 2).sum()
        pred1 = w.stock0 + w.returns - w.rentals + mv
        r2r = 1 - ((w.stock1 - pred1) ** 2).sum() / ((w.stock1 - w.stock1.mean()) ** 2).sum()
        drop = np.where(mv > 0, mv, 0.0); pick = np.where(mv < 0, -mv, 0.0)
        camp = (w.campus == 1).values
        cd = pd.Series(drop[camp]).groupby(w.hod.values[camp]).sum()
        rows.append({"window_h": win_h, "threshold": T, "share_flagged": round(float(m.mean()), 3),
                     "drop_per_day": round(float(drop.sum() / ndays), 1), "pick_per_day": round(float(pick.sum() / ndays), 1),
                     "r2_quiet": round(float(r2q), 3), "r2_reproduce": round(float(r2r), 3),
                     "campus_drop_before_bells": round(float(cd.reindex([11, 16]).sum() / cd.sum()), 3),
                     "campus_drop_peak_hod": int(cd.idxmax())})
        print(rows[-1])
sens = pd.DataFrame(rows)
sens.to_csv(OUT / "moves_sensitivity.csv", index=False)

# ---------------------------------------------------------------- 3. ten-minute jumps
panel = pd.read_parquet(NTU / "panel_10min.parquet")
panel = panel[panel.sno.isin(st.sno)].sort_values(["sno", "ts"])
panel["jump"] = panel.groupby("sno").bikes.diff()
panel["win"] = panel.ts.dt.floor("3h")
J = 8
pj = panel.groupby(["sno", "win"]).agg(max_up=("jump", "max"), max_down=("jump", "min")).reset_index()
wk = ok.groupby(["sno", "win"]).agg(move=("move", "max"), wres=("win_resid", "first")).reset_index()
wk = wk.merge(pj, on=["sno", "win"], how="left")
up = wk.max_up >= J; down = wk.max_down <= -J
wk["jump_any"] = up | down
wk["jump_dir"] = np.where(wk.wres > 0, up, down)
checks["jump_threshold"] = J
checks["p_jump_given_flag"] = round(float(wk.loc[wk.move == 1, "jump_dir"].mean()), 3)
checks["p_jump_given_noflag"] = round(float(wk.loc[wk.move == 0, "jump_any"].mean()), 3)
checks["share_jump_windows_flagged"] = round(float(wk.loc[wk.jump_any, "move"].mean()), 3)
big = panel[panel.jump.abs() >= J]
checks["jump_bikes_per_day_up"] = round(float(big.jump[big.jump > 0].sum() / ndays), 1)
checks["jump_bikes_per_day_down"] = round(float(-big.jump[big.jump < 0].sum() / ndays), 1)
# the largest rental burst trips alone could produce in 10 minutes: max hourly rentals at any station / 6 is a bound
checks["max_hourly_rentals_any_station"] = int(ok.rentals.max())
print({k: checks[k] for k in checks if "jump" in k})

# ---------------------------------------------------------------- 4. rates
tr = ok[ok.date <= TRAIN_END]
cell = tr.groupby(["sno", "campus", "offday", "hod"]).agg(hours=("rentals", "size"), R=("rentals", "sum"), E=("exposure", "sum")).reset_index()
cell["lam_naive"] = cell.R / cell.hours
cell["lam_cens"] = cell.R / cell.E.replace(0, np.nan)
te = ok[(ok.date >= TEST_START) & (ok.offday == 0)].merge(cell[["sno", "offday", "hod", "lam_naive", "lam_cens"]], on=["sno", "offday", "hod"])
te["well_stocked"] = te.stock0 >= np.maximum(8, 0.5 * te.total)
ws = te[te.well_stocked & (te.campus == 1)]
rv = ws.groupby("hod").agg(n=("rentals", "size"), actual=("rentals", "mean"), naive=("lam_naive", "mean"), cens=("lam_cens", "mean"),
                           full_exposure=("exposure", lambda x: float(np.mean(x == 1)))).reset_index()
rv["ratio_naive"] = rv.actual / rv.naive
rv["ratio_cens"] = rv.actual / rv.cens
rv.to_csv(OUT / "rate_validation.csv", index=False)
day = rv[(rv.hod >= 8) & (rv.hod <= 21)]
checks["rate_check_rows"] = int(ws.shape[0])
checks["rate_ratio_naive_8_21"] = round(float(day.actual.sum() / day.naive.sum()), 3)
checks["rate_ratio_cens_8_21"] = round(float(day.actual.sum() / day.cens.sum()), 3)
for hh in (12, 17, 18):
    r = rv[rv.hod == hh].iloc[0]
    checks[f"rate_ratio_naive_{hh}"] = round(float(r.ratio_naive), 3)
    checks[f"rate_ratio_cens_{hh}"] = round(float(r.ratio_cens), 3)
print(rv.round(3).to_string())
json.dump(checks, open(OUT / "moves_checks.json", "w"), indent=1)
print(json.dumps(checks, indent=1))
