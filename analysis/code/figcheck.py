"""Figure QA. check(fig, name, ...) reports, before a figure is saved:
  - text clipped by the figure edge
  - (diagrams) text spilling out of the box it belongs to
  - data-coordinate labels leaving their axes
  - overlapping text pairs
  - text or legends drawn on top of data marks (lines, bars, scatter points, images, arrows)
boxes: optional list of (x0, y0, x1, y1) rectangles in data coordinates of `ax` (diagram boxes).
marks: run the text-on-marks check (off for diagrams, whose text sits on boxes by design).
allow_on_marks: text strings that may sit on marks (e.g. owner tags drawn inside Gantt bars).
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.path import Path
from matplotlib.text import Annotation


def _bboxes(fig):
    r = fig.canvas.get_renderer()
    out = []
    for t in fig.findobj(lambda a: hasattr(a, "get_window_extent") and a.__class__.__name__ in ("Text", "Annotation")):
        if not t.get_visible() or not t.get_text().strip():
            continue
        bb = t.get_window_extent(renderer=r)
        if bb.width == 0:
            continue
        out.append((t, bb))
    return out


def _densify(pts, step=2.0):
    """add points along the segments so that a line crossing a label is detected."""
    if len(pts) < 2:
        return pts
    out = [pts[:1]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = int(np.hypot(*(b - a)) // step)
        if n > 0:
            out.append(a + (b - a) * np.linspace(0, 1, n + 2)[1:-1, None])
        out.append(b[None, :])
    return np.vstack(out)


def _marks(ax, r):
    """display-space geometry of the data marks of one axes: points (N x 2, with a source tag per point),
    rectangles (bboxes) and images. Points outside the axes box are dropped (they are clipped anyway)."""
    pts, src, rects, images = [], [], [], []

    def add(block, tag):
        if len(block):
            pts.append(np.asarray(block, float)); src.extend([tag] * len(block))

    for k, ln in enumerate(ax.lines):
        if not ln.get_visible() or ln.get_gid() == "bg":
            continue
        xy = np.column_stack([np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)])
        xy = xy[np.isfinite(xy).all(axis=1)]
        if len(xy):
            add(_densify(ln.get_transform().transform(xy)), f"line{k}:{ln.get_label()[:15]}")
    for k, p in enumerate(ax.patches):
        if not p.get_visible() or p.get_gid() == "bg":
            continue
        if isinstance(p, Rectangle):
            bb = p.get_window_extent(r)
            if bb.width > 0.5 and bb.height > 0.5:
                rects.append(bb)
        else:
            path = p.get_path().transformed(p.get_transform())
            v = path.vertices if path.codes is None else path.vertices[(path.codes != Path.STOP) & (path.codes != Path.CLOSEPOLY)]
            add(_densify(v), f"patch{k}:{type(p).__name__}")
    for k, c in enumerate(ax.collections):
        if not c.get_visible():
            continue
        if isinstance(c, PathCollection):          # scatter
            off = c.get_offset_transform().transform(c.get_offsets())
            add(off, f"scatter{k}")
        else:                                       # fill_between etc.: polygon vertices
            for path in c.get_paths():
                v = path.vertices if path.codes is None else path.vertices[(path.codes != Path.STOP) & (path.codes != Path.CLOSEPOLY)]
                add(_densify(c.get_transform().transform(v), 4.0), f"coll{k}:{type(c).__name__}")
    for im in ax.images:
        if im.get_visible():
            images.append(im.get_window_extent(r))
    if pts:
        P = np.vstack(pts); S = np.array(src)
        ab = ax.get_window_extent(r)
        keep = (P[:, 0] >= ab.x0 - 1) & (P[:, 0] <= ab.x1 + 1) & (P[:, 1] >= ab.y0 - 1) & (P[:, 1] <= ab.y1 + 1)
        P, S = P[keep], S[keep]
    else:
        P, S = np.zeros((0, 2)), np.array([])
    return P, rects, images, S


def check(fig, name, boxes=None, ax=None, tol=0.5, allow_outside=False, marks=True, allow_on_marks=()):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    problems = []
    items = _bboxes(fig)
    for t, bb in items:
        if bb.x0 < -tol or bb.y0 < -tol or bb.x1 > W + tol or bb.y1 > H + tol:
            problems.append(f"clipped by figure edge: '{t.get_text()[:40]}' bbox=({bb.x0:.0f},{bb.y0:.0f},{bb.x1:.0f},{bb.y1:.0f}) fig=({W},{H})")
    if boxes is not None and ax is not None:
        for t, bb in items:
            if t.axes is not ax:
                continue
            x, y = t.get_position()
            inside = [b for b in boxes if b[0] <= x <= b[2] and b[1] <= y <= b[3]]
            if not inside:
                continue
            b = inside[0]
            bx0, by0 = ax.transData.transform((b[0], b[1])); bx1, by1 = ax.transData.transform((b[2], b[3]))
            if bb.x0 < bx0 - tol or bb.x1 > bx1 + tol or bb.y0 < by0 - tol or bb.y1 > by1 + tol:
                problems.append(f"spills out of its box: '{t.get_text()[:40]}' by ({bx0 - bb.x0:.0f},{bb.x1 - bx1:.0f},{by0 - bb.y0:.0f},{bb.y1 - by1:.0f}) px")
    for t, bb in items:
        axx = t.axes
        if allow_outside or axx is None or t.get_transform() is not axx.transData:
            continue
        ab = axx.get_window_extent(renderer=r)
        if bb.x0 < ab.x0 - tol or bb.x1 > ab.x1 + tol or bb.y0 < ab.y0 - tol or bb.y1 > ab.y1 + tol:
            problems.append(f"label leaves its axes: '{t.get_text()[:40]}'")
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            if a.overlaps(b):
                problems.append(f"overlap: '{items[i][0].get_text()[:30]}' <-> '{items[j][0].get_text()[:30]}'")
    if marks:
        # regions = free texts and annotations inside each axes + the legend; marks of that axes (and of
        # every axes for figure-level texts and figure legends)
        tick_ids = set()
        for a in fig.axes:
            for lab in a.get_xticklabels() + a.get_yticklabels() + a.get_xticklabels(minor=True) + a.get_yticklabels(minor=True):
                tick_ids.add(id(lab))
            tick_ids.update(id(x) for x in (a.xaxis.label, a.yaxis.label, a.title, a._left_title, a._right_title))
        geo = {a: _marks(a, r) for a in fig.axes}
        regions = []
        for t, bb in items:
            if id(t) in tick_ids or t.get_text() in allow_on_marks:
                continue
            regions.append((t.get_text()[:30], bb, [t.axes] if t.axes is not None else list(fig.axes)))
        for a in fig.axes:
            lg = a.get_legend()
            if lg is not None and lg.get_visible():
                regions.append(("legend", lg.get_window_extent(r), [a]))
        for lg in fig.legends:
            regions.append(("figure legend", lg.get_window_extent(r), list(fig.axes)))
        for label, bb, axes_list in regions:
            sb = bb.expanded(0.85, 0.85) if bb.width > 4 and bb.height > 4 else bb   # shrink about the centre: touching edges do not count
            hit = []
            for a in axes_list:
                pts, rects, images, _ = geo[a]
                if len(pts) and np.any((pts[:, 0] >= sb.x0) & (pts[:, 0] <= sb.x1) & (pts[:, 1] >= sb.y0) & (pts[:, 1] <= sb.y1)):
                    hit.append("line/arrow/area")
                if any(sb.overlaps(rb) for rb in rects):
                    hit.append("bar/box")
                if any(ib.overlaps(sb) for ib in images):
                    hit.append("image")
            if hit:
                where = ""
                for a in axes_list:
                    pts, srcs = geo[a][0], geo[a][3]
                    m = (pts[:, 0] >= sb.x0) & (pts[:, 0] <= sb.x1) & (pts[:, 1] >= sb.y0) & (pts[:, 1] <= sb.y1) if len(pts) else np.zeros(0, bool)
                    if m.any():
                        where = f" <- {srcs[m][0]} at px {pts[m][0].round(0).tolist()}"
                        break
                problems.append(f"on marks ({', '.join(sorted(set(hit)))}): '{label}'{where}")
    tag = "OK " if not problems else "BAD"
    print(f"[{tag}] {name}")
    for p in problems:
        print("     ", p)
    return problems
