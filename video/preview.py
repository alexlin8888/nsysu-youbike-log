"""Draw single frames of the video at full size to look at them before a render.

Usage: python video/preview.py OUT_DIR SCENE@T [SCENE@T ...]     (T in seconds from the scene start)
       python video/preview.py OUT_DIR SCENE T1 T2 ...
Needs the video folder served at http://127.0.0.1:8771 (python -m http.server 8771 in video/).
"""
import base64
import sys
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
args = sys.argv[2:]
jobs = defaultdict(list)
if "@" in args[0]:
    for a in args:
        sc, t = a.split("@"); jobs[sc].append(float(t))
else:
    jobs[args[0]] = [float(x) for x in args[1:]]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    for scene, times in jobs.items():
        pg.goto(f"http://127.0.0.1:8771/engine/stage.html?scene={scene}")
        pg.wait_for_function("window.READY === true", timeout=30000)
        for t in times:
            data = pg.evaluate(f"frameJpeg({t}, 0.9)")
            f = out / f"{scene}_{t:05.2f}.jpg"
            f.write_bytes(base64.b64decode(data.split(",", 1)[1]))
            print(f)
    if errors:
        print("ERRORS:", errors[:8])
    b.close()
