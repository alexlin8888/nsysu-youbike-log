"""Report vertical white space in each column of a two-column CVPR PDF.

Occupied intervals per column = text lines (chars), images and drawn rules/rects (tables, boxes).
A gap is any vertical run inside the text area not covered by those, longer than MIN_GAP points.
The bottom of a column counts as a gap when the column ends early (except on the last page).

Usage: python whitespace.py FILE.pdf [--min 18]
"""
import sys

import pdfplumber

PDF = sys.argv[1]
MIN_GAP = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 18.0
TOP, BOTTOM = 72.0, 792 - 1622 / 20       # text area in points (page 612 x 792)
COLS = [(72.0, 72.0 + 4677 / 20), (72.0 + 4677 / 20 + 544 / 20, 72.0 + 2 * 4677 / 20 + 544 / 20)]


def merge(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + 0.5:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


report = []
with pdfplumber.open(PDF) as pdf:
    n = len(pdf.pages)
    for pi, page in enumerate(pdf.pages, start=1):
        objs = []
        for ch in page.chars:
            objs.append((ch["x0"], ch["x1"], ch["top"], ch["bottom"]))
        for im in page.images:
            objs.append((im["x0"], im["x1"], im["top"], im["bottom"]))
        for r in page.rects + page.lines:
            objs.append((r["x0"], r["x1"], r["top"], r["bottom"]))
        # the full-width title block on page 1: anything spanning both columns
        span_bottom = TOP
        for x0, x1, t, b in objs:
            if x0 < COLS[0][1] - 5 and x1 > COLS[1][0] + 5:
                span_bottom = max(span_bottom, b)
        for ci, (cx0, cx1) in enumerate(COLS, start=1):
            iv = [(max(t, TOP), min(b, BOTTOM)) for x0, x1, t, b in objs
                  if x1 > cx0 + 1 and x0 < cx1 - 1 and b > TOP and t < BOTTOM]
            top = span_bottom if pi == 1 else TOP
            iv = merge([(a, b) for a, b in iv if b > top])
            if not iv:
                report.append((pi, ci, top, BOTTOM, BOTTOM - top, "empty column"))
                continue
            prev = top
            for a, b in iv:
                if a - prev >= MIN_GAP:
                    report.append((pi, ci, prev, a, a - prev, "gap"))
                prev = max(prev, b)
            if BOTTOM - prev >= MIN_GAP and not (pi == n and ci == 2):
                report.append((pi, ci, prev, BOTTOM, BOTTOM - prev, "column ends early"))
print(f"{PDF}: {n} pages; gaps >= {MIN_GAP:.0f} pt (one text line = 12 pt)")
for pi, ci, a, b, h, kind in report:
    print(f"  page {pi} col {ci}: {kind:<18} {h:5.0f} pt  (y {a:.0f}-{b:.0f})")
print("total gap", round(sum(r[4] for r in report)), "pt")
