"""One PDF for the team chat: the HW5 tasks (docs/HW5_TASKS.md) followed by the narration script (build/NARRATION.md).

Usage: python video/pack.py [OUT_PDF]   (default video/out/HW5分工與旁白稿.pdf)

The script starts on a new page, so the person recording can print only that part. Run script.py first.
"""
import sys
from datetime import date
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out" / "HW5分工與旁白稿.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

md = lambda p: markdown.markdown(p.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
tasks = md(HERE.parent / "docs" / "HW5_TASKS.md")
script = md(HERE / "build" / "NARRATION.md")

CSS = """
@page { size: A4; margin: 15mm 16mm 16mm; }
:root { --ink: #1d2733; --mid: #4b5868; --line: #c9d2dc; --tint: #eef3f8; --accent: #1f5fae; }
body { font-family: "Noto Sans CJK TC", sans-serif; color: var(--ink); font-size: 10.5pt; line-height: 1.6; margin: 0; }
.top { font-size: 8.5pt; color: var(--mid); border-bottom: 1px solid var(--line); padding-bottom: 4px; margin-bottom: 10px; }
h1 { font-size: 17pt; margin: 0 0 8px; line-height: 1.3; }
h2 { font-size: 12.5pt; margin: 16px 0 6px; padding-left: 8px; border-left: 4px solid var(--accent); line-height: 1.35; break-after: avoid; }
p { margin: 0 0 7px; }
ol, ul { margin: 0 0 8px; padding-left: 1.4em; }
li { margin-bottom: 3px; }
table { border-collapse: collapse; width: 100%; margin: 4px 0 10px; font-size: 9.5pt; break-inside: avoid; }
th, td { border: 1px solid var(--line); padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: var(--tint); }
code { font-family: "Noto Sans CJK TC", sans-serif; background: var(--tint); padding: 0 3px; border-radius: 3px; }
pre { background: var(--tint); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; white-space: pre-wrap; font-size: 9pt; line-height: 1.5; break-inside: avoid; }
pre code { background: none; padding: 0; }
.script { break-before: page; }
.script p { font-size: 12pt; line-height: 1.65; margin: 0 0 7px; }
.script ul li { font-size: 10pt; }
.script h2 { font-size: 13pt; margin-top: 14px; }
"""

html = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>HW5 分工與旁白稿</title><style>{CSS}</style></head>
<body><div class="top">人工智慧導論 期末專題 第 54 組　Beat the Bell　更新於 {date.today().isoformat()}</div>
<section>{tasks}</section><section class="script">{script}</section></body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.set_content(html, wait_until="load")
    pg.pdf(path=str(OUT), format="A4", print_background=True, prefer_css_page_size=True)
    b.close()
print(OUT)
