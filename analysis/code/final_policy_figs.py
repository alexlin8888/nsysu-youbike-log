"""Figures of the voucher study (Sec. 3.10 of the report) and of the policy brief.

Usage: python final_policy_figs.py FINAL_DIR OUT_DIR

FINAL_DIR is analysis/results/final; run final_reward.py and final_policy.py first. Draws
  fig_final_reward.png   (a) bikes returned to the campus stations per half hour on the held-out teaching days, split by
                         which voucher rule pays them, (b) the share of time the stations are empty, (c) what each
                         measure of the what-if grid cuts, evening and morning
  fig_brief_timing.png   (a) and (b) with Chinese labels, wide, for report/build_brief.js
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401
from figcheck import check  # noqa: E402

FINAL, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.2})
UNPAID = "#c9c8c3"            # returns no rule pays: a quiet grey, distinct from the grid
tm = pd.read_csv(FINAL / "reward" / "reward_timing.csv")
G = pd.read_csv(FINAL / "policy" / "policy_grid.csv")
x = np.arange(len(tm))
now, pred, ret, empty = tm.paid_now_per_day.values, tm.paid_pred_per_day.values, tm.returns_per_day.values, 100 * tm.empty_share.values
bell = list(tm.time).index("17:00") - 0.5
hours = [k for k, t in enumerate(tm.time) if t.endswith(":00")]


def cut(window, reward, truck, stagger=0):
    g = G[(G.window == window) & (G.reward == reward) & (G.truck == truck) & (G.stagger == stagger)]
    return 100 * float(g.cut.iloc[0])


def save(fig, name, ax=None, allow_on_marks=()):
    check(fig, name, ax=ax, allow_on_marks=allow_on_marks)
    fig.savefig(OUT / name)
    plt.close(fig)
    print("wrote", name)


def returns_panel(ax, labels):
    kw = dict(width=0.78, edgecolor=SURF, linewidth=0.5)       # a thin surface gap between the stacked parts
    ax.bar(x, now, color=INK2, label=labels[0], **kw)
    ax.bar(x, pred - now, bottom=now, color=BLUE, label=labels[1], **kw)
    ax.bar(x, ret - pred, bottom=pred, color=UNPAID, label=labels[2], **kw)
    ax.axvline(bell, color=INK, lw=0.6, ls=(0, (3, 2)))
    ax.set_xlim(-0.6, len(tm) - 0.4); ax.set_ylim(0, 52); ax.set_yticks([0, 25, 50]); grid(ax)
    ax.set_xticks(hours); ax.set_xticklabels([])


def empty_panel(ax):
    ax.bar(x, empty, width=0.78, color=ORANGE)
    ax.axvline(bell, color=INK, lw=0.6, ls=(0, (3, 2)))
    ax.set_xlim(-0.6, len(tm) - 0.4); ax.set_ylim(0, 74); ax.set_yticks([0, 50]); grid(ax)
    ax.set_xticks(hours); ax.set_xticklabels([tm.time[k] for k in hours])
    top = int(np.argmax(empty))
    ax.text(top + 0.5, empty[top] + 2, f"{empty[top]:.0f}%", fontsize=6, color=INK2, va="bottom", ha="center")


# ======================= report figure =======================
fig = plt.figure(figsize=(W, 3.9))
ax1 = fig.add_axes([0.125, 0.715, 0.86, 0.19]); ax2 = fig.add_axes([0.125, 0.555, 0.86, 0.085])
ax3 = fig.add_axes([0.43, 0.085, 0.255, 0.33]); ax4 = fig.add_axes([0.725, 0.085, 0.255, 0.33])
returns_panel(ax1, ["today's rule pays", "predictive rule also pays", "no voucher"])
ax1.set_ylabel("bikes", labelpad=2)
ax1.text(bell + 0.12, 49, "17:00 bell", fontsize=6, color=INK2, va="top")
ax1.legend(loc="lower left", bbox_to_anchor=(-0.13, 1.0), ncol=3, frameon=False, handletextpad=0.3, columnspacing=0.8, borderaxespad=0.1, fontsize=5.9, handlelength=1.1)
empty_panel(ax2); ax2.set_ylim(0, 82); ax2.set_ylabel("%", labelpad=2)
rows = [("voucher, +25% response", cut("evening", 0.25, 0), cut("morning", 0.25, 0)),
        ("voucher, +50%", cut("evening", 0.5, 0), cut("morning", 0.5, 0)),
        ("voucher, +100%", cut("evening", 1.0, 0), cut("morning", 1.0, 0)),
        ("trucks before the bell", cut("evening", 0, 2), cut("morning", 0, 1)),
        ("trucks + voucher (+50%)", cut("evening", 0.5, 2), cut("morning", 0.5, 1)),
        ("staggered class ends", cut("evening", 0, 0, 1), None)]
y = np.arange(len(rows))[::-1]
for ax, col, name in ((ax3, 1, "evening"), (ax4, 2, "morning")):
    for k, r in enumerate(rows):
        v = r[col]
        if v is None:
            ax.text(0.6, y[k], "not tested", fontsize=5.8, color=MUTED, va="center")
            continue
        ax.barh(y[k], v, height=0.62, color=BLUE, edgecolor=SURF, linewidth=0.5)
        ax.text(v + 0.8, y[k], f"{v:.0f}%", fontsize=5.9, color=INK2, va="center")
    ax.set_xlim(0, 36); ax.set_xticks([0, 10, 20, 30]); ax.set_ylim(-0.6, len(rows) - 0.4); grid(ax, axis="x")
    ax.set_yticks(y); ax.tick_params(axis="y", length=0)
    ax.set_title(name, fontsize=6.5, color=INK2, loc="left", pad=2)
ax3.set_yticklabels([r[0] for r in rows]); ax4.set_yticklabels([])
fig.text(0.705, 0.012, "cut against today, %", fontsize=6.5, color=INK2, ha="center", va="bottom")
fig.text(0.01, 0.995, "(a) Bikes returned to campus per half hour, by which rule pays", fontsize=7.2, fontweight="bold", va="top")
fig.text(0.01, 0.675, "(b) Share of time campus stations are empty", fontsize=7.2, fontweight="bold", va="top")
fig.text(0.01, 0.478, "(c) What each measure cuts", fontsize=7.2, fontweight="bold", va="top")
save(fig, "fig_final_reward.png", ax=ax1)

# ======================= brief figure (Chinese, wide) =======================
fm.fontManager.addfont("/usr/share/fonts/truetype/arphic-bkai00mp/bkai00mp.ttf")      # the Kai face that stands in for 標楷體
plt.rcParams["font.family"] = ["Liberation Sans", "AR PL KaitiM Big5"]
fig = plt.figure(figsize=(6.85, 1.45))
ax1 = fig.add_axes([0.05, 0.19, 0.6, 0.56]); ax2 = fig.add_axes([0.72, 0.19, 0.27, 0.56])
returns_panel(ax1, ["現行規則會付", "預測型多付的", "沒有獎勵"])
ax1.set_xticklabels([tm.time[k] for k in hours])
ax1.text(bell + 0.12, 49, "17:00 下課", fontsize=7, color=INK2, va="top")
ax1.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=3, frameon=False, handletextpad=0.3, columnspacing=1.0, borderaxespad=0.1, fontsize=7.2, handlelength=1.1)
empty_panel(ax2)
ax2.set_xticks(hours[::2]); ax2.set_xticklabels([tm.time[k] for k in hours[::2]])
fig.text(0.005, 0.985, "每半小時還到校內 8 站的車（台／天）", fontsize=8, va="top")
fig.text(0.68, 0.985, "校內站沒車的時間（%）", fontsize=8, va="top")
save(fig, "fig_brief_timing.png", ax=ax1)
