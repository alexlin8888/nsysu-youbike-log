"""Report figures, version 2: every figure at column width (3.25 in), fonts >= 6.5 pt at print size,
legends outside the data area, no labels over marks.

Usage: python figs_v2.py LOGGER_DATA_DIR HW1_DIR MODEL_DIR SIM_DIR DEMAND_DIR NSYSU_DIR OUT_DIR
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from nsysu_data import CAMPUS, GATEWAY, load_logger, load_stations  # noqa: E402
from figcheck import check  # noqa: E402

BOXES = []   # diagram boxes of the current figure, for the spill check


def save(fig, name, ax=None, allow_outside=False):
    check(fig, name, boxes=BOXES or None, ax=ax, allow_outside=allow_outside)
    fig.savefig(OUT / name); plt.close(fig); BOXES.clear()

DATA, HW1, MODEL, SIM, DEMAND, NSYSU, OUT = [Path(a) for a in sys.argv[1:8]]
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "legend.fontsize": 6.5})


def legend_above(ax, ncol, bbox_to_anchor=(0, 1.0), columnspacing=1.0, **kw):
    return ax.legend(loc="lower left", bbox_to_anchor=bbox_to_anchor, ncol=ncol, frameon=False, handlelength=1.4,
                     columnspacing=columnspacing, borderaxespad=0.0, handletextpad=0.5, **kw)


def panel_label(ax, text, y=1.0):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, fontweight="bold", va="bottom", ha="left")


# ======================= Figure 1: motivation (NTU profile + NSYSU snapshot) =======================
P = pd.read_csv(HW1 / "fig1_ntu_profile.csv")
t = pd.to_datetime("2025-03-03 " + P.t)
x = (t.dt.hour + t.dt.minute / 60).values
snap = json.load(open(HW1 / "nsysu_snapshot.json"))
fig = plt.figure(figsize=(W, 3.1))
ax = fig.add_axes([0.13, 0.645, 0.85, 0.235])
axs = fig.add_axes([0.13, 0.585, 0.85, 0.05])
axb = fig.add_axes([0.36, 0.115, 0.60, 0.38])
ax.fill_between(x, P.bikes_p25, P.bikes_p75, color=SEQ[2], linewidth=0, label="IQR over 20 weekdays")
ax.plot(x, P.bikes_mean, color=BLUE, linewidth=1.6, label="mean, 59 NTU campus stations")
for xb, lab in [(12 + 10 / 60, "12:10"), (15 + 10 / 60, "15:10"), (17 + 20 / 60, "17:20")]:
    ax.axvline(xb, color=ORANGE, linewidth=0.9, linestyle=(0, (3, 2)))
    ax.text(xb + 0.1, 132, lab, color=ORANGE, fontsize=6.3, va="bottom", ha="left")
i0 = np.argmin(abs(x - 17.0)); i1 = np.argmin(abs(x - (17 + 40 / 60)))
ax.annotate("", xy=(x[i1], P.bikes_mean[i1]), xytext=(x[i0], P.bikes_mean[i0]), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8, shrinkA=0, shrinkB=0))
ax.text(18.3, 300, f"−{(1 - P.bikes_mean[i1] / P.bikes_mean[i0]) * 100:.0f}% in 40 min", fontsize=6.5, color=INK, va="center")
ax.set_ylim(120, 830); ax.set_xlim(7, 21.6); ax.set_yticks([200, 400, 600, 800])
ax.set_ylabel("bikes available", labelpad=2)
ax.set_xticks(range(7, 22, 2)); ax.tick_params(axis="x", labelbottom=False, length=0)
grid(ax)
leg = legend_above(ax, 2, fontsize=6.3, bbox_to_anchor=(0, 1.02))
fig.text(0.01, 0.995, "(a) NTU campus, 20 weekdays in Mar 2025 (period ends in orange)", fontsize=7.2, fontweight="bold", va="top")
strip = P.empty_mean.values[None, :]
axs.imshow(strip, aspect="auto", cmap=seq_cmap, vmin=0, vmax=0.35, extent=[x[0], x[-1], 0, 1])
axs.set_yticks([]); axs.set_xlim(7, 21.6)
axs.set_xticks(range(7, 22, 2)); axs.set_xticklabels([f"{h:02d}:00" for h in range(7, 22, 2)]); axs.tick_params(axis="x", length=2, pad=1.5)
for spine in axs.spines.values():
    spine.set_visible(False)
axs.text(-0.012, 0.5, "% empty", transform=axs.transAxes, fontsize=6.3, color=INK2, va="center", ha="right")
for xx in [9.5, 13.0, 18.5]:
    v = P.empty_mean.values[np.argmin(abs(x - xx))]
    axs.text(xx, 0.5, f"{v * 100:.0f}%", fontsize=6.3, color="white" if v > 0.17 else INK, va="center", ha="center", fontweight="bold")
short = {"中山大學圖資大樓": "Library *", "中山大學西灣藝廊": "Xiziwan Hall *", "中山大學材料大樓": "Materials *",
         "中山大學體育館": "Gymnasium *", "中山大學海工館": "Marine Eng. *", "濱海臨海路口(西南側)": "Binhai/Linhai Rd.",
         "捷運哈瑪星站(1號出口)": "KRT Sizihwan Exit 1", "捷運哈瑪星站(2號出口)": "KRT Sizihwan Exit 2"}
sel = sorted([s for s in snap if s["name_tw"] in short], key=lambda s: s["dist_m"])[:8]
names = [short[s["name_tw"]] for s in sel][::-1]
bikes = np.array([s["bikes"] for s in sel])[::-1]; caps = np.array([s["cap"] for s in sel])[::-1]
y = np.arange(len(sel))
axb.barh(y, caps, color=GRID, height=0.62, linewidth=0)
axb.barh(y, bikes, color=[CRIT if b == 0 else BLUE for b in bikes], height=0.62, linewidth=0)
for yi, b, c in zip(y, bikes, caps):
    axb.text(c + 1, yi, ("0 bikes" if b == 0 else f"{b}/{c}"), va="center", fontsize=6.3, color=CRIT if b == 0 else INK2, fontweight="bold" if b == 0 else "normal")
axb.set_yticks(y); axb.set_yticklabels(names)
axb.set_xlim(0, 76); axb.set_xticks([0, 20, 40, 60]); axb.set_xlabel("bikes / docks (grey = docks; * = on campus)", labelpad=2)
axb.tick_params(axis="y", length=0, pad=2)
grid(axb, "x")
fig.text(0.01, 0.525, "(b) NSYSU area, 28 Sep 2026, 17:12 (12 min after the bell)", fontsize=7.2, fontweight="bold", va="top")
save(fig, "fig1_motivation.png", ax=ax)

# ======================= Figure 2: pipeline =======================
fig, ax = plt.subplots(figsize=(W, 1.5)); ax.set_xlim(-1.0, 101.0); ax.set_ylim(0, 47); ax.axis("off")


def pbox(x0, y0, w, h, title, lines, fc="#f2f6fc", ec=BLUE, tag=None):
    BOXES.append((x0, y0, x0 + w, y0 + h))
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0.3,rounding_size=1.4", fc=fc, ec=ec, lw=0.8))
    ax.text(x0 + w / 2, y0 + h - 2.4, title, ha="center", va="top", fontsize=7, fontweight="bold", color=INK)
    ax.text(x0 + w / 2, y0 + h - 9.8, lines, ha="center", va="top", fontsize=6, color=INK2, linespacing=1.25)
    if tag:
        ax.text(x0 + w / 2, y0 - 2.2, tag, ha="center", va="top", fontsize=5.8, color=ORANGE, fontstyle="italic")


bw, bh, gap, y0 = 23.6, 25.0, 1.7, 18.0
xs = [0.5 + i * (bw + gap) for i in range(4)]
pbox(xs[0], y0, bw, bh, "1  Data", "hourly trip records\n10-min inventory\nclass timetables\nlive station feed", fc="#f7f7f5", ec=MUTED, tag="open data + timetables")
pbox(xs[1], y0, bw, bh, "2  Reconstruct", "censored rent /\nreturn rates;\ninfer truck moves", tag="uncertainty")
pbox(xs[2], y0, bw, bh, "3  Predict", "P(stockout in h)\nschedule-aware\nGBM, calibrated", tag="learning")
pbox(xs[3], y0, bw, bh, "4  Plan", "rolling-horizon\nroute search\nmin E[unmet]+β·km", tag="search / agent")
for a, b in zip(xs[:-1], xs[1:]):
    ax.add_patch(FancyArrowPatch((a + bw + 0.2, y0 + bh / 2), (b - 0.3, y0 + bh / 2), arrowstyle="-|>", mutation_scale=6, lw=0.8, color=INK2))
BOXES.append((0.5, 1.0, 99.5, 11.4))
ax.add_patch(FancyBboxPatch((0.5, 1.0), 99, 10.4, boxstyle="round,pad=0.3,rounding_size=1.2", fc="#fff3ee", ec=ORANGE, lw=0.7))
ax.text(50, 6.2, "5  Evaluate:  replay real NTU trips → compare the policies\nwith the operator’s own moves → demo live at NSYSU", ha="center", va="center", fontsize=6.0, color=INK, linespacing=1.3)
ax.add_patch(FancyArrowPatch((xs[3] + bw - 2.0, y0 - 0.2), (xs[3] + bw - 2.0, 11.8), arrowstyle="-|>", mutation_scale=6, lw=0.8, color=INK2))
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
save(fig, "fig2_pipeline.png", ax=ax)

# ======================= Figure 3: architecture =======================
fig = plt.figure(figsize=(W, 2.95))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
FILL = {"src": "#eeeeea", "tab": "#e8f0fb", "mod": "#d6e5f8", "out": "#fde8df"}
EDGE = {"src": MUTED, "tab": SEQ[5], "mod": BLUE, "out": ORANGE}


def abox(x, y, w, h, title, lines, kind):
    BOXES.append((x, y, x + w, y + h))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=FILL[kind], ec=EDGE[kind], lw=0.8))
    ax.text(x + w / 2, y + h - 1.3, title, ha="center", va="top", fontsize=6.6, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + 1.1, lines, ha="center", va="bottom", fontsize=5.5, color=INK2, linespacing=1.15)


def aarrow(x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=5, lw=0.7, color=INK2, shrinkA=0, shrinkB=0))


ax.text(1, 98, "NTU lane: open data, method development", fontsize=6.2, color=INK2, va="top", style="italic")
ax.text(67, 98, "NSYSU lane: deployment", fontsize=6.2, color=INK2, va="top", style="italic")
ax.plot([65.5, 65.5], [2, 94], color=GRID, lw=0.6, ls=(0, (3, 2)))
abox(1, 78, 30, 14, "Trip records [1]", "monthly zip, 10 months\n10.2 M trips, hourly", "src")
abox(33, 78, 30, 14, "Snapshots [2]", "295 days, every 10 min\n2.97 M station records", "src")
abox(67.5, 78, 31.5, 14, "Live station API [12]", "GitHub Actions logger\n309 stations, 10 min", "src")
abox(1, 59, 30, 13, "flows_hourly", "station × hour:\nrentals, returns", "tab")
abox(33, 59, 30, 13, "panel_10min", "station × 10 min: bikes,\ndocks; forward-filled", "tab")
abox(67.5, 59, 31.5, 13, "NSYSU panel", "station × 10 min\n+ NSYSU calendar", "tab")
abox(1, 40, 30, 13, "Reconcile (2.3)", "Δs − (q − r) → truck moves\nexposure → rates λ", "mod")
abox(33, 40, 30, 13, "Features + labels (2.4)", "time, bell, state,\nneighbours, flows", "mod")
abox(67.5, 40, 31.5, 13, "Inventory-only features", "same code, NSYSU bells\nno trip flows", "mod")
abox(1, 21, 30, 13, "Replay simulator (2.6)", "real trips, K trucks\nunmet, empty-min, km", "out")
abox(33, 21, 30, 13, "LightGBM predictor", "P(empty in 30 / 60 min)\nBrier, AUC, ECE", "mod")
abox(67.5, 21, 31.5, 13, "Transfer (2.5)", "zero-shot / fine-tune\nvs. NSYSU-only", "out")
abox(33, 3, 30, 12, "Pre-emptive planner", "rentals saved per\ntruck-minute; route search", "out")
abox(67.5, 3, 31.5, 12, "Live demo (planned)", "map, P(empty) per station,\nnext-bell truck plan", "out")
for xx in (16, 48, 83.25):
    aarrow(xx, 78, xx, 72.3); aarrow(xx, 59, xx, 53.3)
aarrow(48, 40, 48, 34.3); aarrow(16, 40, 16, 34.3); aarrow(31, 46.5, 33, 46.5)
aarrow(48, 21, 48, 15.3); aarrow(33, 9, 16, 9); aarrow(16, 9, 16, 21)
aarrow(63, 27.5, 67.5, 27.5); aarrow(83.25, 40, 83.25, 34.3); aarrow(83.25, 21, 83.25, 15.3)
save(fig, "fig_architecture.png", ax=ax)

# ======================= Figure 4: NSYSU tide =======================
prof = pd.read_csv(NSYSU / "nsysu_profile.csv")
summ = json.load(open(NSYSU / "nsysu_summary.json"))
df = load_logger(DATA); st = load_stations(DATA).set_index("sno")
full = df[df.date.between("2026-10-02", "2026-10-14")]; wk = full[full.weekday]
KRT = ["501209026", "501209023"]
SHORT = {"501209052": "Library", "501209070": "Xiziwan Hall", "501209051": "Engineering", "501209054": "Materials",
         "501209039": "Social Sci.", "501209069": "Gymnasium", "501209040": "Marine Eng.", "501209071": "Marine Res.",
         "501209026": "KRT Exit 1", "501209023": "KRT Exit 2", "501209024": "Binhai Rd.", "501209062": "Gushan ES A",
         "501209042": "Gushan ES B", "501209036": "Pier-1 Br.", "501209022": "Shaochuan", "501209032": "Sizihwan Sc.",
         "501209025": "Marina Park", "501209104": "Shinhamacho", "501209028": "Xinbin PS"}
order = list(CAMPUS) + KRT + ["501209024", "501209062", "501209042", "501209028"]   # campus, KRT, 4 busiest gateways
pe = (wk[wk.sno.isin(order)].assign(e=lambda z: (z.bikes == 0).astype(float)).pivot_table(index="sno", columns="slot", values="e").reindex(order))
x = np.arange(144) / 6
fig = plt.figure(figsize=(W, 3.3))
ax = fig.add_axes([0.24, 0.60, 0.665, 0.26])
axh = fig.add_axes([0.24, 0.09, 0.665, 0.40])
cax = fig.add_axes([0.922, 0.09, 0.018, 0.40])
ax.fill_between(x, prof.campus_wk_p25, prof.campus_wk_p75, color=SEQ[2], lw=0, label="IQR of the campus mean")
ax.plot(x, prof.campus_wk, color=BLUE, lw=1.5, label=f"campus, 8 stations, {summ['campus_capacity']} docks")
ax.plot(x, prof.krt_wk, color=ORANGE, lw=1.5, label=f"KRT Sizihwan, 2 exits, {summ['krt_capacity']} docks")
ax.plot(x, prof.campus_we, color=BLUE, lw=0.9, ls=(0, (2, 2)), label="campus, weekend")
for h, ha, dx in ((12, "center", 0), (16, "right", -0.12), (17, "left", 0.12)):
    ax.axvline(h, color=MUTED, lw=0.6, ls=(0, (3, 2)))
    ax.text(h + dx, 236, f"{h}:00", fontsize=6.2, color=INK2, va="top", ha=ha)
ax.set_xlim(5, 24); ax.set_ylim(0, 240); ax.set_yticks([0, 100, 200])
ax.set_xticks(range(6, 25, 3)); ax.tick_params(axis="x", labelbottom=False, length=0)
ax.set_ylabel("bikes available", labelpad=2)
grid(ax)
h_, l_ = ax.get_legend_handles_labels()
fig.legend(h_, l_, loc="upper left", bbox_to_anchor=(0.01, 0.962), ncol=2, frameon=False, fontsize=6.2, handlelength=1.4, columnspacing=1.2, labelspacing=0.3)
fig.text(0.01, 0.995, "(a) Weekday mean over 8 teaching days, Oct 2026", fontsize=7.2, fontweight="bold", va="top")
im = axh.imshow(pe.values, aspect="auto", cmap=seq_cmap, vmin=0, vmax=1, extent=[0, 24, len(order), 0], interpolation="nearest")
axh.set_yticks(np.arange(len(order)) + 0.5); axh.set_yticklabels([SHORT[s] for s in order], fontsize=6.0)
axh.axhline(8, color=SURF, lw=1.4); axh.axhline(10, color=SURF, lw=1.4)
axh.set_xlim(5, 24); axh.set_xticks(range(6, 25, 3)); axh.set_xticklabels([f"{h:02d}:00" for h in range(6, 25, 3)])
axh.tick_params(axis="y", length=0)
for h in (12, 16, 17):
    axh.axvline(h, color=SURF, lw=0.7, ls=(0, (3, 2)))
for yy, lab in ((0.15, "campus"), (8.15, "KRT"), (10.15, "gateway")):
    axh.text(5.15, yy, lab, fontsize=5.8, color=INK2, ha="left", va="top", style="italic")
cb = fig.colorbar(im, cax=cax, ticks=[0, 0.5, 1]); cb.ax.tick_params(labelsize=6, length=1.5, pad=1); cb.outline.set_linewidth(0.4)
fig.text(0.01, 0.545, "(b) Weekday probability that a station is empty", fontsize=7.2, fontweight="bold", va="top")
save(fig, "fig_nsysu_tide.png", ax=ax)

# ======================= Figure 5: bell-aligned drops =======================
m_c = prof.campus_wk.values
fig, ax = plt.subplots(figsize=(W, 1.75))
fig.subplots_adjust(left=0.16, right=0.78, top=0.95, bottom=0.23)
for bell, c in (("12:00", BLUE), ("16:00", ORANGE), ("17:00", AQUA), ("15:00", PURPLE)):
    h = int(bell[:2]); base = m_c[h * 6 - 1]
    ks = np.arange(-2, 7)
    ax.plot(ks * 10, [(m_c[h * 6 + k] / base - 1) * 100 for k in ks], color=c, lw=1.4, marker="o", ms=2.6, label=f"{bell} bell")
ax.axvline(0, color=MUTED, lw=0.6, ls=(0, (3, 2)))
ax.set_xlabel("minutes after the bell", labelpad=2); ax.set_ylabel("campus bikes vs.\n10 min before (%)", labelpad=2)
ax.set_xticks(range(-20, 61, 20)); ax.set_ylim(-100, 10); ax.set_yticks([-100, -75, -50, -25, 0])
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, handlelength=1.4, borderaxespad=0)
grid(ax)
save(fig, "fig_nsysu_bells.png", ax=ax)

# ======================= Figure 6: operator moves =======================
pm = pd.read_csv(DEMAND / "moves_profile.csv"); ds = json.load(open(DEMAND / "demand_summary.json"))
fig, ax = plt.subplots(figsize=(W, 2.0))
fig.subplots_adjust(left=0.14, right=0.98, top=0.78, bottom=0.18)
hod = np.arange(24)
for campus, col, lab in ((1, BLUE, "campus"), (0, ORANGE, "ring")):
    c = pm[pm.campus == campus].set_index("hod").reindex(hod).fillna(0)
    off = -0.2 if campus == 1 else 0.2
    ax.bar(hod + off, c.drop_per_day, width=0.38, color=col, lw=0, label=f"{lab}: drop-off")
    ax.bar(hod + off, -c.pick_per_day, width=0.38, color=col, alpha=0.45, lw=0, label=f"{lab}: pick-up")
ax.axhline(0, color=MUTED, lw=0.5)
for xb in (12.17, 17.33):
    ax.axvline(xb, color=INK2, lw=0.6, ls=(0, (3, 2)))
ax.set_xticks(range(0, 24, 3)); ax.set_xticklabels([f"{xx:02d}" for xx in range(0, 24, 3)])
ax.set_xlabel("hour of day", labelpad=2); ax.set_ylabel("bikes per day", labelpad=2)
legend_above(ax, 2, fontsize=6.2)
grid(ax)
save(fig, "fig_ntu_moves.png", ax=ax)

# ======================= Figure 7: censoring =======================
cp = pd.read_csv(DEMAND / "censoring_profile.csv")
fig, ax = plt.subplots(figsize=(W, 1.7))
fig.subplots_adjust(left=0.14, right=0.98, top=0.80, bottom=0.21)
ax.plot(cp.hod, cp.lam_naive, color=MUTED, lw=1.4, label="observed rentals per station-hour")
ax.plot(cp.hod, cp.lam_cens, color=BLUE, lw=1.6, label="censoring-corrected demand rate")
ax.fill_between(cp.hod, cp.lam_naive, cp.lam_cens, color=SEQ[2], lw=0)
ax.set_xticks(range(6, 24, 3)); ax.set_xlim(6, 23); ax.set_ylim(0, 36)
ax.set_xlabel("hour of day (weekdays)", labelpad=2); ax.set_ylabel("rentals / station-hour", labelpad=2)
legend_above(ax, 1, fontsize=6.2)
grid(ax)
save(fig, "fig_ntu_censoring.png", ax=ax)

# ======================= Figure 8: model =======================
rel = pd.read_csv(MODEL / "reliability.csv"); met = pd.read_csv(MODEL / "metrics.csv")
fig = plt.figure(figsize=(W, 2.1))
ax1 = fig.add_axes([0.11, 0.19, 0.36, 0.55]); ax2 = fig.add_axes([0.60, 0.19, 0.38, 0.55])
ax1.plot([0, 1], [0, 1], color=MUTED, lw=0.6, ls=(0, (3, 2)))
for model, (c, lab) in {"seasonal": (MUTED, "seasonal baseline"), "lgb_inv": (ORANGE, "GBM, inventory only"), "lgb_full": (BLUE, "GBM + trip flows")}.items():
    r = rel[(rel.h == 30) & (rel.model == model) & (rel.n > 200)]
    ax1.plot(r.p_mean, r.y_mean, color=c, lw=1.3, marker="o", ms=2.4, label=lab)
ax1.set_xlim(0, 1); ax1.set_ylim(0, 1); ax1.set_xticks([0, 0.5, 1]); ax1.set_yticks([0, 0.5, 1])
ax1.set_xlabel("predicted P(empty in 30 min)", labelpad=2); ax1.set_ylabel("observed frequency", labelpad=2)
legend_above(ax1, 1, fontsize=6.0)
fig.text(0.01, 0.985, "(a) Reliability", fontsize=7.2, fontweight="bold", va="top")
grid(ax1, "both")
order_m = ["persistence", "seasonal", "lgb_inv", "lgb_full"]; labels = {"persistence": "persistence", "seasonal": "seasonal", "lgb_inv": "GBM inv.", "lgb_full": "GBM+flows"}
subs = [("all", "all"), ("campus", "campus"), ("classend", "class-end")]
xs = np.arange(len(subs)); wdt = 0.2; cols = [MUTED, SEQ[3], ORANGE, BLUE]
for k, m in enumerate(order_m):
    v = [met[(met.h == 30) & (met.model == m) & (met.subset == s)].auc.iloc[0] for s, _ in subs]
    ax2.bar(xs + (k - 1.5) * wdt, v, width=wdt - 0.02, color=cols[k], lw=0, label=labels[m])
    for xx, yy in zip(xs + (k - 1.5) * wdt, v):
        ax2.text(xx, yy + 0.008, f"{yy:.2f}", ha="center", va="bottom", fontsize=5.4, color=INK2, rotation=90)
ax2.set_ylim(0.5, 1.09); ax2.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0]); ax2.set_xticks(xs); ax2.set_xticklabels([l for _, l in subs])
ax2.set_ylabel("AUC, h = 30 min", labelpad=2)
legend_above(ax2, 2, fontsize=6.0, columnspacing=0.8)
fig.text(0.52, 0.985, "(b) AUC by subset", fontsize=7.2, fontweight="bold", va="top")
grid(ax2)
save(fig, "fig_model.png", ax=ax)

# ======================= Figure 9: transfer =======================
tm = pd.read_csv(MODEL / "transfer" / "transfer_metrics.csv")
fig, ax = plt.subplots(figsize=(W, 1.95))
fig.subplots_adjust(left=0.14, right=0.98, top=0.86, bottom=0.24)
models = [("persistence", "persist."), ("seasonal_nsysu", "seasonal\n6 days"), ("ntu_zero_shot", "NTU model\nzero-shot"), ("ntu_finetuned", "NTU model\n+ fine-tune"), ("nsysu_only", "NSYSU only\n6 days")]
xs = np.arange(len(models))
for k, (sub, c, lab) in enumerate((("all309", SEQ[3], "309 stations within 5 km"), ("campus8", BLUE, "8 campus stations"))):
    v = [tm[(tm.h == 30) & (tm.model == m) & (tm.subset == sub)].auc.iloc[0] for m, _ in models]
    ax.bar(xs + (k - 0.5) * 0.36, v, width=0.34, color=c, lw=0, label=lab)
    for xx, yy in zip(xs + (k - 0.5) * 0.36, v):
        ax.text(xx, yy + 0.008, f"{yy:.2f}", ha="center", va="bottom", fontsize=5.6, color=INK2, rotation=90)
ax.set_ylim(0.5, 1.09); ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0]); ax.set_xticks(xs); ax.set_xticklabels([l for _, l in models], fontsize=6.2)
ax.set_ylabel("AUC at NSYSU, h = 30 min", labelpad=2)
legend_above(ax, 2, fontsize=6.2, bbox_to_anchor=(0, 1.07))
grid(ax)
save(fig, "fig_transfer.png", ax=ax)

# ======================= Figure 10: simulation =======================
rows = []
for k in (1, 3, 6):
    s = pd.read_csv(SIM / f"k{k}" / "sim_summary.csv").set_index("policy")
    for pol in ("reactive", "point", "prob"):
        rows.append({"trucks": k, "policy": pol, "unmet_reduction": s.loc[pol, "unmet_reduction"],
                     "empty_reduction": 1 - s.loc[pol, "empty_station_min"] / s.loc["none", "empty_station_min"]})
sim = pd.DataFrame(rows)
fig = plt.figure(figsize=(W, 1.85))
ax1 = fig.add_axes([0.11, 0.2, 0.38, 0.6]); ax2 = fig.add_axes([0.60, 0.2, 0.38, 0.6])
pc = {"reactive": MUTED, "point": ORANGE, "prob": BLUE}; pl = {"reactive": "reactive", "point": "predictive, point forecast", "prob": "predictive, probabilistic"}
xs = np.arange(3)
for ax, col, ttl in ((ax1, "unmet_reduction", "(a) Unmet rentals avoided"), (ax2, "empty_reduction", "(b) Empty minutes")):
    for k, pol in enumerate(("reactive", "point", "prob")):
        v = sim[sim.policy == pol].sort_values("trucks")[col].values * 100
        ax.bar(xs + (k - 1) * 0.27, v, width=0.25, color=pc[pol], lw=0, label=pl[pol])
        for xx, yy in zip(xs + (k - 1) * 0.27, v):
            ax.text(xx, yy + 0.6, f"{yy:.0f}", ha="center", va="bottom", fontsize=5.8, color=INK2)
    ax.set_xticks(xs); ax.set_xticklabels(["1 truck", "3 trucks", "6 trucks"])
    ax.set_ylabel("% vs. no rebalancing", labelpad=2)
    panel_label(ax, ttl, y=1.02)
    grid(ax)
ax1.set_ylim(0, 34); ax2.set_ylim(0, 48)
h_, l_ = ax1.get_legend_handles_labels()
fig.legend(h_, l_, loc="lower center", bbox_to_anchor=(0.5, 0.86), ncol=3, frameon=False, fontsize=6.2, handlelength=1.4, columnspacing=1.2)
save(fig, "fig_sim.png", ax=ax)

# ======================= Figure 12: Gantt =======================
D = lambda m, d: dt.date(2026, m, d)
TODAY = D(10, 29)
tasks = [("Data pipeline & matching", D(10, 1), D(10, 18), "PL", 1.0), ("Demand & operator moves", D(10, 10), D(10, 28), "JC", 1.0),
         ("Stockout predictor", D(10, 19), D(11, 14), "SL", 0.8), ("Calibration & transfer", D(11, 8), D(11, 25), "JC", 0.6),
         ("Planner & simulator", D(11, 5), D(12, 6), "PL", 0.4), ("NSYSU live demo app", D(11, 20), D(12, 14), "SL", 0.1),
         ("Report & presentation", D(11, 22), D(12, 22), "all", 0.15)]
ms = [(D(10, 1), "Proposal"), (D(10, 29), "Midterm"), (D(11, 26), "Video"), (D(12, 24), "Final")]
start = D(9, 29); end = dt.date(2027, 1, 4)
fig, ax = plt.subplots(figsize=(W, 1.8))
n = len(tasks)
for i, (name, s, e, who, done) in enumerate(tasks):
    yv = n - 1 - i; left, width = (s - start).days, (e - s).days
    ax.barh(yv, width, left=left, height=0.58, color=SEQ[2], linewidth=0)
    ax.barh(yv, width * done, left=left, height=0.58, color=BLUE if who != "all" else "#5598e7", linewidth=0)
    ax.text(left + 1.6, yv, who, va="center", ha="left", fontsize=5.8, color="white" if done > 0.15 else INK2, fontweight="bold")
    ax.text(left + width + 1.5, yv, f"{int(done * 100)}%", va="center", ha="left", fontsize=5.8, color=INK2)
ax.set_yticks(range(n)); ax.set_yticklabels([t_[0] for t_ in tasks][::-1], fontsize=6.3)
ax.tick_params(axis="y", length=0)
months = [D(10, 1), D(11, 1), D(12, 1)]
ax.set_xticks([(m - start).days for m in months]); ax.set_xticklabels(["Oct", "Nov", "Dec"])
ax.set_xlim(0, (end - start).days)
grid(ax, "x")
ax.axvspan(0, (TODAY - start).days, color="#f3f3f0", zorder=0)
for m, lab in ms:
    xm = (m - start).days
    ax.plot([xm, xm], [-0.6, n - 0.35], color=ORANGE, lw=0.7, linestyle=(0, (3, 2)), zorder=0)
    ax.plot([xm], [n - 0.35], marker="D", color=ORANGE, ms=2.8, clip_on=False)
    ax.text(xm, n + 0.05, f"{lab}\n{m.month}/{m.day}", ha=("right" if lab == "Final" else "center"), va="bottom", fontsize=5.8, color=ORANGE, linespacing=1.1)
ax.set_ylim(-0.6, n + 1.0)
for spine in ["left", "bottom"]:
    ax.spines[spine].set_visible(False)
fig.subplots_adjust(left=0.37, right=0.95, top=0.97, bottom=0.12)
save(fig, "fig_gantt_hw3.png", ax=ax, allow_outside=True)

# ======================= Figure 11: demo mock-up =======================
import math as _m
rng = np.random.default_rng(7)
lat0, lng0 = 22.6273, 120.2658
pts = [s_ for s_ in snap if s_["dist_m"] <= 1200]
lon = np.array([s_["lng"] for s_ in pts]); latv = np.array([s_["lat"] for s_ in pts])
kx = 111320 * _m.cos(_m.radians(lat0)); ky = 110574
X = (lon - lng0) * kx; Y = (latv - lat0) * ky
capv = np.array([s_["cap"] for s_ in pts]); bikesv = np.array([s_["bikes"] for s_ in pts])
pp = np.clip(1 - bikesv / np.maximum(capv, 1), 0, 1) ** 1.6
pp = np.clip(pp * 0.85 + rng.normal(0, 0.05, len(pp)), 0.02, 0.97)
fig = plt.figure(figsize=(W, 2.75))
ax = fig.add_axes([0.01, 0.045, 0.82, 0.74])
cax = fig.add_axes([0.86, 0.1, 0.028, 0.6])
sc = ax.scatter(X, Y, s=10 + capv * 1.2, c=pp, cmap=seq_cmap, vmin=0, vmax=1, edgecolor="white", linewidth=0.7, zorder=3)
name_idx = {s_["name_tw"]: i for i, s_ in enumerate(pts)}


def lab(n, txt, dx=0, dy=0, ha="left", va="center"):
    i = name_idx[n]; ax.text(X[i] + dx, Y[i] + dy, txt, fontsize=6.3, color=INK, ha=ha, va=va, zorder=5)


lab("中山大學體育館", "Gym (48/63)", -50, -90, ha="right")
lab("中山大學西灣藝廊", "Xiziwan Hall (1/17)", 0, 78, ha="center")
lab("中山大學材料大樓", "Materials (4/27)", 60, 22)
lab("捷運哈瑪星站(1號出口)", "KRT Exit 1 (0/26)", -30, -78, ha="right")
lab("捷運哈瑪星站(2號出口)", "KRT Exit 2 (0/43)", 271, -83, ha="right")
lab("中山大學海工館", "Marine Eng. (7/31)", 60, 0)
lab("中山大學海資館", "Marine Res. (8/17)", 66, 0)
lab("西子灣風景區", "Sizihwan Scenic (17/28)", -60, 0, ha="right")
route = ["中山大學體育館", "中山大學西灣藝廊", "中山大學材料大樓", "捷運哈瑪星站(1號出口)", "捷運哈瑪星站(2號出口)"]
for a_, b_ in zip(route[:-1], route[1:]):
    i, j = name_idx[a_], name_idx[b_]
    ax.add_patch(FancyArrowPatch((X[i], Y[i]), (X[j], Y[j]), arrowstyle="-|>", mutation_scale=7, lw=1.1, color=ORANGE, zorder=4, shrinkA=5, shrinkB=5))
fig.text(0.01, 0.985, "LIVE 16:50  \u00b7  next bell 17:00  \u00b7  horizon 30 min", fontsize=7.2, fontweight="bold", color=INK, va="top")
fig.text(0.01, 0.93, "Truck plan: Gym \u2192 Xiziwan Hall \u2192 Materials \u2192 KRT Exit 1 \u2192 Exit 2\nexpected unmet rentals avoided in 30 min: 41", fontsize=6.0, color=INK2, va="top", linespacing=1.3)
cb = fig.colorbar(sc, cax=cax, ticks=[0, 0.5, 1])
cb.ax.tick_params(labelsize=6, length=1.5, pad=1.2); cb.outline.set_linewidth(0.4)
cb.set_label("P(stockout in 30 min)", fontsize=6.2, labelpad=2)
ax.plot([720, 1220], [-1040, -1040], color=INK, lw=0.8); ax.text(970, -1000, "500 m", ha="center", fontsize=6, color=INK)
ax.set_xlim(-760, 1260); ax.set_ylim(-1090, 430)
ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(True); spine.set_color(GRID)
fig.text(0.01, 0.01, "Mock-up: real positions and stock (28 Sep 2026, 17:12); probabilities and route illustrative", fontsize=5.6, color=MUTED, ha="left", va="bottom", fontstyle="italic")
save(fig, "fig3_demo_mock.png", ax=ax)
print("figures v2 written")
