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
  NARRATION.md   the script for the voice actor, with the time of every line
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "build"
OUT.mkdir(parents=True, exist_ok=True)
RATE = 3.8          # syllables per second
GAP = 0.32          # silence between two lines of a scene
MIN_LINE = 1.5      # no subtitle shorter than this

# scene id, seconds before the first line, seconds after the last line, minimum length, lines.
# A line may be (text, seconds) to hold the picture that much longer after it.
SCENES = [
    ("hook", 2.4, 0.9, 0, [
        "這是中山大學資管系的阿哲",
        "每天五點下課鐘一響　他就衝去 YouBike 站",
        "可是常常一台車都沒有",
    ]),
    ("title", 0, 0, 3.4, []),
    ("data", 0.7, 0.9, 0, [
        "我們從十月開始　每十分鐘記錄一次　中山大學五公里內的 309 個站",
        "上課日傍晚五點到八點　校內的站有四成時間是空的",
        "五點半到六點半　超過一半",
        "早上剛好反過來　車停滿了　還不了",
    ]),
    ("app", 0.5, 0.8, 0, [
        "更麻煩的是　這時校內大部分的站同時沒車",
        "App 只能叫你走遠一點去借",
        "車　必須在下課前就回到校內",
    ]),
    ("timing", 0.6, 1.0, 0, [
        "車有回來　只是回得太早",
        "下午兩點到晚上八點還到校內的車　將近七成在五點前就到了",
        "可是官方的友愛接力　要等站空了才送五元",
        "所以這些車　只有 3% 拿到獎勵",
    ]),
    ("sitting", 0.6, 0.9, 0, [
        "阿哲還有另一個問題　他一整天都坐著",
        "國健署的調查裡　近五成國人每週身體活動不到 150 分鐘",
        "世界衛生組織說　騎腳踏車通勤也算運動",
    ]),
    ("idea", 0.6, 1.0, 0, [
        "所以我們提出預測型友愛接力",
        "模型每十分鐘算一次　哪一站四十分鐘內可能借空",
        "就提前開放還車獎勵",
        "而且不送現金　改送三十分鐘騎乘時數",
        "時數只能拿來騎車　等於鼓勵大家多騎一段",
    ]),
    ("method", 0.6, 0.9, 0, [
        "方法分三步　先記錄車數",
        "從車數的變化　估出每一站每十分鐘借和還的速度",
        ("再往後推算借空的機率", 1.2),
        "紐約的 Citi Bike　照各站將來缺多少車給點數",
        "巴黎的 Vélib' 曾送十五分鐘　給把車騎上坡的人",
        "我們把這兩個做法　用在中山的上下課",
    ]),
    ("demo", 0.6, 1.0, 0, [
        "這是我們的網站",
        "借車分頁告訴你去哪一站　最晚幾點出發",
        "政策分頁算給學校和營運商看",
        "十一月十一日下午四點半　現行規則一站都不付",
        "提案會在海資館　體育館和材料大樓送三十分鐘",
        "試算顯示　如果騎回校內的人多一半",
        "傍晚借不到車少 11%　每天多 25 趟騎車",
        "再加上下課前兩趟補車　少 27%",
    ]),
    ("results", 0.6, 1.2, 0, [
        "我們用十二個沒有參與訓練的上課日檢驗",
        "91% 的借空　在發生前大約四十分鐘就被標出來",
        "我們寫了一頁建議書給學校　市府和營運商",
        "會有多少人因此提早還車還不知道　所以建議在校內試辦四週",
        "下次下課鐘響　阿哲走到圖資站　就有車可以騎",
    ]),
    ("end", 0, 0, 6.0, []),
]

# how the numbers are read aloud: syllable count for the timing, and the reading printed in NARRATION.md
READ = {"309": "三百零九", "150": "一百五十", "3%": "百分之三", "11%": "百分之十一", "25": "二十五", "27%": "百分之二十七", "91%": "百分之九十一"}
SPOKEN = {k: len(v) for k, v in READ.items()}
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
            lines.append({"scene": sid, "i": len(lines), "k": k, "text": text, "start": round(cur, 2), "end": round(cur + dur, 2), "syll": syllables(text)})
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
    md = ["# 期末影片旁白稿", "",
          f"影片長度 {int(total // 60)} 分 {total % 60:04.1f} 秒。每一行旁白對應一句字幕，下面的時間是那句字幕出現和消失的時間；"
          "照著影片裡的字幕念，念完一句停一下，速度和字幕一致就會對上。數字照括號裡的念法。"
          "每一句可以單獨錄成一個檔，檔名用句子前面的編號（例如 07.wav），mix_voice.py 會把它放到那句的時間。", ""]
    for s in scenes:
        md.append(f"## {ts(s['start'], '.')[3:8]}　{s['id']}（{s['dur']:.1f} 秒）")
        for l in [l for l in lines if l["scene"] == s["id"]]:
            spoken = l["text"].replace("　", "，")
            for k, v in READ.items():
                spoken = re.sub(rf"(?<![0-9]){re.escape(k)}(?![0-9%])", f"{k}（{v}）", spoken)
            md.append(f"- {l['i'] + 1:02d}　`{ts(l['start'], '.')[3:10]}–{ts(l['end'], '.')[3:10]}`　{spoken}")
        md.append("")
    (OUT / "NARRATION.md").write_text("\n".join(md), encoding="utf-8")
    print(f"total {total:.1f} s, {len(lines)} lines, {sum(l['syll'] for l in lines)} syllables")
    for s in scenes:
        print(f"{s['id']:8s} {s['start']:6.1f} {s['dur']:5.1f}")
