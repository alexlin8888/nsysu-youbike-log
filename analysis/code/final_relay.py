"""Can the page tell a rider where the operator's reward will still be on offer on arrival?

Usage: python final_relay.py DATA_DIR RATES_DIR OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16]

Since 1 July 2026 YouBike in Kaohsiung pays a NT$5 ride voucher for borrowing at a station with no free dock, or
for returning a bike to a station with no bike ("friendship relay"). The station's state at the moment of
borrowing or returning decides, between 06:00 and 24:00. The operator's app shows which stations are empty or full
now; a rider needs to know which will be when the ride there is over. This script scores two answers on the
held-out teaching days, for the 19 stations between campus and metro, 10 and 20 minutes ahead:

  now     the station is empty (full) at this snapshot, so it will be then      what the operator's app shows
  page    the chain's chance that it is empty (full) then is at least a threshold   what the page marks

Rates are fitted up to --fit-end; the days after it are scored. Writes OUT_DIR/relay_summary.csv (one row per
event, group, period and horizon: how often each answer is right and how many of the cases it finds),
relay_thresholds.csv (the page's answer at thresholds 0.5 to 0.8) and relay_returns.csv (bikes that appeared at an
empty station per day, counted from the stock 10 minutes later: riders' returns and the operator's deliveries).

"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from route_planner import STEP, ChainValues, load_slot_rates  # noqa: E402

DATA, RATES, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIT_END, TEST_END = ARG("--fit-end", "2026-10-29"), ARG("--test-end", "2026-11-16")
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
FIRST, LAST = 36, 144                      # the reward runs from 06:00 to 24:00
THRESHOLD = 0.6                            # the chance from which the page marks a station (RELAY in site/src/app.js)
PERIODS = {"06-24": (36, 144), "17-20": (102, 120), "09-11": (54, 66)}
OUT.mkdir(parents=True, exist_ok=True)

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
GROUPS = {"campus": [sidx[s] for s in CAMPUS if s in sidx], "gateway": [sidx[s] for s in GATEWAY if s in sidx]}
GROUPS["corridor"] = GROUPS["campus"] + GROUPS["gateway"]

rates = pd.read_csv(RATES / "rates.csv", dtype={"sno": str})
prior = pd.read_csv(RATES / "rates_prior.csv")
R = np.zeros((N, 24)); Qr = np.zeros((N, 24))
for row in prior[prior.offday == 0].itertuples():
    R[:, row.hod] = row.pr; Qr[:, row.hod] = row.pq
for row in rates[(rates.offday == 0) & rates.sno.isin(sidx)].itertuples():
    R[sidx[row.sno], row.hod] = row.lam_r; Qr[sidx[row.sno], row.hod] = row.lam_q
chain = ChainValues(R, Qr, CAP, 90, 20, load_slot_rates(RATES / "rates_slots.csv", sidx))

df = load_logger(DATA)
df = df[df.sno.isin(sidx) & (df.age <= 20)].copy()
df["i"] = df.sno.map(sidx)
dstr = df.date.astype(str).str.slice(0, 10)
days = sorted(d for d in dstr.unique() if pd.Timestamp(d).dayofweek < 5 and d not in OFFDAYS)
test_days = [d for d in days if FIT_END < d <= TEST_END]

rows, back = [], []
for day in test_days:
    d = df[dstr == day]
    b = np.full((146, N), np.nan); k = np.full((146, N), np.nan)
    b[d.slot.values, d.i.values] = d.bikes.values; k[d.slot.values, d.i.values] = d.docks.values
    for slot in range(FIRST, LAST - 1):
        known = ~np.isnan(b[slot]) & ~np.isnan(k[slot])
        if known.sum() < 50:
            continue
        bikes = np.where(known, b[slot], 0).astype(int)
        P = np.zeros((N, chain.C + 1), np.float32); P[np.arange(N), np.clip(bikes, 0, CAP)] = 1.0
        for step in (1, 2):
            P = chain._fwd(slot * STEP + STEP * (step - 1), P)
            if slot + step >= LAST:
                break
            for j in GROUPS["corridor"]:
                if not known[j] or np.isnan(b[slot + step, j]) or np.isnan(k[slot + step, j]):
                    continue
                rows.append((day, slot, j, step * STEP, float(P[j, 0]), float(P[j, CAP[j]]), int(b[slot, j] == 0), int(k[slot, j] == 0),
                             int(b[slot + step, j] == 0), int(k[slot + step, j] == 0)))
    # bikes that arrived at a campus station that was empty: a stock increase from 0 between two snapshots
    for name, (a, z) in PERIODS.items():
        for g in ("campus", "gateway"):
            got = empty_slots = full_slots = left = 0
            for j in GROUPS[g]:
                for slot in range(a, z):
                    x0, x1, k0, k1 = b[slot, j], b[slot + 1, j], k[slot, j], k[slot + 1, j]
                    if np.isnan(x0) or np.isnan(x1):
                        continue
                    empty_slots += x0 == 0; full_slots += k0 == 0
                    if x0 == 0:
                        got += x1                    # every bike standing there 10 minutes later was returned to an empty station or brought by a truck
                    if k0 == 0 and not np.isnan(k1):
                        left += k1                   # every dock free 10 minutes later was freed by a rental from a full station or by a truck
            back.append((day, name, g, int(empty_slots), int(full_slots), float(got), float(left)))

res = pd.DataFrame(rows, columns=["day", "slot", "j", "ahead", "p_empty", "p_full", "empty_now", "full_now", "empty_then", "full_then"])
res["group"] = np.where(res.j.isin(GROUPS["campus"]), "campus", "gateway")


def score(g, event, th=THRESHOLD):
    y = g[event + "_then"].values; now = g[event + "_now"].values; p = g["p_" + event].values
    mark = p >= th
    out = {"cases": len(g), "share_true": y.mean(), "true_per_day": y.sum() / g.day.nunique()}
    out["now_marked"] = now.mean(); out["now_right"] = y[now == 1].mean() if now.sum() else np.nan; out["now_finds"] = now[y == 1].mean() if y.sum() else np.nan
    out["page_marked"] = mark.mean(); out["page_right"] = y[mark].mean() if mark.sum() else np.nan; out["page_finds"] = mark[y == 1].mean() if y.sum() else np.nan
    two = 0 < y.sum() < len(y)
    out["auc_page"] = roc_auc_score(y, p) if two else np.nan; out["auc_now"] = roc_auc_score(y, now) if two else np.nan
    out["brier_page"] = float(((p - y) ** 2).mean()); out["brier_now"] = float(((now - y) ** 2).mean())
    return out


summary, sweep = [], []
for event in ("empty", "full"):
    for grp in ("campus", "gateway", "corridor"):
        for per, (a, z) in PERIODS.items():
            for ahead in (10, 20):
                g = res[(res.ahead == ahead) & (res.slot >= a) & (res.slot < z) & ((res.group == grp) | (grp == "corridor"))]
                if len(g) < 100:
                    continue
                summary.append({"event": event, "group": grp, "period": per, "ahead": ahead, **score(g, event)})
                if per == "06-24":
                    for th in (0.5, 0.6, 0.7, 0.8):
                        s = score(g, event, th)
                        sweep.append({"event": event, "group": grp, "ahead": ahead, "threshold": th, "page_marked": s["page_marked"], "page_right": s["page_right"], "page_finds": s["page_finds"]})
summary = pd.DataFrame(summary); summary.round(4).to_csv(OUT / "relay_summary.csv", index=False)
pd.DataFrame(sweep).round(4).to_csv(OUT / "relay_thresholds.csv", index=False)
back = pd.DataFrame(back, columns=["day", "period", "group", "empty_station_slots", "full_station_slots", "bikes_into_empty", "docks_out_of_full"])
per_day = back.groupby(["period", "group"])[["empty_station_slots", "full_station_slots", "bikes_into_empty", "docks_out_of_full"]].mean().round(1).reset_index()
per_day.to_csv(OUT / "relay_returns.csv", index=False)
json.dump({"test_days": test_days, "fit_end": FIT_END, "threshold": THRESHOLD, "stations": len(GROUPS["corridor"]), "pairs": int(len(res))}, open(OUT / "relay_setup.json", "w"), indent=1)
pd.set_option("display.width", 250)
print(f"{len(test_days)} days, {len(res)} station-snapshots")
print(summary[summary.group.isin(["campus", "corridor"])].round(3).to_string(index=False))
print(pd.DataFrame(sweep)[lambda x: x.group == "corridor"].round(3).to_string(index=False))
print(per_day.to_string(index=False))
