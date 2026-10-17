"""Report figures added in v10 to show the method and the results as figures rather than tables.

Usage: python figs_v4.py NTU_DIR TIMETABLE_DIR MODEL_DIR SIM_DIR OUT_DIR

  fig_method.png      (a) one NTU station-day: observed stock, the stock implied by trips alone, empty (censored)
                      spells and the inferred truck moves per hour; (b) the birth-death roll-out of Sec. 2.4.1
  fig_bells.png       students released by each bell vs. bikes leaving the NSYSU campus in the next 20 min
  fig_nsysu.png       (a) NSYSU transfer AUC with station-day bootstrap intervals; (b) change in AUC from the
                      timetable features, leave-one-day-out, with day-bootstrap intervals
  fig_sim_ci.png      unmet rentals and empty station-minutes avoided by policy and fleet size, with day-bootstrap
                      intervals
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, Patch
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from figcheck import check  # noqa: E402

NTU, TT, MODEL, SIM, OUT = (Path(a) for a in sys.argv[1:6])
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "legend.fontsize": 6.2})
rng = np.random.default_rng(11)


def save(fig, name, ax=None, allow_outside=False, marks=True, allow_on_marks=()):
    check(fig, name, ax=ax, allow_outside=allow_outside, marks=marks, allow_on_marks=allow_on_marks)
    fig.savefig(OUT / name)
    plt.close(fig)


def title(fig, x, y, text):
    fig.text(x, y, text, fontsize=7.2, fontweight="bold", va="top")


# ======================= method: one station-day and the roll-out chain =======================
SNO, DAY = "500119087", "2024-09-25"           # NTU Main Library (SW), 30 docks, a Wednesday
h = pd.read_parquet(NTU / "hourly.parquet")
h = h[h.sno.astype(str) == SNO]
p = pd.read_parquet(NTU / "panel_10min.parquet")
p = p[p.sno.astype(str) == SNO]
d0 = pd.Timestamp(DAY) + pd.Timedelta(hours=6)
d1 = pd.Timestamp(DAY) + pd.Timedelta(hours=23)
q = p[(p.ts >= d0) & (p.ts <= d1)].sort_values("ts")
hh = h[(h.hour >= d0) & (h.hour < d1)].sort_values("hour")
cap = int(q.total.max())
xq = ((q.ts - pd.Timestamp(DAY)).dt.total_seconds() / 3600).values
xh = ((hh.hour - pd.Timestamp(DAY)).dt.total_seconds() / 3600).values
implied = np.r_[hh.stock0.iloc[0], hh.stock0.iloc[0] + (hh.returns - hh.rentals).cumsum().values]

fig = plt.figure(figsize=(W, 2.6))
ax = fig.add_axes([0.14, 0.573, 0.83, 0.3])
axm = fig.add_axes([0.14, 0.423, 0.83, 0.112])
axd = fig.add_axes([0, 0, 1, 0.3077]); axd.set_xlim(0, 100); axd.set_ylim(0, 24.6); axd.axis("off")   # equal x/y scale
# empty spells (stock 0 at a 10-minute snapshot): rentals there cannot be observed
emp = (q.bikes.values == 0)
for i in np.where(emp)[0]:
    ax.axvspan(xq[i], xq[i] + 1 / 6, color=GRID, lw=0, gid="bg")
ax.step(xq, q.bikes, where="post", color=BLUE, lw=1.3, label="observed stock")
ax.plot(np.r_[xh, xh[-1] + 1], implied, color=ORANGE, lw=1.1, ls=(0, (3, 1.6)), label="trips only, no trucks")
ax.axhline(cap, color=INK2, lw=0.6)
ax.text(14.5, cap + 1.5, f"capacity {cap} docks", ha="center", va="bottom", fontsize=6.0, color=INK2)
ax.set_xlim(6, 23); ax.set_ylim(-5, 65); ax.set_yticks([0, 30, 60])
ax.set_xticks(range(6, 24, 3)); ax.set_xticklabels([])
ax.set_ylabel("bikes", labelpad=2)
grid(ax)
hl, ll = ax.get_legend_handles_labels()
hl.append(Patch(facecolor=GRID, edgecolor="none")); ll.append("empty: rentals censored")
ax.legend(hl, ll, loc="lower left", bbox_to_anchor=(-0.01, 1.0), ncol=3, frameon=False, handlelength=1.6,
          columnspacing=0.8, borderaxespad=0.2, handletextpad=0.4, fontsize=5.9)
title(fig, 0.01, 0.995, "(a) One station-day: trips, stock and trucks")
mv = hh[(hh.move == 1) & (hh.resid.abs() >= 5)]      # the hours that carry the flagged 3-h residual
xs_m = ((mv.hour - pd.Timestamp(DAY)).dt.total_seconds() / 3600).values + 0.5
axm.bar(xs_m, mv.resid.clip(lower=0), width=0.7, color=BLUE, lw=0)
axm.bar(xs_m, mv.resid.clip(upper=0), width=0.7, color=BLUE, alpha=0.45, lw=0)
axm.axhline(0, color=MUTED, lw=0.5)
axm.set_xlim(6, 23); axm.set_ylim(-55, 55); axm.set_yticks([-40, 0, 40])
axm.set_xticks(range(6, 24, 3)); axm.set_xticklabels([f"{t:02d}:00" for t in range(6, 24, 3)])
axm.set_ylabel("truck\nmoves", labelpad=2, fontsize=6.0, linespacing=1.0)
for xx, rr in zip(xs_m, mv.resid.values):
    axm.text(xx + 0.5, rr * 0.5, f"{rr:+.0f}".replace("-", "−"), ha="left", va="center", fontsize=5.9, color=INK2)
for a in (ax, axm):
    for xb in (12 + 10 / 60, 17 + 20 / 60):
        a.axvline(xb, color=INK2, lw=0.5, ls=(0, (2, 2)), gid="bg")

# (b) birth-death chain of the roll-out
title(fig, 0.01, 0.30, "(b) Roll-out: P(empty within h) from a birth–death chain")
states = [("0", 9), ("1", 25), ("2", 41), ("3", 57), ("…", 73), ("c", 89)]
yc, r = 10.0, 4.6
for lab, xc in states:
    empty = lab == "0"
    if lab != "…":
        axd.add_patch(Circle((xc, yc), r, fc="#fde8df" if empty else "#e8f0fb", ec=ORANGE if empty else BLUE, lw=0.9))
    axd.text(xc, yc, lab, ha="center", va="center", fontsize=7.2, color=INK, fontweight="bold" if empty else "normal")
for (la, xa), (lb, xb) in zip(states[:-1], states[1:]):
    if la != "0":           # no return out of the empty state: it is absorbing for the first-passage probability
        axd.add_patch(FancyArrowPatch((xa + r + 0.4, yc + 2.0), (xb - r - 0.4, yc + 2.0), connectionstyle="arc3,rad=-0.45",
                                      arrowstyle="-|>", mutation_scale=6, lw=0.8, color=AQUA))
    axd.add_patch(FancyArrowPatch((xb - r - 0.4, yc - 2.0), (xa + r + 0.4, yc - 2.0), connectionstyle="arc3,rad=-0.45",
                                  arrowstyle="-|>", mutation_scale=6, lw=0.8, color=PURPLE))
axd.text(49, 17.0, "return, rate λq(τ)", ha="center", va="bottom", fontsize=6.2, color=INK2)
axd.text(57, 3.3, "rental, rate λr(τ) (censoring-corrected)", ha="center", va="top", fontsize=6.2, color=INK2)
axd.text(4.0, 16.5, "empty (absorbing)", ha="left", va="bottom", fontsize=6.0, color=INK2)
save(fig, "fig_method.png", ax=ax)
print(f"method: station {SNO} {DAY}, capacity {cap}, moves {list(zip(xs_m - 0.5, mv.resid.values))}, "
      f"empty slots {int(emp.sum())}, rentals {int(hh.rentals.sum())}, returns {int(hh.returns.sum())}")

# ======================= bells: students released vs. campus outflow =======================
b = pd.read_csv(TT / "bell_outflow.csv")
b = b[b.out20.notna() & (b.bell >= 9 * 60) & (b.bell <= 18 * 60)]
fig = plt.figure(figsize=(W, 1.7))
ax = fig.add_axes([0.16, 0.22, 0.81, 0.56])
rho = {}
for kind, col, lab in (("placebo", MUTED, "20 min starting 30 min before the bell"), ("bell", BLUE, "20 min after the bell")):
    d = b[b.kind == kind]
    rho[kind] = spearmanr(d.released, d.out20)[0]
    jitter = rng.uniform(-0.03, 0.03, len(d))
    if kind == "placebo":
        ax.scatter(d.released / 1000 + jitter, d.out20, s=11, facecolor="none", edgecolor=col, lw=0.7, label=f"{lab}, ρ = {rho[kind]:.2f}")
    else:
        ax.scatter(d.released / 1000 + jitter, d.out20, s=11, color=col, lw=0, label=f"{lab}, ρ = {rho[kind]:.2f}")
ax.set_xlim(-0.2, 4.9); ax.set_xticks([0, 1, 2, 3, 4]); ax.set_ylim(0, 110); ax.set_yticks([0, 50, 100])
ax.set_xlabel("students whose class ends at the bell (thousand)", labelpad=2)
ax.set_ylabel("bikes leaving campus\nstations in 20 min", labelpad=2)
ax.legend(loc="lower left", bbox_to_anchor=(-0.01, 1.0), ncol=1, frameon=False, handletextpad=0.3, borderaxespad=0.2,
          labelspacing=0.3, fontsize=6.2)
grid(ax, "both")
save(fig, "fig_bells.png", ax=ax)
print(f"bells: n={len(b[b.kind == 'bell'])}, rho={rho}")

# ======================= NSYSU: transfer and timetable features =======================
ci = pd.read_csv(MODEL / "ci_v2" / "ci_transfer.csv")
ci = ci[ci.h == 30]
td = pd.read_csv(MODEL / "timetable" / "tt_diff.csv")
td = td[(td.a == "inv+tt") & (td.b == "inv")]
fig = plt.figure(figsize=(W, 1.75))
ax1 = fig.add_axes([0.215, 0.2, 0.285, 0.62])
ax2 = fig.add_axes([0.725, 0.2, 0.255, 0.62])
models = [("persistence", "persistence"), ("seasonal_nsysu", "seasonal"), ("ntu_zero_shot", "NTU zero-shot"),
          ("ntu_finetuned", "NTU fine-tuned"), ("nsysu_only", "NSYSU only")]
for k, (sub, col, lab, mk) in enumerate((("all309", BLUE, "309 stations", "o"), ("campus8", ORANGE, "campus", "s"))):
    for i, (m, _) in enumerate(models):
        r = ci[(ci.subset == sub) & (ci.model == m)].iloc[0]
        y = len(models) - 1 - i + (0.14 if k == 0 else -0.14)
        ax1.plot([r.auc_lo, r.auc_hi], [y, y], color=col, lw=1.0)
        ax1.plot([r.auc], [y], marker=mk, ms=3.2, color=col, lw=0, label=lab if i == 0 else None)
ax1.set_yticks(range(len(models))); ax1.set_yticklabels([l for _, l in models][::-1], fontsize=6.3)
ax1.set_xlim(0.6, 1.0); ax1.set_xticks([0.6, 0.7, 0.8, 0.9, 1.0]); ax1.set_xticklabels(["0.6", "0.7", "0.8", "0.9", "1"])
ax1.set_ylim(-0.6, len(models) - 0.4)
ax1.set_xlabel("AUC, h = 30 min", labelpad=2)
ax1.tick_params(axis="y", length=0)
ax1.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=2, frameon=False, handletextpad=0.2, columnspacing=0.8,
           borderaxespad=0.2, fontsize=6.0)
grid(ax1, "x")
subs = [("all309", "all"), ("campus8", "campus"), ("gateway11", "gateways"), ("prebell_campus", "pre-bell"),
        ("morning_gateway", "AM gateways")]
for k, (hz, col, mk) in enumerate(((30, BLUE, "o"), (60, ORANGE, "s"))):
    for i, (s_, _) in enumerate(subs):
        r = td[(td.h == hz) & (td.subset == s_)].iloc[0]
        y = len(subs) - 1 - i + (0.14 if k == 0 else -0.14)
        ax2.plot([r.d_auc_lo, r.d_auc_hi], [y, y], color=col, lw=1.0)
        ax2.plot([r.d_auc], [y], marker=mk, ms=3.2, color=col, lw=0, label=f"h = {hz}" if i == 0 else None)
ax2.axvline(0, color=INK2, lw=0.6)
ax2.set_yticks(range(len(subs))); ax2.set_yticklabels([l for _, l in subs][::-1], fontsize=6.3)
ax2.set_xlim(-0.02, 0.025); ax2.set_xticks([-0.02, 0, 0.02]); ax2.set_xticklabels(["−0.02", "0", "+0.02"])
ax2.set_ylim(-0.6, len(subs) - 0.4)
ax2.set_xlabel("ΔAUC with features", labelpad=2)
ax2.tick_params(axis="y", length=0)
ax2.legend(loc="lower left", bbox_to_anchor=(-0.3, 1.0), ncol=2, frameon=False, handletextpad=0.2, columnspacing=0.8,
           borderaxespad=0.2, fontsize=6.0)
grid(ax2, "x")
title(fig, 0.01, 0.995, "(a) Transfer to NSYSU")
title(fig, 0.53, 0.995, "(b) Timetable features")
save(fig, "fig_nsysu.png", ax=ax1)

# ======================= simulator: avoided unmet rentals and empty minutes =======================
POL = [("reactive", MUTED, "reactive", "o"), ("point", ORANGE, "point forecast", "s"), ("prob", BLUE, "probabilistic (ours)", "D")]
KS = [1, 3, 6]
rows = []
for k in KS:
    d = pd.read_csv(SIM / f"k{k}" / "sim_daily.csv")
    for metric in ("unmet", "empty_station_min"):
        w = d.pivot(index="date", columns="policy", values=metric)
        nd = len(w)
        idx = [rng.integers(0, nd, nd) for _ in range(1000)]
        for pol, *_ in POL:
            red = 1 - w[pol].sum() / w["none"].sum()
            bs = np.array([1 - w[pol].values[i].sum() / w["none"].values[i].sum() for i in idx])
            rows.append({"K": k, "metric": metric, "policy": pol, "red": red, "lo": np.percentile(bs, 2.5), "hi": np.percentile(bs, 97.5)})
R = pd.DataFrame(rows)
R.to_csv(OUT / "fig_sim_data.csv", index=False)
fig = plt.figure(figsize=(W, 1.62))
axes = [fig.add_axes([0.105, 0.14, 0.36, 0.62]), fig.add_axes([0.615, 0.14, 0.36, 0.62])]
for ax, metric, ylab, ylim, yt in ((axes[0], "unmet", "% unmet rentals avoided", (0, 32), [0, 10, 20, 30]),
                                    (axes[1], "empty_station_min", "% empty minutes avoided", (0, 48), [0, 10, 20, 30, 40])):
    for j, (pol, col, lab, mk) in enumerate(POL):
        d = R[(R.metric == metric) & (R.policy == pol)].set_index("K").reindex(KS)
        x = np.arange(len(KS)) + (j - 1) * 0.13
        ax.plot(x, d.red * 100, color=col, lw=1.0, marker=mk, ms=3.0, label=lab)
        ax.vlines(x, d.lo * 100, d.hi * 100, color=col, lw=0.9)
    ax.set_xticks(range(len(KS))); ax.set_xticklabels([f"{k} truck" + ("s" if k > 1 else "") for k in KS])
    ax.set_xlim(-0.4, len(KS) - 0.6); ax.set_ylim(*ylim); ax.set_yticks(yt)
    ax.set_ylabel(ylab, labelpad=2)
    grid(ax)
h_, l_ = axes[0].get_legend_handles_labels()
fig.legend(h_, l_, loc="upper left", bbox_to_anchor=(0.005, 0.925), ncol=3, frameon=False, handlelength=1.6, columnspacing=1.0,
           fontsize=6.2)
title(fig, 0.01, 0.995, "(a) Unmet rentals")
title(fig, 0.515, 0.995, "(b) Empty station-minutes")
save(fig, "fig_sim_ci.png", ax=axes[0])
print(R.round(3).to_string())
