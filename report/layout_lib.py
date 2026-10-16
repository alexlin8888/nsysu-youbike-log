"""Coordinate-descent search over figure anchors (the element a figure follows) and sizes, minimising
blank space at the ends of columns. Each candidate is a full build (node + LibreOffice) + measurement.
Writes layout.json ({file: {"after": element id, "frac": scale}})."""
import json
import os
import subprocess
import time

import pdfplumber

ROOT = os.path.dirname(os.path.abspath(__file__))
TOP, BOTTOM = 72.0, 792 - 1622 / 20
COLS = [(72.0, 72.0 + 4677 / 20), (72.0 + 4677 / 20 + 544 / 20, 72.0 + 2 * 4677 / 20 + 544 / 20)]
SOFFICE = os.environ.get("SOFFICE", "soffice.py")   # LibreOffice wrapper that converts docx -> pdf
# allowed anchors (element ids from DUMP=1) and sizes per figure; default anchor first
SPACE = {
    "fig1_motivation.png": ([11, 6, 8, 9, 10, 13, 15], [1.0, 0.9]),
    "fig2_pipeline.png": ([21, 13, 15, 18, 23], [1.0]),
    "fig_architecture.png": ([27, 18, 21, 23, 25, 29, 30, 32, 34], [1.0]),
    "fig_nsysu_tide_a.png": ([85, 82, 84, 87], [1.0, 0.9]),
    "fig_nsysu_tide_b.png": ([85, 82, 84, 87, 88], [1.0, 0.9]),
    "fig_ntu_moves.png": ([89, 87, 88, 91, 94], [1.0, 0.9]),
    "fig_moves_check.png": ([89, 88, 91, 94, 95, 97], [1.0]),
    "fig_model.png": ([95, 91, 94, 97, 98, 99, 100], [1.0, 0.9]),
    "fig_gantt_hw3.png": ([121, 113, 115, 116, 117, 118, 119, 120], [1.0]),
    "fig3_demo_mock.png": ([122, 115, 116, 117, 118, 119, 120, 121], [1.0]),
}
cache = {}


def build(layout, keep_files=False):
    key = json.dumps(layout, sort_keys=True)
    if key in cache and not keep_files:
        return cache[key]
    env = dict(os.environ, FIG_DIR="figs/", LAYOUT=key)
    out = subprocess.run(["node", "build_hw3.js"], cwd=ROOT, env=env, capture_output=True, text=True).stdout
    if "ORDER_VIOLATION" in out:
        cache[key] = None
        return None
    figs = json.loads([l for l in out.splitlines() if l.startswith("FIGS:")][0][5:])
    subprocess.run(["python3", SOFFICE, "--headless", "--convert-to", "pdf", "HW3_54.docx"], cwd=ROOT, capture_output=True)
    cols = []
    with pdfplumber.open(os.path.join(ROOT, "HW3_54.pdf")) as pdf:
        n = len(pdf.pages)
        for pi, page in enumerate(pdf.pages, start=1):
            for ci, (x0, x1) in enumerate(COLS, start=1):
                crop = page.crop((x0 - 2, TOP - 2, x1 + 2, BOTTOM + 2))
                bottoms = [c["bottom"] for c in crop.chars] + [TOP]
                bottoms += [im["bottom"] for im in page.images if im["x1"] > x0 and im["x0"] < x1]
                bottoms += [r["bottom"] for r in crop.rects + crop.lines]
                cols.append((pi, ci, BOTTOM - max(bottoms)))
    full = BOTTOM - TOP - 1
    last_col2_empty = any(p == n and c == 2 and g >= full for p, c, g in cols)
    gaps = [(p, c, g) for (p, c, g) in cols if not (p == n and (c == 2 or last_col2_empty))]
    score = sum(max(0.0, g - 10) ** 2 for _, _, g in gaps) / 100 + 400 * max(0, n - 10)
    for f, v in layout.items():
        d = SPACE[f][0][0]
        score += 0.6 * abs(v.get("after", d) - d) + 60 * (1 - v.get("frac", 1.0))
    res = {"score": score, "pages": n, "gaps": gaps}
    cache[key] = res
    return res


def show(res, label):
    bad = [(p, c, round(g)) for p, c, g in res["gaps"] if g > 14]
    print(f"{label}: score {res['score']:.1f}, pages {res['pages']}, gaps>14: {bad}", flush=True)


