"""A record of what the page advised, written before the outcome is known, and its score afterwards.

demo_state.py calls update() after every snapshot. It does two things.

1. It appends to DATA_DIR/advice/YYYY-MM-DD.csv what the page says at this snapshot to a rider who is two minutes
   from each of the 19 stations between campus and the metro:
     bike  leaving now: the station with the fewest expected minutes until the rider is on a bike (walk + chance of
           finding none x the cost of going on to the next one; among the stations within MARGIN minutes of the
           fewest, the one with the best chance), its chance, and the minutes the page expects for leaving now
           and in 10, 20 and 30 minutes
     dock  riding in to that station in 10 minutes: the station with the fewest expected minutes until the rider
           stands at the destination without the bike
   together with what a rider does without the page: go to the station in front ("near"), or to the nearest
   station that shows a bike (a dock) right now ("alt", what the operator's app allows). The logger commits the
   file with the snapshot, so the commit history shows that each line existed before the minutes it is about.

2. It scores the lines whose outcome is known against the snapshots logged since. Each of the three first choices
   is followed the way final_time.py follows a rider: if the logger shows no bike (no dock) at the minute of
   arrival, the rider goes on to the nearest station that shows one, up to three stations, then gives up
   (GIVE_UP minutes). The totals per day go to DOCS_DIR/track.json, which the page shows under "About".

The rule is that of site/src/app.js (planBike, planDock); RULE changes whenever it does, and track.json starts
again. Chances are read the way the page reads them: in 63rds, linear between the 10-minute steps.
"""
import csv
import json
from pathlib import Path

import numpy as np

RULE = "v2"                       # fewest expected minutes, the surest station within MARGIN of that; path-length walking and riding minutes
REACH_KM = {"bike": 2.0, "dock": 0.6}
ACCESS = 2                        # minutes from the rider's door to the station in front of it
DOCK_AHEAD = 10                   # the Return tab's default: riding in 10 minutes from now
G = 12.0                          # the rule's guess for the cost of a second failure
MARGIN = 0.5                      # expected minutes given up for a better chance at the first station
GIVE_UP = 15.0
NEAR = 12                         # stations the rule looks at
STEP = 10
LOOK = (0, 10, 20, 30)            # departures the page is asked about
COLS = ["time", "kind", "place", "pick", "p", "leg", "e0", "e10", "e20", "e30", "alt", "leg_alt"]
# windows of the final report (teaching days): name -> (group of places, kind, first minute, last minute)
WINDOWS = {"leave": ("campus", "bike", 17 * 60, 19 * 60 + 50), "arrive": ("gateway", "bike", 8 * 60 + 30, 10 * 60 + 50), "dock": ("campus", "dock", 9 * 60, 10 * 60 + 50),
           "bike_day": ("corridor", "bike", 6 * 60, 22 * 60 + 50), "dock_day": ("corridor", "dock", 6 * 60, 22 * 60 + 50)}
FIELDS = ["cases", "min_pick", "min_near", "min_alt", "ok_pick", "ok_near", "ok_alt", "slow_pick", "slow_near", "slow_alt",
          "n0", "err0", "n10", "err10", "n20", "err20", "n30", "err30"]
HM = lambda m: f"{int(m) // 60:02d}:{int(m) % 60:02d}"
MIN = lambda s: int(s[:2]) * 60 + int(s[3:])


def chance(q, now, j, t_min, minute):
    """Chance in [0, 1] that station j has what is needed at `minute`: the count now, then the page's steps, linear in between."""
    steps = q.shape[0]
    x = min(float(steps), max(0.0, (minute - t_min) / STEP))
    a = int(x); f = x - a
    pa = float(now[j] >= 1) if a == 0 else q[a - 1, j] / 63.0
    pb = pa if a >= steps else q[a, j] / 63.0
    return (1 - f) * pa + f * pb


def plan(kind, o, t_min, t_go, q, now, km, walk, ride, observed):
    """The page's rule for a rider at station o (bike) or bound for it (dock) at minute t_go.
    Returns (station, chance, minutes to reach it, expected minutes) or None."""
    if kind == "bike":
        cand = [j for j in np.lexsort((km[o], walk[o])) if observed[j] and km[o, j] <= REACH_KM[kind]][:NEAR]
        leg = {j: ACCESS + int(walk[o, j]) for j in cand}; tail = {j: 0 for j in cand}; hop = walk
    else:
        cand = [j for j in range(len(observed)) if observed[j] and km[o, j] <= REACH_KM[kind]]
        leg = {j: int(ride[o, j]) for j in cand}; tail = {j: int(walk[j, o]) for j in cand}; hop = ride
        cand = sorted(cand, key=lambda j: (leg[j] + tail[j], km[o, j]))[:NEAR]
    best, opts = None, []
    for j in cand:
        p = chance(q, now, j, t_min, t_go + leg[j])
        on = min((hop[j, j2] + tail[j2] + (1 - chance(q, now, j2, t_min, t_go + leg[j] + hop[j, j2])) * G for j2 in cand if j2 != j), default=G)
        e = leg[j] + p * tail[j] + (1 - p) * on
        opts.append((j, p, leg[j], e))
        if best is None or e < best[3] - 1e-9:
            best = opts[-1]
    if best is not None:
        least = best[3]
        for o in opts:                                           # in the order of cand, as the page does
            if o[3] <= least + MARGIN + 1e-9 and o[1] > best[1] + 1e-9:
                best = o
    return best


def shows(kind, o, now, km, walk, ride, observed):
    """What the operator's app allows: the nearest station that shows a bike (a dock) now. Returns (station, minutes to reach it)."""
    if kind == "bike":
        cand = [j for j in np.lexsort((km[o], walk[o])) if observed[j] and km[o, j] <= REACH_KM[kind] and now[j] >= 1]
        return (cand[0], ACCESS + int(walk[o, cand[0]])) if cand else (o, ACCESS)
    cand = sorted((j for j in range(len(observed)) if observed[j] and km[o, j] <= REACH_KM[kind] and now[j] >= 1), key=lambda j: (ride[o, j] + walk[j, o], km[o, j]))
    return (cand[0], int(ride[o, cand[0]])) if cand else (o, 0)


def record(path, sno, groups, t_min, qb, qk, bikes, docks, km, walk, ride, observed):
    """Append this snapshot's advice to path unless the snapshot is already there. Returns the number of lines written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = HM(t_min)
    if path.exists():
        with open(path, newline="") as f:
            if any(r and r[0] == stamp for r in csv.reader(f)):
                return 0
    rows = []
    for o in np.nonzero(groups != "other")[0]:
        if not observed[o]:
            continue
        b = plan("bike", o, t_min, t_min, qb, bikes, km, walk, ride, observed)
        if b is not None:
            later = [plan("bike", o, t_min, t_min + d, qb, bikes, km, walk, ride, observed)[3] for d in LOOK[1:]]
            alt, leg_alt = shows("bike", o, bikes, km, walk, ride, observed)
            rows.append([stamp, "bike", sno[o], sno[b[0]], f"{b[1]:.2f}", b[2], f"{b[3]:.1f}"] + [f"{e:.1f}" for e in later] + [sno[alt], leg_alt])
        d = plan("dock", o, t_min, t_min + DOCK_AHEAD, qk, docks, km, walk, ride, observed)
        if d is not None:
            alt, leg_alt = shows("dock", o, docks, km, walk, ride, observed)
            rows.append([stamp, "dock", sno[o], sno[d[0]], f"{d[1]:.2f}", d[2], f"{d[3]:.1f}", "", "", "", sno[alt], leg_alt])
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLS)
        w.writerows(rows)
    return len(rows)


def had(x, j, minute):
    """Share of the arrival minute's 10-minute interval in which station j had what was needed (final_time.py)."""
    s0, f = int(minute // STEP), (minute % STEP) / STEP
    if s0 >= x.shape[0] - 1:
        return np.nan
    x0, x1 = x[s0, j], x[s0 + 1, j]
    if np.isnan(x0) or np.isnan(x1):
        return np.nan
    return (1 - f) * float(x0 >= 1) + f * float(x1 >= 1)


def follow(kind, x, o, first, leg, t_go, km, walk, ride):
    """(expected minutes, first try ok) for a rider whose first choice is `first`, reached `leg` minutes after t_go, and
    who after a failure goes on to the nearest station that shows what is needed. None if a snapshot is missing."""
    hop = walk if kind == "bike" else ride
    mass, minutes, elapsed, t, j, visited, first_ok = 1.0, 0.0, 0.0, t_go, first, set(), np.nan
    for attempt in range(3):
        t += leg; elapsed += leg
        h = had(x, j, t)
        if np.isnan(h):
            return None
        if attempt == 0:
            first_ok = h
        minutes += mass * h * (elapsed + (0 if kind == "bike" else walk[j, o]))
        mass *= 1 - h
        visited.add(j)
        if mass < 1e-9 or attempt == 2:
            break
        row = x[int(t // STEP)]
        centre = j if kind == "bike" else o
        cand = [c for c in range(x.shape[1]) if c not in visited and not np.isnan(row[c]) and row[c] >= 1 and km[centre, c] <= REACH_KM[kind]]
        if not cand:
            break
        nxt = min(cand, key=lambda c: (hop[j, c] + (0 if kind == "bike" else walk[c, o]), km[centre, c]))
        leg, j = int(hop[j, nxt]), nxt
    if mass >= 1e-9:
        minutes += mass * (elapsed + GIVE_UP + (0 if kind == "bike" else walk[j, o]))
    return minutes, first_ok


def score(path, day_df, sidx, groups, km, walk, ride):
    """Totals per window for one day's advice file, in the order of FIELDS."""
    N = len(sidx)
    b = np.full((145, N), np.nan); k = np.full((145, N), np.nan)
    i = day_df.sno.map(sidx).values; s = day_df.slot.values
    b[s, i] = day_df.bikes.values; k[s, i] = day_df.docks.values
    tot = {w: [0.0] * len(FIELDS) for w in WINDOWS}
    lines = list(csv.DictReader(open(path, newline="")))
    real = {}                                                   # (place, minute) -> minutes a rider who looks when leaving then needed
    cases = []
    for r in lines:
        o = sidx.get(r["place"])
        if o is None or r["pick"] not in sidx or r["alt"] not in sidx:
            continue
        kind, t = r["kind"], MIN(r["time"])
        x = b if kind == "bike" else k
        t_go = t if kind == "bike" else t + DOCK_AHEAD
        got = [follow(kind, x, o, sidx[r["pick"]], int(r["leg"]), t_go, km, walk, ride),
               follow(kind, x, o, o, ACCESS if kind == "bike" else 0, t_go, km, walk, ride),
               follow(kind, x, o, sidx[r["alt"]], int(r["leg_alt"]), t_go, km, walk, ride)]
        if any(g is None for g in got):                         # the outcome is not logged yet, or a snapshot is missing: keep the three paired
            continue
        if kind == "bike":
            real[(o, t)] = got[2][0]
        cases.append((r, o, kind, t, got))
    for r, o, kind, t, got in cases:
        for w, (grp, wkind, first, last) in WINDOWS.items():
            if wkind != kind or not (first <= t <= last) or not (grp == "corridor" or groups[o] == grp):
                continue
            a = tot[w]
            a[0] += 1
            for n, g in enumerate(got):
                a[1 + n] += g[0]; a[4 + n] += g[1]; a[7 + n] += float(g[0] > 10)
            if kind == "bike":                                  # what the page said 0, 10, 20 and 30 minutes earlier about leaving at that minute
                for n, d in enumerate(LOOK):
                    said = r[f"e{d}"]
                    if said and (o, t + d) in real:
                        a[10 + 2 * n] += 1; a[11 + 2 * n] += abs(float(said) - real[(o, t + d)])
    return {w: [round(v, 2) for v in a] for w, a in tot.items()}


def update(data_dir, docs_dir, df, sno, groups, day, t_min, offday_of, qb, qk, bikes, docks, km, walk, ride, observed, snapshot_at):
    """Record this snapshot's advice, then rescore the days in df. offday_of(day) -> 0 for a teaching day."""
    adv = Path(data_dir) / "advice"
    sidx = {s: n for n, s in enumerate(sno)}
    written = record(adv / f"{day}.csv", list(sno), groups, t_min, qb, qk, bikes, docks, km, walk, ride, observed) if qb is not None else 0
    out = Path(docs_dir) / "track.json"
    try:
        track = json.load(open(out, encoding="utf-8"))
        if track.get("rule") != RULE:
            track = {}
    except (OSError, ValueError):
        track = {}
    track.setdefault("rule", RULE); track.setdefault("days", {})
    dstr = df.date.astype(str).str.slice(0, 10)
    for d in sorted(dstr.unique()):
        f = adv / f"{d}.csv"
        if f.exists():
            with open(f, newline="") as fh:
                if next(csv.reader(fh), None) != COLS:          # a file written by an earlier rule: leave it out
                    continue
            track["days"][d] = {"teaching": int(not offday_of(d)), "w": score(f, df[dstr == d], sidx, groups, km, walk, ride)}
    if track["days"]:
        track["since"] = min(track["days"])
    track["updated"] = snapshot_at
    track["fields"] = FIELDS
    json.dump(track, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return written
