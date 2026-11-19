#!/usr/bin/env python3
"""Assemble the demo page from site/src into one self-contained file.

Usage: python3 site/build.py [--artifact OUT.html]

Writes docs/index.html (what GitHub Pages serves), docs/manifest.webmanifest and docs/sw.js (the service worker
that lets the installed app open without a network; its cache name carries a hash of the page, so a new page
replaces the old copy). Leaflet is served from docs/vendor/ so the page does not depend on a CDN during a demo;
only the Barlow web font comes from outside. The font stylesheet is loaded without holding up the first paint,
and the page uses system fonts until it arrives. With --artifact it also writes a fragment for a hosted
preview, which must load Leaflet from a CDN instead.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, DOCS = HERE / "src", HERE.parent / "docs"
read = lambda name: (SRC / name).read_text(encoding="utf-8")

TITLE = "Beat the Bell｜中山大學 YouBike"
DESC = "中山大學校內和周邊的 YouBike：現在出發幾分鐘騎得上車、晚一點走會不會要找很久、騎車和走路哪個快。每 10 分鐘更新。"
OG = "中山大學下課借 YouBike：現在出發幾分鐘騎得上車，晚一點走會不會要找很久。"
FONTS = "https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Semi+Condensed:wght@500;600&display=swap"
style = "<style>\n" + read("leaflet.css") + "\n" + read("style.css") + "</style>\n"
script = "<script>\n" + read("strings.js") + "\n" + read("app.js") + "</script>\n"

head = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{OG}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#10202f">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Beat the Bell">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONTS}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONTS}"></noscript>
"""
page = head + style + "</head>\n<body>\n" + read("body.html") + '<script src="vendor/leaflet.js"></script>\n' + script + "</body>\n</html>\n"
(DOCS / "index.html").write_text(page, encoding="utf-8")
(DOCS / ".nojekyll").write_text("", encoding="utf-8")
version = hashlib.sha256((page + read("sw.js")).encode()).hexdigest()[:10]
(DOCS / "sw.js").write_text(read("sw.js").replace("__VERSION__", version), encoding="utf-8")

manifest = {
    "name": TITLE, "short_name": "Beat the Bell", "description": DESC, "lang": "zh-Hant",
    "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#10202f", "theme_color": "#10202f",
    "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
              {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
}
(DOCS / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"docs/index.html {len(page.encode()) // 1024} KB, docs/sw.js btb-{version}")

if "--artifact" in sys.argv:
    out = Path(sys.argv[sys.argv.index("--artifact") + 1])
    frag = (f"<title>Beat the Bell</title>\n<meta name=\"claude:viewport-fit-sides\" content=\"cover\">\n<link rel=\"stylesheet\" href=\"{FONTS}\">\n" + style + read("body.html")
            + '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>\n' + script)
    out.write_text(frag, encoding="utf-8")
    print(f"{out} {len(frag.encode()) // 1024} KB")
