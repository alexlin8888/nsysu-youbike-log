"""Static figures for the midterm report: system architecture and the updated Gantt chart."""
import datetime as dt
import sys
from pathlib import Path

from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import *  # noqa: E402,F401

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)

# ================= architecture / data flow =================
fig = plt.figure(figsize=(W, 2.45))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
FILL = {"src": "#eeeeea", "tab": "#e8f0fb", "mod": "#d6e5f8", "out": "#fde8df"}
EDGE = {"src": MUTED, "tab": SEQ[5], "mod": BLUE, "out": ORANGE}


def box(x, y, w, h, title, lines, kind, fs=5.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=FILL[kind], ec=EDGE[kind], lw=0.8))
    ax.text(x + w / 2, y + h - 1.4, title, ha="center", va="top", fontsize=fs + 0.6, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + 1.2, lines, ha="center", va="bottom", fontsize=fs - 0.2, color=INK2, linespacing=1.15)


def arrow(x0, y0, x1, y1, **kw):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=5, lw=0.7, color=INK2, shrinkA=0, shrinkB=0, **kw))


# lanes
ax.text(1, 97.5, "NTU (open data, method development)", fontsize=5.2, color=INK2, va="top", style="italic")
ax.text(67, 97.5, "NSYSU (deployment)", fontsize=5.2, color=INK2, va="top", style="italic")
ax.plot([65.5, 65.5], [2, 95], color=GRID, lw=0.6, ls=(0, (3, 2)))
# sources
box(1, 78, 30, 14, "Trip records [1]", "monthly zip, 10 months\n10.2 M trips in area, hourly", "src")
box(33, 78, 30, 14, "Inventory snapshots [2]", "295 days, every 10 min\n2.97 M station records", "src")
box(67.5, 78, 31.5, 14, "Live station API [12]", "GitHub Actions logger, 10 min\n309 stations, since 1 Oct", "src")
# tables
box(1, 59, 30, 13, "flows_hourly", "station × hour: rentals, returns\n(name → station id matching)", "tab")
box(33, 59, 30, 13, "panel_10min", "station × slot: bikes, docks, cap.\nforward-fill, staleness rule", "tab")
box(67.5, 59, 31.5, 13, "NSYSU panel", "station × slot: bikes, docks\nholiday / semester calendar", "tab")
# modules
box(1, 40, 30, 13, "Reconcile (2.3)", "Δs − (q − r) → truck moves\nexposure → censored rates λ", "mod")
box(33, 40, 30, 13, "Features + labels (2.4)", "time, bell, state, neighbours,\nflows → y30 / y60", "mod")
box(67.5, 40, 31.5, 13, "Inventory-only features", "same code, NSYSU bells\nno trip flows", "mod")
# models / outputs
box(1, 21, 30, 13, "Replay simulator (2.6)", "real trips, K trucks, policies\nunmet, empty-min, truck-km", "out")
box(33, 21, 30, 13, "LightGBM predictor", "P(empty within 30 / 60 min)\nBrier, AUC, ECE", "mod")
box(67.5, 21, 31.5, 13, "Transfer (2.5)", "zero-shot / fine-tune\nvs. NSYSU-only", "out")
box(33, 3, 30, 12, "Pre-emptive planner", "greedy: rentals saved per\ntruck-minute → route search", "out")
box(67.5, 3, 31.5, 12, "Live demo (planned)", "latest.json → map, P(empty),\nnext-bell truck plan", "out")
# arrows
for x in (16, 48, 83.25):
    arrow(x, 78, x, 72.3); arrow(x, 59, x, 53.3)
arrow(48, 40, 48, 34.3)
arrow(16, 40, 16, 34.3)
arrow(31, 46.5, 33, 46.5)          # reconcile -> features (flows / rates)
arrow(31, 27.5, 33, 27.5, connectionstyle="arc3,rad=0")  # simulator <- predictor
arrow(48, 21, 48, 15.3)            # predictor -> planner
arrow(33, 9, 16, 9); arrow(16, 9, 16, 21)   # planner -> simulator
arrow(63, 27.5, 67.5, 27.5)        # predictor -> transfer
arrow(83.25, 40, 83.25, 34.3)
arrow(83.25, 21, 83.25, 15.3)
fig.savefig(OUT / "fig_architecture.png")

# ================= Gantt (updated) =================
D = lambda m, d: dt.date(2026, m, d)
TODAY = D(10, 29)
tasks = [
    ("Data pipeline & matching", D(10, 1), D(10, 18), "PL", 1.0),
    ("Demand & operator moves", D(10, 10), D(10, 28), "JC", 1.0),
    ("Stockout predictor", D(10, 19), D(11, 14), "SL", 0.8),
    ("Calibration & transfer", D(11, 8), D(11, 25), "JC", 0.6),
    ("Planner & simulator", D(11, 5), D(12, 6), "PL", 0.4),
    ("NSYSU live demo app", D(11, 20), D(12, 14), "SL", 0.1),
    ("Report & presentation", D(11, 22), D(12, 22), "all", 0.15),
]
ms = [(D(10, 1), "Proposal"), (D(10, 29), "Midterm"), (D(11, 26), "Video"), (D(12, 24), "Final")]
start = D(9, 29); end = dt.date(2027, 1, 4)
fig, ax = plt.subplots(figsize=(2.6, 1.45))
n = len(tasks)
for i, (name, s, e, who, done) in enumerate(tasks):
    yv = n - 1 - i
    left, width = (s - start).days, (e - s).days
    ax.barh(yv, width, left=left, height=0.58, color=SEQ[2], linewidth=0)
    ax.barh(yv, width * done, left=left, height=0.58, color=BLUE if who != "all" else "#5598e7", linewidth=0)
    ax.text(left + 1.6, yv, who, va="center", ha="left", fontsize=4.6, color="white" if done > 0.15 else INK2, fontweight="bold")
    ax.text(left + width + 1.5, yv, f"{int(done * 100)}%", va="center", ha="left", fontsize=4.4, color=INK2)
ax.set_yticks(range(n)); ax.set_yticklabels([t[0] for t in tasks][::-1], fontsize=4.9)
ax.tick_params(axis="y", length=0)
months = [D(10, 1), D(11, 1), D(12, 1)]
ax.set_xticks([(m - start).days for m in months]); ax.set_xticklabels(["Oct", "Nov", "Dec"], fontsize=5.2)
ax.set_xlim(0, (end - start).days)
grid(ax, "x")
xt = (TODAY - start).days
ax.axvspan(0, xt, color="#f3f3f0", zorder=0)
for m, lab in ms:
    xm = (m - start).days
    ax.plot([xm, xm], [-0.6, n - 0.35], color=ORANGE, lw=0.7, linestyle=(0, (3, 2)), zorder=0)
    ax.plot([xm], [n - 0.35], marker="D", color=ORANGE, ms=2.6, clip_on=False)
    ax.text(xm, n + 0.02, f"{lab}\n{m.month}/{m.day}", ha=("right" if lab == "Final" else "center"), va="bottom", fontsize=4.5, color=ORANGE, linespacing=1.1)
ax.set_ylim(-0.6, n + 0.9)
for spine in ["left", "bottom"]:
    ax.spines[spine].set_visible(False)
fig.subplots_adjust(left=0.35, right=0.95, top=0.97, bottom=0.12)
fig.savefig(OUT / "fig_gantt_hw3.png")
print("written")
