"""Demand reconstruction and operator-move inference on the NTU hourly table.

Usage: python ntu_demand.py NTU_DIR OUT_DIR
Writes rates.csv (station x offday x hour: naive and censoring-corrected rental rates), moves_profile.csv,
demand_summary.json and figures fig_ntu_moves.png, fig_ntu_censoring.png.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from features import TW_HOLIDAYS  # noqa: E402

NTU = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
h = pd.read_parquet(NTU / "hourly.parquet")
st = pd.read_csv(NTU / "ntu_stations.csv", dtype={"sno": str})
h = h.merge(st[["sno", "campus", "name"]], on="sno")
h["date"] = h.hour.dt.normalize()
h["hod"] = h.hour.dt.hour
h["offday"] = ((h.hour.dt.dayofweek >= 5) | h.date.dt.strftime("%Y-%m-%d").isin(TW_HOLIDAYS)).astype(int)
ok = h.dropna(subset=["stock0", "stock1", "exposure"])
sem = ok[(ok.date >= "2025-02-17") & (ok.date <= "2025-06-13")]   # spring semester, best snapshot coverage
print(f"usable station-hours: {len(ok)} (spring semester {len(sem)})")

# ---------- censoring-corrected rental rates ----------
grp = sem.groupby(["sno", "campus", "offday", "hod"])
rates = grp.agg(hours=("rentals", "size"), rentals=("rentals", "sum"), exposure=("exposure", "sum"),
                empty_share=("exposure", lambda x: float(np.mean(x < 1)))).reset_index()
rates["lam_naive"] = rates.rentals / rates.hours
rates["lam_cens"] = rates.rentals / rates.exposure.replace(0, np.nan)
rates["correction"] = rates.lam_cens / rates.lam_naive.replace(0, np.nan)
rates.to_csv(OUT / "rates.csv", index=False)
camp_wd = rates[(rates.campus == 1) & (rates.offday == 0)]
prof = camp_wd.groupby("hod").agg(lam_naive=("lam_naive", "mean"), lam_cens=("lam_cens", "mean"),
                                   exposure=("exposure", "sum"), hours=("hours", "sum")).reset_index()
prof["correction"] = prof.lam_cens / prof.lam_naive
prof.to_csv(OUT / "censoring_profile.csv", index=False)

# ---------- operator moves ----------
mv = ok.copy()
mv["drop"] = np.where((mv.move == 1) & (mv.resid > 0), mv.resid, 0.0)
mv["pick"] = np.where((mv.move == 1) & (mv.resid < 0), -mv.resid, 0.0)
ndays = mv.date.nunique()
prof_mv = mv.groupby(["campus", "hod"]).agg(drop=("drop", "sum"), pick=("pick", "sum")).reset_index()
prof_mv["drop_per_day"] = prof_mv["drop"] / ndays
prof_mv["pick_per_day"] = prof_mv["pick"] / ndays
prof_mv.to_csv(OUT / "moves_profile.csv", index=False)
daily = mv.groupby("date").agg(drop=("drop", "sum"), pick=("pick", "sum"), rentals=("rentals", "sum"))
quiet = ok[ok.move == 0]
ss_res = ((quiet.delta - (quiet.returns - quiet.rentals)) ** 2).sum()
ss_tot = ((quiet.delta - quiet.delta.mean()) ** 2).sum()
r2_quiet = 1 - ss_res / ss_tot
# how well the inferred moves explain inventory: reproduce stock1 from stock0 + flows + inferred move
rep = ok.copy()
rep["pred1"] = rep.stock0 + rep.returns - rep.rentals + np.where(rep.move == 1, rep.resid, 0.0)
r2_rep = 1 - ((rep.stock1 - rep.pred1) ** 2).sum() / ((rep.stock1 - rep.stock1.mean()) ** 2).sum()
r2_noop = 1 - ((rep.stock1 - (rep.stock0 + rep.returns - rep.rentals)) ** 2).sum() / ((rep.stock1 - rep.stock1.mean()) ** 2).sum()

summary = {
    "station_hours": int(len(ok)), "days": int(ndays), "stations": int(ok.sno.nunique()),
    "move_station_hours_share": round(float(ok.move.mean()), 4),
    "truck_dropoff_per_day": round(float(daily["drop"].mean()), 1), "truck_pickup_per_day": round(float(daily["pick"].mean()), 1),
    "rentals_per_day": round(float(daily.rentals.mean()), 1),
    "truck_share_of_rentals": round(float(daily["drop"].mean() / daily.rentals.mean()), 3),
    "r2_quiet_hours": round(float(r2_quiet), 3), "r2_reproduce_with_moves": round(float(r2_rep), 3),
    "r2_reproduce_without_moves": round(float(r2_noop), 3),
    "campus_wd_correction_12": round(float(prof.loc[prof.hod == 12, "correction"].iloc[0]), 3),
    "campus_wd_correction_17": round(float(prof.loc[prof.hod == 17, "correction"].iloc[0]), 3),
    "campus_wd_correction_18": round(float(prof.loc[prof.hod == 18, "correction"].iloc[0]), 3),
    "campus_wd_correction_max": round(float(prof.correction.max()), 3),
    "campus_wd_correction_max_hod": int(prof.loc[prof.correction.idxmax(), "hod"]),
    "campus_wd_empty_share_1718": round(float(camp_wd[camp_wd.hod.isin([17, 18])].empty_share.mean()), 3),
    "campus_dropoff_share_before_bells": None,
}
# share of campus drop-offs that happen in the hour before 12:10 / 17:20 (pre-emptive) vs after
c = prof_mv[prof_mv.campus == 1].set_index("hod")
summary["campus_dropoff_share_before_bells"] = round(float(c.loc[[11, 16], "drop"].sum() / c["drop"].sum()), 3)
summary["campus_dropoff_peak_hod"] = int(c["drop"].idxmax())
summary["campus_pickup_peak_hod"] = int(c["pick"].idxmax())
json.dump(summary, open(OUT / "demand_summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1))

# ---------- figure: operator moves by hour ----------
fig, ax = plt.subplots(figsize=(W, 1.5))
fig.subplots_adjust(left=0.13, right=0.98, top=0.86, bottom=0.2)
hod = np.arange(24)
for campus, col, lab in ((1, BLUE, "campus"), (0, ORANGE, "ring")):
    c = prof_mv[prof_mv.campus == campus].set_index("hod").reindex(hod).fillna(0)
    off = -0.2 if campus == 1 else 0.2
    ax.bar(hod + off, c.drop_per_day, width=0.38, color=col, lw=0, label=f"{lab}: drop-off")
    ax.bar(hod + off, -c.pick_per_day, width=0.38, color=col, alpha=0.45, lw=0, label=f"{lab}: pick-up")
ax.axhline(0, color=MUTED, lw=0.5)
for xb in (12.17, 17.33):
    ax.axvline(xb, color=INK2, lw=0.6, ls=(0, (3, 2)))
ax.set_xticks(range(0, 24, 3)); ax.set_xticklabels([f"{x:02d}" for x in range(0, 24, 3)])
ax.set_xlabel("hour of day", fontsize=6, labelpad=1); ax.set_ylabel("bikes / day", fontsize=6, labelpad=1)
ax.legend(ncol=2, fontsize=5.2, loc="upper left", handlelength=1.2, columnspacing=1, borderaxespad=0.1)
ax.set_title(f"Inferred truck moves, {summary['stations']} NTU-area stations, {ndays} days", fontsize=6.4, loc="left", pad=2)
grid(ax)
fig.savefig(OUT / "fig_ntu_moves.png")

# ---------- figure: censoring correction ----------
fig, ax = plt.subplots(figsize=(W * 0.62, 1.35))
fig.subplots_adjust(left=0.2, right=0.97, top=0.9, bottom=0.21)
ax.plot(prof.hod, prof.lam_naive, color=MUTED, lw=1.3, label="observed rentals / h")
ax.plot(prof.hod, prof.lam_cens, color=BLUE, lw=1.5, label="censoring-corrected rate")
ax.fill_between(prof.hod, prof.lam_naive, prof.lam_cens, color=SEQ[2], lw=0)
ax.set_xticks(range(6, 24, 3)); ax.set_xlim(6, 23)
ax.set_xlabel("hour of day (weekdays)", fontsize=6, labelpad=1)
ax.set_ylabel("rentals per station-hour", fontsize=5.8, labelpad=1)
ax.legend(fontsize=5.2, loc="upper left", handlelength=1.4, borderaxespad=0.2)
grid(ax)
fig.savefig(OUT / "fig_ntu_censoring.png")
print("figures written")
