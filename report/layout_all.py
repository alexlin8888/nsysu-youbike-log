"""Full layout search: grid over Sec. 1-2 figures, grid over Sec. 3.2-3.3 figures, then coordinate descent
over tables and all figures. Starts from layout.json."""
import itertools, json, os, time
from layout_lib import build, show, ROOT, SPACE

SPACE.update({
    "Table 2": ([79, 84, 85], [1.0]),
    "Table 3": ([91, 94, 95], [1.0]),
    "Table 4": ([95, 98, 99], [1.0]),
    "Table 5": ([102, 105], [1.0]),
    "Table 6": ([107, 110, 111], [1.0]),
    "Table 7": ([113, 121, 122], [1.0]),
})
SPACE["fig_gantt_hw3.png"] = ([121, 113, 116, 122], [1.0])
SPACE["fig3_demo_mock.png"] = ([122, 113, 116, 121], [1.0])
layout = json.load(open(os.path.join(ROOT, "layout.json")))


def setf(lay, f, a, fr=1.0):
    d = SPACE[f][0][0]
    v = {}
    if a != d:
        v["after"] = a
    if fr != 1.0:
        v["frac"] = fr
    if v:
        lay[f] = v
    else:
        lay.pop(f, None)


best = build(layout)
show(best, "start")
t0 = time.time()


def grid(F, OPTS, tag):
    global best, layout
    for combo in itertools.product(*OPTS):
        if any(combo[i] > combo[i + 1] for i in range(len(combo) - 1)):
            continue
        lay = dict(layout)
        for f, a in zip(F, combo):
            setf(lay, f, a)
        r = build(lay)
        if r is not None and r["score"] < best["score"] - 0.3:
            best, layout = r, lay
            show(best, f"{tag} {combo} ({time.time() - t0:.0f}s)")
    json.dump(layout, open(os.path.join(ROOT, "layout.json"), "w"), indent=1)


grid(["fig1_motivation.png", "fig2_pipeline.png", "fig_architecture.png"], [[6, 11, 13, 15], [15, 18, 21, 23], [21, 23, 25, 27, 29]], "gridA")
grid(["fig_nsysu_tide_a.png", "fig_nsysu_tide_b.png", "fig_ntu_moves.png", "fig_moves_check.png"],
     [[82, 84, 85], [84, 85, 87], [87, 88, 89], [88, 89, 91, 94]], "gridB")
ORDER = list(SPACE.keys())
for rnd in range(2):
    changed = False
    for f in ORDER:
        anchors, fracs = SPACE[f]
        for a in anchors:
            for fr in fracs:
                lay = dict(layout)
                setf(lay, f, a, fr)
                if lay == layout:
                    continue
                r = build(lay)
                if r is not None and r["score"] < best["score"] - 0.3:
                    best, layout, changed = r, lay, True
        show(best, f"descent {rnd} {f} -> {layout.get(f, 'default')} ({time.time() - t0:.0f}s)")
        json.dump(layout, open(os.path.join(ROOT, "layout.json"), "w"), indent=1)
    if not changed:
        break
build(layout, keep_files=True)
print("final layout", json.dumps(layout))
show(best, "final")
