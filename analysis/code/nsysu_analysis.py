"""Quantify class-end stockouts around NSYSU from the logger panel.

Outputs (in OUT): nsysu_profile.csv, nsysu_stations.csv, nsysu_bells.csv, nsysu_episodes.csv,
nsysu_summary.json and the figures fig_nsysu_tide.png / fig_nsysu_bells.png.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from nsysu_data import CAMPUS, GATEWAY, load_logger, load_stations  # noqa: E402

DATA = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out")
OUT.mkdir(parents=True, exist_ok=True)
FIRST, LAST = "2026-10-02", "2026-10-14"          # complete days only
KRT = ["501209026", "501209023"]

df = load_logger(DATA)
st = load_stations(DATA).set_index("sno")
full = df[df.date.between(FIRST, LAST)]
wk, we = full[full.weekday], full[~full.weekday]
weekdays = sorted(wk.date.unique())


def total_by_slot(d, snos):
    x = d[d.sno.isin(snos)].groupby(["date", "slot"]).bikes.sum().unstack(0)
    return x.mean(axis=1), x.quantile(0.25, axis=1), x.quantile(0.75, axis=1)


def empty_share_by_slot(d, snos):
    x = d[d.sno.isin(snos)].assign(e=lambda z: z.bikes == 0).groupby(["date", "slot"]).e.mean().unstack(0)
    return x.mean(axis=1)


# ---------- daily profile ----------
prof = pd.DataFrame(index=range(144))
prof["t"] = [f"{s // 6:02d}:{(s % 6) * 10:02d}" for s in prof.index]
for name, snos, d in [("campus_wk", CAMPUS, wk), ("krt_wk", KRT, wk), ("campus_we", CAMPUS, we), ("krt_we", KRT, we)]:
    m, lo, hi = total_by_slot(d, snos)
    prof[name], prof[name + "_p25"], prof[name + "_p75"] = m, lo, hi
    prof[name + "_empty"] = empty_share_by_slot(d, snos)
prof.to_csv(OUT / "nsysu_profile.csv", index=False)

# ---------- per-station table ----------
rows = []
for sno in list(CAMPUS) + list(GATEWAY):
    d = wk[wk.sno == sno]
    am = d[(d.slot >= 48) & (d.slot < 66)]      # 08:00-11:00
    pm = d[(d.slot >= 102) & (d.slot < 120)]    # 17:00-20:00
    day = d[(d.slot >= 48) & (d.slot < 132)]    # 08:00-22:00
    rows.append({
        "sno": sno, "name": st.loc[sno, "short"], "group": st.loc[sno, "group"], "capacity": int(st.loc[sno, "capacity"]),
        "dist_m": int(st.loc[sno, "dist_m"]),
        "bikes_10": d[d.slot == 60].bikes.mean(), "bikes_18": d[d.slot == 108].bikes.mean(),
        "empty_am": (am.bikes == 0).mean(), "full_am": (am.docks == 0).mean(),
        "empty_pm": (pm.bikes == 0).mean(), "full_pm": (pm.docks == 0).mean(),
        "empty_day": (day.bikes == 0).mean(),
    })
stations = pd.DataFrame(rows)
stations.to_csv(OUT / "nsysu_stations.csv", index=False)

# ---------- bell-aligned drops (campus total, weekdays) ----------
m_c, _, _ = total_by_slot(wk, CAMPUS)
bells = []
for h in range(9, 20):
    base = m_c[h * 6 - 1]
    rec = {"bell": f"{h:02d}:00", "bikes_before": base}
    for k in range(0, 7):
        rec[f"d{k * 10}"] = m_c[h * 6 + k] - base
    rec["pct_20"] = (m_c[h * 6 + 2] - base) / base if base else np.nan
    bells.append(rec)
bells = pd.DataFrame(bells)
bells.to_csv(OUT / "nsysu_bells.csv", index=False)

# ---------- stockout episodes at campus stations (weekdays, 07:00-23:00) ----------
eps = []
for (date, sno), g in wk[wk.sno.isin(CAMPUS)].groupby(["date", "sno"]):
    g = g.set_index("slot").reindex(range(144))
    e = (g.bikes == 0).values
    s = 0
    while s < 144:
        if e[s]:
            t = s
            while t < 144 and e[t]:
                t += 1
            if 42 <= s < 138:
                eps.append({"date": date, "sno": sno, "name": st.loc[sno, "short"], "start_slot": s, "len_slots": t - s})
            s = t
        else:
            s += 1
eps = pd.DataFrame(eps)
eps["start"] = eps.start_slot.map(lambda s: f"{s // 6:02d}:{(s % 6) * 10:02d}")
eps["minutes"] = eps.len_slots * 10
eps.to_csv(OUT / "nsysu_episodes.csv", index=False)

# ---------- overnight / early-morning jumps = operator refills ----------
pan = wk[wk.sno.isin(list(CAMPUS) + list(GATEWAY))].pivot_table(index=["date", "slot"], columns="sno", values="bikes")
dif = pan.groupby(level=0).diff()
big = dif.stack().reset_index().rename(columns={0: "delta"})
big = big[big.delta.abs() >= 8]
big["hour"] = big.slot // 6
big["name"] = big.sno.map(st["short"])
jumps = big.groupby(["name", "hour"]).delta.agg(["count", "sum"]).reset_index()

# ---------- summary numbers ----------
cap_campus = int(st.loc[list(CAMPUS), "capacity"].sum())
summary = {
    "weekdays": weekdays, "n_weekdays": len(weekdays), "campus_capacity": cap_campus,
    "krt_capacity": int(st.loc[KRT, "capacity"].sum()),
    "campus_bikes_10": round(float(m_c[60]), 1), "campus_bikes_17": round(float(m_c[102]), 1),
    "campus_bikes_18": round(float(m_c[108]), 1), "campus_bikes_06": round(float(m_c[36]), 1),
    "campus_empty_share_18": round(float(prof.loc[108, "campus_wk_empty"]), 3),
    "campus_empty_share_max": round(float(prof.campus_wk_empty.max()), 3),
    "campus_empty_share_max_t": prof.loc[prof.campus_wk_empty.idxmax(), "t"],
    "krt_bikes_10": round(float(prof.loc[60, "krt_wk"]), 1), "krt_bikes_18": round(float(prof.loc[108, "krt_wk"]), 1),
    "krt_empty_share_am": round(float(stations[stations.sno.isin(KRT)].empty_am.mean()), 3),
    "bell_12_drop_20min": round(float(bells.loc[bells.bell == "12:00", "d20"].iloc[0]), 1),
    "bell_12_pct_20min": round(float(bells.loc[bells.bell == "12:00", "pct_20"].iloc[0]), 3),
    "bell_16_drop_40min": round(float(bells.loc[bells.bell == "16:00", "d40"].iloc[0]), 1),
    "bell_17_drop_40min": round(float(bells.loc[bells.bell == "17:00", "d40"].iloc[0]), 1),
    "episodes_n": int(len(eps)), "episodes_per_station_day": round(len(eps) / (8 * len(weekdays)), 2),
    "episode_median_min": float(eps.minutes.median()), "episode_mean_min": round(float(eps.minutes.mean()), 1),
    "episode_p90_min": float(eps.minutes.quantile(0.9)),
    "episodes_start_after_bell_share": round(float((eps.start_slot % 6 <= 2).mean()), 3),
    "campus_station_minutes_empty_per_weekday": round(float(eps.minutes.sum() / len(weekdays)), 0),
}
json.dump(summary, open(OUT / "nsysu_summary.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1, ensure_ascii=False))
print(stations.round(2).to_string())
print(bells.round(0).to_string())
print(eps.groupby("name").minutes.describe().round(0))
print("start minute within hour share:", eps.groupby(eps.start_slot % 6).size().to_dict())
print(jumps[jumps["count"] >= 3].to_string())

# ---------- Figure: the campus<->KRT tide ----------
SHORT = {"501209052": "Library", "501209070": "Xiziwan Hall", "501209051": "Engineering", "501209054": "Materials",
         "501209039": "Social Sci.", "501209069": "Gymnasium", "501209040": "Marine Eng.", "501209071": "Marine Res.",
         "501209026": "KRT Exit 1", "501209023": "KRT Exit 2", "501209024": "Binhai Rd.", "501209062": "Gushan ES A",
         "501209042": "Gushan ES B", "501209036": "Pier-1 Br.", "501209022": "Shaochuan", "501209032": "Sizihwan Sc.",
         "501209025": "Marina Park", "501209104": "Shinhamacho", "501209028": "Xinbin PS"}
x = np.arange(144) / 6
fig = plt.figure(figsize=(W, 2.6))
ax = fig.add_axes([0.235, 0.575, 0.70, 0.375])
axh = fig.add_axes([0.235, 0.115, 0.70, 0.40])
cax = fig.add_axes([0.945, 0.115, 0.018, 0.40])
ax.fill_between(x, prof.campus_wk_p25, prof.campus_wk_p75, color=SEQ[2], lw=0)
ax.plot(x, prof.campus_wk, color=BLUE, lw=1.5, label=f"8 campus stations (cap. {cap_campus})")
ax.plot(x, prof.krt_wk, color=ORANGE, lw=1.5, label=f"2 KRT Sizihwan exits (cap. {summary['krt_capacity']})")
ax.plot(x, prof.campus_we, color=BLUE, lw=0.8, ls=(0, (2, 2)), label="campus, weekend")
for h, yy in ((12, 118), (16, 118), (17, 92)):
    ax.axvline(h, color=MUTED, lw=0.6, ls=(0, (3, 2)))
    ax.text(h + 0.12, yy, f"{h}:00", fontsize=5.2, color=INK2, va="bottom", ha="left")
ax.set_xlim(5, 24); ax.set_ylim(0, 215)
ax.set_xticks(range(6, 25, 3)); ax.tick_params(axis="x", labelbottom=False, length=0)
ax.set_yticks([0, 100, 200])
ax.set_ylabel("bikes available", fontsize=6, labelpad=1)
ax.legend(loc="upper left", fontsize=5.1, handlelength=1.5, borderaxespad=0.1, labelspacing=0.2)
ax.set_title(f"(a) Weekday mean over {len(weekdays)} days, Oct 2026 (band = IQR)", fontsize=6.3, loc="left", pad=2)
grid(ax)
order = list(CAMPUS) + KRT + [s for s in GATEWAY if s not in KRT]
pe = (wk[wk.sno.isin(order)].assign(e=lambda z: (z.bikes == 0).astype(float))
      .pivot_table(index="sno", columns="slot", values="e").reindex(order))
im = axh.imshow(pe.values, aspect="auto", cmap=seq_cmap, vmin=0, vmax=1, extent=[0, 24, len(order), 0], interpolation="nearest")
axh.set_yticks(np.arange(len(order)) + 0.5)
axh.set_yticklabels([SHORT[s] for s in order], fontsize=4.8)
axh.axhline(8, color=SURF, lw=1.2); axh.axhline(10, color=SURF, lw=1.2)
axh.set_xlim(5, 24); axh.set_xticks(range(6, 25, 3)); axh.set_xticklabels([f"{h:02d}:00" for h in range(6, 25, 3)])
axh.tick_params(axis="y", length=0)
for h in (12, 16, 17):
    axh.axvline(h, color=SURF, lw=0.6, ls=(0, (3, 2)))
axh.text(23.8, 0.3, "campus", fontsize=4.6, color=INK, ha="right", va="top")
axh.text(23.8, 8.3, "KRT", fontsize=4.6, color=INK, ha="right", va="top")
axh.text(23.8, 10.3, "gateway", fontsize=4.6, color=INK, ha="right", va="top")
axh.set_title("(b) Weekday P(station empty)", fontsize=6.3, loc="left", pad=2)
cb = fig.colorbar(im, cax=cax, ticks=[0, 0.5, 1])
cb.ax.tick_params(labelsize=4.8, length=1.5, pad=1); cb.outline.set_linewidth(0.4)
fig.savefig(OUT / "fig_nsysu_tide.png")

# ---------- Figure: bell-aligned drops ----------
fig, ax = plt.subplots(figsize=(W * 0.62, 1.35))
fig.subplots_adjust(left=0.25, right=0.97, top=0.93, bottom=0.21)
cols = {"12:00": BLUE, "16:00": ORANGE, "17:00": AQUA, "15:00": PURPLE}
for bell, c in cols.items():
    h = int(bell[:2]); base = m_c[h * 6 - 1]
    ks = np.arange(-2, 7)
    y = [(m_c[h * 6 + k] / base - 1) * 100 for k in ks]
    ax.plot(ks * 10, y, color=c, lw=1.4, marker="o", ms=2.2, label=bell)
ax.axvline(0, color=MUTED, lw=0.6, ls=(0, (3, 2)))
ax.set_xlabel("minutes after the bell", fontsize=6, labelpad=1)
ax.set_ylabel("campus bikes, change vs.\n10 min before bell (%)", fontsize=5.6, labelpad=2)
ax.set_xticks(range(-20, 61, 20)); ax.set_ylim(-100, 10)
ax.legend(fontsize=5.3, loc="lower left", ncol=1, handlelength=1.4, borderaxespad=0.2, labelspacing=0.25)
grid(ax)
fig.savefig(OUT / "fig_nsysu_bells.png")
print("figures written")
