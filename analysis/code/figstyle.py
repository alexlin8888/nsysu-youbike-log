"""Shared matplotlib style for all report figures (CVPR column width 3.25 in)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import font_manager as fm

# palette (dataviz reference instance, light mode)
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
PURPLE = "#8a5cd6"
CRIT, GOOD = "#d03b3b", "#1e9e5a"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8983", "#e6e5e1", "#ffffff"
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
       "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
seq_cmap = LinearSegmentedColormap.from_list("seqblue", SEQ)
CAT = [BLUE, ORANGE, AQUA, PURPLE, YELLOW]   # fixed categorical order

for f in ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
    try:
        fm.fontManager.addfont(f)
    except Exception:
        pass

plt.rcParams.update({
    "font.family": "Liberation Sans", "font.size": 7, "axes.titlesize": 7.5,
    "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.5, "xtick.color": INK2, "ytick.color": INK2,
    "axes.labelcolor": INK2, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.major.size": 2, "ytick.major.size": 2, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "savefig.dpi": 300, "savefig.facecolor": SURF, "figure.facecolor": SURF,
    "legend.frameon": False,
})
W = 3.25  # column width in inches


def grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
