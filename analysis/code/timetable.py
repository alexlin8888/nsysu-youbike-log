"""NSYSU course timetable -> class sessions and timetable-intensity features.

Input: the public course query (selcrs.nsysu.edu.tw, 115 學年度第 1 學期), queried once per weekday, either as
  courses_115-1.json  one record per (query weekday, course):
      [query_wkday, dept, code, grade, class, name, credits, quota, enrolled, time_room, mon, tue, ..., sun]
  courses_115-1.tsv   one line per (code, class) as exported from the browser, "不分班" written as "":
      code, class, dept, enrolled, building, days    with days = "1:89;3:B5" (weekday:periods, 1 = Monday)
where mon..sun hold the period letters of that day (e.g. "89" = periods 8 and 9, "B5" = B and 5) and building is
the room's building code (e.g. SS) as extracted by building(). The query lists some courses twice (cross-listed
under a second class label with identical time and enrolment), so courses are deduplicated by code.
Courses taught off campus (inter-university, online or remote, Taipei and Shanghai EMBA sites, company sites, the
Pingtung aquarium, the veterans hospital) are dropped by on_campus().

Outputs (CLI):
  sessions.csv  one row per class session: code, weekday (1=Mon), start, end (minutes of day), enrolled, building
  bells.csv     per weekday and period end: number of sessions and students released, sessions/students starting
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# official period table (selcrs query form)
PERIODS = [("A", "07:00", "07:50"), ("1", "08:10", "09:00"), ("2", "09:10", "10:00"), ("3", "10:10", "11:00"),
           ("4", "11:10", "12:00"), ("B", "12:10", "13:00"), ("5", "13:10", "14:00"), ("6", "14:10", "15:00"),
           ("7", "15:10", "16:00"), ("8", "16:10", "17:00"), ("9", "17:10", "18:00"), ("C", "18:20", "19:10"),
           ("D", "19:15", "20:05"), ("E", "20:10", "21:00"), ("F", "21:05", "21:55")]
ORDER = {p: i for i, (p, _, _) in enumerate(PERIODS)}
_m = lambda s: int(s[:2]) * 60 + int(s[3:])
START = {p: _m(a) for p, a, _ in PERIODS}
END = {p: _m(b) for p, _, b in PERIODS}
BELLS = sorted(set(END.values()))          # minutes of day at which some period ends


def _int(x):
    try:
        return int(str(x).strip())
    except ValueError:
        return 0


def building(time_room):
    """building code from e.g. '一8,9(社SS 2002-1)' -> 'SS'; non-coded rooms keep their Chinese name."""
    rooms = re.findall(r"\(([^)]*)\)", time_room or "")
    for r in rooms:
        m = re.search(r"([A-Z]{2,3})\s*\d", r)
        if m:
            return m.group(1)
        if r.strip():
            return re.split(r"[/\s\d]", r.strip())[0][:8]
    return ""


def load(path):
    """course dicts (code, class, dept, enrolled, building, days[7]) from the .json or .tsv export."""
    path = Path(path)
    out = []
    if path.suffix == ".json":
        for rec in json.load(open(path, encoding="utf-8")):
            out.append({"code": rec[2], "class": rec[4], "dept": rec[1], "enrolled": _int(rec[8]),
                        "building": building(rec[9]), "days": [x or "" for x in rec[10:17]]})
    else:
        for line in open(path, encoding="utf-8"):
            f = line.rstrip("\n").split("\t")
            if len(f) < 6:
                continue
            days = [""] * 7
            for part in filter(None, f[5].split(";")):
                wd, ps = part.split(":")
                days[int(wd) - 1] = ps
            out.append({"code": f[0], "class": f[1], "dept": f[2], "enrolled": _int(f[3]), "building": f[4],
                        "days": days})
    return out


OFFSITE = {"網路大學", "同步遠距", "台北", "上海同濟大學", "高雄榮總", "自行安排"}


def on_campus(c):
    b = c["building"]
    return not (c["dept"].startswith("校際") or b in OFFSITE or b.endswith("廠區") or b.startswith("海生館"))


def sessions(courses):
    """one row per contiguous block of periods on a weekday (a course meeting 1,2 and 5,6 on Monday has two)."""
    seen, out = set(), []
    for c in courses:
        if c["code"] in seen:
            continue
        seen.add(c["code"])
        for wd, s in enumerate(c["days"], start=1):
            ps = sorted({ch for ch in (s or "") if ch in ORDER}, key=ORDER.get)
            if not ps:
                continue
            block = [ps[0]]
            for p in ps[1:] + [None]:
                if p is not None and ORDER[p] == ORDER[block[-1]] + 1:
                    block.append(p)
                    continue
                out.append({"code": c["code"], "class": c["class"], "dept": c["dept"], "weekday": wd,
                            "start": START[block[0]], "end": END[block[-1]], "periods": "".join(block),
                            "enrolled": c["enrolled"], "building": c["building"]})
                if p is not None:
                    block = [p]
    return pd.DataFrame(out)


def bell_table(sess):
    rows = []
    for wd in range(1, 8):
        s = sess[sess.weekday == wd]
        for b in BELLS:
            e = s[s.end == b]
            rows.append({"weekday": wd, "bell": b, "sessions_ending": len(e), "students_released": int(e.enrolled.sum())})
        for st in sorted(set(START.values())):
            a = s[s.start == st]
            rows.append({"weekday": wd, "start": st, "sessions_starting": len(a), "students_arriving": int(a.enrolled.sum())})
    return pd.DataFrame(rows)


def intensity(sess, ts, offday):
    """timetable-intensity features for timestamps ts (pandas DatetimeIndex/Series) and an off-day mask.
    tt_out30 / tt_out60: students whose class ends in (t, t+30] / (t, t+60]  (bikes about to be rented)
    tt_outprev30:        students whose class ended in (t-30, t]
    tt_in30:             students whose class starts in (t, t+30]           (bikes about to be returned)
    tt_now:              students in class at t
    All in hundreds of students; zero on off days."""
    ts = pd.Series(pd.to_datetime(ts)).reset_index(drop=True)
    wd = ts.dt.dayofweek.values + 1
    mod = (ts.dt.hour * 60 + ts.dt.minute).values
    # per weekday arrays over minutes of day
    grid = {}
    for d in range(1, 8):
        s = sess[sess.weekday == d]
        end_cnt = np.zeros(24 * 60 + 61); start_cnt = np.zeros(24 * 60 + 61); now = np.zeros(24 * 60 + 1)
        np.add.at(end_cnt, s.end.values, s.enrolled.values)
        np.add.at(start_cnt, s.start.values, s.enrolled.values)
        for a, b, n in zip(s.start.values, s.end.values, s.enrolled.values):
            now[a:b] += n
        ce, cs = np.cumsum(end_cnt), np.cumsum(start_cnt)
        grid[d] = (ce, cs, now)
    out = np.zeros((len(ts), 5), dtype=np.float32)
    for d in range(1, 8):
        m = wd == d
        if not m.any():
            continue
        ce, cs, now = grid[d]
        t = mod[m]
        out[m, 0] = ce[t + 30] - ce[t]
        out[m, 1] = ce[t + 60] - ce[t]
        out[m, 2] = ce[t] - ce[np.maximum(t - 30, 0)]
        out[m, 3] = cs[t + 30] - cs[t]
        out[m, 4] = now[np.minimum(t, 24 * 60)]
    out[np.asarray(offday, bool)] = 0.0
    return pd.DataFrame(out / 100.0, columns=["tt_out30", "tt_out60", "tt_outprev30", "tt_in30", "tt_now"])


if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    recs = load(src)
    camp = [c for c in recs if on_campus(c)]
    print(f"{len(recs)} records, {len({c['code'] for c in recs})} courses; off campus: "
          f"{len({c['code'] for c in recs}) - len({c['code'] for c in camp})} courses, "
          f"{sum(c['enrolled'] for c in {c['code']: c for c in recs if not on_campus(c)}.values())} enrolments")
    sess = sessions(camp)
    sess.to_csv(out / "sessions.csv", index=False)
    bt = bell_table(sess)
    bt.to_csv(out / "bells.csv", index=False)
    print(f"{len(recs)} records, {sess[['code', 'class']].drop_duplicates().shape[0]} courses with a time slot, {len(sess)} sessions, "
          f"{int(sess.enrolled.sum())} student-sessions")
    rel = bt.dropna(subset=["bell"]).pivot_table(index="bell", columns="weekday", values="students_released", aggfunc="sum")
    rel.index = [f"{int(b) // 60:02d}:{int(b) % 60:02d}" for b in rel.index]
    print(rel.reindex(columns=range(1, 8)).fillna(0).astype(int).to_string())
    print("buildings:", sess.groupby("building").enrolled.sum().sort_values(ascending=False).head(25).to_dict())
