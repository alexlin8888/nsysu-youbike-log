"""How many minutes until a rider is on a bike, or rid of one? The page's advice against what really happened.

Usage: python final_time.py DATA_DIR RATES_DIR PLACES_JSON OUT_DIR [--fit-end 2026-10-29] [--test-end 2026-11-16]

final_rider.py asks whether the first station a rule sends a rider to had a bike. A rider cares about something
else: how long it takes to be on a bike, counting the walk to a second or third station when the first one fails,
and whether the bike beats walking. This script replays the logged days minute by minute for one rider at a time.

  borrow  the rider is two minutes from one of the stations of a group and leaves at minute m. A policy names a
          station; the rider walks there along the paths of PLACES_JSON (demo_places.py). If the logger shows a bike
          at the minute of arrival the clock stops. If not, the policy is asked again from that station with what a
          phone shows then, up to three stations; after the third the rider gives up (GIVE_UP minutes are added).
  dock    the rider rides in to one of the stations and chooses, LEAD minutes earlier, where to return. A full
          station costs a ride to another one and the walk back. The clock runs from reaching the area to standing
          at the destination without a bike.

Policies (all see the snapshot of the 10-minute slot they are asked in):
  nearest    the station in front of you; after a failure, the nearest station that shows a bike (a dock)
  official   what the operator's app allows: the nearest station that shows at least one bike (dock) now
  counts3/5  the cautious version: at least 3 (5) now
  chain0.9   the nearest station whose chance on arrival is at least 0.9 (0.95 for a dock), else the best chance;
             the rule of the page until 18 Nov
  expect     the station with the fewest expected minutes: walk + chance of failure x the cost of going on from
             there. The chance comes from the birth-death chain run from the snapshot to the minute of arrival
             (linear between 10-minute steps).
  expectm    the same, but among the stations within MARGIN minutes of the fewest expected minutes the one with
             the best chance: a rider is not sent past an empty rack when a surer station costs half a minute.
             This is the rule of the page from 18 Nov (RULE v2 in demo_track.py).
Outcomes between two snapshots are weighted by time, as in final_rider.py, so a result is an expectation over the
two possible states and not a draw.

"trip" adds the ride for the evening case (campus to the metro, 501209026) and compares the door-to-door minutes
with walking all the way.

The script also asks whether the page knows in advance how long it will take. 0, 10, 20 and 30 minutes before a
rider leaves, the page's own number of minutes (the "expectm" rule's) is compared with what a rider who looks at the counts when
leaving (the "official" policy) then needed. Two baselines: the same formula fed with the counts alone, as if
nothing changed until then, and the usual number of minutes for that place and minute on the days the rates were
fitted on.

Writes time_cases.csv, time_summary.csv (means with day-bootstrap intervals, and differences to "official"),
time_by_minute.csv, time_foresight.csv, time_foresight_summary.csv and time_setup.json.
"""
import json
import math
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
OUTCOME = ARG("--outcome", "mid")      # how an arrival between two snapshots is scored: mid (weighted by time), late (the later snapshot), early
OFFDAYS = set(HOLIDAYS) | {"2026-10-23"}
HM = lambda s: int(s[:2]) * 60 + int(s[3:])
ACCESS = 2                 # minutes from the rider's door to the station in front of it
REACH = {"bike": 2.0, "dock": 0.6}        # straight-line km searched around the rider (bike) or the destination (dock)
GIVE_UP = 15.0             # minutes charged after a third failure
G = 12.0                   # the "expect" rule's guess for the cost of a second failure
MARGIN = 0.5               # "expectm": expected minutes a rider gives up for a better chance at the first station
TRIES = 3
AHEAD = 9                  # chain steps available to a policy
SEED = 11
METRO = "501209026"        # KRT exit 1: where the evening trip ends
# name: (group of starting points, what is needed, first and last minute of leaving / riding in)
SCENARIOS = {
    "leave": ("campus", "bike", HM("17:00"), HM("19:50")),
    "arrive": ("gateway", "bike", HM("08:30"), HM("10:50")),
    "dock": ("campus", "dock", HM("09:00"), HM("10:50")),
    "leave_rest": ("campus", "bike", HM("07:00"), HM("16:50")),
    "arrive_rest": ("gateway", "bike", HM("11:00"), HM("21:50")),
    "dock_rest": ("campus", "dock", HM("11:00"), HM("21:50")),
}
LEADS = {"bike": (0, 10), "dock": (10, 0)}          # minutes between looking at the phone and leaving (riding in)
POLICIES = ["nearest", "official", "counts3", "counts5", "chain", "expect", "expectm", "expect6", "expect20"]

st = load_stations(DATA)
st = st[st.logged == 1].reset_index(drop=True)
N = len(st)
sidx = {s: i for i, s in enumerate(st.sno)}
CAP = st.capacity.values.astype(int)
KM, WALK, RIDE = station_minutes(list(st.sno), st.lat.values, st.lng.values, PLACES_JSON)
PLACES = {"campus": [sidx[s] for s in CAMPUS if s in sidx], "gateway": [sidx[s] for s in GATEWAY if s in sidx]}
K_METRO = sidx[METRO]

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
    b[d.slot.values, d.i.values] = d.bikes.values
    k[d.slot.values, d.i.values] = d.docks.values
    return b, k


def had(x, j, minute):
    """Share of the arrival minute's 10-minute interval, weighted by time, in which station j had what was needed."""
    s0, f = int(minute // STEP), (minute % STEP) / STEP
    if s0 >= 143:
        return np.nan
    x0, x1 = x[s0, j], x[s0 + 1, j]
    if np.isnan(x0) or np.isnan(x1):
        return np.nan
    if OUTCOME == "late":                      # the worst case for a rider who trusts the count: whatever changes in the interval has already happened
        return float(x1 >= 1)
    if OUTCOME == "early":
        return float(x0 >= 1)
    return (1 - f) * float(x0 >= 1) + f * float(x1 >= 1)


class Phone:
    """What a phone shows in one 10-minute slot of one day: the counts, and the chain's chances for the steps after it."""

    def __init__(self, b, k, slot):
        self.t = slot * STEP
        self.known = ~np.isnan(b[slot]) & ~np.isnan(k[slot])
        self.bikes = np.where(self.known, b[slot], 0).astype(int)
        self.docks = np.where(self.known, k[slot], 0).astype(int)
        P = np.zeros((N, chain.C + 1), np.float32); P[np.arange(N), np.clip(self.bikes, 0, CAP)] = 1.0
        pb = [(self.bikes >= 1).astype(float)]; pk = [(self.docks >= 1).astype(float)]
        for step in range(AHEAD):
            P = chain._fwd(self.t + STEP * step, P)
            pb.append(1 - P[:, 0]); pk.append(1 - P[np.arange(N), CAP])
        self.p = {"bike": np.array(pb), "dock": np.array(pk)}
        self.now = {"bike": self.bikes, "dock": self.docks}

    def chance(self, need, j, minute):
        """Chance that station j has a bike (a dock) at `minute`: linear between the chain's 10-minute steps."""
        x = min(float(AHEAD), max(0.0, (minute - self.t) / STEP))
        a = int(x); f = x - a
        p = self.p[need]
        return (1 - f) * p[a, j] + f * p[min(AHEAD, a + 1), j]


def choose(policy, need, phone, cand, leg, tail, first, start, t_leave, g=G):
    """The station a policy names. cand: stations in the order the rider would try them; leg[j]: minutes to reach j;
    tail[j]: minutes still to go after getting what is needed at j (0 for a bike, the walk back for a dock);
    first: is this the rider's first choice; start: the station in front of the rider (the destination, for a dock)."""
    if not cand:
        return None
    now = phone.now[need]
    shows = [j for j in cand if now[j] >= 1]
    if policy == "nearest" and first:
        return start if start in cand else cand[0]
    if policy in ("nearest", "official"):
        return shows[0] if shows else None
    if policy.startswith("counts"):
        kk = int(policy[6:])
        return next((j for j in cand if now[j] >= kk), shows[0] if shows else None)
    ch = {j: phone.chance(need, j, t_leave + leg[j]) for j in cand}
    if policy == "chain":
        th = 0.9 if need == "bike" else 0.95
        return next((j for j in cand if ch[j] >= th), max(cand, key=lambda j: ch[j]))
    gg = {"expect": g, "expectm": g, "expect6": 6.0, "expect20": 20.0}[policy]
    return expected(need, phone, cand, leg, tail, t_leave, gg, ch, margin=MARGIN if policy == "expectm" else 0.0)[0]


def expected(need, phone, cand, leg, tail, t_leave, gg=G, ch=None, counts_only=False, margin=0.0):
    """(station, minutes): the station with the fewest expected minutes and that number; with a margin, the station
    with the best chance among those within `margin` minutes of the fewest, and its own number. counts_only replaces
    the chain's chances by what the phone shows now (1 if the station has a bike, else 0): the forecast of a rider
    who assumes nothing will change."""
    if not cand:
        return None, GIVE_UP
    now = phone.now[need]
    p = (lambda j, minute: float(now[j] >= 1)) if counts_only else (lambda j, minute: phone.chance(need, j, minute))
    best, best_e = None, 1e9
    near = cand[:12]
    opts = []
    for j in near:
        pj = p(j, t_leave + leg[j]) if (ch is None or counts_only) else ch[j]
        # going on from j if it fails: the cheapest second station, itself charged gg minutes if it fails too
        on = min((HOP[need][j, j2] + tail[j2] + (1 - p(j2, t_leave + leg[j] + HOP[need][j, j2])) * gg for j2 in near if j2 != j), default=gg)
        e = leg[j] + pj * tail[j] + (1 - pj) * on
        opts.append((j, pj, e))
        if e < best_e - 1e-9:
            best, best_e = j, e
    if margin > 0:
        for j, pj, e in opts:                                    # in the order of `near`, so a tie stays with the nearer station
            if e <= best_e + margin + 1e-9 and pj > next(o[1] for o in opts if o[0] == best) + 1e-9:
                best = j
        best_e = next(o[2] for o in opts if o[0] == best)
    return best, best_e


HOP = {"bike": WALK, "dock": RIDE}          # how the rider moves between stations: on foot when looking for a bike, riding when looking for a dock


def run(policy, need, b, k, phones, o, t_decide, t_go):
    """Expected minutes for one rider. Returns (minutes, first try ok, share that gave up, first station, door-to-door
    minutes of the evening trip or nan), or None when a snapshot the outcome needs is missing."""
    x = b if need == "bike" else k
    loc, t, visited = o, t_go, set()
    mass, minutes, first_ok, first_pick, trip = 1.0, 0.0, np.nan, -1, 0.0
    elapsed = 0.0
    for attempt in range(TRIES):
        slot = int((t_decide if attempt == 0 else t) // STEP)
        if slot not in phones:
            phones[slot] = Phone(b, k, slot)
        ph = phones[slot]
        if ph.known.sum() < 50:                                  # the logger missed this snapshot: nothing to look at, so no case
            return None
        centre = loc if need == "bike" else o                    # a bike is sought around the rider, a dock around the destination
        hop = HOP[need][loc]
        cand = [j for j in np.lexsort((KM[centre], hop if need == "bike" else WALK[:, o])) if ph.known[j] and KM[centre, j] <= REACH[need] and j not in visited]
        access = ACCESS if (attempt == 0 and need == "bike") else 0
        leg = {j: access + hop[j] for j in cand}
        tail = {j: (0 if need == "bike" else WALK[j, o]) for j in cand}
        if need == "dock":
            cand.sort(key=lambda j: leg[j] + tail[j])               # nearest in minutes still to go: the ride there and the walk back
        j = choose(policy, need, ph, cand, leg, tail, attempt == 0, o, t)
        if j is None:
            break
        if attempt == 0:
            first_pick = j
        arrive = t + leg[j]
        h = had(x, j, arrive)
        if np.isnan(h):
            return None
        elapsed += leg[j]
        if attempt == 0:
            first_ok = h
        minutes += mass * h * (elapsed + tail[j])
        trip += mass * h * (elapsed + 1 + RIDE[j, K_METRO] + 1)   # one minute to take the bike, one to return it
        mass *= 1 - h
        if mass < 1e-9:
            mass = 0.0
            break
        loc, t = j, arrive
        visited.add(j)
    minutes += mass * (elapsed + GIVE_UP + (WALK[loc, o] if need == "dock" else 0))
    trip += mass * (elapsed + WALK[loc, K_METRO])                 # no bike after three stations: walk the rest
    return minutes, first_ok, mass, first_pick, trip


ONLY = ARG("--only", None)
if ONLY:
    SCENARIOS = {k: v for k, v in SCENARIOS.items() if k in ONLY.split(",")}
PRED_LEADS = (0, 10, 20, 30)          # how long before leaving the page is asked "how many minutes until I ride?"


def foresee(b, k, phones, o, t_look, t_go):
    """What the page would say at t_look about leaving at t_go: expected minutes by the chain, and by the counts alone."""
    slot = int(t_look // STEP)
    if slot not in phones:
        phones[slot] = Phone(b, k, slot)
    ph = phones[slot]
    if ph.known.sum() < 50:
        return None
    cand = [j for j in np.lexsort((KM[o], WALK[o])) if ph.known[j] and KM[o, j] <= REACH["bike"]]
    leg = {j: ACCESS + WALK[o, j] for j in cand}; tail = {j: 0 for j in cand}
    return expected("bike", ph, cand, leg, tail, t_go, margin=MARGIN)[1], expected("bike", ph, cand, leg, tail, t_go, counts_only=True, margin=MARGIN)[1]


rows, pred = [], []
for day in [d for d in days if d <= TEST_END]:
    b, k = panel(day)
    phones = {}
    test = day in test_days
    for name, (grp, need, first, last) in SCENARIOS.items():
        for lead in (LEADS[need] if test else (0,)):
            for t_go in range(first, last + 1, STEP):
                for o in PLACES[grp]:
                    got = {p: run(p, need, b, k, phones, o, t_go - lead, t_go) for p in (POLICIES if test else ["official"])}
                    if any(v is None for v in got.values()):   # keep the comparison paired
                        continue
                    if test:
                        for p, (minutes, ok, gave_up, pick, trip) in got.items():
                            rows.append((name, lead, day, t_go, st.sno[o], p, minutes, ok, gave_up, st.sno[pick] if pick >= 0 else "", trip if name.startswith("leave") else np.nan,
                                         ACCESS + WALK[o, K_METRO] if name.startswith("leave") else np.nan))
                    if need == "bike" and lead == 0:           # what a rider who looks when leaving really needs, against what the page said earlier
                        real = got["official"]
                        for ahead in (PRED_LEADS if test else (0,)):
                            f = foresee(b, k, phones, o, t_go - ahead, t_go) if test else (np.nan, np.nan)
                            if f is not None:
                                pred.append((name, day, int(test), t_go, st.sno[o], ahead, f[0], f[1], real[0], real[4], ACCESS + WALK[o, K_METRO]))
    print(day, len(rows), len(pred), flush=True)
res = pd.DataFrame(rows, columns=["scenario", "lead", "day", "minute", "place", "policy", "minutes", "first_ok", "gave_up", "first_pick", "trip_min", "walk_all_min"])
res.to_csv(OUT / "time_cases.csv", index=False)

rng = np.random.default_rng(SEED)
day_list = sorted(res.day.unique())
draws = rng.integers(0, len(day_list), size=(1000, len(day_list)))
summ = []
for (name, lead), sub in res.groupby(["scenario", "lead"]):
    agg = sub.assign(over10=(sub.minutes > 10).astype(float), bike_wins=(sub.trip_min < sub.walk_all_min).astype(float)).groupby(["policy", "day"]).agg(
        n=("minutes", "size"), minutes=("minutes", "sum"), ok=("first_ok", "sum"), gave_up=("gave_up", "sum"), over10=("over10", "sum"), trip=("trip_min", "sum"), walk_all=("walk_all_min", "sum"), bike_wins=("bike_wins", "sum"))
    get = lambda p: agg.loc[p].reindex(day_list).fillna(0)
    boot = lambda p, col: p[col].values[draws].sum(1) / np.maximum(p.n.values[draws].sum(1), 1)
    base = get("official")
    for p in POLICIES:
        a = get(p)
        n = a.n.sum()
        d = boot(a, "minutes") - boot(base, "minutes")
        row = {"scenario": name, "lead": lead, "policy": p, "cases": int(n), "minutes": a.minutes.sum() / n, "minutes_lo": np.percentile(boot(a, "minutes"), 2.5), "minutes_hi": np.percentile(boot(a, "minutes"), 97.5),
               "first_ok": a.ok.sum() / n, "over_10_min": a.over10.sum() / n, "gave_up": a.gave_up.sum() / n,
               "vs_official": a.minutes.sum() / n - base.minutes.sum() / base.n.sum(), "vs_official_lo": np.percentile(d, 2.5), "vs_official_hi": np.percentile(d, 97.5)}
        if name.startswith("leave"):
            dt = boot(a, "trip") - boot(base, "trip")
            row.update({"trip_min": a.trip.sum() / n, "walk_all_min": a.walk_all.sum() / n, "bike_faster_share": a.bike_wins.sum() / n,
                        "trip_vs_official": a.trip.sum() / n - base.trip.sum() / base.n.sum(), "trip_vs_official_lo": np.percentile(dt, 2.5), "trip_vs_official_hi": np.percentile(dt, 97.5)})
        summ.append(row)
summ = pd.DataFrame(summ)
summ.to_csv(OUT / "time_summary.csv", index=False)
json.dump({"test_days": test_days, "fit_end": FIT_END, "outcome": OUTCOME, "access_min": ACCESS, "reach_km": REACH, "give_up_min": GIVE_UP, "g_min": G, "margin_min": MARGIN, "tries": TRIES, "leads": LEADS, "metro": METRO,
           "scenarios": {k: {"start_points": v[0], "needs": v[1], "from": v[2], "to": v[3]} for k, v in SCENARIOS.items()}}, open(OUT / "time_setup.json", "w"), indent=1)
# ---- does the page know in advance how long it will take? ----
pr = pd.DataFrame(pred, columns=["scenario", "day", "test", "minute", "place", "ahead", "by_chain", "by_counts", "real", "real_trip", "walk_all"])
usual = pr[pr.test == 0].groupby(["scenario", "minute", "place"]).real.mean().rename("usual").reset_index()      # the same place and minute on the days the rates were fitted on
pt = pr[pr.test == 1].merge(usual, on=["scenario", "minute", "place"], how="left")
pt.to_csv(OUT / "time_foresight.csv", index=False)


def auc(score, event):
    score, event = np.asarray(score, float), np.asarray(event, bool)
    if event.all() or not event.any():
        return np.nan
    r = pd.Series(score).rank().values
    return (r[event].sum() - event.sum() * (event.sum() + 1) / 2) / (event.sum() * (~event).sum())


fore = []
for (name, ahead), g in pt.groupby(["scenario", "ahead"]):
    g = g.dropna(subset=["usual"])
    slow = g.real > 8
    row = {"scenario": name, "ahead": ahead, "cases": len(g), "real_mean": g.real.mean(), "slow_share": slow.mean()}
    for col in ("by_chain", "by_counts", "usual"):
        row[f"mae_{col}"] = (g[col] - g.real).abs().mean(); row[f"auc_slow_{col}"] = auc(g[col], slow)
    # leave the bike alone when the page expects the ride to take longer than the walk (evening trip to the metro)
    if name.startswith("leave"):
        walk = g.by_chain + 2 + RIDE[[sidx[s] for s in g.place], K_METRO] >= g.walk_all
        row.update({"told_to_walk": walk.mean(), "trip_always_try": g.real_trip.mean(), "trip_with_advice": np.where(walk, g.walk_all, g.real_trip).mean()})
    fore.append(row)
fore = pd.DataFrame(fore)
fore.to_csv(OUT / "time_foresight_summary.csv", index=False)
by_minute = res[(res.lead == 0) & res.policy.isin(["official", "chain", "expect", "expectm"])].groupby(["scenario", "minute", "policy"]).agg(cases=("minutes", "size"), minutes=("minutes", "mean"), over10=("minutes", lambda x: (x > 10).mean())).reset_index()
by_minute.to_csv(OUT / "time_by_minute.csv", index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300); pd.set_option("display.max_columns", 30)
print(fore.round(3).to_string(index=False))
print(summ[["scenario", "lead", "policy", "cases", "minutes", "minutes_lo", "minutes_hi", "first_ok", "over_10_min", "gave_up", "vs_official", "vs_official_lo", "vs_official_hi"]].round(3).to_string(index=False))
t = summ[summ.scenario.str.startswith("leave")][["scenario", "lead", "policy", "trip_min", "walk_all_min", "bike_faster_share", "trip_vs_official", "trip_vs_official_lo", "trip_vs_official_hi"]]
print(t.round(3).to_string(index=False))
