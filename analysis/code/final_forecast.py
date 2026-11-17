"""How good is the after-class forecast the demo page shows? A prospective check on days the rates never saw.

Usage: python final_forecast.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16]

The page tells a rider how many bikes a station is expected to hold 20 minutes after the next class end, and the
chance that it is empty or full then (demo_state.py: ChainValues.forecast with the rates of nsysu_rates.py).
RATES_DIR holds rates fitted on the logger up to --fit-end; every teaching weekday after it is a test day.
For each bell and each station, forecasts are made 10, 30 and 60 minutes before the bell from the logged stock
and compared with the logged stock 20 minutes after it.

Methods compared on the same rows:
  chain          the birth-death chain with hourly rates and, for the campus corridor, 10-minute rates (rates_slots.csv)
  chain_hourly   the same chain with hourly rates only (what the page ran before the 10-minute rates)
  persistence    the stock stays as it is now
  seasonal       that station's mean stock, or its share of empty / full snapshots, at the target time of day over the
                 teaching weekdays of the fitting period

Writes forecast_metrics.csv (subset, lead, method: MAE, RMSE, Brier and AUC for empty and for full),
forecast_ci.csv (paired differences in MAE with 95% intervals from a bootstrap over test days),
forecast_by_bell.csv (campus stations, forecast made 30 minutes before each bell), forecast_reliability.csv
(deciles of the chain's P(empty) and P(full) against what happened) and forecast_setup.json.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from features import NSYSU_BELLS  # noqa: E402
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP, ChainValues, load_slot_rates  # noqa: E402

DATA, RATES, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIT_END, TEST_END = ARG("--fit-end", "2026-10-29"), ARG("--test-end", "2026-11-16")
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}   # 23 Oct: every Kaohsiung station was closed, nothing to forecast
AFTER = 20                                 # minutes after the bell, as on the page
LEADS = [10, 30, 60]                       # minutes before the bell at which the forecast is made
BELLS = sorted(int(b[:2]) * 60 + int(b[3:]) for b in NSYSU_BELLS)
SEED = 5

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
group = np.where(st.sno.isin(CAMPUS), "campus", np.where(st.sno.isin(GATEWAY), "gateway", "other"))

rates = pd.read_csv(RATES / "rates.csv", dtype={"sno": str})
prior = pd.read_csv(RATES / "rates_prior.csv")
R = np.zeros((N, 24)); Qr = np.zeros((N, 24))
for row in prior[prior.offday == 0].itertuples():
    R[:, row.hod] = row.pr; Qr[:, row.hod] = row.pq
for row in rates[(rates.offday == 0) & rates.sno.isin(sidx)].itertuples():
    R[sidx[row.sno], row.hod] = row.lam_r; Qr[sidx[row.sno], row.hod] = row.lam_q
slot_rates = load_slot_rates(RATES / "rates_slots.csv", sidx)
chains = {"chain_hourly": ChainValues(R, Qr, CAP, 90, 20)}
if slot_rates is not None:
    chains["chain"] = ChainValues(R, Qr, CAP, 90, 20, slot_rates)
else:
    chains["chain"] = chains["chain_hourly"]

df = load_logger(DATA)
df = df[df.sno.isin(sidx) & (df.age <= 20)].copy()
df["i"] = df.sno.map(sidx)
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS)
fit_days = [d for d in days if "2026-10-02" <= d <= FIT_END]
test_days = [d for d in days if FIT_END < d <= TEST_END]


def panel(day):
    """bikes and free docks as (144, N) arrays, NaN where a station did not report."""
    d = df[dstr == day]
    b = np.full((144, N), np.nan); k = np.full((144, N), np.nan)
    b[d.slot.values, d.i.values] = d.bikes.values
    k[d.slot.values, d.i.values] = d.docks.values
    return b, k


# seasonal baselines from the fitting period
fit = np.stack([panel(d)[0] for d in fit_days]); fitk = np.stack([panel(d)[1] for d in fit_days])
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    seas_bikes = np.nanmean(fit, axis=0)
    seas_empty = np.nanmean(np.where(np.isnan(fit), np.nan, fit == 0), axis=0)
    seas_full = np.nanmean(np.where(np.isnan(fitk), np.nan, fitk == 0), axis=0)

rows = []
for day in test_days:
    b, k = panel(day)
    for bell in BELLS:
        at = bell + AFTER
        for lead in LEADS:
            t = ((bell - lead) // STEP) * STEP               # the snapshot the page would be showing
            steps = (at - t) // STEP                         # same rounding as demo_state.py
            s0, s1 = t // STEP, t // STEP + steps
            if t < 6 * 60 or s1 > 137:                       # the planner's window, 06:00-23:00
                continue
            ok = ~np.isnan(b[s0]) & ~np.isnan(b[s1]) & ~np.isnan(k[s1])
            if ok.sum() < 50:                                # the logger missed this snapshot
                continue
            now = np.where(ok, b[s0], 0).astype(int)
            f = {name: c.forecast(t, now, steps) for name, c in chains.items()}
            for i in np.flatnonzero(ok):
                rows.append((day, bell, lead, i, now[i], b[s1, i], k[s1, i], f["chain"][0][i], f["chain"][1][i], f["chain"][2][i],
                             f["chain_hourly"][0][i], f["chain_hourly"][1][i], f["chain_hourly"][2][i], seas_bikes[s1, i], seas_empty[s1, i], seas_full[s1, i]))
res = pd.DataFrame(rows, columns=["day", "bell", "lead", "i", "now", "bikes", "docks", "eb", "pe", "pf", "hb", "he", "hf", "sb", "se", "sf"])
res["group"] = group[res.i.values]
res["is_empty"] = (res.bikes == 0).astype(int); res["is_full"] = (res.docks == 0).astype(int)
res["cap"] = CAP[res.i.values]
for c in ("sb", "se", "sf"):
    res[c] = res[c].fillna(res[c].mean())
res["pb"] = res.now.astype(float); res["pe0"] = (res.now == 0).astype(float); res["pf0"] = (res.now >= res.cap).astype(float)
METHODS = {"chain": ("eb", "pe", "pf"), "chain_hourly": ("hb", "he", "hf"), "persistence": ("pb", "pe0", "pf0"), "seasonal": ("sb", "se", "sf")}
subsets = {"all309": res.group.notna(), "corridor19": res.group.isin(["campus", "gateway"]), "campus8": res.group == "campus"}


def auc(y, p):
    return float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else np.nan


out = []
for name, m in subsets.items():
    for lead in LEADS:
        r = res[m & (res.lead == lead)]
        if not len(r):
            continue
        for method, (cb, ce, cf) in METHODS.items():
            out.append({"subset": name, "lead_before_bell": lead, "method": method, "n": len(r), "bells": r.groupby(["day", "bell"]).ngroups,
                        "mae": float(np.abs(r[cb] - r.bikes).mean()), "rmse": float(np.sqrt(((r[cb] - r.bikes) ** 2).mean())),
                        "empty_rate": float(r.is_empty.mean()), "brier_empty": float(((r[ce] - r.is_empty) ** 2).mean()), "auc_empty": auc(r.is_empty, r[ce]),
                        "full_rate": float(r.is_full.mean()), "brier_full": float(((r[cf] - r.is_full) ** 2).mean()), "auc_full": auc(r.is_full, r[cf])})
met = pd.DataFrame(out)
met.to_csv(OUT / "forecast_metrics.csv", index=False)

# paired differences in MAE, bootstrap over test days (the same resampled days for every method)
rng = np.random.default_rng(SEED)
ci = []
for name, m in subsets.items():
    for lead in LEADS:
        r = res[m & (res.lead == lead)]
        per_day = {meth: r.assign(e=np.abs(r[cols[0]] - r.bikes)).groupby("day").e.agg(["sum", "size"]) for meth, cols in METHODS.items()}
        n_days = len(per_day["chain"])
        draws = rng.integers(0, n_days, size=(1000, n_days))
        mae = {meth: (v["sum"].values[draws].sum(1) / v["size"].values[draws].sum(1)) for meth, v in per_day.items()}
        point = {meth: v["sum"].sum() / v["size"].sum() for meth, v in per_day.items()}
        for other in ("chain_hourly", "persistence", "seasonal"):
            diff = mae["chain"] - mae[other]
            ci.append({"subset": name, "lead_before_bell": lead, "chain_minus": other, "diff_mae": float(point["chain"] - point[other]),
                       "lo": float(np.percentile(diff, 2.5)), "hi": float(np.percentile(diff, 97.5))})
ci = pd.DataFrame(ci)
ci.to_csv(OUT / "forecast_ci.csv", index=False)

# campus stations by bell, forecast made 30 minutes before it
x = res[(res.group == "campus") & (res.lead == 30)]
by = pd.DataFrame({bell: {"n": len(d), "mean_bikes": d.bikes.mean(), "mae_chain": np.abs(d.eb - d.bikes).mean(), "mae_chain_hourly": np.abs(d.hb - d.bikes).mean(),
                          "mae_seasonal": np.abs(d.sb - d.bikes).mean(), "mae_persistence": np.abs(d.pb - d.bikes).mean(),
                          "bias_chain": (d.eb - d.bikes).mean(), "bias_chain_hourly": (d.hb - d.bikes).mean()} for bell, d in x.groupby("bell")}).T
by.index = [f"{int(b) // 60:02d}:{int(b) % 60:02d}" for b in by.index]
by.to_csv(OUT / "forecast_by_bell.csv", index_label="bell")

# reliability of the chain's P(empty) and P(full), forecasts made 30 minutes before the bell
rel = []
for name, m in subsets.items():
    r = res[m & (res.lead == 30)]
    for ev, p, y in (("empty", r.pe, r.is_empty), ("full", r.pf, r.is_full)):
        bins = np.clip((p * 10).astype(int), 0, 9)
        for bno in range(10):
            mm = bins == bno
            if mm.sum():
                rel.append({"subset": name, "event": ev, "bin": bno, "n": int(mm.sum()), "p_mean": float(p[mm].mean()), "observed": float(y[mm].mean())})
        rel.append({"subset": name, "event": ev, "bin": -1, "n": len(r), "p_mean": float(p.mean()), "observed": float(y.mean()),
                    "ece": float(sum((bins == bno).mean() * abs(y[bins == bno].mean() - p[bins == bno].mean()) for bno in range(10) if (bins == bno).any()))})
pd.DataFrame(rel).to_csv(OUT / "forecast_reliability.csv", index=False)
res.to_parquet(OUT / "forecast_rows.parquet", index=False)
json.dump({"fit_days": fit_days, "test_days": test_days, "after_bell_min": AFTER, "leads_before_bell_min": LEADS, "bells": NSYSU_BELLS, "rows": len(res),
           "rates_dir": str(RATES), "slot_rates": slot_rates is not None, "slot_stations": 0 if slot_rates is None else int(len(slot_rates[0])), "offdays": sorted(OFFDAYS)},
          open(OUT / "forecast_setup.json", "w"), indent=1)
pd.set_option("display.width", 240)
print(f"fit days {len(fit_days)} ({fit_days[0]}..{fit_days[-1]}), test days {len(test_days)} ({test_days[0]}..{test_days[-1]}), rows {len(res)}, slot rates: {slot_rates is not None}")
print(met[met.lead_before_bell == 30].round(3).to_string(index=False))
print(ci[ci.lead_before_bell == 30].round(3).to_string(index=False))
print(by.round(2).to_string())
