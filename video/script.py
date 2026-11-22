"""The narration of the final video, and the timeline every other part of the video follows.

Usage: python video/script.py [OUT_DIR]   (default video/build)

The video is cut to a narration that a person will record afterwards. Each scene holds a list of narration lines; a
line is shown as one subtitle and timed by how long it takes to say: about 3.8 syllables a second, which is an
unhurried Mandarin narration (a digit group is counted by its spoken length, e.g. "309" as 三百零九, four syllables).
Scenes without narration (the title, the end card) have a fixed length.

Writes
  cues.json      scenes with start and length, every narration line with its start and end (seconds from the video
                 start), and the subtitles (a long line is shown as two); the animation (engine/scenes.js), the sound
                 (audio.py) and the subtitles all read it
  subtitles.srt  for YouTube's caption upload
  subtitles.ass  for burning the subtitles into the video (Noto Sans CJK TC)
  NARRATION.md   the script for the voice: one recording per scene with narration (seven), a pause between lines
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "build"
OUT.mkdir(parents=True, exist_ok=True)
RATE = 4.1          # syllables per second
GAP = 0.3           # silence between two lines of a scene
MIN_LINE = 1.5      # no subtitle shorter than this

# scene id, seconds before the first line, seconds after the last line, minimum length, lines.
# A line may be (text, seconds) to hold the picture that much longer after it.
SCENES = [
    ("hook", 2.4, 0.8, 0, [
        "下午五點下課　阿哲衝去 YouBike 站　一台車都沒有　換了三個站　也都是空的",
        "我們記錄了將近兩個月　上課日傍晚五點半到六點半　校內的站有一半以上的時間沒車",
        "所以我們做了一套 AI 系統　讓車在下課之前就回到學校",
    ]),
    ("title", 0, 0, 3.4, []),
    ("cause", 0.6, 0.8, 0, [
        "這是因為　下課鐘一響　上百人同時借車　校內的站半小時左右就空了　傍晚騎回學校的車又少",
        "早上剛好相反　大家騎車來上課　站被停滿　車還不進去",
    ]),
    ("relay", 0.6, 0.8, 0, [
        "高雄今年七月開始有一個獎勵　叫做「友愛接力」　從停滿的站借車　或把車還到空的站　就送你一張 5 元的騎乘券",
        "北北桃先試辦過　發出四百多萬張騎乘券　四十四萬人次參與",
        "可是它要等站已經空了才給　對學校來說太晚了　車要在五點下課之前回來　下課的人才借得到",
        "我們的資料顯示　下午騎回學校的車　七成在五點前就到了　那時站還沒空　所以只有 3% 拿到獎勵",
    ]),
    ("idea", 0.6, 0.8, 0, [
        "我們把它改成預測型　系統每 10 分鐘預測一次　哪一站四十分鐘內可能被借光　那一站現在還車就有獎勵",
        "資料是我們自己記錄的　中山大學附近 309 個站　從十月起每 10 分鐘一筆",
        "拿 12 個模型沒看過的上課日來測試　91% 的空站　系統大約在 40 分鐘前就抓到了",
        ("獎勵也改成一小時免費騎乘　有月票或學生卡的人　前 30 分鐘本來就免費　送一小時才有感", 1.4),
        "國健署的調查裡　將近一半的人每週身體活動不到 150 分鐘",
        "紐約和巴黎的公共自行車　也用過類似的獎勵",
    ]),
    ("demo", 0.6, 0.8, 0, [
        "這些都做進了我們的網站　用手機打開就能用",
        "學生用「借車」分頁　選你在哪棟樓　它告訴你去哪一站借　走幾分鐘　最晚幾點要出發",
        "早上看「還車」分頁　哪一站還有位子　滿了要改去哪裡　都寫在上面",
        "「政策」分頁模擬提案上路以後　地圖上標「+1小時」的站快被借光了　現在把車還到這裡　就送一小時騎乘時數",
        "學校和營運商還能在下面試算　按下「多 50%」　代表因為獎勵　回來還車的人多一半　網站就算出借不到車的人會少多少",
    ]),
    ("impact", 0.6, 0.8, 0, [
        "按下去會看到　光靠獎勵　每天傍晚少 23 人次借不到車",
        "如果營運商也照預測在下課前補兩趟車　每天少 56 人次　借不到車的人少了四分之一以上",
        "獎勵也讓每天多出 25 趟騎車回學校　送出去的免費騎乘　加起來大約 69 小時",
        "我們把這些寫成一頁建議書　給學校、市政府和營運商　建議先在校內試辦四週　看實際有多少人參與",
    ]),
    ("ending", 0.8, 3.2, 0, [
        "下次五點的鐘聲響起　希望阿哲走到站　車已經在那裡等他",
    ]),
    ("end", 0, 0, 6.0, []),
]

# how the numbers are read aloud: syllable count for the timing, and the reading printed in NARRATION.md
READ = {"309": "三百零九", "150": "一百五十", "3%": "百分之三", "91%": "百分之九十一", "50%": "百分之五十", "+1小時": "加一小時",
        "10": "十", "12": "十二", "23": "二十三", "25": "二十五", "30": "三十", "40": "四十", "56": "五十六", "69": "六十九", "5": "五"}
SPOKEN = {k: len(v) for k, v in READ.items()}
NAMES = {"hook": "問題", "title": "片名", "cause": "原因", "relay": "現在的獎勵：友愛接力", "idea": "我們的做法", "demo": "怎麼用",
         "impact": "改善多少", "ending": "結尾", "end": "片尾"}
SUB_MAX = 18       # a subtitle wider than this many CJK characters is split at its full-width spaces
LATIN = {"YouBike": 2, "App": 1, "Citi": 2, "Bike": 1, "Vélib'": 2}


def syllables(line):
    n = 0
    for tok in re.findall(r"[一-鿿]|[0-9]+%?|[A-Za-zé']+", line):
        if re.match(r"[一-鿿]", tok):
            n += 1
        elif tok in SPOKEN:
            n += SPOKEN[tok]
        elif tok in LATIN:
            n += LATIN[tok]
        elif tok[0].isdigit():
            n += 2 * len(tok.rstrip("%")) + (3 if tok.endswith("%") else 0)
        else:
            n += max(1, len(tok) // 3)
    return n


def width(text):
    """Display width in CJK characters (Latin letters, digits and spaces count about half)."""
    return sum(1 if re.match(r"[一-鿿　，。？！％]", ch) else 0.55 for ch in text)


def split_sub(line):
    """Split a narration line into subtitles of at most SUB_MAX characters, at its full-width spaces, each timed by its
    share of the syllables. A line that fits stays one subtitle."""
    if width(line["text"]) <= SUB_MAX:
        return [dict(text=line["text"], start=line["start"], end=line["end"])]
    chunks = []
    for part in line["text"].split("　"):
        if chunks and width(chunks[-1] + "　" + part) <= SUB_MAX:
            chunks[-1] += "　" + part
        else:
            chunks.append(part)
    total = sum(syllables(c) for c in chunks)
    out, t = [], line["start"]
    for c in chunks:
        d = (line["end"] - line["start"]) * syllables(c) / total
        out.append(dict(text=c, start=round(t, 2), end=round(t + d, 2)))
        t += d
    return out


def build():
    t = 0.0
    scenes, lines = [], []
    for sid, lead, tail, minimum, ls in SCENES:
        start = t
        cur = start + lead
        for k, item in enumerate(ls):
            text, hold = item if isinstance(item, tuple) else (item, 0.0)
            dur = max(MIN_LINE, syllables(text) / RATE)
            # the phrases of the line (split at its full-width spaces), each timed by its share of the syllables, so an
            # animation can start on a phrase rather than on the whole line
            parts, at, tot = [], cur, sum(max(1, syllables(x)) for x in text.split("　"))
            for x in text.split("　"):
                d = dur * max(1, syllables(x)) / tot
                parts.append({"text": x, "start": round(at, 2), "end": round(at + d, 2)})
                at += d
            lines.append({"scene": sid, "i": len(lines), "k": k, "text": text, "start": round(cur, 2), "end": round(cur + dur, 2), "syll": syllables(text), "parts": parts})
            cur += dur + GAP + hold
        end = max(cur - (GAP if ls else 0) + tail, start + minimum)
        scenes.append({"id": sid, "start": round(start, 2), "dur": round(end - start, 2)})
        t = end
    return scenes, lines, round(t, 2)


def ts(x, sep=","):
    h, rem = divmod(x, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)):03d}"


def ass_ts(x):
    h, rem = divmod(x, 3600); m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


if __name__ == "__main__":
    scenes, lines, total = build()
    subs = [s for l in lines for s in split_sub(l)]
    json.dump({"fps": 30, "width": 1920, "height": 1080, "total": total, "scenes": scenes, "lines": lines, "subs": subs}, open(OUT / "cues.json", "w"), ensure_ascii=False, indent=1)
    with open(OUT / "subtitles.srt", "w", encoding="utf-8") as f:
        for n, l in enumerate(subs, 1):
            f.write(f"{n}\n{ts(l['start'])} --> {ts(l['end'])}\n{l['text']}\n\n")
    ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           "Style: Sub,Noto Sans CJK TC Medium,54,&H00FFFFFF,&H00FFFFFF,&H00141E28,&H80000000,0,0,0,0,100,100,1,0,1,3.2,1.2,2,120,120,72,1", "",
           "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for l in subs:
        ass.append(f"Dialogue: 0,{ass_ts(l['start'])},{ass_ts(l['end'])},Sub,,0,0,0,,{l['text']}")
    (OUT / "subtitles.ass").write_text("\n".join(ass) + "\n", encoding="utf-8")
    # the script for the voice: one recording per scene that has narration (seven), each line on its own row; the
    # numbers are the lines of cues.json, and mix_voice.py cuts each recording at its pauses
    keys = sorted(READ, key=len, reverse=True)
    pat = re.compile("|".join(rf"(?<![0-9]){re.escape(k)}(?![0-9%])" for k in keys))
    spoken = lambda l: pat.sub(lambda m: f"{m.group(0)}（{READ[m.group(0)]}）", l["text"].replace("　", "，"))
    voiced = [s for s in scenes if any(l["scene"] == s["id"] for l in lines)]
    md = ["# 期末影片旁白稿", "",
          f"影片長 {int(total // 60)} 分 {total % 60:02.0f} 秒，旁白分成 {len(voiced)} 段。一段錄成一個檔，檔名 1 到 {len(voiced)}"
          "（m4a、mp3、wav 都可以）；也可以全部錄在同一個檔，段和段之間停兩秒。", "",
          "- 語氣像新聞主播：咬字清楚、速度平穩、語氣肯定，句尾不拖音、不上揚；捲舌音和平舌音要分清楚，不要含糊。",
          "- 速度和影片字幕一樣，大約每秒 4 個字。先開著影片跟字幕念一遍，再正式錄。",
          "- 每句念完停一秒再念下一句；句子裡的逗號只要稍微停。",
          "- 數字照括號裡的念法。念錯了就把那一段整段重錄。",
          "- 每段標題寫著大約幾秒（含句子之間停的那一秒）。錄完看一下錄音長度，比它多出兩成以上，就念快一點再錄一次。",
          "- 用手機在安靜的房間錄，嘴巴離手機約 20 公分。", ""]
    for n, s in enumerate(voiced, 1):
        ls = [l for l in lines if l["scene"] == s["id"]]
        secs = sum(l["end"] - l["start"] for l in ls) + (len(ls) - 1) * 1.0
        md.append(f"## 第 {n} 段：{NAMES.get(s['id'], s['id'])}（檔名 {n}，{len(ls)} 句，約 {secs:.0f} 秒）")
        md.append("")
        for l in ls:
            md.append(f"{l['i'] + 1:02d}　{spoken(l)}")
            md.append("")
    (OUT / "NARRATION.md").write_text("\n".join(md), encoding="utf-8")
    print(f"total {total:.1f} s, {len(lines)} lines, {sum(l['syll'] for l in lines)} syllables")
    for s in scenes:
        print(f"{s['id']:8s} {s['start']:6.1f} {s['dur']:5.1f}")
