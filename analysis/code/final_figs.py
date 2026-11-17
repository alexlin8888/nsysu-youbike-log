"""Figures added for the final report (all at CVPR column width).

Usage: python final_figs.py FINAL_DIR OUT_DIR [RATES_DIR]

FINAL_DIR is analysis/results/final. Each figure is drawn when its inputs exist:
  fig_final_weeks.png     final_nsysu_days.csv        the campus tide on every teaching weekday of the logging period
  fig_final_transfer.png  transfer/weeks_*.csv        AUC against weeks of local data; zero-shot AUC by logging week
  fig_final_forecast.png  forecast/forecast_*.csv     the after-class forecast against its baselines; reliability
  fig_final_planner.png   planner/planner_by_slot.csv what the planner expects and plans at NSYSU, by time of day
  fig_final_rates.png     RATES_DIR/rates*.csv        hourly and 10-minute chain rates at the campus stations
  fig_final_rider.png     rider/rider_summary.csv     does the advice get a rider a bike or a dock: success against extra walking
  fig_final_sim.png       sim/sim_summary.csv         simulated trucks at NSYSU: what one to three campus trucks avoid
  fig_architecture_final.png                          the system as deployed
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from figcheck import check  # noqa: E402

FINAL, OUT = Path(sys.argv[1]), Path(sys.argv[2])
RATES = Path(sys.argv[3]) if len(sys.argv) > 3 else FINAL.parent / "nsysu" / "rates"      # nsysu_rates.py output
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.2})


def save(fig, name, ax=None, allow_outside=False, marks=True, allow_on_marks=()):
    check(fig, name, ax=ax, allow_outside=allow_outside, marks=marks, allow_on_marks=allow_on_marks)
    fig.savefig(OUT / name)
    plt.close(fig)
    print("wrote", name)


def title(fig, x, y, text):
    fig.text(x, y, text, fontsize=7.2, fontweight="bold", va="top")


# ======================= the tide on every teaching weekday =======================
f = FINAL / "final_nsysu_days.csv"
if f.exists():
    d = pd.read_csv(f)
    d["x"] = (pd.to_datetime(d.date) - pd.Timestamp("2026-10-01")).dt.days
    fig = plt.figure(figsize=(W, 2.25))
    ax1 = fig.add_axes([0.115, 0.585, 0.865, 0.3]); ax2 = fig.add_axes([0.115, 0.115, 0.865, 0.27])
    ax1.plot(d.x, d.campus_10, marker="o", ms=2.6, lw=0, color=BLUE, label="10:00")
    ax1.plot(d.x, d.campus_18, marker="s", ms=2.6, lw=0, color=ORANGE, label="18:00")
    ax1.set_ylim(0, 231); ax1.set_yticks([0, 100, 200]); ax1.set_ylabel("bikes", labelpad=2)
    ax1.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, frameon=False, handletextpad=0.1, columnspacing=0.9, borderaxespad=0.15)
    ax2.bar(d.x, -d.drop_12_20, width=0.72, color=BLUE)
    ax2.axhline(-d.drop_12_20.mean(), color=INK2, lw=0.7, ls=(0, (3, 2)))
    ax2.set_ylim(0, 130); ax2.set_yticks([0, 50, 100]); ax2.set_ylabel("bikes", labelpad=2)
    ticks = [(pd.Timestamp(t) - pd.Timestamp("2026-10-01")).days for t in ("2026-10-05", "2026-10-19", "2026-11-02", "2026-11-16")]
    for ax in (ax1, ax2):
        ax.set_xlim(0, 47.5); ax.set_xticks(ticks); ax.set_xticklabels(["5 Oct", "19 Oct", "2 Nov", "16 Nov"]); grid(ax)
        for day in ("2026-10-09", "2026-10-23", "2026-10-26"):           # days without classes inside the weeks
            ax.axvspan((pd.Timestamp(day) - pd.Timestamp("2026-10-01")).days - 0.42, (pd.Timestamp(day) - pd.Timestamp("2026-10-01")).days + 0.42, color=GRID, lw=0, zorder=0)
    ax1.set_xticklabels([])
    title(fig, 0.01, 0.995, "(a) Bikes at the 8 campus stations")
    title(fig, 0.01, 0.475, "(b) Bikes gone from them within 20 min of the 12:00 bell")
    save(fig, "fig_final_weeks.png", ax=ax1)

# ======================= transfer by weeks of local data; zero-shot by week =======================
f = FINAL / "transfer" / "weeks_metrics.csv"
if f.exists():
    m = pd.read_csv(f); ci = pd.read_csv(FINAL / "transfer" / "weeks_ci.csv"); wk = pd.read_csv(FINAL / "transfer" / "zero_shot_by_week.csv")
    m = m[m.h == 30]
    fig = plt.figure(figsize=(W, 1.72))
    ax1 = fig.add_axes([0.13, 0.215, 0.36, 0.56]); ax2 = fig.add_axes([0.625, 0.215, 0.355, 0.56])
    for sub, ls, mk in (("all309", "-", "o"), ("campus8", (0, (3, 1.5)), "s")):
        z = m[(m.model == "zero_shot") & (m.subset == sub)].auc.iloc[0]
        for model, col in (("fine_tuned", BLUE), ("local_only", ORANGE)):
            r = m[(m.model == model) & (m.subset == sub)].sort_values("weeks")
            c = ci[(ci.model == model) & (ci.subset == sub)].sort_values("weeks")
            xs = np.r_[0, r.weeks.values] if model == "fine_tuned" else r.weeks.values
            ys = np.r_[z, r.auc.values] if model == "fine_tuned" else r.auc.values
            ax1.plot(xs, ys, color=col, lw=1.0, ls=ls, marker=mk, ms=2.6)
            for _, cc in c.iterrows():
                xo = cc.weeks + (-0.06 if model == "fine_tuned" else 0.06)      # side by side, not on top of each other
                ax1.plot([xo, xo], [cc.auc_lo, cc.auc_hi], color=col, lw=0.6)
    ax1.set_xticks([0, 1, 2, 3, 4]); ax1.set_xlim(-0.3, 4.3); ax1.set_xlabel("weeks of NSYSU data", labelpad=2)
    lo = np.floor(min(m.auc.min(), ci.auc_lo.min()) * 100) / 100; hi = np.ceil(max(m.auc.max(), ci.auc_hi.max()) * 100) / 100
    ax1.set_ylim(lo, hi); ax1.set_ylabel("AUC, h = 30 min", labelpad=2); grid(ax1)
    from matplotlib.lines import Line2D
    ax1.legend(handles=[Line2D([], [], color=BLUE, lw=1.0, label="fine-tuned"), Line2D([], [], color=ORANGE, lw=1.0, label="local only"),
                        Line2D([], [], color=INK2, lw=1.0, marker="o", ms=2.6, label="309 stations"), Line2D([], [], color=INK2, lw=1.0, ls=(0, (3, 1.5)), marker="s", ms=2.6, label="campus")],
               loc="lower left", bbox_to_anchor=(-0.34, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.15, fontsize=5.9, handlelength=1.9)
    w30 = wk[(wk.h == 30) & (wk.days >= 3)]      # a week needs three logged days to be drawn
    for sub, col, mk, lab in (("all309", BLUE, "o", "309 stations"), ("campus8", ORANGE, "s", "campus")):
        r = w30[w30.subset == sub].sort_values("week")
        ax2.plot(r.week, r.auc, color=col, lw=1.0, marker=mk, ms=2.6, label=lab)
    ax2.set_xticks(sorted(w30.week.unique())); ax2.set_xlabel("week of the semester", labelpad=2)
    ax2.set_ylim(np.floor(w30[w30.subset.isin(["all309", "campus8"])].auc.min() * 50) / 50, 1.0); ax2.set_ylabel("zero-shot AUC", labelpad=2); grid(ax2)
    ax2.legend(loc="lower left", bbox_to_anchor=(-0.05, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.15, fontsize=5.9)
    title(fig, 0.01, 0.995, "(a) Local data"); title(fig, 0.53, 0.995, "(b) Week by week")
    save(fig, "fig_final_transfer.png", ax=ax1)

# ======================= the after-class forecast =======================
f = FINAL / "forecast" / "forecast_by_bell.csv"
if f.exists():
    by = pd.read_csv(f); rel = pd.read_csv(FINAL / "forecast" / "forecast_reliability.csv")
    fig = plt.figure(figsize=(W, 1.85))
    ax1 = fig.add_axes([0.115, 0.2, 0.47, 0.6]); ax2 = fig.add_axes([0.725, 0.2, 0.255, 0.6])
    x = np.arange(len(by))
    for col, c, lab, mk, lw in (("mae_persistence", MUTED, "persistence", "v", 0.9), ("mae_seasonal", ORANGE, "seasonal mean", "s", 0.9),
                                ("mae_chain_hourly", AQUA, "chain, hourly rates", "^", 0.9), ("mae_chain", BLUE, "chain, 10-min rates", "o", 1.3)):
        ax1.plot(x, by[col], color=c, lw=lw, marker=mk, ms=2.4, label=lab)
    ax1.set_xticks([1, 4, 7, 10, 13]); ax1.set_xticklabels([by.bell.values[k][:2] for k in (1, 4, 7, 10, 13)])
    ax1.set_ylim(0, 14.5); ax1.set_yticks([0, 4, 8, 12]); ax1.set_ylabel("mean error, bikes", labelpad=2); ax1.set_xlabel("class end (bell)", labelpad=2); grid(ax1)
    ax1.legend(loc="lower left", bbox_to_anchor=(-0.2, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.15, fontsize=5.9)
    ax2.plot([0, 1], [0, 1], color=INK2, lw=0.6, ls=(0, (3, 2)))
    for sub, c, mk, lab in (("all309", BLUE, "o", "309 stations"), ("campus8", ORANGE, "s", "campus")):
        r = rel[(rel.subset == sub) & (rel.event == "empty") & (rel.bin >= 0) & (rel.n >= 25)]
        ax2.plot(r.p_mean, r.observed, color=c, lw=1.0, marker=mk, ms=2.6, label=lab)
    ax2.set_xlim(0, 0.8); ax2.set_ylim(0, 0.8); ax2.set_xticks([0, 0.4, 0.8]); ax2.set_yticks([0, 0.4, 0.8])
    ax2.set_xlabel("forecast P(empty)", labelpad=2); ax2.set_ylabel("share empty", labelpad=2); grid(ax2)
    ax2.legend(loc="lower left", bbox_to_anchor=(-0.42, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.7, borderaxespad=0.15, fontsize=5.9)
    title(fig, 0.01, 0.995, "(a) Campus stock 20 min after a bell"); title(fig, 0.62, 0.995, "(b) Reliability")
    save(fig, "fig_final_forecast.png", ax=ax1)

# ======================= the planner at NSYSU by time of day =======================
f = FINAL / "planner" / "planner_by_slot.csv"
if f.exists():
    p = pd.read_csv(f)
    fig = plt.figure(figsize=(W, 1.75))
    ax1 = fig.add_axes([0.125, 0.2, 0.36, 0.6]); ax2 = fig.add_axes([0.625, 0.2, 0.355, 0.6])
    hours = p.t_min / 60
    smooth = lambda v: v.rolling(3, center=True, min_periods=1).mean()          # 30-minute running mean
    ax1.fill_between(hours, p.unmet_p25, p.unmet_p75, color=BLUE, alpha=0.18, lw=0)
    ax1.plot(hours, p.unmet_mean, color=BLUE, lw=1.1, label="309 stations")
    ax1.plot(hours, p.unmet_campus_mean, color=ORANGE, lw=1.1, label="campus (8)")
    ax2.plot(hours, smooth(p.dropped_campus), color=ORANGE, lw=1.1, label="delivered to campus")
    ax2.plot(hours, smooth(p.picked_campus), color=AQUA, lw=1.1, label="taken from campus")
    for ax in (ax1, ax2):
        ax.set_xlim(6, 23); ax.set_xticks([6, 9, 12, 15, 18, 21]); ax.set_xlabel("time of day", labelpad=2); grid(ax)
        for b in (12, 16, 17):
            ax.axvline(b, color=INK2, lw=0.5, ls=(0, (2, 2)), zorder=0)
    top = 200 * np.ceil(p.unmet_p75.max() / 200)
    ax1.set_ylim(0, top * 1.02); ax1.set_yticks(np.arange(0, top + 1, 200)); ax1.set_ylabel("unmet rentals, next 90 min", labelpad=2)
    ax2.set_ylim(0, 34); ax2.set_yticks([0, 10, 20, 30]); ax2.set_ylabel("bikes per plan", labelpad=2)
    ax1.legend(loc="lower left", bbox_to_anchor=(-0.36, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.15, fontsize=5.9)
    ax2.legend(loc="lower left", bbox_to_anchor=(-0.42, 1.0), ncol=1, frameon=False, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.15, fontsize=5.9, labelspacing=0.2)
    title(fig, 0.01, 0.995, "(a) Expected without a truck"); title(fig, 0.53, 0.995, "(b) The one-truck plan")
    save(fig, "fig_final_planner.png", ax=ax1)

# ======================= architecture as deployed (replaces the midterm diagram) =======================
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

fig = plt.figure(figsize=(W, 2.95))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
FILL = {"src": "#eeeeea", "tab": "#e8f0fb", "mod": "#d6e5f8", "out": "#fde8df"}
EDGE = {"src": MUTED, "tab": SEQ[5], "mod": BLUE, "out": ORANGE}
BOXES = []


def abox(x, y, w, h, head, lines, kind):
    BOXES.append((x, y, x + w, y + h))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=FILL[kind], ec=EDGE[kind], lw=0.8))
    ax.text(x + w / 2, y + h - 1.6, head, ha="center", va="top", fontsize=6.6, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + 1.4, lines, ha="center", va="bottom", fontsize=5.5, color=INK2, linespacing=1.15)


def aarrow(x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=5, lw=0.7, color=INK2, shrinkA=0, shrinkB=0))


ax.text(1, 98, "NTU lane: open data, method development", fontsize=6.2, color=INK2, va="top", style="italic")
ax.text(67, 98, "NSYSU lane: deployment", fontsize=6.2, color=INK2, va="top", style="italic")
ax.plot([65.5, 65.5], [2, 94], color=GRID, lw=0.6, ls=(0, (3, 2)))
abox(1, 78, 30, 14, "Trip records [1]", "monthly zip, 10 months\n10.2 M trips, hourly", "src")
abox(33, 78, 30, 14, "Snapshots [2]", "295 days, every 10 min\n2.97 M station records", "src")
abox(67.5, 78, 31.5, 14, "Live station API [12]", "GitHub Actions logger\n309 stations, 10 min", "src")
abox(1, 59, 30, 13, "flows_hourly", "station × hour:\nrentals, returns", "tab")
abox(33, 59, 30, 13, "panel_10min", "station × 10 min:\nbikes, docks, capacity", "tab")
abox(67.5, 59, 31.5, 13, "NSYSU panel", "station × 10 min\n+ calendar, catalogue", "tab")
abox(1, 40, 30, 13, "Reconcile (2.3)", "residual → truck moves\nexposure → rates λ", "mod")
abox(33, 40, 30, 13, "Features (2.4)", "time, bell, state,\nneighbours, flows", "mod")
abox(67.5, 40, 31.5, 13, "Chain rates (2.7)", "fitted to stock changes,\nper hour and per 10 min", "mod")
abox(1, 21, 30, 13, "Simulator (2.6)", "real trips, K trucks;\nunmet, empty-min, km", "out")
abox(33, 21, 30, 13, "Predictor (2.4)", "GBM + Poisson roll-out,\nP(empty in 30–120 min)", "mod")
abox(67.5, 21, 31.5, 13, "Transfer (2.5)", "NTU model zero-shot,\n0–4 weeks of local data", "out")
abox(33, 2, 30, 13, "Planner (2.6)", "route search with\nannealing and 2-opt", "out")
abox(67.5, 2, 31.5, 13, "Live app (2.8)", "where to borrow, where\nto return; truck route", "out")
for xx in (16, 48, 83.25):
    aarrow(xx, 78, xx, 72.3); aarrow(xx, 59, xx, 53.3)
aarrow(48, 40, 48, 34.3); aarrow(16, 40, 16, 34.3); aarrow(31, 46.5, 33, 46.5)
aarrow(48, 21, 48, 15.3); aarrow(33, 8.5, 16, 8.5); aarrow(16, 8.5, 16, 21)
aarrow(63, 27.5, 67.5, 27.5); aarrow(83.25, 40, 83.25, 34.3); aarrow(83.25, 21, 83.25, 15.3)
aarrow(63, 8.5, 67.5, 8.5)
check(fig, "fig_architecture_final.png", boxes=BOXES, ax=ax, marks=False)
fig.savefig(OUT / "fig_architecture_final.png"); plt.close(fig)
print("wrote fig_architecture_final.png")

# ======================= hourly against 10-minute rates at the campus stations =======================
f = RATES / "rates_slots.csv"
if f.exists():
    sys.path.insert(0, str(Path(__file__).parent))
    from nsysu_data import CAMPUS  # noqa: E402
    rs = pd.read_csv(f, dtype={"sno": str}); rh = pd.read_csv(RATES / "rates.csv", dtype={"sno": str})
    rs = rs[rs.sno.isin(CAMPUS)].groupby("slot")[["lam_r", "lam_q"]].sum()
    rh = rh[rh.sno.isin(CAMPUS) & (rh.offday == 0)].groupby("hod")[["lam_r", "lam_q"]].sum()
    fig = plt.figure(figsize=(W, 2.2))
    axes = [fig.add_axes([0.125, 0.6, 0.855, 0.265]), fig.add_axes([0.125, 0.15, 0.855, 0.245])]
    for ax, col, colour, head in ((axes[0], "lam_r", BLUE, "(a) Rentals"), (axes[1], "lam_q", ORANGE, "(b) Returns")):
        hx = np.r_[rh.index.values, rh.index.values[-1] + 1]
        ax.step(hx, np.r_[rh[col].values, rh[col].values[-1]], where="post", color=MUTED, lw=1.0, label="hourly rate")
        ax.plot(rs.index.values / 6 + 1 / 12, rs[col].values, color=colour, lw=1.3, label="10-minute rate")
        for b in (9, 12, 16, 17):
            ax.axvline(b, color=INK2, lw=0.6, ls=(0, (2, 2)), zorder=0)
        ax.set_xlim(6, 23); ax.set_xticks(range(6, 24, 3)); top = 100 * np.ceil(max(rs[col].max(), rh[col].max()) * 1.04 / 100)
        ax.set_ylim(0, top * 1.02); ax.set_yticks(np.arange(0, top + 1, 200 if top > 300 else 100)); ax.set_ylabel("bikes per hour", labelpad=2); grid(ax)
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.9, borderaxespad=0.15)
    axes[1].set_xlabel("time of day (teaching days)", labelpad=2)
    axes[0].tick_params(labelbottom=False)
    title(fig, 0.01, 0.995, "(a) Rental rate, 8 campus stations"); title(fig, 0.01, 0.52, "(b) Return rate")
    save(fig, "fig_final_rates.png", ax=axes[0])

# ======================= does the advice get a rider a bike (a dock)? =======================
f = FINAL / "rider" / "rider_summary.csv"
if f.exists():
    r = pd.read_csv(f)
    fig = plt.figure(figsize=(W, 1.9))
    panels = [("leave", "(a) Leaving campus,\n17:00-19:50", "chain0.9"), ("dock", "(b) Returning on\ncampus, 09:00-10:50", "chain0.95"), ("arrive", "(c) Borrowing below\ncampus, 08:30-10:50", "chain0.9")]
    axes = [fig.add_axes([0.115 + 0.295 * k, 0.2, 0.26, 0.5]) for k in range(3)]
    for ax, (name, head, used) in zip(axes, panels):
        g = r[r.scenario == name].set_index("strategy")
        cs = [c for c in g.index if c.startswith("counts")]; ch = [c for c in g.index if c.startswith("chain")]
        ax.plot(g.loc[cs, "extra_walk_min"], 100 * g.loc[cs, "success"], color=MUTED, lw=1.0, marker="s", ms=2.6, label="live counts, at least K")
        ax.plot(g.loc[ch, "extra_walk_min"], 100 * g.loc[ch, "success"], color=BLUE, lw=1.2, marker="o", ms=2.8, label="chance on arrival (chain)")
        ax.plot([0], [100 * g.loc["nearest", "success"]], marker="D", ms=3.6, lw=0, color=ORANGE, label="nearest station")
        ax.plot([g.loc[used, "extra_walk_min"]], [100 * g.loc[used, "success"]], marker="o", ms=6.5, mfc="none", mec=BLUE, mew=0.9, lw=0)
        ax.set_ylim(58, 101); ax.set_yticks([60, 70, 80, 90, 100]); top = float(g.loc[cs + ch, "extra_walk_min"].max()); ax.set_xlim(-0.08 * top - 0.15, top * 1.08)
        ax.set_xticks([0, 2, 4, 6] if top > 4 else [0, 1, 2, 3] if top > 2.4 else [0, 1, 2]); grid(ax)
        ax.set_xlabel("extra walk, min", labelpad=2)
        if ax is not axes[0]:
            ax.set_yticklabels([])
        ax.set_title(head, fontsize=6.6, loc="left", pad=3)
    axes[0].set_ylabel("got one on arrival, %", labelpad=2)
    axes[0].legend(loc="lower left", bbox_to_anchor=(-0.48, 1.4), ncol=3, frameon=False, handletextpad=0.3, columnspacing=0.9, borderaxespad=0.1, fontsize=6.0)
    save(fig, "fig_final_rider.png", ax=axes[0])

# ======================= simulated trucks at NSYSU =======================
f = FINAL / "sim" / "sim_summary.csv"
if f.exists():
    m = pd.read_csv(f)
    fig = plt.figure(figsize=(W, 1.75))
    ax = fig.add_axes([0.125, 0.2, 0.86, 0.6])
    series = [("evening", "unmet_campus", "no bike on campus, 17:00-20:00", BLUE, "o"), ("morning", "unmet_gateway", "no bike below campus, 08:00-11:00", ORANGE, "s"),
              ("morning", "refused_campus", "no dock on campus, 08:00-11:00", AQUA, "^")]
    for shift, col, lab, colour, mk in series:
        g = m[(m["shift"] == shift) & (m.policy == "campus")].sort_values("trucks")
        y = 100 * g[col + "_avoided"].values; lo = 100 * g[col + "_lo"].values; hi = 100 * g[col + "_hi"].values
        ax.plot(g.trucks, y, color=colour, lw=1.2, marker=mk, ms=3.2, label=lab)
        ax.vlines(g.trucks, lo, hi, color=colour, lw=0.8)
    ax.set_xticks([1, 2, 3]); ax.set_xlim(0.7, 3.3); ax.set_ylim(0, 100); ax.set_yticks([0, 25, 50, 75, 100]); grid(ax)
    ax.set_xlabel("trucks serving the campus corridor", labelpad=2); ax.set_ylabel("failed attempts avoided, %", labelpad=2)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.13, 1.0), ncol=1, frameon=False, handletextpad=0.4, borderaxespad=0.1, fontsize=6.0, labelspacing=0.25)
    save(fig, "fig_final_sim.png", ax=ax)
