"""Midterm figures added after the first draft: horizon sweep and operator-inference checks.

Usage: python figs_v3.py SWEEP_DIR DEMAND_DIR CI_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from figcheck import check  # noqa: E402

SWEEP, DEMAND, CI, OUT = [Path(a) for a in sys.argv[1:5]]
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "legend.fontsize": 6.5})


def save(fig, name, ax=None, allow_outside=False, marks=True, allow_on_marks=()):
    check(fig, name, ax=ax, allow_outside=allow_outside, marks=marks, allow_on_marks=allow_on_marks)
    fig.savefig(OUT / name); plt.close(fig)


def panel_label(ax, text, y=1.0):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, fontweight="bold", va="bottom", ha="left")


# ======================= horizon sweep =======================
met = pd.read_csv(SWEEP / "sweep_metrics.csv")
ci = pd.read_csv(CI / "ci_predictor.csv") if (CI / "ci_predictor.csv").exists() else None
H = [30, 60, 90, 120]
models = [("seasonal", MUTED, "seasonal", ":"), ("mc_cens_cal", PURPLE, "Poisson roll-out (calibrated)", "-"),
          ("logistic", AQUA, "logistic regression", "-"), ("lgb_inv", ORANGE, "GBM, inventory only", "-"),
          ("lgb_full", BLUE, "GBM + trip flows", "-")]
fig = plt.figure(figsize=(W, 1.95))
ax1 = fig.add_axes([0.12, 0.2, 0.37, 0.56]); ax2 = fig.add_axes([0.62, 0.2, 0.36, 0.56])
for m, c, lab, ls in models:
    r = met[(met.model == m) & (met.subset == "all")].set_index("h").reindex(H)
    ax1.plot(H, r.auc, color=c, lw=1.3, ls=ls, marker="o", ms=2.6, label=lab)
    ax2.plot(H, r.brier, color=c, lw=1.3, ls=ls, marker="o", ms=2.6)
    if ci is not None and m in ("lgb_full", "mc_cens_cal"):
        cc = ci[(ci.model == m) & (ci.subset == "all")].set_index("h").reindex(H)
        ax1.fill_between(H, cc.auc_lo, cc.auc_hi, color=c, alpha=0.18, lw=0)
        ax2.fill_between(H, cc.brier_lo, cc.brier_hi, color=c, alpha=0.18, lw=0)
for ax in (ax1, ax2):
    ax.set_xticks(H); ax.set_xticklabels([str(h) for h in H]); ax.set_xlim(22, 128)
    ax.set_xlabel("horizon h (min)", labelpad=2)
    grid(ax)
ax1.set_ylim(0.78, 0.95); ax1.set_yticks([0.8, 0.85, 0.9, 0.95]); ax1.set_ylabel("AUC", labelpad=2)
ax2.set_ylim(0.06, 0.2); ax2.set_yticks([0.08, 0.12, 0.16, 0.2]); ax2.set_ylabel("Brier score", labelpad=2)
panel_label(ax1, "(a) Ranking quality", y=1.03); panel_label(ax2, "(b) Probability quality", y=1.03)
h_, l_ = ax1.get_legend_handles_labels()
fig.legend(h_, l_, loc="lower center", bbox_to_anchor=(0.5, 0.86), ncol=3, frameon=False, fontsize=6.0, handlelength=1.5, columnspacing=1.0)
save(fig, "fig_horizon.png", ax=ax1)

# ======================= operator-inference checks =======================
sens = pd.read_csv(DEMAND / "moves_sensitivity.csv")
rv = pd.read_csv(DEMAND / "rate_validation.csv")
chk = json.load(open(DEMAND / "moves_checks.json"))
fig = plt.figure(figsize=(W, 1.85))
ax1 = fig.add_axes([0.13, 0.21, 0.34, 0.52]); ax2 = fig.add_axes([0.61, 0.21, 0.34, 0.52])
wins = [1, 3, 6]; ths = [3, 5, 8]; xs = np.arange(len(ths)); wd = 0.26
cols = {1: SEQ[3], 3: BLUE, 6: SEQ[10]}
for k, w in enumerate(wins):
    v = [sens[(sens.window_h == w) & (sens.threshold == t)].drop_per_day.iloc[0] / 1000 for t in ths]
    ax1.bar(xs + (k - 1) * wd, v, width=wd - 0.03, color=cols[w], lw=0, label=f"{w} h window")
ax1.axhline(chk["jump_bikes_per_day_up"] / 1000, color=ORANGE, lw=0.9, ls=(0, (3, 2)), label="≥ 8-bike jumps")
ax1.set_xticks(xs); ax1.set_xticklabels([f"T = {t}" for t in ths]); ax1.set_xlabel("move threshold (bikes)", labelpad=2)
ax1.set_ylabel("drop-offs, thousand bikes/day", labelpad=2); ax1.set_ylim(0, 3.4); ax1.set_yticks([0, 1, 2, 3])
ax1.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=2, frameon=False, fontsize=5.8, handlelength=1.1, columnspacing=0.6, borderaxespad=0, handletextpad=0.4, labelspacing=0.3)
grid(ax1)
d = rv[(rv.hod >= 7) & (rv.hod <= 21)]
ax2.axhline(1, color=MUTED, lw=0.6)
ax2.plot(d.hod, d.ratio_naive, color=MUTED, lw=1.2, marker="o", ms=2.2, label="naive rate")
ax2.plot(d.hod, d.ratio_cens, color=BLUE, lw=1.4, marker="o", ms=2.2, label="corrected rate")
for xb in (12.17, 17.33):
    ax2.axvline(xb, color=ORANGE, lw=0.6, ls=(0, (3, 2)))
ax2.set_xticks([8, 12, 16, 20]); ax2.set_xlim(6.5, 21.5); ax2.set_ylim(0.85, 1.55); ax2.set_yticks([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
ax2.set_xlabel("hour of day (campus, weekdays)", labelpad=2, fontsize=6.5); ax2.set_ylabel("actual rentals / rate", labelpad=2)
ax2.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=1, frameon=False, fontsize=5.8, handlelength=1.2, borderaxespad=0, handletextpad=0.4, labelspacing=0.3)
grid(ax2)
fig.text(0.01, 0.985, "(a) Inferred truck volume", fontsize=7.2, fontweight="bold", va="top")
fig.text(0.50, 0.985, "(b) Rate check, well-stocked hours", fontsize=7.0, fontweight="bold", va="top")
save(fig, "fig_moves_check.png", ax=ax1)
print("written")
