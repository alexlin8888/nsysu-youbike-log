"""Does the size of a bell (students released by the catalogue) predict the campus outflow after it?

Usage: python timetable_bells.py LOGGER_DATA_DIR SESSIONS_CSV OUT_DIR

For every teaching day of the complete logger window (2-16 Oct 2026) and every official period end, the eight
campus stations are summarised over the 20 minutes after the bell:
  stock    campus bikes at the last 10-minute slot at or before the bell
  out20    bikes leaving: sum over stations and the two 10-minute steps of max(0, s[t-1] - s[t])
  in20     bikes arriving: the same with max(0, s[t] - s[t-1])
  net20    stock change over the 20 minutes
and joined with the number of students whose class ends at that bell on that weekday (released) and whose class
starts within 20 minutes after it (arriving). A placebo uses the same 20-minute windows started 30 minutes before
each bell. Writes bell_outflow.csv and prints rank correlations.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from features import TW_HOLIDAYS  # noqa: E402
from nsysu_data import CAMPUS, load_logger  # noqa: E402
from timetable import BELLS, START  # noqa: E402

DATA, SESS, OUT = (Path(a) for a in sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)
COMPLETE = [f"2026-10-{d:02d}" for d in range(2, 17)]
TEACH = [d for d in COMPLETE if pd.Timestamp(d).dayofweek < 5 and d not in TW_HOLIDAYS]

df = load_logger(DATA, days=set(COMPLETE))
df = df[df.sno.isin(CAMPUS)]
wide = df.pivot_table(index=["date", "slot"], columns="sno", values="bikes")
sess = pd.read_csv(SESS)


def window(day, s0):
    """campus stock at slot s0 and gross out/in flows over slots s0+1, s0+2."""
    try:
        w = wide.loc[day].reindex(range(s0, s0 + 3))
    except KeyError:
        return np.nan, np.nan, np.nan, np.nan
    if w.isna().all(axis=1).any():
        return np.nan, np.nan, np.nan, np.nan
    d = w.diff().iloc[1:]
    return (w.iloc[0].sum(), float((-d.clip(upper=0)).sum().sum()), float(d.clip(lower=0).sum().sum()),
            w.iloc[-1].sum() - w.iloc[0].sum())


rows = []
for day in TEACH:
    wd = pd.Timestamp(day).dayofweek + 1
    s = sess[sess.weekday == wd]
    for b in BELLS:
        released = int(s.loc[s.end == b, "enrolled"].sum())
        arriving = int(s.loc[(s.start > b) & (s.start <= b + 20), "enrolled"].sum())
        in_class = int(s.loc[(s.start <= b - 10) & (s.end > b + 10), "enrolled"].sum())
        for kind, t0 in (("bell", b), ("placebo", b - 30)):
            stock, out20, in20, net20 = window(day, t0 // 10)
            rows.append({"day": day, "weekday": wd, "bell": b, "kind": kind, "released": released, "arriving": arriving,
                         "in_class": in_class, "stock": stock, "out20": out20, "in20": in20, "net20": net20})
R = pd.DataFrame(rows)
R.to_csv(OUT / "bell_outflow.csv", index=False)

pd.set_option("display.width", 200)
for kind in ("bell", "placebo"):
    r = R[(R.kind == kind) & R.out20.notna() & (R.bell >= START["1"]) & (R.bell <= 18 * 60)]
    rho, p = spearmanr(r.released, r.out20)
    rho_s, p_s = spearmanr(r.released, r.out20 / r.stock.clip(lower=1))
    print(f"{kind}: n={len(r)}  rho(released, out20)={rho:.2f} (p={p:.1e})  rho(released, out20/stock)={rho_s:.2f} (p={p_s:.1e})")
r = R[(R.kind == "bell") & R.out20.notna()]
g = r.groupby("bell").agg(released=("released", "mean"), out20=("out20", "mean"), in20=("in20", "mean"),
                          stock=("stock", "mean"), net20=("net20", "mean"))
g.index = [f"{b // 60:02d}:{b % 60:02d}" for b in g.index]
print(g.round(1).to_string())
# within-time-of-day check: does the weekday-to-weekday variation of a bell's size explain its outflow?
r = r[(r.bell >= START["1"]) & (r.bell <= 18 * 60)].copy()
r["rel_dev"] = r.released - r.groupby("bell").released.transform("mean")
r["out_dev"] = r.out20 - r.groupby("bell").out20.transform("mean")
rho, p = spearmanr(r.rel_dev, r.out_dev)
print(f"within-bell deviations: n={len(r)} rho={rho:.2f} (p={p:.1e})")
