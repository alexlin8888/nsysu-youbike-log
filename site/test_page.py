#!/usr/bin/env python3
"""Functional checks of the demo page in a real browser (Playwright + Chromium).

Usage: python3 site/test_page.py [BASE_URL]        default http://127.0.0.1:8770/index.html

Serve docs/ first (python3 -m http.server 8770 --directory docs). Every check runs at six window sizes;
checks of the sheet run on phone sizes only. The data files are the real ones in docs/, except where a check
needs a particular situation (fresh data, stale data, a day off, a failed download) and rewrites state.json on
the fly. Two outside services are replaced so that a run does not depend on them: map tiles are a blank image
(BTB_REAL_TILES=1 asks OpenStreetMap instead) and the operator's API is silent unless a check supplies its
reply. Prints one line per check and exits non-zero if any failed.
"""
import asyncio
import base64
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770/index.html"
TZ = timezone(timedelta(hours=8))
SIZES = {"desktop 1440x900": (1440, 900, False), "laptop 1280x720": (1280, 720, False), "tablet 820x1180": (820, 1180, True),
         "phone 390x844": (390, 844, True), "phone 430x932": (430, 932, True), "phone 360x640": (360, 640, True)}
if os.environ.get("BTB_SIZES"):                 # e.g. BTB_SIZES="phone 390" runs one size while editing
    SIZES = {k: v for k, v in SIZES.items() if any(k.startswith(x.strip()) for x in os.environ["BTB_SIZES"].split(","))}
REPLAY_DAY = None           # filled in from replays.json: the newest class day with a truck plan at 16:00
REAL_TILES = os.environ.get("BTB_REAL_TILES") == "1"
PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
TRACK_FIELDS = ["cases", "min_pick", "min_near", "min_alt", "ok_pick", "ok_near", "ok_alt", "slow_pick", "slow_near", "slow_alt",
                "n0", "err0", "n10", "err10", "n20", "err20", "n30", "err30"]
results = []


def record(size, name, ok, detail=""):
    results.append((size, name, ok, detail))
    print(("PASS" if ok else "FAIL"), "|", size, "|", name, ("| " + detail if detail else ""), flush=True)


async def ready(page, replay=False):
    """Wait until the page has drawn its data: the status line has left "loading" (or an error is shown) and the list of places is in."""
    try:
        await page.wait_for_function("""() => { const s = document.getElementById('statusText').textContent; return (s !== '讀取資料中' && s !== 'Loading data') || !document.getElementById('err').hidden; }""", timeout=30000)
        if replay:
            await page.wait_for_function("""() => document.getElementById('shell').dataset.mode === 'replay' && /^\\d\\d:\\d\\d$/.test(document.getElementById('sliderT').textContent)""", timeout=30000)
        await page.wait_for_function("() => document.querySelectorAll('#fromSel option').length > 3", timeout=8000)
    except Exception:  # noqa: BLE001 - the check that follows reports what is missing
        pass
    await page.wait_for_timeout(700)


async def reload(page):
    await page.reload(wait_until="domcontentloaded")
    await ready(page)


async def new_page(browser, size, scheme="light", geo=None, perms=None, query="", state_patch=None, fail_state=False, counts=None, track=None):
    """counts: the operator's reply (a list of stations) for this page; None leaves the API unanswered.
    track: a replacement for track.json, or False for "no such file"; None serves the real one."""
    w, h, touch = SIZES[size]
    ctx = await browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, locale="zh-TW", has_touch=touch, is_mobile=touch and w < 768,
                                    geolocation=geo, permissions=perms or [])
    page = await ctx.new_page()
    page.errors = []; page.api_calls = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" and "ERR_FAILED" not in m.text and "Failed to load resource" not in m.text else None)
    page.on("pageerror", lambda e: page.errors.append("PAGEERROR " + str(e)))
    if not REAL_TILES:
        await page.route("https://tile.openstreetmap.org/**", lambda r: r.fulfill(status=200, content_type="image/png", body=PIXEL))

    async def api(route):
        page.api_calls.append(route.request.post_data or "")
        if counts is None:
            await route.abort()
        else:
            await route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body=json.dumps({"retCode": 1, "retVal": {"data": counts}}))
    await page.route("https://apis.youbike.com.tw/**", api)
    if track is not None:
        await page.route("**/track.json*", lambda r: r.fulfill(status=404, body="") if track is False else r.fulfill(status=200, content_type="application/json", body=json.dumps(track)))
    if fail_state:
        await page.route("**/state.json*", lambda r: r.fulfill(status=503, body="unavailable"))
    elif state_patch:
        async def patch(route):
            resp = await route.fetch()
            data = await resp.json()
            state_patch(data)
            await route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        await page.route("**/state.json*", patch)
    await page.goto(BASE + query, wait_until="domcontentloaded", timeout=90000)
    await ready(page, replay="replay=" in query)
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
    record(size, "map tiles are drawn", tiles > 0, f"{tiles} tiles" + ("" if REAL_TILES else " (blank stand-ins)"))
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
    picks = await page.locator("#best .pick").count()
    best_name = await page.locator("#best button.pick .nm").first.inner_text() if await page.locator("#best button.pick").count() else ""
    record(size, "a suggestion is shown", best_hidden is None and picks >= 1, f"{picks} suggestion(s): " + " / ".join(x.replace(chr(10), " ")[:40] for x in await page.locator("#best .pick .why").all_inner_texts()))
    if best_name:
        await page.locator("#best button.pick").first.click(); await page.wait_for_timeout(500)
        card_name = await page.locator("#card .nm").inner_text()
        record(size, "tapping the suggestion opens that station", card_name == best_name and re.fullmatch(r"#\d+", await page.evaluate("location.hash")) is not None, f"{card_name} {await page.evaluate('location.hash')}")
        if is_phone(size):
            record(size, "opening a station brings the sheet to half height", await sheet_state(page) == "half", await sheet_state(page))
        href = await page.get_attribute("#card a.btn", "href"); target = await page.get_attribute("#card a.btn", "target")
        record(size, "walking directions link is well formed", bool(re.match(r"https://www\.google\.com/maps/dir/\?api=1&destination=22\.\d+,120\.\d+&travelmode=walking$", href or "")) and target == "_blank", href or "")
        facts = await page.locator("#card .fact .v").all_inner_texts()
        says = (await page.locator("#card .says").inner_text()).replace("\n", " ")
        record(size, "card shows bikes, docks and the answer on arrival", len(facts) == 2 and all(re.search(r"\d|–", f) for f in facts) and bool(re.search(r"你到的時候|現在沒車", says)), " | ".join(f.replace("\n", "") for f in facts) + " | " + says[:50])
        # the forecast block is in state.json once the logger runs the current demo_state.py; an older snapshot has none
        has_ahead = await page.evaluate("fetch('state.json', { cache: 'no-store' }).then(r => r.json()).then(j => !!j.ahead)")
        cells = await page.evaluate("Array.from(document.querySelectorAll('#card .ahead .cell')).map(c => c.querySelector('b').textContent + '@' + c.querySelector('span').textContent)")
        record(size, "card lists the next 90 minutes in five steps", (len(cells) == 5 and all(re.fullmatch(r"\d+@\d\d:\d\d", c) for c in cells)) if has_ahead else not cells, " ".join(cells) if has_ahead else "snapshot without a forecast block")
        chart = await page.locator("#card .chart svg path").count(); dashed = await page.locator("#card .chart svg path[stroke-dasharray]").count()
        record(size, "card draws today's stock and the forecast", chart >= 2 and dashed == (1 if has_ahead else 0), f"{chart} paths, {dashed} dashed")
        box = await page.locator("#card").bounding_box()
        record(size, "card fits the panel width", box["x"] >= 0 and box["x"] + box["width"] <= SIZES[size][0] + 1, str(box))
        # favourite on, visible in the list, survives a reload, favourite off
        await open_sheet(page, size)
        await page.click("#favBtn"); await page.wait_for_timeout(300)
        fav_rows = await page.locator("#favs .row").count(); fav_shown = await page.get_attribute("#favSec", "hidden") is None
        star = await page.locator(".glyph .star").count()
        await reload(page)
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


async def check_when(browser, size):
    """Borrow tab: leaving now or after a class end, the minutes for later departures, the usual day, another start."""
    ctx, page = await new_page(browser, size, query=f"?replay={REPLAY_DAY}&t=16:00")
    await open_sheet(page, size)
    chips = await page.locator("#whenChips .opt").all_inner_texts()
    pressed = await page.locator("#whenChips .opt[aria-pressed=true]").all_inner_texts()
    record(size, "borrow: leave now or after the next class end", chips[:1] == ["現在"] and "17:00 下課" in chips and pressed == ["現在"] and await page.inner_text("#whenK") == "幾點走", " / ".join(chips))
    labels = [await page.inner_text("#fromK"), await page.inner_text("#toK")]; vals = [await page.input_value("#fromSel"), await page.input_value("#toSel")]
    opts = await page.locator("#fromSel option").count(); groups = await page.evaluate("Array.from(document.querySelectorAll('#toSel optgroup')).map(g => g.label)")
    record(size, "borrow: asks from where and, if the rider likes, where to", labels == ["從哪裡", "到哪裡"] and vals == ["lib", ""] and opts >= 18 and groups == ["校內", "校外", "其他"], f"{labels} {vals}, {opts} places, {groups}")
    why0 = await page.locator("#best .why").first.inner_text()
    colours0 = await page.evaluate("Array.from(document.querySelectorAll('#near .badge')).map(b => b.className).join(' ')")
    await page.locator("#whenChips .opt", has_text="17:00 下課").click(); await page.wait_for_timeout(350)
    why1 = await page.locator("#best .why").first.inner_text()
    colours1 = await page.evaluate("Array.from(document.querySelectorAll('#near .badge')).map(b => b.className).join(' ')")
    pressed = await page.locator("#whenChips .opt[aria-pressed=true]").all_inner_texts()
    record(size, "choosing the class end re-reads every station for that time", why0 == "現在去這站借" and why1 == "17:00 下課後去這站借" and pressed == ["17:00 下課"] and colours0 != colours1, f"{why0} -> {why1}")
    name = await page.locator("#best button.pick .nm").first.inner_text()
    box = await page.locator("#best button.pick").first.bounding_box()
    record(size, "the suggestion fits its column", box is not None and box["x"] >= 0 and box["x"] + box["width"] <= SIZES[size][0] + 0.5, f"x {box['x']:.0f}, width {box['width']:.0f}")
    await page.locator("#best button.pick").first.click(); await page.wait_for_timeout(500)
    record(size, "the after-class suggestion opens its station", await page.locator("#card .nm").inner_text() == name, name)
    await ctx.close()
    # 16:40 on a class day: how long the short wait still holds, and the minutes for leaving later
    ctx, page = await new_page(browser, size, query=f"?replay={REPLAY_DAY}&t=16:40")
    await open_sheet(page, size)
    tip = await page.inner_text("#tip") if await page.get_attribute("#tip", "hidden") is None else ""
    record(size, "a line under the suggestion says when to leave, or what to do after a miss", bool(re.search(r"\d\d:\d\d 前出發，約 \d+ 分鐘內騎上車。\d\d:\d\d 出發約 \d+ 分鐘。|接下來一小時出發，約 \d+ 分鐘內騎上車|沒車的話，再走 \d+ 分鐘|想穩一點|比較近", tip)), tip)
    later = await page.evaluate("Array.from(document.querySelectorAll('#later svg text')).map(x => x.textContent)")
    bars = await page.locator("#later svg rect").count(); head = (await page.inner_text("#laterSec h2")).replace("\n", " ")
    nums, ticks = later[0::2], later[1::2]
    step = [(int(b[:2]) * 60 + int(b[3:]) - int(a[:2]) * 60 - int(a[3:])) % 1440 for a, b in zip(ticks[1:], ticks[2:])] if all(re.fullmatch(r"\d\d:\d\d", x) for x in ticks[1:]) else []
    record(size, "minutes until riding are drawn for departures over the next hour", await page.get_attribute("#laterSec", "hidden") is None and bars == 7 and "幾點走，幾分鐘騎得上車" in head and ticks[:1] == ["現在"] and step == [10] * 5 and all(re.fullmatch(r"\d+", n) and int(n) >= 1 for n in nums), f"{head} | {' '.join(nums)} | {' '.join(ticks)}")
    m = re.search(r"(\d\d:\d\d) 前出發，約 (\d+) 分鐘內騎上車。(\d\d:\d\d) 出發約 (\d+) 分鐘", tip); calm = re.search(r"接下來一小時出發，約 (\d+) 分鐘內", tip)
    mm = lambda x: int(x[:2]) * 60 + int(x[3:])
    if m and len(ticks) == 7:                                   # the line is a summary of the bars: same minutes, same times
        at = [mm(ticks[1]) - 10] + [mm(x) for x in ticks[1:]]
        before = [int(n) for n, x in zip(nums, at) if x < mm(m.group(1))]
        record(size, "the line and the bars give the same minutes", before and max(before) == int(m.group(2)) and m.group(3) in ticks and nums[ticks.index(m.group(3))] == m.group(4) and int(m.group(4)) >= int(m.group(2)) + 2, f"{tip} | {' '.join(nums)}")
    elif calm:
        record(size, "the line and the bars give the same minutes", max(int(n) for n in nums) == int(calm.group(1)), f"{tip} | {' '.join(nums)}")
    sub = await page.locator("#near .row .sub").first.inner_text()
    record(size, "each row says when its answer changes", bool(re.search(r"\d\d:\d\d", " ".join(await page.locator("#near .row .sub").all_inner_texts()))), sub.replace("\n", " "))
    usual = await page.get_attribute("#usualSec", "hidden") is None
    ubars = await page.locator("#usual svg rect").count(); head = (await page.inner_text("#usualSec h2")).replace("\n", " ")
    record(size, "the usual day on campus is drawn in half hours", usual and ubars == 34 and "校內平常幾點難借" in head and bool(re.search(r"\d\d:\d\d 到 \d\d:\d\d", head)), f"{ubars} bars | {head}")
    first = await page.locator("#near .row .nm").first.inner_text()
    await page.select_option("#fromSel", "krt"); await page.wait_for_timeout(600)
    await open_sheet(page, size)
    first2 = await page.locator("#near .row .nm").first.inner_text(); head2 = (await page.inner_text("#usualSec h2")).replace("\n", " ")
    record(size, "the metro station can be the start", await page.input_value("#fromSel") == "krt" and "哈瑪星" in first2 and first2 != first and "這一帶平常幾點難借" in head2 and await page.locator(".originicon").count() == 1, f"{first} -> {first2} | {head2}")
    record(size, "borrow tab runs without script errors", not page.errors, "; ".join(page.errors[:3]))
    await ctx.close()


async def check_trip(browser, size):
    """Borrow tab with a destination: where to borrow, where to return, the minutes door to door, and walking when it is faster."""
    ctx, page = await new_page(browser, size, query=f"?replay={REPLAY_DAY}&t=17:30&from=cm&to=krt")
    await open_sheet(page, size)
    vals = [await page.input_value("#fromSel"), await page.input_value("#toSel")]
    whys = await page.locator("#best button.pick .why").all_inner_texts(); names = await page.locator("#best button.pick .nm").all_inner_texts()
    tip = await page.inner_text("#tip") if await page.get_attribute("#tip", "hidden") is None else ""
    m = re.search(r"全程約 (\d+) 分鐘。走路要 (\d+) 分鐘", tip)
    record(size, "a link sets the start and the destination", vals == ["cm", "krt"], str(vals))
    record(size, "a trip names a station to borrow at and one to return at", whys == ["現在去這站借", "騎到這站還"] and len(set(names)) == 2, " / ".join(f"{a}: {b}" for a, b in zip(whys, names)))
    record(size, "the trip is timed door to door against walking", m is not None and 3 <= int(m.group(1)) < int(m.group(2)) <= 40, tip)
    cells = await page.locator("#best button.pick .walk").all_inner_texts()
    back = int(re.search(r"\d+", cells[1]).group()) if len(cells) == 2 else 99
    record(size, "the return station is a short walk from the destination", len(cells) == 2 and "到目的地" in cells[1] and back <= 8, " | ".join(c.replace("\n", " ") for c in cells))
    marks = [await page.locator(".originicon").count(), await page.locator(".originicon.to").count()]
    record(size, "start and destination are both marked on the map", marks == [2, 1], str(marks))
    over = await page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    boxes = [await page.locator("#fromSel").bounding_box(), await page.locator("#toSel").bounding_box()]
    record(size, "the two selectors sit side by side inside the panel", over[0] <= over[1] and all(b and b["x"] >= 0 and b["x"] + b["width"] <= SIZES[size][0] for b in boxes) and abs(boxes[0]["y"] - boxes[1]["y"]) < 2 and boxes[0]["x"] + boxes[0]["width"] <= boxes[1]["x"], f"{boxes[0]['x']:.0f}+{boxes[0]['width']:.0f}, {boxes[1]['x']:.0f}+{boxes[1]['width']:.0f}")
    # the destination can be dropped again
    await page.select_option("#toSel", ""); await page.wait_for_timeout(400)
    whys = await page.locator("#best button.pick .why").all_inner_texts(); tip = await page.inner_text("#tip") if await page.get_attribute("#tip", "hidden") is None else ""
    record(size, "without a destination only the borrowing station is named", whys == ["現在去這站借"] and "全程" not in tip and await page.locator(".originicon").count() == 1, f"{whys} | {tip}")
    record(size, "trip view runs without script errors", not page.errors, "; ".join(page.errors[:3]))
    await ctx.close()
    # two buildings next to each other: walking wins, and no ride is proposed that ends where it started
    ctx, page = await new_page(browser, size, query=f"?replay={REPLAY_DAY}&t=16:40&from=lib&to=eng")
    await open_sheet(page, size)
    walk = (await page.locator("#best .pick.walkit").inner_text()).replace("\n", " ") if await page.locator("#best .pick.walkit").count() else ""
    names = await page.locator("#best button.pick .nm").all_inner_texts()
    record(size, "a trip shorter on foot says so", bool(re.search(r"直接走比較快 走路 \d+ 分鐘", walk)) and len(set(names)) == len(names) and not page.errors, walk + " | " + " / ".join(names))
    await ctx.close()


async def check_dock(browser, size):
    """Return tab: where to return on arrival, by destination and arrival time."""
    ctx, page = await new_page(browser, size, query=f"?replay={REPLAY_DAY}&t=09:00")
    await page.click("#tabDock"); await page.wait_for_timeout(450)
    await open_sheet(page, size)
    chips = await page.locator("#whenChips .opt").all_inner_texts()
    pressed = await page.locator("#whenChips .opt[aria-pressed=true]").all_inner_texts()
    labels = [await page.inner_text("#toK"), await page.inner_text("#whenK")]
    one = await page.get_attribute("#fromWrap", "hidden") is not None and await page.locator("#toSel option[value='']").count() == 0
    record(size, "return: asks where to and when", await page.get_attribute("#tabDock", "aria-selected") == "true" and await page.get_attribute("#paneRider", "hidden") is None and labels == ["到哪裡", "幾點到"] and one and chips == ["現在", "10 分後", "20 分後", "30 分後"] and pressed == ["10 分後"], f"{labels} {chips} {pressed}")
    why = await page.locator("#best .why").first.inner_text(); sub = (await page.locator("#best .pick .sub").first.inner_text()).replace("\n", " ")
    cls = await page.locator("#best .pick .badge").first.get_attribute("class")
    record(size, "return: one station is suggested, with its free docks", await page.locator("#best button.pick").count() == 1 and why == "騎到這站還" and "空位" in sub and " x" not in cls, f"{sub} [{cls}]")
    hard = await page.locator("#near .badge.x, #near .badge.r, #near .badge.y").count()
    rows = await page.locator("#near .row").count(); lab = await page.locator("#near .row .walk small").first.inner_text()
    record(size, "return: the list is ordered from the destination and marks the stations filling up", rows == 8 and lab == "到目的地" and hard >= 1, f"{rows} rows, {hard} filling up, '{lab}'")
    counts = await page.evaluate("Array.from(document.querySelectorAll('#near .row')).slice(0, 3).map(r => r.querySelector('.badge').textContent + ' ' + r.querySelector('.nm').textContent)")
    await page.locator("#near .row").first.click(); await page.wait_for_timeout(450)
    free = (await page.locator("#card .fact .v").nth(1).inner_text()).strip(); says = (await page.locator("#card .says").inner_text()).replace("\n", " ")
    cap = await page.locator("#card .ahead .cap").inner_text()
    record(size, "return: the number on a row is its free docks, and the card forecasts docks", counts[0].split(" ")[0] == free and "預估空位" in cap and bool(re.search(r"位子|停滿", says)), f"{counts[0]} | card {free} | {says[:40]}")
    await page.click("#cardX"); await page.wait_for_timeout(200)
    await page.locator("#whenChips .opt", has_text="30 分後").click(); await page.wait_for_timeout(350)
    pressed = await page.locator("#whenChips .opt[aria-pressed=true]").all_inner_texts()
    record(size, "return: the arrival time can be moved", pressed == ["30 分後"], str(pressed))
    head = (await page.inner_text("#usualSec h2")).replace("\n", " ") if await page.get_attribute("#usualSec", "hidden") is None else ""
    record(size, "return: the usual day shows when campus docks are full", "校內平常幾點難還" in head and await page.locator("#usual svg rect").count() == 34 and await page.get_attribute("#laterSec", "hidden") is not None, head)
    if not is_phone(size) and SIZES[size][0] >= 1100:
        record(size, "legend follows the return tab", "你騎到的時候" in await page.inner_text("#legend"), (await page.inner_text("#legend")).replace("\n", " ")[:50])
    # a station that may be full comes with the way on, and the destination can change
    await page.select_option("#toSel", "eng"); await page.wait_for_timeout(500)
    await open_sheet(page, size)
    first = await page.locator("#near .row .nm").first.inner_text()
    tip = await page.inner_text("#tip") if await page.get_attribute("#tip", "hidden") is None else ""
    weak = "weak" in (await page.locator("#best button.pick").first.get_attribute("class")) or "poor" in (await page.locator("#best button.pick").first.get_attribute("class"))
    record(size, "return: an uncertain station comes with the next one to try", (bool(re.search(r"停滿的話，再騎 \d+ 分鐘到|想穩一點可以還", tip)) if weak else True) and await page.input_value("#toSel") == "eng", f"{first} | {'uncertain' if weak else 'sure'} | {tip}")
    # the borrow tab keeps its own places and time
    await page.click("#tabRider"); await page.wait_for_timeout(400)
    await open_sheet(page, size)
    borrow = [await page.input_value("#fromSel"), await page.input_value("#toSel"), await page.locator("#whenChips .opt[aria-pressed=true]").all_inner_texts(), await page.inner_text("#fromK")]
    await page.click("#tabDock"); await page.wait_for_timeout(400)
    record(size, "borrow and return keep separate places and times", borrow == ["lib", "", ["現在"], "從哪裡"] and await page.input_value("#toSel") == "eng" and await page.locator("#whenChips .opt[aria-pressed=true]").all_inner_texts() == ["30 分後"], str(borrow))
    record(size, "return tab runs without script errors", not page.errors, "; ".join(page.errors[:3]))
    await ctx.close()


async def check_relay(browser, size):
    """The operator's NT$5 reward: stations likely to be still empty (for a return) or still full (for a rental) on arrival are marked."""
    day = "2026-11-11"                                          # a day the page keeps for good (docs/replays_keep.txt)
    ctx, page = await new_page(browser, size, query=f"?replay={day}&t=18:00&tab=dock&to=lib")
    await open_sheet(page, size)
    tags = await page.locator("#near .row .relay").all_inner_texts()
    rows = await page.evaluate("Array.from(document.querySelectorAll('#near .row')).filter(r => r.querySelector('.relay')).map(r => r.querySelector('.nm').childNodes[0].textContent)")
    tip = (await page.inner_text("#tip")).replace("\n", " ") if await page.get_attribute("#tip", "hidden") is None else ""
    record(size, "return, evening: stations likely to be empty on arrival carry the reward mark", len(tags) >= 1 and set(tags) == {"+5 元"} and bool(re.search(r"約 \d 成還是空站.*可拿 5 元騎乘券", tip)), f"{len(tags)} marked: {' / '.join(rows[:3])} | {tip}")
    boxes = await page.evaluate("Array.from(document.querySelectorAll('.relay')).map(e => { const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.right)]; })")
    record(size, "the mark stays inside its row", all(a >= 0 and b <= SIZES[size][0] for a, b in boxes) and (await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")), str(boxes[:4]))
    if rows:
        await page.locator("#near .row", has=page.locator(".relay")).first.click(); await page.wait_for_timeout(450)
        note = (await page.inner_text("#card .relaynote")).replace("\n", " ") if await page.locator("#card .relaynote").count() else ""
        bikes = (await page.locator("#card .fact .v").first.inner_text()).replace("\n", "").replace(" ", "")
        record(size, "the card of a marked station explains the reward", "還是空站" in note and "5 元騎乘券" in note, f"{bikes} bikes | {note}")
    record(size, "reward marks (return) run without script errors", not page.errors, "; ".join(page.errors[:3]))
    await ctx.close()
    # a morning rental on campus: the racks are full, and borrowing from a full one pays
    ctx, page = await new_page(browser, size, query=f"?replay={day}&t=09:30&from=lib&to=")
    await open_sheet(page, size)
    tag = await page.locator("#best button.pick .relay").count()
    tip = (await page.inner_text("#tip")).replace("\n", " ") if await page.get_attribute("#tip", "hidden") is None else ""
    docks = await page.evaluate("(() => { const r = Array.from(document.querySelectorAll('#near .row')).find(r => r.querySelector('.relay')); return r ? r.querySelector('.nm').childNodes[0].textContent : ''; })()")
    record(size, "borrow, morning: a station likely to be full on arrival carries the reward mark", tag == 1 and bool(re.search(r"約 \d 成還是滿站.*可拿 5 元騎乘券", tip)), f"{docks} | {tip}")
    await ctx.close()
    # the reward runs from 06:00: the library station, empty and forecast to stay so, is marked at 07:00 and not at 05:00
    seen = {}
    for minute in (420, 300):
        def emptied(data, minute=minute):
            fresh(data); data["t_min"] = minute; data["in_window"] = True
            if not data.get("ahead"):
                return
            i = next(n for n, x in enumerate(data["stations"]) if x["sno"] == "501209052")
            data["bikes"][i] = 0; data["docks"][i] = data["stations"][i]["cap"]
            for key, ch in (("bike", "0"), ("bikes", "0"), ("dock", "_")):
                data["ahead"][key][i] = ch * 9
            seen["forecast"] = True
        ctx, page = await new_page(browser, size, state_patch=emptied, query="?tab=dock&to=lib&fresh=0")
        await open_sheet(page, size)
        seen[minute] = await page.evaluate("Array.from(document.querySelectorAll('#near .row')).filter(r => r.querySelector('.relay')).map(r => r.querySelector('.nm').childNodes[0].textContent)")
        await ctx.close()
    if seen.get("forecast"):
        record(size, "the reward mark keeps to the reward's hours", "中山大學圖資大樓" in seen[420] and not seen[300], f"07:00 {seen[420][:2]} | 05:00 {seen[300]}")
    ctx, page = await new_page(browser, size, query=f"?replay={day}&t=18:00&tab=dock&to=lib&lang=en")
    await open_sheet(page, size)
    tags = set(await page.locator("#near .row .relay").all_inner_texts()); tip = (await page.inner_text("#tip")).replace("\n", " ")
    record(size, "English: the mark and its line are translated", tags == {"+NT$5"} and "NT$5 ride voucher" in tip and not re.search(r"[\u4e00-\u9fff]", tip), f"{tags} | {tip}")
    await page.click("#tabAbout"); await page.wait_for_timeout(300)
    record(size, "about tab explains the reward", "friendship relay" in await page.inner_text("#aboutWhat"))
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
    await page.select_option("#fromSel", "pick"); await page.wait_for_timeout(450)
    hint = await page.get_attribute("#hint", "hidden") is None and "設成起點" in await page.inner_text("#hint")
    if is_phone(size):
        record(size, "picking a start lowers the sheet to show the map", await sheet_state(page) == "peek", await sheet_state(page))
    m = await page.locator("#map").bounding_box()
    await page.mouse.click(m["x"] + m["width"] * 0.85, m["y"] + m["height"] * (0.2 if is_phone(size) else 0.8)); await page.wait_for_timeout(500)
    await open_sheet(page, size)
    first2 = await page.locator("#near .row .nm").first.inner_text()
    record(size, "pick a start on the map: hint shown, list re-sorted", hint and await page.input_value("#fromSel") == "pick" and first2 != first and await page.get_attribute("#hint", "hidden") is not None, f"{first} -> {first2}")
    record(size, "the picked start is marked on the map", await page.locator(".originicon").count() == 1)
    await page.select_option("#fromSel", "lib"); await page.wait_for_timeout(400)
    record(size, "back to the library restores the list", await page.locator("#near .row .nm").first.inner_text() == first and await page.input_value("#fromSel") == "lib")
    # a destination picked on the map can be called off
    await page.select_option("#toSel", "pick"); await page.wait_for_timeout(400)
    hint2 = await page.inner_text("#hint") if await page.get_attribute("#hint", "hidden") is None else ""
    await page.keyboard.press("Escape"); await page.wait_for_timeout(300)
    record(size, "picking a destination shows its own hint, and Escape calls it off", "設成目的地" in hint2 and await page.get_attribute("#hint", "hidden") is not None and await page.input_value("#toSel") == "", hint2)
    # a place chosen from the list is kept for the next visit
    await open_sheet(page, size)
    await page.select_option("#fromSel", "ss"); await page.wait_for_timeout(300)
    await page.select_option("#toSel", "krt"); await page.wait_for_timeout(300)
    await reload(page)
    kept = [await page.input_value("#fromSel"), await page.input_value("#toSel")]
    record(size, "chosen places are remembered", kept == ["ss", "krt"], str(kept))
    await ctx.close()
    # my location: on campus, far away, refused
    ctx, page = await new_page(browser, size, state_patch=fresh, geo={"latitude": 22.6247, "longitude": 120.2811}, perms=["geolocation"])
    await open_sheet(page, size)
    await page.select_option("#fromSel", "me"); await page.wait_for_timeout(900)
    await open_sheet(page, size)
    record(size, "my location near campus becomes the start", await page.input_value("#fromSel") == "me" and await page.get_attribute("#fab", "aria-pressed") == "true", await page.locator("#near .row .nm").first.inner_text())
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh, geo={"latitude": 25.0174, "longitude": 121.5397}, perms=["geolocation"])
    await page.click("#fab"); await page.wait_for_timeout(900)
    toast = await page.inner_text("#toast")
    record(size, "my location far from NSYSU keeps the campus start and says why", await page.input_value("#fromSel") == "lib" and "不在中山附近" in toast, toast)
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await page.click("#fab"); await page.wait_for_timeout(1200)
    toast = await page.inner_text("#toast")
    record(size, "location refused: a message points to the map picker", "拿不到你的位置" in toast and await page.input_value("#fromSel") == "lib", toast)
    await ctx.close()


async def check_fresh(browser, size):
    """While the page is open it reads the operator's counts for the stations around campus and re-reads the forecast from them."""
    now = datetime.now(TZ) - timedelta(minutes=3)
    if now.hour * 60 + now.minute < 5:                         # the snapshot and the reading would fall on two different days
        return
    have = {}

    def recent(data):
        fresh(data); data["t_min"] = now.hour * 60 + now.minute; data["in_window"] = True
        have["table"] = bool(data.get("fresh") and data.get("ahead")); have["cap"] = {s["sno"]: s["cap"] for s in data["stations"]}
        have["sno"] = (data.get("fresh") or {}).get("sno", [])
    # the library has just run out and Engineering has 7 bikes, whatever the snapshot says
    reply = [{"station_no": "501209052", "available_spaces": 0, "empty_spaces": 22, "status": 1}, {"station_no": "501209051", "available_spaces": 7, "empty_spaces": 3, "status": 1},
             {"station_no": "501209054", "available_spaces": 5, "empty_spaces": 5, "status": 0}]
    ctx, page = await new_page(browser, size, state_patch=recent, counts=reply)
    await page.wait_for_timeout(600)
    await open_sheet(page, size)
    if not have.get("table"):
        record(size, "a snapshot without the table of forecasts keeps its own counts", "即時數字" not in await page.inner_text("#hNearSub") and not page.errors, "snapshot written before the logger learned the table")
        await ctx.close(); return
    asked = json.loads(page.api_calls[0])["station_no"] if page.api_calls else []
    record(size, "the page asks the operator for the stations around campus", asked == have["sno"] and 10 <= len(asked) <= 20, f"{len(asked)} stations")
    sub = await page.inner_text("#hNearSub"); status = await page.inner_text("#statusText")
    record(size, "fresh counts are announced with their time", bool(re.search(r"車數是 \d\d:\d\d 的即時數字", sub)) and bool(re.search(r"\d\d:\d\d 更新", status)) and "stale" not in (await page.get_attribute("#status", "class")), f"{sub} | {status}")
    rows = await page.evaluate("Object.fromEntries(Array.from(document.querySelectorAll('#near .row')).map(r => [r.querySelector('.nm').textContent.replace('★', ''), [r.querySelector('.badge').textContent, r.querySelector('.badge').className, r.querySelector('.sub').textContent]]))")
    lib, eng = rows.get("中山大學圖資大樓"), rows.get("中山大學工學院")
    record(size, "a station that has just emptied reads empty at once", lib is not None and lib[0] == "0" and (" x" in lib[1] or " r" in lib[1]) and bool(re.search(r"現在沒車|很可能沒車", lib[2])), str(lib))
    record(size, "a station's new count replaces the snapshot's", eng is not None and eng[0] == "7", str(eng))
    best = await page.locator("#best button.pick .nm").first.inner_text()
    record(size, "the suggestion moves off the station that emptied", best != "中山大學圖資大樓", best)
    await page.fill("#q", "圖資"); await page.wait_for_timeout(250); await page.keyboard.press("Enter"); await page.wait_for_timeout(500)
    fact = (await page.locator("#card .fact .v").first.inner_text()).replace("\n", "").replace(" ", "")
    cells = await page.evaluate("Array.from(document.querySelectorAll('#card .ahead .cell span')).map(c => c.textContent)")
    start = (now + timedelta(minutes=3)).hour * 60 + (now + timedelta(minutes=3)).minute
    first_cell = int(cells[0][:2]) * 60 + int(cells[0][3:]) if cells else -99
    record(size, "the card shows the fresh count and forecasts from the minute it was read", fact == "0/22" and len(cells) == 5 and 9 <= (first_cell - start) % 1440 <= 11, f"{fact} | {' '.join(cells)}")
    record(size, "fresh counts run without script errors", not page.errors, "; ".join(page.errors[:3]))
    await ctx.close()
    # a reply that is no use is ignored, and ?fresh=0 does not ask at all
    ctx, page = await new_page(browser, size, state_patch=recent, counts=[])
    await open_sheet(page, size)
    record(size, "an empty reply leaves the snapshot in place", "即時數字" not in await page.inner_text("#hNearSub") and await page.locator("#near .row").count() == 8 and not page.errors)
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=recent, counts=reply, query="?fresh=0")
    await open_sheet(page, size)
    record(size, "?fresh=0 keeps the page on the logger's snapshot", not page.api_calls and "即時數字" not in await page.inner_text("#hNearSub"), f"{len(page.api_calls)} requests")
    await ctx.close()


async def check_ops(browser, size):
    ctx, page = await new_page(browser, size, state_patch=fresh)
    await page.click("#tabOps"); await page.wait_for_timeout(500)
    await open_sheet(page, size)
    stats = [await page.inner_text(i) for i in ("#tEmpty", "#tRisk", "#tUnmet", "#tSaved")]
    record(size, "dispatch tab shows its four numbers", all(re.search(r"\d|–", s) for s in stats) and await page.get_attribute("#paneRider", "hidden") is not None, " | ".join(s.replace("\n", " ") for s in stats))
    scope = (await page.inner_text("#hKpi")).replace("\n", " ")
    record(size, "dispatch numbers are for the stations around campus", "校園這一帶" in scope and "19 站" in scope, scope)
    rows = await page.locator("#risk li").count()
    vals = [float(v.strip("%")) for v in await page.locator("#risk .pv").all_inner_texts()]
    record(size, "risk list: ten stations, highest first", rows == 10 and vals == sorted(vals, reverse=True), str(vals))
    outside = await page.evaluate("Array.from(document.querySelectorAll('#risk .nm')).map(e => e.textContent).filter(n => !/中山大學|哈瑪星|鼓山|哨船|濱海|西子灣|船渠|新濱/.test(n))")
    record(size, "risk list stays within the stations around campus", not outside, str(outside))
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
    # a truck trip is judged against the campus corridor, so the share it removes is a readable number
    ctx, page = await new_page(browser, size, query=f"?replay={REPLAY_DAY}&t=16:00&tab=ops")
    await page.wait_for_timeout(1200)
    await open_sheet(page, size)
    unmet = float(re.search(r"[\d.]+", await page.inner_text("#tUnmet")).group()); saved = await page.inner_text("#tSaved")
    pct = re.search(r"(\d+)%", saved)
    record(size, "the trip's gain is shown against the corridor's shortfall", unmet > 0 and pct is not None and 1 <= int(pct.group(1)) <= 100, f"shortfall {unmet:.0f}, trip {saved.replace(chr(10), ' ')}")
    await ctx.close()


async def check_about_lang(browser, size):
    days = {"2026-11-18": {"teaching": 1, "w": {"leave": [120, 444, 468, 450, 96, 78, 110, 6, 9, 7, 120, 96, 110, 143, 100, 150, 90, 153],
                                               "arrive": [80, 224, 240, 232, 70, 62, 72, 1, 2, 1, 80, 40, 70, 77, 60, 72, 50, 65],
                                               "dock": [60, 84, 96, 90, 55, 50, 53, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], "bike_day": [0] * 18, "dock_day": [0] * 18}},
            "2026-11-21": {"teaching": 0, "w": {"leave": [50, 500, 500, 500] + [0] * 14, "arrive": [0] * 18, "dock": [0] * 18, "bike_day": [0] * 18, "dock_day": [0] * 18}}}
    ctx, page = await new_page(browser, size, state_patch=fresh, track={"rule": "v2", "since": "2026-11-18", "updated": "2026-11-21 12:00", "fields": TRACK_FIELDS, "days": days})
    await page.click("#tabAbout"); await page.wait_for_timeout(400)
    await open_sheet(page, size)
    what = await page.inner_text("#aboutWhat")
    record(size, "about tab explains the colours and the numbers", await page.locator("#aboutKey li").count() == 7 and "LightGBM" in await page.inner_text("#aboutHow") and "3.7 分鐘" in what and "0.86" in what and "93%" not in what)
    rec = (await page.inner_text("#aboutTrack")).replace("\n", " ") if await page.get_attribute("#aboutTrack", "hidden") is None else ""
    record(size, "about tab shows the record of the page's advice, teaching days only", "從 11/18 起" in rec and "目前有 1 個上課日" in rec and "120 次。照建議平均 3.7 分鐘騎上車，看官方 App 的車數是 3.8 分鐘，走到最近的站是 3.9 分鐘" in rec
           and "出發前 20 分鐘預告的時間，平均差 1.5 分鐘" in rec and "60 次。照建議平均多花 1.4 分鐘" in rec, rec[:260])
    await page.click("#lEn"); await page.wait_for_timeout(400)
    en = [await page.inner_text(i) for i in ("#tabRiderT", "#tabDockT", "#tabOpsT", "#tabAboutT", "#mLive")]
    left_about = await page.evaluate("Array.from(document.querySelectorAll('#paneAbout section:not(.langrow) *')).filter(e => e.children.length === 0 && /[\\u4e00-\\u9fff]/.test(e.textContent)).map(e => e.textContent.trim()).filter(Boolean).slice(0, 4)")
    leftover = []
    for tab_id in ("#tabRider", "#tabDock"):
        await page.click(tab_id); await page.wait_for_timeout(300)
        leftover += await page.evaluate("Array.from(document.querySelectorAll('#paneRider *, .tabs *, .top *, #legend *')).filter(e => e.children.length === 0 && /[\\u4e00-\\u9fff]/.test(e.textContent)).map(e => e.textContent.trim()).filter(Boolean).slice(0, 6)")
    record(size, "English: tabs, header, borrow, return and about are translated", en == ["Borrow", "Return", "Dispatch", "About", "Live"] and not leftover and not left_about, f"{en} leftover {leftover} {left_about}")
    await reload(page)
    record(size, "language choice is remembered", await page.inner_text("#tabRiderT") == "Borrow" and await page.evaluate("document.documentElement.lang") == "en")
    await page.click("#tabAbout"); await page.wait_for_timeout(300); await open_sheet(page, size)
    await page.click("#lZh"); await page.wait_for_timeout(300)
    record(size, "back to Chinese", await page.inner_text("#tabRiderT") == "借車")
    over = await page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    record(size, "English text does not widen the page", over[0] <= over[1], str(over))
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh, track=False, query="?tab=about")
    await open_sheet(page, size)
    record(size, "without a record file the about tab leaves the record out", await page.get_attribute("#aboutTrack", "hidden") is not None and "這個頁面在做什麼" in await page.inner_text("#aboutWhat") and not page.errors, "; ".join(page.errors[:2]))
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh, track={"rule": "v2", "since": "2026-11-18", "updated": "2026-11-18 16:00", "fields": TRACK_FIELDS, "days": {"2026-11-18": {"teaching": 1, "w": {"leave": [4, 12, 12, 12] + [0] * 14}}}}, query="?tab=about")
    await open_sheet(page, size)
    rec = (await page.inner_text("#aboutTrack")).replace("\n", " ") if await page.get_attribute("#aboutTrack", "hidden") is None else ""
    record(size, "a record with too few cases says it has just started", "紀錄剛開始" in rec and "次。照建議" not in rec, rec[:120])
    await ctx.close()
    ctx, page = await new_page(browser, size, query="?tab=ops&lang=en")
    record(size, "links can set the tab and the language", await page.get_attribute("#tabOps", "aria-selected") == "true" and await page.inner_text("#tabOpsT") == "Dispatch")
    await ctx.close()
    ctx, page = await new_page(browser, size, state_patch=fresh, query="?tab=dock&to=eng")
    record(size, "a link can open the return tab with a destination", await page.get_attribute("#tabDock", "aria-selected") == "true" and await page.inner_text("#toK") == "到哪裡" and await page.input_value("#toSel") == "eng")
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
        fresh(data); data["offday"] = 1; data["next_bell"] = None
    ctx, page = await new_page(browser, size, state_patch=dayoff)
    board = await page.inner_text("#mini" if is_phone(size) else "#board")
    await open_sheet(page, size)
    rows = await page.locator("#near .row").count()
    chips = await page.locator("#whenChips .opt").all_inner_texts()
    record(size, "a day off: board says so, the list works and no class end is offered", "今天沒課" in board and rows == 8 and chips == ["現在"], board.replace("\n", " ") + " | " + "/".join(chips))
    await ctx.close()

    def no_forecast(data):                         # a snapshot written by the logger before it learned the forecast block
        fresh(data); data.pop("ahead", None); data.pop("fresh", None)
    ctx, page = await new_page(browser, size, state_patch=no_forecast)
    await open_sheet(page, size)
    rows = await page.locator("#near .row").count(); picks = await page.locator("#best .pick").count(); later = await page.get_attribute("#laterSec", "hidden") is not None and await page.locator(".relay").count() == 0
    await page.locator("#near .row").first.click(); await page.wait_for_timeout(400)
    record(size, "a snapshot without the forecast still lists stations and opens a card", rows == 8 and picks == 1 and later and await page.locator("#card .fact").count() == 2 and await page.locator("#card .ahead").count() == 0 and not page.errors, "; ".join(page.errors[:2]))
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
    dock = await page.get_attribute("#tabDock", "aria-selected")
    await page.keyboard.press("ArrowRight"); await page.wait_for_timeout(250)
    ops = await page.get_attribute("#tabOps", "aria-selected")
    await page.keyboard.press("ArrowLeft"); await page.wait_for_timeout(200); await page.keyboard.press("ArrowLeft"); await page.wait_for_timeout(250)
    record(size, "arrow keys move between the four tabs", dock == "true" and ops == "true" and await page.get_attribute("#tabRider", "aria-selected") == "true")
    await open_sheet(page, size)
    await page.locator("#near .row").first.focus(); await page.keyboard.press("Enter"); await page.wait_for_timeout(400)
    record(size, "Enter on a focused row opens the station", await page.get_attribute("#cardWrap", "hidden") is None)
    if SIZES[size][2]:
        small = await page.evaluate("""Array.from(document.querySelectorAll('.tabs button, .opt, .row, .seg button, .fab, .btn, .more, #grip, .card .x, .trip select, .pick')).filter(e => e.offsetParent !== null).map(e => [e.id || e.className, Math.round(e.getBoundingClientRect().height)]).filter(x => x[1] < 30)""")
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
    out = await page.evaluate("""async (base) => { const r = {}; for (const f of ['manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png', 'vendor/leaflet.js', 'replays.json', 'outlook.json', 'places.json']) { const x = await fetch(base + f); r[f] = x.status; } const m = await (await fetch(base + 'manifest.webmanifest')).json(); r.name = m.short_name; r.icons = m.icons.length; r.display = m.display; return r; }""", base)
    record(size, "manifest, icons, the map library and the data files are served", all(v == 200 for k, v in out.items() if isinstance(v, int) and k != "icons") and out["display"] == "standalone" and out["icons"] == 3, json.dumps(out))
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
            for check in (check_load, check_rider, check_when, check_trip, check_dock, check_relay, check_search, check_origin, check_fresh, check_ops, check_replay, check_about_lang, check_states, check_keyboard_a11y):
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
            await check_assets(browser, next(iter(SIZES)))
        except Exception as exc:  # noqa: BLE001
            record(next(iter(SIZES)), "check_assets crashed", False, str(exc).splitlines()[0][:200])
        await browser.close()
    failed = [r for r in results if not r[2]]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    for size, name, _, detail in failed:
        print("  FAIL", size, "|", name, "|", detail)
    sys.exit(1 if failed else 0)


asyncio.run(main())
