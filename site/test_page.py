#!/usr/bin/env python3
"""Functional checks of the demo page in a real browser (Playwright + Chromium).

Usage: python3 site/test_page.py [BASE_URL]        default http://127.0.0.1:8770/index.html

Serve docs/ first (python3 -m http.server 8770 --directory docs). Every check runs at several window sizes;
checks of the sheet run on phone sizes only. The data files are the real ones in docs/, except where a check
needs a particular situation (fresh data, stale data, a day off, a failed download) and rewrites state.json on
the fly. Prints one line per check and exits non-zero if any failed.
"""
import asyncio
import json
import re
import sys
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770/index.html"
TZ = timezone(timedelta(hours=8))
SIZES = {"desktop 1440x900": (1440, 900, False), "laptop 1280x720": (1280, 720, False), "tablet 820x1180": (820, 1180, True),
         "phone 390x844": (390, 844, True), "phone 430x932": (430, 932, True), "phone 360x640": (360, 640, True)}
REPLAY_DAY = None           # filled in from replays.json: the newest class day with a truck plan around 16:00
results = []


def record(size, name, ok, detail=""):
    results.append((size, name, ok, detail))
    print(("PASS" if ok else "FAIL"), "|", size, "|", name, ("| " + detail if detail else ""), flush=True)


async def new_page(browser, size, scheme="light", geo=None, perms=None, query="", state_patch=None, fail_state=False):
    w, h, touch = SIZES[size]
    ctx = await browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, locale="zh-TW", has_touch=touch, is_mobile=touch and w < 768,
                                    geolocation=geo, permissions=perms or [])
    page = await ctx.new_page()
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append("PAGEERROR " + str(e)))
    if fail_state:
        await page.route("**/state.json*", lambda r: r.fulfill(status=503, body="unavailable"))
    elif state_patch:
        async def patch(route):
            resp = await route.fetch()
            data = await resp.json()
            state_patch(data)
            await route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        await page.route("**/state.json*", patch)
    await page.goto(BASE + query, wait_until="networkidle", timeout=90000)
    await page.wait_for_timeout(900)
    return ctx, page


def fresh(data):
    data["snapshot_at"] = (datetime.now(TZ) - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")


def is_phone(size):
    return SIZES[size][0] < 768


async def sheet_state(page):
    return await page.get_attribute("#shell", "data-sheet")


async def open_sheet(page, size):
    """On phones the list sits in a sheet; open it fully so every control can be reached."""
    if is_phone(size) and await sheet_state(page) != "full":
        await page.evaluate("document.getElementById('grip').click()")
        await page.wait_for_timeout(350)
        if await sheet_state(page) != "full":
            await page.evaluate("document.getElementById('grip').click()")
            await page.wait_for_timeout(350)


async def swipe(page, x, y1, y2, steps=8):
    cdp = await page.context.new_cdp_session(page)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y1}]})
    for k in range(1, steps + 1):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y1 + (y2 - y1) * k / steps}]})
        await page.wait_for_timeout(16)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await page.wait_for_timeout(450)


# ---------------------------------------------------------------- checks
async def check_load(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    status = await page.inner_text("#statusText")
    record(size, "loads without script errors", not page.errors, "; ".join(page.errors[:3]))
    record(size, "status shows the snapshot time as fresh", bool(re.search(r"\d\d:\d\d", status)) and "stale" not in (await page.get_attribute("#status", "class")), status)
    over = await page.evaluate("[document.documentElement.scrollWidth, window.innerWidth, document.documentElement.scrollHeight, window.innerHeight]")
    record(size, "no sideways or page scroll", over[0] <= over[1] and over[2] <= over[3], str(over))
    board = await page.inner_text("#mini" if is_phone(size) else "#board")
    record(size, "bell board shows a countdown or a day-off note", bool(re.search(r"\d+ 分|今天|小時", board)), board.replace("\n", " ")[:60])
    glyphs = await page.locator(".glyph").count()
    record(size, "map draws every station", glyphs >= 300, f"{glyphs} marks")
    tiles = await page.evaluate("Array.from(document.querySelectorAll('.leaflet-tile')).filter(t => t.complete && t.naturalWidth > 0).length")
    record(size, "map tiles load", tiles > 0, f"{tiles} tiles")
    attr = await page.locator(".leaflet-control-attribution").bounding_box()
    record(size, "map attribution is on screen", attr is not None and attr["width"] > 20 and attr["y"] >= 0 and attr["y"] < SIZES[size][1], str(attr))
    # nothing interactive is clipped off the right edge
    clipped = await page.evaluate("""Array.from(document.querySelectorAll('button, a, input, select')).filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 1 || r.left < -1); }).map(e => e.id || e.className).slice(0, 5)""")
    record(size, "no control hangs off the edge", not clipped, str(clipped))
    await ctx.close()


async def check_rider(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await open_sheet(page, size)
    n = await page.locator("#near .row").count()
    record(size, "nearby list shows 8 stations", n == 8, str(n))
    await page.click("#more"); await page.wait_for_timeout(200)
    n16 = await page.locator("#near .row").count()
    await page.click("#more"); await page.wait_for_timeout(200)
    n8 = await page.locator("#near .row").count()
    record(size, "show more / show fewer", n16 == 16 and n8 == 8, f"{n16} then {n8}")
    walks = await page.locator("#near .row .walk").all_inner_texts()
    nums = [int(re.search(r"\d+", w).group()) for w in walks]
    record(size, "nearby list is ordered by walking time", nums == sorted(nums), str(nums))
    best_hidden = await page.get_attribute("#best", "hidden")
    best_name = await page.locator("#best .nm").inner_text() if await page.locator("#best .nm").count() else ""
    record(size, "a suggestion is shown", best_hidden is None and (bool(best_name) or "none" in (await page.get_attribute("#best", "class"))), best_name)
    if best_name:
        await page.click("#best"); await page.wait_for_timeout(500)
        card_name = await page.locator("#card .nm").inner_text()
        record(size, "tapping the suggestion opens that station", card_name == best_name and re.fullmatch(r"#\d+", await page.evaluate("location.hash")) is not None, f"{card_name} {await page.evaluate('location.hash')}")
        if is_phone(size):
            record(size, "opening a station brings the sheet to half height", await sheet_state(page) == "half", await sheet_state(page))
        href = await page.get_attribute("#card a.btn", "href"); target = await page.get_attribute("#card a.btn", "target")
        record(size, "walking directions link is well formed", bool(re.match(r"https://www\.google\.com/maps/dir/\?api=1&destination=22\.\d+,120\.\d+&travelmode=walking$", href or "")) and target == "_blank", href or "")
        facts = await page.locator("#card .fact .v").all_inner_texts()
        record(size, "card shows bikes, docks and the 30-minute chance", len(facts) == 3 and all(re.search(r"\d|–", f) for f in facts), " | ".join(f.replace("\n", "") for f in facts))
        chart = await page.locator("#card .chart svg path").count()
        record(size, "card draws today's stock", chart >= 1, f"{chart} paths")
        box = await page.locator("#card").bounding_box()
        record(size, "card fits the panel width", box["x"] >= 0 and box["x"] + box["width"] <= SIZES[size][0] + 1, str(box))
        # favourite on, visible in the list, survives a reload, favourite off
        await open_sheet(page, size)
        await page.click("#favBtn"); await page.wait_for_timeout(300)
        fav_rows = await page.locator("#favs .row").count(); fav_shown = await page.get_attribute("#favSec", "hidden") is None
        star = await page.locator(".glyph .star").count()
        await page.reload(wait_until="networkidle"); await page.wait_for_timeout(900)
        fav_after = await page.locator("#favs .row").count()
        record(size, "save a station: listed, starred on the map, kept after reload", fav_rows == 1 and fav_shown and star >= 1 and fav_after == 1, f"rows {fav_rows}, stars {star}, after reload {fav_after}")
        await open_sheet(page, size)
        await page.click("#favBtn"); await page.wait_for_timeout(300)
        record(size, "remove the saved station", await page.locator("#favs .row").count() == 0 and await page.get_attribute("#favSec", "hidden") is not None)
        await page.click("#cardX"); await page.wait_for_timeout(200)
        record(size, "close button hides the card and clears the address", await page.get_attribute("#cardWrap", "hidden") is not None and await page.evaluate("location.hash") == "")
        await page.locator("#near .row").nth(1).click(); await page.wait_for_timeout(300)
        await page.keyboard.press("Escape"); await page.wait_for_timeout(200)
        record(size, "Escape closes the card", await page.get_attribute("#cardWrap", "hidden") is not None)
    await ctx.close()


async def check_search(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await open_sheet(page, size)
    await page.fill("#q", "圖資"); await page.wait_for_timeout(250)
    hits = await page.locator("#qres button").all_inner_texts()
    record(size, "search finds a station by short name", any("圖資" in h for h in hits), " / ".join(h.replace("\n", " ") for h in hits)[:80])
    await page.keyboard.press("Enter"); await page.wait_for_timeout(500)
    record(size, "Enter opens the first result", "圖資" in await page.locator("#card .nm").inner_text())
    await open_sheet(page, size)
    await page.fill("#q", "library"); await page.wait_for_timeout(250)
    record(size, "search matches English names", await page.locator("#qres button").count() >= 1)
    await page.fill("#q", "不存在的站名"); await page.wait_for_timeout(250)
    record(size, "search with no match says so", "找不到" in await page.inner_text("#qres"), await page.inner_text("#qres"))
    await page.fill("#q", "捷運"); await page.wait_for_timeout(250)
    box = await page.locator("#qres").bounding_box()
    record(size, "result list stays inside the window", box["x"] >= 0 and box["x"] + box["width"] <= SIZES[size][0] + 1 and await page.locator("#qres button").count() == 8, str(box))
    await page.keyboard.press("Escape"); await page.wait_for_timeout(200)
    record(size, "Escape closes the results", await page.get_attribute("#qres", "hidden") is not None)
    await ctx.close()


async def check_origin(browser, size):
    # a starting point picked on the map
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await open_sheet(page, size)
    first = await page.locator("#near .row .nm").first.inner_text()
    await page.click("#oPick"); await page.wait_for_timeout(450)
    hint = await page.get_attribute("#hint", "hidden") is None
    if is_phone(size):
        record(size, "picking a start lowers the sheet to show the map", await sheet_state(page) == "peek", await sheet_state(page))
    m = await page.locator("#map").bounding_box()
    await page.mouse.click(m["x"] + m["width"] * 0.85, m["y"] + m["height"] * (0.2 if is_phone(size) else 0.8)); await page.wait_for_timeout(500)
    await open_sheet(page, size)
    first2 = await page.locator("#near .row .nm").first.inner_text()
    pressed = await page.get_attribute("#oPick", "aria-pressed")
    record(size, "pick a start on the map: hint shown, list re-sorted", hint and pressed == "true" and first2 != first and await page.get_attribute("#hint", "hidden") is not None, f"{first} -> {first2}")
    record(size, "the picked start is marked on the map", await page.locator(".originicon").count() == 1)
    await page.click("#oCampus"); await page.wait_for_timeout(400)
    record(size, "back to campus restores the list", await page.locator("#near .row .nm").first.inner_text() == first and await page.get_attribute("#oCampus", "aria-pressed") == "true")
    await ctx.close()
    # my location: on campus, far away, refused
    ctx, page = await new_page(browser, size, state_patch=fresh, geo={"latitude": 22.6247, "longitude": 120.2811}, perms=["geolocation"])
    await open_sheet(page, size)
    await page.click("#oMe"); await page.wait_for_timeout(900)
    await open_sheet(page, size)
    record(size, "my location near campus becomes the start", await page.get_attribute("#oMe", "aria-pressed") == "true" and await page.get_attribute("#fab", "aria-pressed") == "true", await page.locator("#near .row .nm").first.inner_text())
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh, geo={"latitude": 25.0174, "longitude": 121.5397}, perms=["geolocation"])
    await page.click("#fab"); await page.wait_for_timeout(900)
    toast = await page.inner_text("#toast")
    record(size, "my location far from NSYSU keeps the campus start and says why", await page.get_attribute("#oCampus", "aria-pressed") == "true" and "不在中山附近" in toast, toast)
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await page.click("#fab"); await page.wait_for_timeout(1200)
    toast = await page.inner_text("#toast")
    record(size, "location refused: a message points to the map picker", "拿不到你的位置" in toast and await page.get_attribute("#oCampus", "aria-pressed") == "true", toast)
    await ctx.close()


async def check_ops(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await page.click("#tabOps"); await page.wait_for_timeout(500)
    await open_sheet(page, size)
    stats = [await page.inner_text(i) for i in ("#tEmpty", "#tRisk", "#tUnmet", "#tSaved")]
    record(size, "dispatch tab shows its four numbers", all(re.search(r"\d|–", s) for s in stats) and await page.get_attribute("#paneRider", "hidden") is not None, " | ".join(s.replace("\n", " ") for s in stats))
    rows = await page.locator("#risk li").count()
    vals = [float(v.strip("%")) for v in await page.locator("#risk .pv").all_inner_texts()]
    record(size, "risk list: ten stations, highest first", rows == 10 and vals == sorted(vals, reverse=True), str(vals))
    await page.click("#hU"); await page.wait_for_timeout(300)
    h_u = await page.inner_text("#hRisk"); vals_u = [float(v) for v in await page.locator("#risk .pv").all_inner_texts()]
    await page.click("#h60"); await page.wait_for_timeout(300)
    h_60 = await page.inner_text("#hRisk")
    record(size, "30 / 60 min / 90-min shortfall switch re-ranks the list", "90" in h_u and vals_u == sorted(vals_u, reverse=True) and "90" not in h_60 and await page.get_attribute("#h60", "aria-pressed") == "true", f"{h_u} | {h_60}")
    await page.locator("#risk li").first.click(); await page.wait_for_timeout(500)
    record(size, "a risk row opens its station", await page.get_attribute("#cardWrap", "hidden") is None)
    plan_or_note = await page.locator("#plans .stop").count() + await page.locator("#plans .empty").count()
    record(size, "route section shows a plan or says why there is none", plan_or_note >= 1, (await page.inner_text("#plans")).replace("\n", " ")[:70])
    if not is_phone(size) and SIZES[size][0] >= 1100:
        record(size, "legend follows the tab", "機率" in await page.inner_text("#legend") or "人次" in await page.inner_text("#legend"), (await page.inner_text("#legend")).replace("\n", " ")[:50])
    await ctx.close()


async def check_replay(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh, perms=["clipboard-read", "clipboard-write"])
    await page.click("#mReplay"); await page.wait_for_timeout(1500)
    bar = await page.get_attribute("#replaybar", "hidden") is None
    mx = int(await page.get_attribute("#slider", "max")); t0 = await page.inner_text("#sliderT")
    record(size, "replay opens with its controls", bar and mx > 30 and re.fullmatch(r"\d\d:\d\d", t0) is not None and await page.get_attribute("#shell", "data-mode") == "replay", f"{mx + 1} snapshots, at {t0}")
    box = await page.locator("#replaybar").bounding_box()
    record(size, "replay bar fits the map", box["x"] >= 0 and box["x"] + box["width"] <= SIZES[size][0] + 1, str(box))
    await page.evaluate("const s = document.getElementById('slider'); s.value = 10; s.dispatchEvent(new Event('input', { bubbles: true }));"); await page.wait_for_timeout(300)
    t1 = await page.inner_text("#sliderT")
    board = await page.inner_text("#mini" if is_phone(size) else "#board")
    record(size, "moving the slider changes the time and the bell board", t1 != t0 and bool(re.search(r"\d", board)), f"{t0} -> {t1}; {board.replace(chr(10), ' ')[:40]}")
    await page.click("#play"); await page.wait_for_timeout(1700)
    t2 = await page.inner_text("#sliderT")
    await page.click("#play"); await page.wait_for_timeout(900); t3 = await page.inner_text("#sliderT"); await page.wait_for_timeout(900)
    record(size, "play advances, pause stops", t2 != t1 and await page.inner_text("#sliderT") == t3, f"{t1} -> {t2} -> {t3}")
    days = await page.locator("#replayDay option").count()
    if days > 1:
        await page.select_option("#replayDay", index=1); await page.wait_for_timeout(1500)
        record(size, "another day loads", await page.locator("#replayDay").input_value() != "" and not page.errors and await page.get_attribute("#err", "hidden") is not None, f"{days} days offered")
    await page.click("#mLive"); await page.wait_for_timeout(500)
    record(size, "back to live", await page.get_attribute("#replaybar", "hidden") is not None and await page.get_attribute("#shell", "data-mode") == "live")
    await ctx.close()
    # a moment with a truck plan, reached by link
    ctx, page = await new_page(browser, size, perms=["clipboard-read", "clipboard-write"], query=f"?replay={REPLAY_DAY}&t=16:00&tab=ops")
    await page.wait_for_timeout(1200)
    await open_sheet(page, size)
    stops = await page.locator("#plans .stop").count()
    record(size, "a link opens a replay moment with a truck plan", await page.inner_text("#sliderT") == "16:00" and stops >= 2 and await page.locator(".stopicon").count() == stops, f"{REPLAY_DAY} 16:00, {stops} stops")
    if stops:
        await page.click("#copyAll"); await page.wait_for_timeout(400)
        clip = await page.evaluate("navigator.clipboard.readText()")
        record(size, "copy route puts the stops on the clipboard", "卡車 1" in clip and clip.count("\n") >= stops and await page.inner_text("#copyAll") == "已複製", clip.replace("\n", " / ")[:110])
        name = await page.locator("#plans .stop .nm").first.inner_text()
        await page.locator("#plans .stop").first.click(); await page.wait_for_timeout(500)
        record(size, "a stop opens its station", await page.locator("#card .nm").inner_text() == name, name)
    await ctx.close()


async def check_about_lang(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await page.click("#tabAbout"); await page.wait_for_timeout(400)
    await open_sheet(page, size)
    record(size, "about tab explains the colours and the numbers", await page.locator("#aboutKey li").count() == 8 and "LightGBM" in await page.inner_text("#aboutHow"))
    await page.click("#lEn"); await page.wait_for_timeout(400)
    en = [await page.inner_text(i) for i in ("#tabRiderT", "#tabOpsT", "#tabAboutT", "#mLive")]
    await page.click("#tabRider"); await page.wait_for_timeout(300)
    leftover = await page.evaluate("Array.from(document.querySelectorAll('#paneRider *, .tabs *, .top *')).filter(e => e.children.length === 0 && /[\\u4e00-\\u9fff]/.test(e.textContent)).map(e => e.textContent.trim()).filter(Boolean).slice(0, 6)")
    record(size, "English: tabs, header and the rider list are translated", en == ["Find a bike", "Dispatch", "About", "Live"] and not leftover, f"{en} leftover {leftover}")
    await page.reload(wait_until="networkidle"); await page.wait_for_timeout(700)
    record(size, "language choice is remembered", await page.inner_text("#tabRiderT") == "Find a bike" and await page.evaluate("document.documentElement.lang") == "en")
    await page.click("#tabAbout"); await page.wait_for_timeout(300); await open_sheet(page, size)
    await page.click("#lZh"); await page.wait_for_timeout(300)
    record(size, "back to Chinese", await page.inner_text("#tabRiderT") == "找車")
    over = await page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    record(size, "English text does not widen the page", over[0] <= over[1], str(over))
    await ctx.close()
    ctx, page = await new_page(browser, size, query="?tab=ops&lang=en")
    record(size, "links can set the tab and the language", await page.get_attribute("#tabOps", "aria-selected") == "true" and await page.inner_text("#tabOpsT") == "Dispatch")
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh, query="#501209069")
    await page.wait_for_timeout(600)
    name = await page.locator("#card .nm").inner_text() if await page.locator("#card .nm").count() else ""
    record(size, "a link can open one station", "體育館" in name, name)
    await ctx.close()


async def check_states(browser, size):
    def stale(data):
        data["snapshot_at"] = (datetime.now(TZ) - timedelta(minutes=140)).strftime("%Y-%m-%d %H:%M")
    ctx, page = await new_page(browser, size, state_patch=stale)
    cls = await page.get_attribute("#status", "class"); err = await page.inner_text("#err") if await page.get_attribute("#err", "hidden") is None else ""
    record(size, "old data is flagged and explained", "stale" in cls and "沒有新資料" in err, f"{await page.inner_text('#statusText')} | {err}")
    await ctx.close()
    ctx, page = await new_page(browser, size, fail_state=True)
    err = await page.inner_text("#err") if await page.get_attribute("#err", "hidden") is None else ""
    record(size, "a failed download says what to do", "重新整理" in err, err)
    await ctx.close()

    def dayoff(data):
        fresh(data); data["offday"] = 1; data["next_bell"] = None; data["bell"] = None
    ctx, page = await new_page(browser, size, state_patch=dayoff)
    board = await page.inner_text("#mini" if is_phone(size) else "#board")
    await open_sheet(page, size)
    rows = await page.locator("#near .row").count()
    record(size, "a day off: board says so, list still works without an after-class estimate", "今天沒課" in board and rows == 8 and "預估剩" not in await page.inner_text("#near"), board.replace("\n", " "))
    await ctx.close()

    def night(data):
        fresh(data); data["in_window"] = False; data["plans"] = []; data["unmet"] = [None] * len(data["unmet"]); data["totals"]["expected_unmet"] = None
    ctx, page = await new_page(browser, size, state_patch=night, query="?tab=ops")
    await open_sheet(page, size)
    record(size, "outside planning hours the route section explains itself", "06:00" in await page.inner_text("#plans") and not page.errors, (await page.inner_text("#plans"))[:40] + " " + "; ".join(page.errors[:2]))
    await ctx.close()
    ctx, page = await new_page(browser, size, scheme="dark", state_patch=fresh)
    bg = await page.evaluate("getComputedStyle(document.body).backgroundColor")
    surface = await page.evaluate("getComputedStyle(document.querySelector(window.innerWidth < 768 ? '#panel' : '.side')).backgroundColor")
    record(size, "dark mode switches the surfaces", bg == "rgb(11, 19, 27)" and surface == "rgb(19, 30, 41)" and not page.errors, f"{bg} {surface}")
    await ctx.close()


async def check_keyboard_a11y(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    unnamed = await page.evaluate("""Array.from(document.querySelectorAll('button, a, input, select')).filter(e => e.offsetParent !== null && !(e.textContent.trim() || e.getAttribute('aria-label') || e.getAttribute('title') || e.getAttribute('placeholder'))).map(e => e.id || e.className)""")
    record(size, "every control has a name for screen readers", not unnamed, str(unnamed))
    await page.focus("#tabRider"); await page.keyboard.press("ArrowRight"); await page.wait_for_timeout(250)
    ops = await page.get_attribute("#tabOps", "aria-selected")
    await page.keyboard.press("ArrowLeft"); await page.wait_for_timeout(250)
    record(size, "arrow keys move between tabs", ops == "true" and await page.get_attribute("#tabRider", "aria-selected") == "true")
    await open_sheet(page, size)
    await page.locator("#near .row").first.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(400)
    record(size, "Enter on a focused row opens the station", await page.get_attribute("#cardWrap", "hidden") is None)
    if SIZES[size][2]:
        small = await page.evaluate("""Array.from(document.querySelectorAll('.tabs button, .opt, .row, .seg button, .fab, .btn, .more, #grip, .card .x')).filter(e => e.offsetParent !== null).map(e => [e.id || e.className, Math.round(e.getBoundingClientRect().height)]).filter(x => x[1] < 30)""")
        record(size, "touch targets are at least 30 px tall", not small, str(small[:6]))
    await ctx.close()


async def check_sheet(browser, size):
    w, h, _ = SIZES[size]
    ctx, page = await new_page(browser, size, state_patch=fresh)
    record(size, "sheet starts at half height", await sheet_state(page) == "half")
    panel = await page.locator("#panel").bounding_box(); nav = await page.locator("#tabs").bounding_box()
    record(size, "tab bar sits at the bottom, sheet above it", abs(nav["y"] + nav["height"] - h) <= 1 and panel["y"] > 80 and panel["y"] < nav["y"], f"panel top {panel['y']:.0f}, nav top {nav['y']:.0f}")
    await page.click("#grip"); await page.wait_for_timeout(400); s1 = await sheet_state(page)
    await page.click("#grip"); await page.wait_for_timeout(400); s2 = await sheet_state(page)
    record(size, "tapping the handle opens and half-closes the sheet", s1 == "full" and s2 == "half", f"{s1}, {s2}")
    y = (await page.locator("#scroll").bounding_box())["y"] + 90
    await swipe(page, w / 2, y, y - 260); s_up = await sheet_state(page)
    top0 = await page.evaluate("document.getElementById('scroll').scrollTop")
    await swipe(page, w / 2, h * 0.7, h * 0.3); top1 = await page.evaluate("document.getElementById('scroll').scrollTop")
    record(size, "swiping up opens the sheet, then the list scrolls", s_up == "full" and top0 == 0 and top1 > 40, f"{s_up}, scrollTop {top0} -> {top1}")
    await page.evaluate("document.getElementById('scroll').scrollTop = 0")
    await swipe(page, w / 2, h * 0.35, h * 0.35 + 240); s_down = await sheet_state(page)
    record(size, "pulling down from the top lowers it", s_down in ("half", "peek"), s_down)
    await page.evaluate("document.getElementById('grip').click()") if await sheet_state(page) == "peek" else None
    await page.wait_for_timeout(300)
    m = await page.locator("#map").bounding_box()
    await page.touchscreen.tap(m["x"] + 30, m["y"] + 150); await page.wait_for_timeout(450)
    s_tap = await sheet_state(page)
    fab = await page.locator("#fab").bounding_box(); panel = await page.locator("#panel").bounding_box()
    record(size, "tapping the map lowers the sheet to a peek", s_tap == "peek", s_tap)
    record(size, "locate button stays just above the sheet", fab["y"] + fab["height"] <= panel["y"] + 1 and panel["y"] - (fab["y"] + fab["height"]) < 40, f"button bottom {fab['y'] + fab['height']:.0f}, sheet top {panel['y']:.0f}")
    await page.click("#tabOps"); await page.wait_for_timeout(400)
    record(size, "choosing a tab raises a peeking sheet", await sheet_state(page) == "half")
    await page.click("#tabRider"); await page.wait_for_timeout(300)
    await page.tap("#q"); await page.wait_for_timeout(400)
    record(size, "focusing the search opens the sheet fully", await sheet_state(page) == "full")
    await page.keyboard.press("Escape")
    # a station tapped on the map opens, and its mark stays in the part of the map the sheet leaves uncovered
    await page.evaluate("document.getElementById('grip').click()"); await page.wait_for_timeout(450)
    panel = await page.locator("#panel").bounding_box(); top = await page.locator(".top").bounding_box()
    spot = await page.evaluate("""([lo, hi]) => { for (const g of document.querySelectorAll('.glyph')) { const r = g.getBoundingClientRect(); const y = r.top + r.height / 2, x = r.left + r.width / 2; if (y > lo + 60 && y < hi - 30 && x > 40 && x < window.innerWidth - 70) return [x, y]; } return null; }""", [top["y"] + top["height"], panel["y"]])
    if spot:
        await page.touchscreen.tap(spot[0], spot[1]); await page.wait_for_timeout(800)
        sel = await page.locator(".glyph.sel").bounding_box(); panel = await page.locator("#panel").bounding_box()
        record(size, "tapping a station on the map opens it, still in view above the sheet", await page.get_attribute("#cardWrap", "hidden") is None and sel is not None and sel["y"] + sel["height"] < panel["y"] and sel["y"] > top["y"] + top["height"], f"mark at y {sel['y']:.0f}, sheet top {panel['y']:.0f}")
    else:
        record(size, "tapping a station on the map opens it, still in view above the sheet", False, "no station mark in the visible part of the map")
    await ctx.close()


async def check_assets(browser, size):
    ctx, page = await new_page(browser, size)
    base = BASE.rsplit("/", 1)[0] + "/"
    out = await page.evaluate("""async (base) => { const r = {}; for (const f of ['manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png', 'vendor/leaflet.js', 'replays.json']) { const x = await fetch(base + f); r[f] = x.status; } const m = await (await fetch(base + 'manifest.webmanifest')).json(); r.name = m.short_name; r.icons = m.icons.length; r.display = m.display; return r; }""", base)
    record(size, "manifest, icons and the map library are served", all(v == 200 for k, v in out.items() if isinstance(v, int) and k != "icons") and out["display"] == "standalone" and out["icons"] == 3, json.dumps(out))
    head = await page.evaluate("[document.querySelector('link[rel=manifest]') !== null, document.querySelector('meta[name=theme-color]').content, document.querySelector('meta[name=viewport]').content, document.title]")
    record(size, "page declares its manifest, theme colour and viewport", head[0] and head[1] == "#10202f" and "viewport-fit=cover" in head[2], str(head))
    await ctx.close()


async def main():
    global REPLAY_DAY
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(); page = await ctx.new_page()
        base = BASE.rsplit("/", 1)[0] + "/"
        REPLAY_DAY = await page.evaluate("""async (base) => { const d = (await (await fetch(base + 'replays.json')).json()).days; for (const day of d) { const r = await (await fetch(base + 'replay_' + day + '.json')).json(); const s = r.slots.find(x => x.snapshot_at.endsWith('16:00')); if (!r.offday && s && s.plans.length) return day; } return d[0]; }""", base) if await page.goto(base + "replays.json") else None
        await ctx.close()
        print("replay day used for the plan checks:", REPLAY_DAY, flush=True)
        for size in SIZES:
            for check in (check_load, check_rider, check_search, check_origin, check_ops, check_replay, check_about_lang, check_states, check_keyboard_a11y):
                try:
                    await check(browser, size)
                except Exception as exc:  # noqa: BLE001 - a crashed check is a failed check
                    record(size, check.__name__ + " crashed", False, str(exc).splitlines()[0][:200])
            if is_phone(size):
                try:
                    await check_sheet(browser, size)
                except Exception as exc:  # noqa: BLE001
                    record(size, "check_sheet crashed", False, str(exc).splitlines()[0][:200])
        try:
            await check_assets(browser, "desktop 1440x900")
        except Exception as exc:  # noqa: BLE001
            record("desktop 1440x900", "check_assets crashed", False, str(exc).splitlines()[0][:200])
        await browser.close()
    failed = [r for r in results if not r[2]]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    for size, name, _, detail in failed:
        print("  FAIL", size, "|", name, "|", detail)
    sys.exit(1 if failed else 0)


asyncio.run(main())
