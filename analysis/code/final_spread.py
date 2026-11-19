"""Can the page say how the search for a bike will go, not just how long it takes on average?

Usage: python final_spread.py DATA_DIR RATES_DIR PLACES_JSON OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16] [--theta 0.6]

The page used to draw one bar per departure time: the expected minutes until the rider is on a bike. final_time.py
found that this number ranks the slow departures well (AUC 0.86-0.90 for searches over 8 minutes, 10 to 30 minutes
ahead) but is no closer in minutes than the counts alone. A mean hides the part a rider cares about, the chance of a
long search. The page now shows ten dots per departure time (Kay et al. 2016, Fernandes et al. 2018): how many times
in ten the first station has a bike, how many times the rider needs another station but is riding within 8 minutes,
and how many times it takes longer.

Leaving now ("p" below), the three shares follow the page's own rule and chances (the "expectm" rule of
final_time.py): the first station j1 with chance p1 on arrival; if it fails, the station the rule would go on to, j2,
with chance p2 when the rider gets there; then j3 from j2. Riding at j1 is "first try", at j2 or j3 within 8 minutes
is "another station", everything else is "over 8 minutes".

Leaving later ("d"), a fixed plan is too pessimistic: the rider looks at the counts again when leaving and walks to
the nearest station that shows a bike then. s_j is the chance that station j shows a bike at departure, r_j the chance
it still has one on arrival given that it showed one, and after a miss the rider tries the nearest other station. The
chance that the first n stations are all empty is taken as (prod of (1 - s_j)) ^ theta. theta = 1 treats the stations
as independent, which understates how often campus stations empty together; THETAS are compared and --theta (0.6,
chosen by leaving one test day out, on 11 of the 12 folds) is the one the page uses. "s" is what the page shows: "p"
for leaving now, "d" with that theta for later.

On the held-out days the shares are compared, at 0 to 60 minutes before a rider leaves, with what a rider who leaves
then and follows the page at that moment (re-reading the counts) went through, scored as in final_time.py (arrivals
between two snapshots weighted by time, up to three stations, then GIVE_UP minutes). Baselines: the fixed plan with
the counts held as they are ("c"), the usual shares for that place and minute on the days the rates were fitted on
("u"), and one constant share per scenario and lead ("const"). "dots" scores the shares rounded to tenths, as drawn.

Writes spread_cases.csv (one row per case and lead; large, not kept in git), spread_reliability.csv (predicted
against observed share by bin of the prediction), spread_summary.csv (Brier scores) and spread_setup.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, HOLIDAYS, load_logger, load_stations  # noqa: E402
from paths import station_minutes  # noqa: E402
from route_planner import STEP, ChainValues, load_slot_rates  # noqa: E402

DATA, RATES, PLACES_JSON, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
ARG = lambda name, default: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
FIT_END, TEST_END = ARG("--fit-end", "2026-10-29"), ARG("--test-end", "2026-11-16")
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
HM = lambda s: int(s[:2]) * 60 + int(s[3:])
ACCESS, REACH, GIVE_UP, G, MARGIN, TRIES, AHEAD = 2, 2.0, 15.0, 12.0, 0.5, 3, 9      # as in final_time.py
SLOW = 8.0                  # minutes: "over 8 minutes" is the red dot
SCENARIOS = {"leave": ("campus", HM("17:00"), HM("19:50")), "arrive": ("gateway", HM("08:30"), HM("10:50")),
             "leave_rest": ("campus", HM("07:00"), HM("16:50"))}
LOOK = (0, 10, 20, 30, 40, 50, 60)      # minutes between asking the page and leaving
BINS = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0001]

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
KM, WALK, RIDE = station_minutes(list(st.sno), st.lat.values, st.lng.values, PLACES_JSON)
PLACES = {"campus": [sidx[s] for s in CAMPUS if s in sidx], "gateway": [sidx[s] for s in GATEWAY if s in sidx]}

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


def panel(day):
    d = df[dstr == day]
    b = np.full((145, N), np.nan); k = np.full((145, N), np.nan)
    b[d.slot.values, d.i.values] = d.bikes.values; k[d.slot.values, d.i.values] = d.docks.values
    return b, k


def had(x, j, minute):
    s0, f = int(minute // STEP), (minute % STEP) / STEP
    if s0 >= 143:
        return np.nan
    x0, x1 = x[s0, j], x[s0 + 1, j]
    if np.isnan(x0) or np.isnan(x1):
        return np.nan
    return (1 - f) * float(x0 >= 1) + f * float(x1 >= 1)


class Phone:
    def __init__(self, b, k, slot):
        self.t = slot * STEP
        self.known = ~np.isnan(b[slot]) & ~np.isnan(k[slot])
        self.bikes = np.where(self.known, b[slot], 0).astype(int)
        P = np.zeros((N, chain.C + 1), np.float32); P[np.arange(N), np.clip(self.bikes, 0, CAP)] = 1.0
        pb = [(self.bikes >= 1).astype(float)]
        for step in range(AHEAD):
            P = chain._fwd(self.t + STEP * step, P)
            pb.append(1 - P[:, 0])
        self.p = np.array(pb)

    def chance(self, j, minute, counts_only=False):
        if counts_only:
            return float(self.bikes[j] >= 1)
        x = min(float(AHEAD), max(0.0, (minute - self.t) / STEP))
        a = int(x); f = x - a
        return (1 - f) * self.p[a, j] + f * self.p[min(AHEAD, a + 1), j]


def candidates(ph, o, visited=()):
    return [j for j in np.lexsort((KM[o], WALK[o])) if ph.known[j] and KM[o, j] <= REACH and j not in visited]


def plan(ph, cand, leg, t, counts_only=False):
    """The page's rule: (j1, p1, on) for each candidate, best by expected minutes, surest within MARGIN of that."""
    near = cand[:12]
    p = lambda j, m: ph.chance(j, m, counts_only)
    opts = []
    for j in near:
        pj = p(j, t + leg[j])
        ons = [(WALK[j, j2] + (1 - p(j2, t + leg[j] + WALK[j, j2])) * G, j2) for j2 in near if j2 != j]
        on = min(ons)[0] if ons else G
        opts.append((j, pj, leg[j] + (1 - pj) * on))
    if not opts:
        return None
    best = min(opts, key=lambda o: o[2])
    for o in opts:
        if o[2] <= best[2] + MARGIN + 1e-9 and o[1] > best[1] + 1e-9:
            best = o
    return best[0], best[1]


def going_on(ph, near, frm, t, exclude, counts_only=False):
    """The station the page would try after a miss at `frm` at minute t, and its chance on arrival."""
    p = lambda j, m: ph.chance(j, m, counts_only)
    ons = [(WALK[frm, j2] + (1 - p(j2, t + WALK[frm, j2])) * G, j2) for j2 in near if j2 not in exclude]
    if not ons:
        return None
    j2 = min(ons)[1]
    return j2, p(j2, t + WALK[frm, j2]), WALK[frm, j2]


def predict(ph, o, t_go, counts_only=False):
    """The page's three shares for a rider who leaves at t_go from two minutes in front of station o."""
    cand = candidates(ph, o)
    leg = {j: ACCESS + WALK[o, j] for j in cand}
    first = plan(ph, cand, leg, t_go, counts_only)
    if first is None:
        return None
    j1, p1 = first
    near = cand[:12]
    m1 = leg[j1]
    green = p1 if m1 <= SLOW else 0.0
    yellow = 0.0
    second = going_on(ph, near, j1, t_go + m1, {j1}, counts_only)
    miss = 1 - p1
    if second is not None:
        j2, p2, h2 = second
        m2 = m1 + h2
        yellow += miss * p2 * (m2 <= SLOW)
        third = going_on(ph, near, j2, t_go + m2, {j1, j2}, counts_only)
        if third is not None:
            j3, p3, h3 = third
            yellow += miss * (1 - p2) * p3 * (m2 + h3 <= SLOW)
    return green, yellow, 1 - green - yellow


THETAS = (1.0, 0.8, 0.6, 0.5, 0.4, 0.3)


def predict_redecide(ph, o, t_go, t_look, theta=1.0):
    """The same three shares for a rider who will look again when leaving, as the page tells its riders to: at t_go
    the rider walks to the nearest station that shows a bike then. s_j: chance station j shows a bike at t_go; r_j:
    chance it still has one on arrival, given that it showed one; after a miss the rider tries the nearest other
    station once more. The chance that the first n stations are all empty is (prod of (1 - s_j))^theta: theta = 1
    treats stations as independent, which understates how often they empty together; theta < 1 couples them."""
    cand = candidates(ph, o)[:12]
    if not cand:
        return None
    leg = {j: ACCESS + WALK[o, j] for j in cand}
    cand.sort(key=lambda j: (leg[j], KM[o, j]))
    green = yellow = 0.0
    prod, before = 1.0, 1.0
    for j in cand:
        sj = ph.chance(j, max(t_go, t_look))
        prod *= 1 - sj
        after = prod ** theta
        pick, before = before - after, after
        if sj <= 0 or pick <= 0:
            continue
        rj = min(1.0, ph.chance(j, t_go + leg[j]) / sj)
        if leg[j] > SLOW:
            continue
        green += pick * rj
        others = [k2 for k2 in cand if k2 != j]
        if others:
            k2 = min(others, key=lambda x: WALK[j, x])
            if leg[j] + WALK[j, k2] <= SLOW:
                yellow += pick * (1 - rj) * ph.chance(k2, t_go + leg[j] + WALK[j, k2])
    return green, yellow, 1 - green - yellow


def realised(b, k, phones, o, t_go):
    """What a rider who leaves at t_go and follows the page then went through: (first try, another station within
    SLOW minutes, longer), as shares (outcomes between snapshots are weighted by time)."""
    loc, t, visited, mass, elapsed = o, t_go, set(), 1.0, 0.0
    green = yellow = 0.0
    for attempt in range(TRIES):
        slot = int(t // STEP)
        if slot not in phones:
            phones[slot] = Phone(b, k, slot)
        ph = phones[slot]
        if ph.known.sum() < 50:
            return None
        cand = candidates(ph, loc, visited)
        access = ACCESS if attempt == 0 else 0
        leg = {j: access + WALK[loc, j] for j in cand}
        first = plan(ph, cand, leg, t)
        if first is None:
            break
        j = first[0]
        arrive = t + leg[j]
        h = had(b, j, arrive)
        if np.isnan(h):
            return None
        elapsed += leg[j]
        if elapsed <= SLOW:
            if attempt == 0:
                green += mass * h
            else:
                yellow += mass * h
        mass *= 1 - h
        if mass < 1e-9:
            mass = 0.0
            break
        loc, t = j, arrive
        visited.add(j)
    return green, yellow, 1 - green - yellow


rows = []
for day in [d for d in days if d <= TEST_END]:
    b, k = panel(day)
    phones = {}
    test = day in test_days
    for name, (grp, first, last) in SCENARIOS.items():
        for t_go in range(first, last + 1, STEP):
            for o in PLACES[grp]:
                real = realised(b, k, phones, o, t_go)
                if real is None:
                    continue
                for look in (LOOK if test else (0,)):
                    slot = int((t_go - look) // STEP)
                    if slot not in phones:
                        phones[slot] = Phone(b, k, slot)
                    ph = phones[slot]
                    if ph.known.sum() < 50:
                        continue
                    pr = predict(ph, o, t_go) if test else (np.nan,) * 3
                    pc = predict(ph, o, t_go, counts_only=True) if test else (np.nan,) * 3
                    pd_ = [predict_redecide(ph, o, t_go, t_go - look, th) if test else (np.nan,) * 3 for th in THETAS]
                    if pr is None or pc is None or any(x is None for x in pd_):
                        continue
                    rows.append((name, day, int(test), t_go, st.sno[o], look, *pr, *pc, *[v for x in pd_ for v in (x[0], x[2])], *real))
    print(day, len(rows), flush=True)

cols = ["scenario", "day", "test", "minute", "place", "look", "p_green", "p_yellow", "p_red", "c_green", "c_yellow", "c_red"] + [f"d{th:g}_{part}" for th in THETAS for part in ("green", "red")] + ["r_green", "r_yellow", "r_red"]
res = pd.DataFrame(rows, columns=cols)
usual = res[res.test == 0].groupby(["scenario", "minute", "place"])[["r_green", "r_red"]].mean().rename(columns={"r_green": "u_green", "r_red": "u_red"}).reset_index()
cases = res[res.test == 1].merge(usual, on=["scenario", "minute", "place"], how="left").dropna(subset=["u_green"])
# the page's dots: the plan of the moment for leaving now, the look-again forecast with the chosen coupling for later
THETA = float(ARG("--theta", 0.6))     # chosen by leaving one test day out: 0.6 on 11 of the 12 days
cases["d_green"], cases["d_red"] = cases[f"d{THETA:g}_green"], cases[f"d{THETA:g}_red"]
cases["s_green"] = np.where(cases.look == 0, cases.p_green, cases.d_green); cases["s_red"] = np.where(cases.look == 0, cases.p_red, cases.d_red)
cases.round(4).to_csv(OUT / "spread_cases.csv", index=False)

rel, summ = [], []
for (name, look), g in cases.groupby(["scenario", "look"]):
    row = {"scenario": name, "look": look, "cases": len(g), "share_green": g.r_green.mean(), "share_red": g.r_red.mean()}
    for part in ("green", "red"):
        y = g["r_" + part]
        for src in ("p", "c", "d", "s", "u"):
            row[f"brier_{part}_{src}"] = float(((g[f"{src}_{part}"] - y) ** 2).mean())
        row[f"brier_{part}_const"] = float(((y.mean() - y) ** 2).mean())
        for th in THETAS:
            row[f"brier_{part}_d{th:g}"] = float(((g[f"d{th:g}_{part}"] - y) ** 2).mean())
        dots = np.round(g["s_" + part] * 10) / 10                 # what ten dots can show
        row[f"brier_{part}_dots"] = float(((dots - y) ** 2).mean())
        for src in ("p", "d", "s"):
            for lo, hi in zip(BINS[:-1], BINS[1:]):
                m = (g[f"{src}_{part}"] >= lo) & (g[f"{src}_{part}"] < hi)
                if m.sum():
                    rel.append({"scenario": name, "look": look, "part": part, "model": src, "bin_lo": lo, "bin_hi": min(hi, 1.0), "cases": int(m.sum()), "predicted": g.loc[m, f"{src}_{part}"].mean(), "observed": y[m].mean()})
    summ.append(row)
rel = pd.DataFrame(rel); summ = pd.DataFrame(summ)
rel.round(4).to_csv(OUT / "spread_reliability.csv", index=False)
summ.round(5).to_csv(OUT / "spread_summary.csv", index=False)
json.dump({"test_days": test_days, "fit_end": FIT_END, "slow_min": SLOW, "theta": THETA, "thetas": THETAS, "access_min": ACCESS, "give_up_min": GIVE_UP, "g_min": G, "margin_min": MARGIN, "tries": TRIES,
           "scenarios": {k: {"start_points": v[0], "from": v[1], "to": v[2]} for k, v in SCENARIOS.items()}, "looks": LOOK}, open(OUT / "spread_setup.json", "w"), indent=1)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
print(summ.round(4).to_string(index=False))
print(rel[(rel.scenario == "leave") & (rel.part == "red")].round(3).to_string(index=False))
