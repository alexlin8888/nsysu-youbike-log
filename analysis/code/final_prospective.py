"""Results on the teaching days logged after the evaluation was frozen (Secs. 3.8 and 3.10 of the final report).

Usage: python final_prospective.py DATA_DIR DOCS_DIR OUT_DIR [--from 2026-11-17]

The held-out evaluation ended on 16 Nov, and nothing in the method was changed after it. The logger kept running, so
two of its checks can be repeated on days no part of the method saw:

  warning  final_reward.py with the chain still fitted up to 29 Oct (results/final/rates_fit_to_1029), on the
           teaching days from --from on: how many stockouts the predictive rule flagged and how early, how often a
           flag was followed by an empty station, and the timing of the operator's reward
  advice   the page's record of advice, written before the outcome since 18 Nov (demo_track.py), summed over the
           teaching days in DOCS_DIR/track.json: minutes until a rider leaving campus between 17:00 and 19:50 is on a
           bike, for the station the page named, the station in front of the rider and the nearest station the live
           counts show; the share whose first station had a bike; and how far the minutes the page expected were off

Writes OUT_DIR/prospective.json, with final_reward.py's files in OUT_DIR/reward.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from nsysu_data import load_logger  # noqa: E402

DATA, DOCS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
FROM = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else "2026-11-17"
RATES = HERE.parent / "results" / "final" / "rates_fit_to_1029"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- warning: the frozen chain on the later days
subprocess.run([sys.executable, str(HERE / "final_reward.py"), str(DATA), str(RATES), str(OUT / "reward"),
                "--test-from", FROM, "--test-end", "2099-12-31"], check=True, stdout=subprocess.DEVNULL)
setup = json.load(open(OUT / "reward" / "reward_setup.json"))
warn = pd.read_csv(OUT / "reward" / "reward_warning.csv").iloc[0]
tim = pd.read_csv(OUT / "reward" / "reward_timing.csv")
val = pd.read_csv(OUT / "reward" / "reward_value.csv")
wi = pd.read_csv(OUT / "reward" / "reward_whatif.csv")
pre = val[(val.window == "14:00-17:00") & val.rule.str.startswith("today")].iloc[0]
pre_pred = val[(val.window == "14:00-17:00") & val.rule.str.startswith("predictive")].iloc[0]
all_day = val[(val.window == "14:00-20:00") & val.rule.str.startswith("today")].iloc[0]
eve = wi[wi.window.str.startswith("evening") & (wi.rule == "predictive")].set_index("alpha")
warning = {
    "days": setup["test_days"], "n_days": len(setup["test_days"]),
    "events": int(warn.empty_events), "flagged": round(float(warn.flagged_before), 4),
    "lead_median_min": float(warn.lead_median_min), "lead_mean_min": round(float(warn.lead_mean_min), 1),
    "precision": round(float(warn.flag_then_empty_share), 4), "base": round(float(warn.base_empty40_share_with_bikes), 4),
    "empty_share_1730_1830": round(float(tim[tim.time.isin(["17:30", "18:00"])].empty_share.mean()), 4),
    "returns_before_17_share": round(float(pre.returns_all_per_day / all_day.returns_all_per_day), 4),
    "paid_now_before_17_share": round(float(pre.returns_paid_per_day / pre.returns_all_per_day), 4),
    "paid_pred_before_17_per_day": round(float(pre_pred.returns_paid_per_day), 1),
    "paid_now_before_17_per_day": round(float(pre.returns_paid_per_day), 1),
    "evening_cut": {str(a): round(float(eve.loc[a, "cut"]), 4) for a in eve.index},
}

# ---------------------------------------------------------------- advice: the record written before the outcome
track = json.load(open(DOCS / "track.json", encoding="utf-8"))
F = track["fields"]
days = sorted(d for d, v in track["days"].items() if v["teaching"] and d >= FROM)
advice = {}
for w in ("leave", "arrive", "dock"):
    tot = dict.fromkeys(F, 0.0)
    used = []
    for d in days:
        row = dict(zip(F, track["days"][d]["w"][w]))
        if row["cases"]:
            used.append(d)
            for k in F:
                tot[k] += row[k]
    n = tot["cases"]
    if not n:
        continue
    a = {"days": used, "n_days": len(used), "cases": int(n)}
    for k in ("pick", "near", "alt"):
        a[f"min_{k}"] = round(tot[f"min_{k}"] / n, 2)
        a[f"ok_{k}"] = round(tot[f"ok_{k}"] / n, 4)
        a[f"slow_{k}"] = round(tot[f"slow_{k}"] / n, 4)
    for ahead in (0, 10, 20, 30):
        a[f"err{ahead}"] = round(tot[f"err{ahead}"] / tot[f"n{ahead}"], 2) if tot[f"n{ahead}"] else None
    advice[w] = a

# ---------------------------------------------------------------- the logger to date
lg = load_logger(DATA)
snaps = lg[["date", "slot"]].drop_duplicates()
logger = {"snapshots": int(len(snaps)), "first_day": str(snaps.date.min()), "last_day": str(snaps.date.max())}

res = {"made": date.today().isoformat(), "frozen_after": "2026-11-16", "rates_fit_end": "2026-10-29", "from": FROM,
       "warning": warning, "advice": advice, "logger": logger}
json.dump(res, open(OUT / "prospective.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
