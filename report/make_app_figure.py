#!/usr/bin/env python3
"""Figure 19 of the final report: two phone screenshots of the web app, side by side.

Usage: python3 report/make_app_figure.py [BASE_URL] [OUT_PNG]
       defaults: http://127.0.0.1:8770/index.html and report/figs/fig_demo_app.png

Serve docs/ first (python3 -m http.server 8770 --directory docs), or pass the public address. The page is opened in
English on a 360 x 760 phone screen with the list pulled up, at two moments of the replay of Wednesday 11 Nov 2026
(a day the page keeps for good, see docs/replays_keep.txt): 16:40 on the Borrow tab and 09:20 on the Return tab.
"""
import asyncio
import io
import sys

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770/index.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "report/figs/fig_demo_app.png"
SHOTS = ["?replay=2026-11-11&t=16:40&lang=en", "?replay=2026-11-11&t=09:20&tab=dock&lang=en"]
W, H, SCALE = 360, 760, 3
PANEL_W, GAP, EDGE = 720, 56, 2


async def shoot(browser, query):
    ctx = await browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=SCALE, has_touch=True, is_mobile=True, locale="en-US")
    page = await ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(BASE + query, wait_until="networkidle")
    await page.wait_for_timeout(1800)
    for _ in range(3):                                         # pull the list up over the map
        if await page.get_attribute("#shell", "data-sheet") == "full":
            break
        await page.evaluate("document.getElementById('grip').click()")
        await page.wait_for_timeout(600)
    png = await page.screenshot()
    await ctx.close()
    if errors:
        raise SystemExit("page error: " + errors[0])
    return Image.open(io.BytesIO(png)).convert("RGB")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        shots = [await shoot(browser, q) for q in SHOTS]
        await browser.close()
    ph = round(PANEL_W * H / W)
    fig = Image.new("RGB", (2 * (PANEL_W + 2 * EDGE) + GAP, ph + 2 * EDGE), "white")
    draw = ImageDraw.Draw(fig)
    for k, im in enumerate(shots):
        x = k * (PANEL_W + 2 * EDGE + GAP)
        fig.paste(im.resize((PANEL_W, ph), Image.LANCZOS), (x + EDGE, EDGE))
        draw.rectangle([x, 0, x + PANEL_W + 2 * EDGE - 1, ph + 2 * EDGE - 1], outline="#9aa5b1", width=EDGE)
    fig.save(OUT, optimize=True)
    print("wrote", OUT, fig.size)


asyncio.run(main())
