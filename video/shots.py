"""Screenshots of the web app for the demo part of the video (JPEG, quality 92, phone size at 2x).

Usage: python video/shots.py [BASE_URL]   (default http://127.0.0.1:8770/index.html, the docs/ folder served locally)

Every shot is a replay moment of Wednesday 11 Nov 2026, the day the report's Fig. 19 also uses, so the numbers on
screen are the ones the narration reads. Writes video/assets/*.jpg and the brief's first page (brief.jpg).
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770/index.html"
OUT = Path(__file__).parent / "assets"
OUT.mkdir(exist_ok=True)
DAY = "?replay=2026-11-11"
SCROLL_TO = "(function(id, d){var s=document.getElementById('scroll'), e=document.getElementById(id); s.scrollTop = e.offsetTop - d; return s.scrollTop})"
SHOTS = [
    # name, query, sheet (half | full), script run before the shot
    ("rider_1640", DAY + "&t=16:40&from=lib&to=", "half", ""),
    ("rider_1740", DAY + "&t=17:40&from=lib&to=", "half", ""),
    ("policy_top", DAY + "&t=16:30&tab=policy", "full", ""),
    ("policy_table", DAY + "&t=16:30&tab=policy", "full", SCROLL_TO + "('polNow', 40)"),
    ("policy_map", DAY + "&t=16:30&tab=policy", "half", ""),
    ("sim_0", DAY + "&t=16:30&tab=policy", "full", SCROLL_TO + "('simEve', 20)"),
    ("sim_50", DAY + "&t=16:30&tab=policy", "full", "(function(){document.querySelector('#simEve [data-k=er] [data-v=\"2\"]').click(); return " + SCROLL_TO + "('simEve', 20)})()"),
    ("sim_50t", DAY + "&t=16:30&tab=policy", "full", "(function(){document.querySelector('#simEve [data-k=er] [data-v=\"2\"]').click(); document.querySelector('#simEve [data-k=et] [data-v=\"2\"]').click(); return " + SCROLL_TO + "('simEve', 20)})()"),
]


RECTS = {}
RECT_JS = """(() => {
  const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return [b.x * 2, b.y * 2, b.width * 2, b.height * 2].map(Math.round); };
  const q = (s) => r(document.querySelector(s));
  const vis = (el) => { const b = el.getBoundingClientRect(); return b.width > 0 && b.y < innerHeight && b.y + b.height > 0 && b.x > -20 && b.x < innerWidth; };
  return {
    best: q('#best'), tip: q('#tip'), tabPolicy: q('#tabPolicy'), tabRider: q('#tabRider'),
    glyphs: Array.from(document.querySelectorAll('.glyph')).filter(vis).map((g) => ({ rect: r(g), text: g.textContent.trim(), mark: !!g.querySelector('.rmark') })).filter((g) => g.rect[1] > 60),
    rows: Array.from(document.querySelectorAll('#polNow tbody tr')).map((tr) => ({ name: tr.querySelector('th').textContent, rect: r(tr), rule: r(tr.children[3]), pred: r(tr.children[4]) })),
    polsum: q('#polNow .polsum'), ruleHead: r(document.querySelectorAll('#polNow thead th')[3]), predHead: r(document.querySelectorAll('#polNow thead th')[4]),
    chip50: q('#simEve [data-k=er] [data-v="2"]'), chipTruck2: q('#simEve [data-k=et] [data-v="2"]'),
    simBig: q('#simEve .simout .big'), simMeta: q('#simEve .simout .meta'), simBars: q('#simEve .simout .simbar.try') || q('#simEve .simout .simbar.now'),
    polChart: q('#polChart'), polWhy: q('#polWhy'),
  };
})()"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, q, sheet, js in SHOTS:
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True, locale="zh-TW", color_scheme="light")
            pg = await ctx.new_page()
            await pg.goto(BASE + q, wait_until="domcontentloaded")
            await pg.wait_for_timeout(3500)
            for _ in range(3):
                if await pg.get_attribute("#shell", "data-sheet") == sheet:
                    break
                await pg.evaluate("document.getElementById('grip').click()")
                await pg.wait_for_timeout(600)
            if js:
                await pg.evaluate(js)
                await pg.wait_for_timeout(900)
            await pg.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=92)
            # where the things the video points at sit in the shot, in image pixels (2x the page's CSS pixels)
            RECTS[name] = await pg.evaluate(RECT_JS)
            print(name)
            await ctx.close()
        await b.close()
    json.dump(RECTS, open(OUT / "rects.json", "w"), ensure_ascii=False, indent=1)
    pdf = Path(__file__).parent.parent / "docs" / "policy_brief.pdf"
    subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", "quality=92", "-r", "110", "-singlefile", str(pdf), str(OUT / "brief")], check=True)
    print("brief")


asyncio.run(main())
