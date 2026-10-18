"""Sequential greedy layout: place figures one at a time in reading order. For figure k every candidate anchor
(and size) is built with the later figures at their current anchors, and scored by the blank space at the
ends of all columns up to the column after the one where figure k lands (pages beyond do not count yet), plus
a small penalty for moving away from the source position. Writes layout.json."""
import json, os, subprocess, sys, time
import pdfplumber
from layout_lib import ROOT, TOP, BOTTOM, COLS, SOFFICE
import importlib
SP = importlib.import_module(os.environ.get("LAYOUT_SPACE", "layout_v14_space"))

SPACE = SP.SPACE
ORDER = [f for f in SPACE if f.endswith(".png")]


def run(layout):
    env = dict(os.environ, FIG_DIR="figs/", LAYOUT=json.dumps(layout))
    out = subprocess.run(["node", "build_hw3.js"], cwd=ROOT, env=env, capture_output=True, text=True).stdout
    if "ORDER_VIOLATION" in out:
        return None
    subprocess.run(["python3", SOFFICE, "--headless", "--convert-to", "pdf", "HW3_54.docx"], cwd=ROOT, capture_output=True)
    cols, imgs = [], []
    with pdfplumber.open(os.path.join(ROOT, "HW3_54.pdf")) as pdf:
        n = len(pdf.pages)
        for pi, page in enumerate(pdf.pages):
            for ci, (x0, x1) in enumerate(COLS):
                crop = page.crop((x0 - 2, TOP - 2, x1 + 2, BOTTOM + 2))
                b = [c["bottom"] for c in crop.chars] + [TOP]
                b += [im["bottom"] for im in page.images if im["x1"] > x0 and im["x0"] < x1]
                b += [r["bottom"] for r in crop.rects + crop.lines]
                cols.append(BOTTOM - max(b))
                for im in page.images:
                    if im["x0"] >= x0 - 3 and im["x1"] <= x1 + 3 and im["top"] >= TOP - 5:
                        imgs.append((pi * 2 + ci, im["top"]))
    imgs.sort()
    return {"pages": n, "cols": cols, "imgs": [c for c, _ in imgs]}


def score_upto(res, k, lay):
    """gaps (> 10 pt) in columns 0 .. col(figure k) + 1, plus displacement penalties of figures 0..k."""
    if res is None or len(res["imgs"]) < len(ORDER):
        return 1e9
    last = res["imgs"][k] + 1
    gaps = sum(max(0.0, g - 10) for g in res["cols"][: last + 1])
    pen = 0.0
    for f in ORDER[: k + 1]:
        v = lay.get(f, {})
        pen += 0.6 * abs(v.get("after", SPACE[f][0][0]) - SPACE[f][0][0]) + 60 * (1 - v.get("frac", 1.0))
    return gaps + pen


def setf(lay, f, a, fr):
    d = SPACE[f][0][0]
    v = {}
    if a != d:
        v["after"] = a
    if fr != 1.0:
        v["frac"] = fr
    lay = {k: dict(x) for k, x in lay.items()}
    if v:
        lay[f] = v
    else:
        lay.pop(f, None)
    return lay


if __name__ == "__main__":
    layout = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    t0 = time.time()
    for k, f in enumerate(ORDER):
        if k < int(os.environ.get("SEQ_START", "0")):
            continue
        best = None
        for a in SPACE[f][0]:
            for fr in SPACE[f][1]:
                lay = setf(layout, f, a, fr)
                res = run(lay)
                sc = score_upto(res, k, lay)
                if best is None or sc < best[0] - 0.3:
                    best = (sc, lay, res)
        layout = best[1]
        r = best[2]
        print(f"{f}: {layout.get(f, 'default')} score {best[0]:.0f} pages {r['pages']} img col {r['imgs'][k]} "
              f"gaps {[round(g) for g in r['cols'][: r['imgs'][k] + 2]]} ({time.time() - t0:.0f}s)", flush=True)
        json.dump(layout, open(os.path.join(ROOT, "layout.json"), "w"), indent=1)
    res = run(layout)
    print("final", json.dumps(layout))
    print("pages", res["pages"], "gaps", [round(g) for g in res["cols"]])
