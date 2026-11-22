"""Put the recorded narration into the finished video.

Usage:
  python video/mix_voice.py VOICE_DIR             the sections of build/NARRATION.md, one file each, whose names start
                                                  with the section number (1 ... 7); or one file per line, 01 ... 25
                                                  (.m4a, .mp3, .wav, .aac and .flac all work)
  python video/mix_voice.py VOICE_FILE            the whole narration in one file, with a pause between lines
  python video/mix_voice.py VOICE_FILE --aligned  one recording already in time with the video

A recording that holds several lines is cut at its pauses. Among the silences between stretches of speech, the cuts
go where the pauses are long and the pieces come out in proportion to the lines' lengths in the script (a dynamic
programme over the candidate pauses), so that a short hesitation inside a line does not split it. Each line is then
trimmed of the silence around it and placed at the start of its subtitle. A line longer than its slot (up to the next
line) is sped up by at most 15% so it ends in time; lines that would need more are listed, so they can be read again a
little faster. Under the voice the music goes down 8 dB and the effects 4 dB, and the whole mix is normalized to
-14 LUFS, the level YouTube plays at. Needs render.py and audio.py to have run.

Writes video/out/beat_the_bell_voice.mp4 (subtitles burnt in), beat_the_bell_voice_clean.mp4 (for the .srt) and, when
lines were cut from longer recordings, voice_split.txt: every piece's length against its line's length in the script.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SR = 48000
CUES = json.loads((HERE / "build" / "cues.json").read_text())
MAX_SPEEDUP = 1.15
AUDIO = (".wav", ".m4a", ".mp3", ".aac", ".flac")
FRAME = 0.02                          # seconds per analysis frame
MIN_PAUSE = 0.18                      # shortest silence that may separate two lines
W_LEN, W_GAP = 4.0, 1.0               # weights of the length match and of the pause length in the split


def decode(path, tempo=1.0):
    af = ["-af", f"atempo={tempo:.4f}"] if abs(tempo - 1) > 1e-3 else []
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def retime(x, tempo):
    """x played tempo times faster, pitch kept (ffmpeg atempo)."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", f"atempo={tempo:.4f}",
                          "-f", "f32le", "-"], input=x.astype(np.float32).tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def level_db(x):
    f = int(FRAME * SR)
    n = len(x) // f
    rms = np.sqrt(np.mean(x[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms)


def speech(x):
    """Per frame: is it speech? Above the noise floor by 12 dB and within 35 dB of the loud frames."""
    db = level_db(x)
    if len(db) == 0:
        return db.astype(bool)
    floor, loud = np.percentile(db, 10), np.percentile(db, 99)
    return db > max(floor + 12, loud - 35)


def trim(x):
    on = np.where(speech(x))[0]
    if len(on) == 0:
        return x
    f = int(FRAME * SR)
    return x[max(0, on[0] - 2) * f: min(len(x), (on[-1] + 3) * f)]


def split(x, want):
    """Cut x into len(want) pieces at pauses; want = the lines' lengths in the script (seconds)."""
    m = len(want)
    if m == 1:
        return [x], []
    sp = speech(x)
    on = np.where(sp)[0]
    if len(on) == 0:
        raise SystemExit("a recording has no speech in it")
    first, last = on[0], on[-1] + 1
    gaps, k = [], first
    while k < last:                                           # silent runs between speech
        if sp[k]:
            k += 1
            continue
        j = k
        while j < last and not sp[j]:
            j += 1
        if (j - k) * FRAME >= MIN_PAUSE:
            gaps.append(((k + j) / 2 * FRAME, (j - k) * FRAME))
        k = j
    if len(gaps) < m - 1:
        raise SystemExit(f"found {len(gaps)} pauses for {m} lines: pause about a second between lines")
    t0, t1 = first * FRAME, last * FRAME
    T = t1 - t0
    p = np.log(np.array(want) / sum(want))
    pos = [t0] + [g[0] for g in gaps] + [t1]                  # candidate cut points, with the two ends
    rew = [0.0] + [W_GAP * math.log(g[1] / MIN_PAUSE) for g in gaps] + [0.0]
    K = len(pos) - 1
    cost = lambda a, b, i: W_LEN * (math.log(max(pos[b] - pos[a], 1e-3) / T) - p[i]) ** 2
    best = {(0, 0): (0.0, None)}                              # (lines placed, last cut) -> (score, previous cut)
    for i in range(1, m):
        for b in range(i, K - (m - 1 - i)):
            cand = [(best[(i - 1, a)][0] + rew[b] - cost(a, b, i - 1), a) for a in range(i - 1, b) if (i - 1, a) in best]
            if cand:
                best[(i, b)] = max(cand)
    end = max(((best[(m - 1, b)][0] - cost(b, K, m - 1), b) for b in range(m - 1, K) if (m - 1, b) in best))
    cuts, b = [K], end[1]
    for i in range(m - 1, 0, -1):
        cuts.append(b)
        b = best[(i, b)][1]
    cuts.append(0)
    cuts = cuts[::-1]
    t = [pos[c] for c in cuts]
    pieces = [x[int(t[i] * SR): int(t[i + 1] * SR)] for i in range(m)]
    return pieces, [t[i + 1] - t[i] for i in range(m)]


def sections():
    """The scenes with narration, in order, each with its lines."""
    out = []
    for s in CUES["scenes"]:
        ls = [l for l in CUES["lines"] if l["scene"] == s["id"]]
        if ls:
            out.append(ls)
    return out


def number(p):
    m = re.match(r"\D*(\d+)", p.stem)
    return int(m.group(1)) if m else None


def read_stereo(path):
    sr, x = wavfile.read(path)
    return x.astype(np.float64) / 32767


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = Path(args[0])
    n = int(CUES["total"] * SR)
    voice = np.zeros(n)
    lines = CUES["lines"]
    audio = {}                                                # line index -> samples
    report = []
    if src.is_dir():
        files = sorted((p for p in src.iterdir() if p.suffix.lower() in AUDIO), key=lambda p: (number(p) is None, number(p) or 0, p.stat().st_mtime))
        secs = sections()
        if len(files) == 1:
            groups = [(files[0], lines)]
        elif len(files) <= len(secs):                         # one file per section
            nums = [number(p) for p in files]
            if all(v is not None and 1 <= v <= len(secs) for v in nums) and len(set(nums)) == len(nums):
                groups = [(p, secs[v - 1]) for p, v in zip(files, nums)]
            else:                                             # unnamed: in the order they were recorded
                groups = list(zip(sorted(files, key=lambda p: p.stat().st_mtime), secs))
            missing = [k + 1 for k in range(len(secs)) if all(g[1] is not secs[k] for g in groups)]
            if missing:
                print("missing sections:", " ".join(map(str, missing)))
        else:                                                 # one file per line
            byline = {number(p): p for p in files}
            groups = [(byline[l["i"] + 1], [l]) for l in lines if l["i"] + 1 in byline]
            missing = [l["i"] + 1 for l in lines if l["i"] + 1 not in byline]
            if missing:
                print("missing lines:", " ".join(f"{v:02d}" for v in missing))
    elif "--aligned" in sys.argv:
        groups = None
        x = decode(src)
        voice[: min(n, len(x))] = x[:n]
    else:
        groups = [(src, lines)]
    slow = []
    if groups is not None:
        for path, ls in groups:
            pieces, got = split(decode(path), [l["end"] - l["start"] for l in ls])
            for l, x, g in zip(ls, pieces, got or [None] * len(ls)):
                audio[l["i"]] = x
                if g is not None:
                    report.append((l, g))
        for k, l in enumerate(lines):
            if l["i"] not in audio:
                continue
            x = trim(audio[l["i"]])
            nxt = lines[k + 1]["start"] if k + 1 < len(lines) else CUES["total"]
            room = nxt - l["start"] - 0.12
            dur = len(x) / SR
            if dur > room:
                x = trim(retime(x, min(MAX_SPEEDUP, dur / room)))
                if dur / room > MAX_SPEEDUP:
                    slow.append(f"{l['i'] + 1:02d} ({dur:.1f} s for {room:.1f} s)")
            x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.1        # every line at the same loudness before the final level
            s = int(l["start"] * SR)
            voice[s:s + len(x)] += x[: max(0, n - s)]
        if slow:
            print("read these lines again a little faster:", "; ".join(slow))
    if report:
        ratios = [g / (l["end"] - l["start"]) for l, g in report]
        med = float(np.median(ratios))
        rows = [f"{l['i'] + 1:02d}  script {l['end'] - l['start']:5.1f} s  piece {g:5.1f} s  x{g / (l['end'] - l['start']) / med:4.2f}  {l['text'][:16]}" for l, g in report]
        odd = [r for r, q in zip(rows, ratios) if abs(q / med - 1) > 0.4]
        (OUT / "voice_split.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"cut {len(report)} lines from the recordings (median pace x{med:.2f} the script's); check voice_split.txt"
              + (f"; pieces far from their line's length: {len(odd)}" if odd else ""))
        for r in odd:
            print("  ", r)
    music, sfx = read_stereo(HERE / "build" / "music.wav")[:n], read_stereo(HERE / "build" / "sfx.wav")[:n]
    # the music 8 dB and the effects 4 dB lower while someone speaks: a speech envelope over 50 ms, 80 ms attack, 400 ms release
    hop = SR // 100                                           # the envelope is followed at 100 Hz
    nb = len(voice) // hop
    on = np.sqrt(np.mean(voice[: nb * hop].reshape(nb, hop) ** 2, axis=1))
    on = (np.convolve(on, np.ones(5) / 5, mode="same") > 0.01).astype(np.float64)
    a_up, a_down = 1 - math.exp(-0.01 / 0.08), 1 - math.exp(-0.01 / 0.4)
    sm, e = np.empty(nb), 0.0
    for i, v in enumerate(on):
        e += (a_up if v > e else a_down) * (v - e)
        sm[i] = e
    duck = np.repeat(sm, hop)
    duck = np.pad(duck, (0, max(0, len(voice) - len(duck))), mode="edge")[: len(voice)]
    g_music, g_sfx = 1 - duck * (1 - 10 ** (-8 / 20)), 1 - duck * (1 - 10 ** (-4 / 20))
    L = min(len(music), len(sfx), len(voice))
    mix = np.stack([voice[:L], voice[:L]], 1) + 0.4 * music[:L] * g_music[:L, None] + 0.6 * sfx[:L] * g_sfx[:L, None]
    tmp = OUT / "voice_mix.wav"
    peak = np.max(np.abs(mix))
    wavfile.write(tmp, SR, (mix / max(1.0, peak / 0.98) * 32767).astype(np.int16))
    for name in ("beat_the_bell", "beat_the_bell_clean"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / f"{name}.mp4"), "-i", str(tmp), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                        str(OUT / f"{name.replace('beat_the_bell', 'beat_the_bell_voice')}.mp4")], check=True)
    print("written:", OUT / "beat_the_bell_voice.mp4", "and", OUT / "beat_the_bell_voice_clean.mp4")


if __name__ == "__main__":
    main()
