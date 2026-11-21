"""Collect the numbers the video draws into video/build/data.json.

Usage: python video/data.py   (run from anywhere; reads docs/ and analysis/results/final/ of this repository)

Every map, chart and number in the video comes from this file, and this file only copies what the site and the
report already publish, so the video cannot drift from them:
  all, slots, campus   docs/replay_2026-11-11.json, the replay the site shows for Wednesday 11 Nov 2026
                       (bikes and free docks every 10 minutes, and the chance of running empty or full within 40 min)
  timing, warning      analysis/results/final/reward/ (report Sec. 3.10, Fig. 21)
  rates_lib            analysis/results/final/rates_fit_to_1029/rates_slots.csv, the library station (rentals and
                       returns per hour by 10-minute slot, fitted on days up to 29 Oct)
  test_days            the 12 held-out teaching days of the reward analysis
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "analysis" / "results" / "final"
OUT = Path(__file__).resolve().parent / "build" / "data.json"
SHORT = {"中山大學圖資大樓": "圖資", "中山大學西灣藝廊": "西灣藝廊", "中山大學工學院": "工學院", "中山大學材料大樓": "材料大樓",
         "中山大學社科院": "社科院", "中山大學體育館": "體育館", "中山大學海工館": "海工館", "中山大學海資館": "海資館"}
LIBRARY = "501209052"


def r3(x):
    return None if x is None else round(float(x), 3)


def main():
    rep = json.loads((ROOT / "docs" / "replay_2026-11-11.json").read_text())
    st = rep["stations"]
    idx = {s["name"]: i for i, s in enumerate(st)}
    campus = []
    for name, short in SHORT.items():
        i = idx[name]
        campus.append({"sno": st[i]["sno"], "name": short, "lat": st[i]["lat"], "lng": st[i]["lng"], "cap": st[i]["cap"],
                       "bikes": [s["bikes"][i] for s in rep["slots"]], "docks": [s["docks"][i] for s in rep["slots"]],
                       "empty40": [r3(s["reward"]["empty"][i]) for s in rep["slots"]],
                       "full40": [r3(s["reward"]["full"][i]) for s in rep["slots"]]})
    timing = [[r["time"], r3(r["empty_share"]), round(float(r["returns_per_day"]), 1), round(float(r["paid_now_per_day"]), 1),
               round(float(r["paid_pred_per_day"]), 1), round(float(r["value_mean"]), 2)]
              for r in csv.DictReader(open(FINAL / "reward" / "reward_timing.csv"))]
    w = next(csv.DictReader(open(FINAL / "reward" / "reward_warning.csv")))
    val = {(r["rule"].split(":")[0], r["window"]): r for r in csv.DictReader(open(FINAL / "reward" / "reward_value.csv"))}
    warning = {"events": int(w["empty_events"]), "flagged": r3(w["flagged_before"]), "lead_median": round(float(w["lead_median_min"])),
               "precision": round(float(w["flag_then_empty_share"]), 2), "base": r3(w["base_empty40_share_with_bikes"]),
               "worth": round(float(val[("predictive", "14:00-20:00")]["value_per_paid_return"]), 2),
               "worth_now": round(float(val[("today", "14:00-20:00")]["value_per_paid_return"]), 2),
               "worth_unpaid": round(float(val[("predictive", "14:00-20:00")]["value_per_return_unpaid"]), 2)}
    rates = [[int(r["slot"]), r3(r["lam_r"]), r3(r["lam_q"])]
             for r in csv.DictReader(open(FINAL / "rates_fit_to_1029" / "rates_slots.csv")) if r["sno"] == LIBRARY]
    setup = json.loads((FINAL / "reward" / "reward_setup.json").read_text())
    data = {"all": [[s["lat"], s["lng"]] for s in st], "slots": [s["t_min"] for s in rep["slots"]], "campus": campus,
            "timing": timing, "warning": warning, "rates_lib": sorted(rates), "test_days": setup["test_days"]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(OUT, len(data["all"]), "stations,", len(data["slots"]), "slots")


if __name__ == "__main__":
    main()
