"""Figure QA: report any text artist that is clipped by the figure edge or (for diagrams) spills out of
the box it belongs to, and any pair of overlapping text artists. Call check(fig, name, boxes=...) before
saving. boxes: optional list of (x0, y0, x1, y1) rectangles in axes-data coordinates with the axis.
"""
import matplotlib.pyplot as plt


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


def check(fig, name, boxes=None, ax=None, tol=0.5, allow_outside=False):
    fig.canvas.draw()
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
            # find the box containing the anchor point
            inside = [b for b in boxes if b[0] <= x <= b[2] and b[1] <= y <= b[3]]
            if not inside:
                continue
            b = inside[0]
            bx0, by0 = ax.transData.transform((b[0], b[1])); bx1, by1 = ax.transData.transform((b[2], b[3]))
            if bb.x0 < bx0 - tol or bb.x1 > bx1 + tol or bb.y0 < by0 - tol or bb.y1 > by1 + tol:
                problems.append(f"spills out of its box: '{t.get_text()[:40]}' by ({bx0 - bb.x0:.0f},{bb.x1 - bx1:.0f},{by0 - bb.y0:.0f},{bb.y1 - by1:.0f}) px")
    # data-coordinate labels must stay inside their axes
    for t, bb in items:
        axx = t.axes
        if allow_outside or axx is None or t.get_transform() is not axx.transData:
            continue
        ab = axx.get_window_extent(renderer=fig.canvas.get_renderer())
        if bb.x0 < ab.x0 - tol or bb.x1 > ab.x1 + tol or bb.y0 < ab.y0 - tol or bb.y1 > ab.y1 + tol:
            problems.append(f"label leaves its axes: '{t.get_text()[:40]}'")
    # overlapping text pairs (same axes or figure-level)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            if a.overlaps(b):
                ta, tb = items[i][0].get_text(), items[j][0].get_text()
                problems.append(f"overlap: '{ta[:30]}' <-> '{tb[:30]}'")
    tag = "OK " if not problems else "BAD"
    print(f"[{tag}] {name}")
    for p in problems:
        print("     ", p)
    return problems
