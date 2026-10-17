"""Every black (non-blue) passage of the HW3 report must be verbatim HW1 text.

Usage: python check_black.py HW3.docx HW1.docx
Groups consecutive non-blue runs of each paragraph (body and table cells) into segments and reports segments
whose whitespace-normalised text is not a substring of the whitespace-normalised HW1 text. Pure numbers,
punctuation and reference markers like "[12] " are ignored.
"""
import re
import sys

import docx
from docx.oxml.ns import qn

BLUE = "0000FF"
norm = lambda s: re.sub(r"\s+", "", s)


def paragraphs(d):
    body = d.element.body
    for p in body.iter(qn("w:p")):
        yield p


def run_color(r):
    rpr = r.find(qn("w:rPr"))
    if rpr is None:
        return None
    c = rpr.find(qn("w:color"))
    return None if c is None else c.get(qn("w:val"))


def segments(p):
    segs, cur = [], ""
    for r in p.iter(qn("w:r")):
        text = "".join(t.text or "" for t in r.iter(qn("w:t")))
        if run_color(r) == BLUE:
            if cur.strip():
                segs.append(cur)
            cur = ""
        else:
            cur += text
    if cur.strip():
        segs.append(cur)
    return segs


hw3, hw1 = docx.Document(sys.argv[1]), docx.Document(sys.argv[2])
ref = norm(" ".join("".join(t.text or "" for t in p.iter(qn("w:t"))) for p in paragraphs(hw1)))
bad, n = [], 0
for p in paragraphs(hw3):
    for s in segments(p):
        k = norm(s)
        if not k or re.fullmatch(r"[\d\W_]*", k) or re.fullmatch(r"\[\d+\]", k):
            continue
        n += 1
        if k not in ref:
            bad.append(s)
print(f"{n} black segments, {len(bad)} not in HW1")
for s in bad:
    print("  NOT IN HW1:", s[:160])
sys.exit(1 if bad else 0)
