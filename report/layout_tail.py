"""Joint search over the anchors of the last figures and Table 4 (Secs. 3.6-4), starting from layout.json.
Score = 400 * (pages - 10) + blank space (> 10 pt) at the ends of all columns except the last page.
Usage: python3 layout_tail.py   (writes layout_tail.json and prints the ranking)"""
import itertools, json, sys
from layout_seq import run

base = json.load(open("layout.json"))
SIM = [104, 106, 107]
GANTT = [109, 112, 117, 118]
DEMO = [112, 117, 118]
T4 = [None, 117, 118]
DEF = {"fig_sim_ci.png": 106, "fig_gantt_hw3.png": 117, "fig3_demo_mock.png": 118}


def score(res):
    if res is None:
        return 1e9
    n = res["pages"]
    cols = res["cols"][: 2 * (n - 1)]
    return 400 * (n - 10) + sum(max(0.0, g - 10) for g in cols)


rows = []
for s, g, d, t in itertools.product(SIM, GANTT, DEMO, T4):
    if not (s <= g <= d):
        continue
    lay = {k: dict(v) for k, v in base.items()}
    for f, a in (("fig_sim_ci.png", s), ("fig_gantt_hw3.png", g), ("fig3_demo_mock.png", d)):
        lay.pop(f, None)
        if a != DEF[f]:
            lay[f] = {"after": a}
    lay.pop("Table 4", None)
    if t is not None:
        lay["Table 4"] = {"after": t}
    res = run(lay)
    sc = score(res)
    rows.append((sc, s, g, d, t, res and res["pages"], res and [round(x) for x in res["cols"][14:]]))
    print(f"sim {s} gantt {g} demo {d} T4 {t}: score {sc:.0f} pages {res and res['pages']} tail {rows[-1][-1]}", flush=True)
rows.sort(key=lambda r: r[0])
best = rows[0]
lay = {k: dict(v) for k, v in base.items()}
for f, a in (("fig_sim_ci.png", best[1]), ("fig_gantt_hw3.png", best[2]), ("fig3_demo_mock.png", best[3])):
    lay.pop(f, None)
    if a != DEF[f]:
        lay[f] = {"after": a}
if best[4] is not None:
    lay["Table 4"] = {"after": best[4]}
json.dump(lay, open("layout_tail.json", "w"), indent=1)
print("best", best[:6])
