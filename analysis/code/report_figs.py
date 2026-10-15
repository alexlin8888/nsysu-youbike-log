"""Figures for the midterm report from the model, transfer and simulation outputs.

Usage: python report_figs.py MODEL_DIR SIM_DIR OUT_DIR
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401

MODEL, SIM, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

# ---------- reliability diagram + metrics ----------
rel = pd.read_csv(MODEL / "reliability.csv")
met = pd.read_csv(MODEL / "metrics.csv")
fig = plt.figure(figsize=(W, 1.55))
ax1 = fig.add_axes([0.10, 0.2, 0.36, 0.72])
ax2 = fig.add_axes([0.60, 0.2, 0.38, 0.72])
ax1.plot([0, 1], [0, 1], color=MUTED, lw=0.6, ls=(0, (3, 2)))
styles = {"seasonal": (MUTED, "seasonal baseline"), "lgb_inv": (ORANGE, "GBM, inventory only"), "lgb_full": (BLUE, "GBM, + trip flows")}
for model, (c, lab) in styles.items():
    r = rel[(rel.h == 30) & (rel.model == model) & (rel.n > 200)]
    ax1.plot(r.p_mean, r.y_mean, color=c, lw=1.3, marker="o", ms=2.3, label=lab)
ax1.set_xlim(0, 1); ax1.set_ylim(0, 1)
ax1.set_xlabel("predicted P(empty within 30 min)", fontsize=5.8, labelpad=1)
ax1.set_ylabel("observed frequency", fontsize=5.8, labelpad=1)
ax1.set_xticks([0, 0.5, 1]); ax1.set_yticks([0, 0.5, 1])
ax1.legend(fontsize=5, loc="upper left", handlelength=1.3, borderaxespad=0.2, labelspacing=0.3)
ax1.set_title("(a) Reliability, NTU test (Apr–Jun 2025)", fontsize=6.2, loc="left", pad=2)
grid(ax1, "both")
# AUC bars by subset for h=30
order = ["persistence", "seasonal", "lgb_inv", "lgb_full"]
labels = {"persistence": "persist.", "seasonal": "seasonal", "lgb_inv": "GBM inv.", "lgb_full": "GBM full"}
subs = [("all", "all stations"), ("campus", "campus"), ("classend", "class-end")]
xs = np.arange(len(subs)); wdt = 0.2
cols = [MUTED, SEQ[3], ORANGE, BLUE]
for k, m in enumerate(order):
    v = [met[(met.h == 30) & (met.model == m) & (met.subset == s)].auc.iloc[0] for s, _ in subs]
    ax2.bar(xs + (k - 1.5) * wdt, v, width=wdt - 0.02, color=cols[k], lw=0, label=labels[m])
    for x, y in zip(xs + (k - 1.5) * wdt, v):
        ax2.text(x, y + 0.01, f"{y:.2f}", ha="center", va="bottom", fontsize=4.2, color=INK2, rotation=90)
ax2.set_ylim(0.5, 1.2); ax2.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0]); ax2.set_xticks(xs); ax2.set_xticklabels([l for _, l in subs], fontsize=5.8)
ax2.set_ylabel("AUC (h = 30 min)", fontsize=5.8, labelpad=1)
ax2.legend(fontsize=4.8, loc="upper left", ncol=2, handlelength=1, columnspacing=0.8, borderaxespad=0.1, labelspacing=0.25)
ax2.set_title("(b) Ranking quality by subset", fontsize=6.2, loc="left", pad=2)
grid(ax2)
fig.savefig(OUT / "fig_model.png")

# ---------- transfer figure ----------
tm = pd.read_csv(MODEL / "transfer" / "transfer_metrics.csv")
fig, ax = plt.subplots(figsize=(W * 0.8, 1.45))
fig.subplots_adjust(left=0.16, right=0.98, top=0.95, bottom=0.24)
models = [("persistence", "persist."), ("seasonal_nsysu", "seasonal\n(6 days)"), ("ntu_zero_shot", "NTU model\nzero-shot"),
          ("ntu_finetuned", "NTU model\n+ fine-tune"), ("nsysu_only", "NSYSU only\n(6 days)")]
xs = np.arange(len(models))
for k, (sub, c, lab) in enumerate((("all309", SEQ[3], "309 stations ≤ 5 km"), ("campus8", BLUE, "8 campus stations"))):
    v = [tm[(tm.h == 30) & (tm.model == m) & (tm.subset == sub)].auc.iloc[0] for m, _ in models]
    ax.bar(xs + (k - 0.5) * 0.36, v, width=0.34, color=c, lw=0, label=lab)
    for x, y in zip(xs + (k - 0.5) * 0.36, v):
        ax.text(x, y + 0.01, f"{y:.2f}", ha="center", va="bottom", fontsize=4.3, color=INK2, rotation=90)
ax.set_ylim(0.5, 1.2); ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0]); ax.set_xticks(xs); ax.set_xticklabels([l for _, l in models], fontsize=5)
ax.set_ylabel("AUC at NSYSU (h = 30 min)", fontsize=5.8, labelpad=1)
ax.legend(fontsize=4.8, loc="upper left", ncol=2, handlelength=1, borderaxespad=0.1, columnspacing=1)
grid(ax)
fig.savefig(OUT / "fig_transfer.png")

# ---------- simulation figure ----------
rows = []
for k in (1, 3, 6):
    s = pd.read_csv(SIM / f"k{k}" / "sim_summary.csv").set_index("policy")
    for pol in ("reactive", "point", "prob"):
        rows.append({"trucks": k, "policy": pol, "unmet_reduction": s.loc[pol, "unmet_reduction"],
                     "empty_reduction": 1 - s.loc[pol, "empty_station_min"] / s.loc["none", "empty_station_min"],
                     "bikes_moved": s.loc[pol, "bikes_moved"]})
sim = pd.DataFrame(rows)
sim.to_csv(OUT / "sim_by_trucks.csv", index=False)
fig = plt.figure(figsize=(W, 1.45))
ax1 = fig.add_axes([0.11, 0.22, 0.38, 0.68]); ax2 = fig.add_axes([0.60, 0.22, 0.38, 0.68])
pc = {"reactive": MUTED, "point": ORANGE, "prob": BLUE}
pl = {"reactive": "reactive", "point": "predictive (point)", "prob": "predictive (probabilistic)"}
xs = np.arange(3)
for ax, col, ttl in ((ax1, "unmet_reduction", "(a) Unmet rentals avoided"), (ax2, "empty_reduction", "(b) Empty station-minutes avoided")):
    for k, pol in enumerate(("reactive", "point", "prob")):
        v = sim[sim.policy == pol].sort_values("trucks")[col].values * 100
        ax.bar(xs + (k - 1) * 0.27, v, width=0.25, color=pc[pol], lw=0, label=pl[pol])
        for x, y in zip(xs + (k - 1) * 0.27, v):
            ax.text(x, y + 0.6, f"{y:.0f}", ha="center", va="bottom", fontsize=4.6, color=INK2)
    ax.set_xticks(xs); ax.set_xticklabels(["1 truck", "3 trucks", "6 trucks"], fontsize=5.8)
    ax.set_ylabel("% vs. no rebalancing", fontsize=5.8, labelpad=1)
    ax.set_title(ttl, fontsize=6.2, loc="left", pad=2)
    grid(ax)
ax1.set_ylim(0, 36); ax2.set_ylim(0, 48)
ax1.legend(fontsize=4.8, loc="upper left", handlelength=1, borderaxespad=0.2, labelspacing=0.3)
fig.savefig(OUT / "fig_sim.png")
print("figures written")
