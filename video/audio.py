"""Music and sound effects of the final video, synthesized here so that every sound is our own.

Usage: python video/audio.py [OUT_DIR]   (default video/build; needs the video folder served on 8771, see preview.py)

Writes, at 48 kHz stereo:
  music.wav   a lo-fi bed (F-E-D-C major sevenths at 84 bpm), quieter under every narration line so a voice fits on top
  sfx.wav     the sound effects, placed at the times listed by sfxEvents() in engine/scenes.js
  mix.wav     music + effects: the sound of the video before the narration is recorded
  sfx.json    the effect list, for reference
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "build"
SR = 48000
RNG = np.random.default_rng(54)
CUES = json.loads((HERE / "build" / "cues.json").read_text())
TOTAL = CUES["total"]


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.005, r=None):
    """Linear attack of a seconds, then exponential decay with time constant r (or flat)."""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    if r:
        e = e * np.exp(-np.maximum(0, t - a) / r)
    return e


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def bell_tone(f, d, decay=1.2, bright=1.0):
    """A struck bell: inharmonic partials, the higher ones dying faster."""
    t = t_axis(d)
    parts = [(0.5, 0.35, 1.0), (1.0, 1.0, 1.0), (2.0, 0.55, 0.6), (2.4, 0.35 * bright, 0.45), (3.0, 0.25 * bright, 0.35), (4.2, 0.15 * bright, 0.25)]
    y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (decay * k)) for r, a, k in parts)
    return y * env(len(t), 0.004)


# ---------- sound effects ----------
def school_bell(phrase=0):
    # the Westminster quarters, the tune of most Taiwanese school bells; phrase 0 rings at the bell, phrase 1 at the end
    notes = [[329.63, 261.63, 293.66, 196.00], [196.00, 293.66, 329.63, 261.63]][phrase]
    gap, d = 0.42, 3.4
    y = np.zeros(int(d * SR))
    for i, f in enumerate(notes):
        tone = bell_tone(f, d - i * gap, decay=0.9, bright=0.8)
        s = int(i * gap * SR)
        y[s:s + len(tone)] += tone * (1.0 if i < 3 else 1.15)
    return lp(y, 6000) * 0.5


def bike_bell():
    d = 0.9
    y = np.zeros(int(d * SR))
    for k, s in enumerate((0.0, 0.14)):
        t = t_axis(d - s)
        tone = sum(a * np.sin(2 * np.pi * 2350 * r * t) * np.exp(-t / dec) for r, a, dec in ((1, 1, 0.25), (1.52, 0.6, 0.18), (2.11, 0.45, 0.12), (2.73, 0.3, 0.08)))
        tone *= 1 + 0.25 * np.sin(2 * np.pi * 28 * t)                   # the shimmer of a thumb-flicked bell
        i = int(s * SR)
        y[i:i + len(tone)] += tone * env(len(t), 0.002) * (1 if k == 0 else 0.8)
    return y * 0.35


def whoosh(d=0.5, lo=300, hi=3000, rise=0.55):
    n = int(d * SR)
    x = RNG.standard_normal(n)
    t = np.arange(n) / n
    out = np.zeros(n)
    # sweep a band-pass up and down by filtering in blocks
    blk = 512
    for i in range(0, n, blk):
        u = t[i]
        f = lo + (hi - lo) * (u / rise if u < rise else (1 - u) / (1 - rise))
        out[i:i + blk] = bp(x[max(0, i - 2048):i + blk], max(60, f * 0.6), min(SR / 2 - 100, f * 1.5))[-len(x[i:i + blk]):]
    shape = np.sin(np.pi * np.clip(t, 0, 1)) ** 1.5
    return out * shape * 0.35


def pop(f0=620, f1=280, d=0.14):
    t = t_axis(d)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.04)
    return y * 0.6


def ding(f=1318.5, d=0.9):
    return bell_tone(f, d, decay=0.35, bright=0.5) * 0.25


def chime():
    a, b = ding(1046.5, 1.2), ding(1568.0, 1.2)
    y = np.zeros(int(1.5 * SR))
    y[:len(a)] += a
    y[int(0.13 * SR):int(0.13 * SR) + len(b)] += b
    return y


def notify():
    y = np.zeros(int(0.5 * SR))
    for s, f in ((0.0, 880), (0.12, 1318.5)):
        t = t_axis(0.3)
        tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * env(len(t), 0.003, 0.08)
        i = int(s * SR)
        y[i:i + len(tone)] += tone
    return y * 0.3


def tap():
    n = int(0.05 * SR)
    x = hp(RNG.standard_normal(n), 1800) * env(n, 0.0005, 0.004)
    t = t_axis(0.05)
    return (x * 0.5 + 0.4 * np.sin(2 * np.pi * 2100 * t) * env(n, 0.0005, 0.01)) * 0.6


def tick():
    t = t_axis(0.06)
    return np.sin(2 * np.pi * 1700 * t) * env(len(t), 0.0005, 0.012) * 0.35


def blip():
    t = t_axis(0.07)
    return np.sin(2 * np.pi * 1250 * t) * env(len(t), 0.002, 0.02) * 0.3


def bonk():
    # two falling tones, a soft "nope" for an empty rack
    y = np.zeros(int(0.8 * SR))
    for s, f in ((0.0, 311.1), (0.2, 233.1)):
        t = t_axis(0.5)
        tone = np.tanh(2.2 * np.sin(2 * np.pi * f * t)) * env(len(t), 0.004, 0.16)
        i = int(s * SR)
        y[i:i + len(tone)] += tone
    return lp(y, 2500) * 0.3


def step():
    n = int(0.09 * SR)
    return lp(RNG.standard_normal(n), 900) * env(n, 0.002, 0.02) * 0.7


def sparkle():
    y = np.zeros(int(0.9 * SR))
    for k in range(7):
        f = [1568, 2093, 2637, 3136, 2349, 2794, 3520][k]
        g = ding(f, 0.5) * 0.5
        i = int((0.08 * k + 0.02 * RNG.random()) * SR)
        y[i:i + len(g)] += g[:len(y) - i]
    return y


def alert():
    y = np.zeros(int(0.6 * SR))
    for s in (0.0, 0.2):
        t = t_axis(0.16)
        tone = np.sin(2 * np.pi * 660 * t) * env(len(t), 0.004, 0.05)
        i = int(s * SR)
        y[i:i + len(tone)] += tone
    return y * 0.3


def scratch():
    return whoosh(0.3, 2500, 600, rise=0.2) * 0.9


def freewheel():
    d = 1.6
    y = np.zeros(int(d * SR))
    k, t = 0, 0.0
    while t < d - 0.02:
        c = tick() * (1 - t / d) * 0.7
        i = int(t * SR)
        y[i:i + len(c)] += c[:len(y) - i]
        t += 1 / (16 + 6 * (1 - t / d))
        k += 1
    return lp(y, 5000)


SFX = {"school_bell": lambda: school_bell(0), "school_bell_soft": lambda: school_bell(1) * 0.8, "bike_bell": bike_bell,
       "whoosh": whoosh, "zoom": lambda: whoosh(1.0, 200, 2500, 0.8), "swipe": lambda: whoosh(0.25, 800, 4000, 0.4) * 0.8,
       "pop": pop, "ding": ding, "chime": chime, "notify": notify, "tap": tap, "tick": tick, "blip": blip, "bonk": bonk,
       "step": step, "sparkle": sparkle, "alert": alert, "scratch": scratch, "freewheel": freewheel}


# ---------- music ----------
BPM = 84
BEAT = 60 / BPM
CHORDS = [[174.61, 220.00, 261.63, 329.63], [164.81, 196.00, 246.94, 293.66], [146.83, 174.61, 220.00, 261.63], [130.81, 164.81, 196.00, 246.94]]
BASS = [87.31, 82.41, 73.42, 65.41]


def epiano(f, d, vel=1.0):
    t = t_axis(d)
    mod = 0.9 * np.exp(-t / 0.35) * np.sin(2 * np.pi * f * 2 * t)     # a touch of FM for the tine
    y = np.sin(2 * np.pi * f * t + mod) + 0.18 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.4)
    return y * env(len(t), 0.006, 1.1) * vel


def kick():
    t = t_axis(0.35)
    f = 48 + 90 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.12)


def snare():
    n = int(0.25 * SR)
    t = t_axis(0.25)
    return (bp(RNG.standard_normal(n), 1200, 6000) * env(n, 0.001, 0.06) * 0.5 + np.sin(2 * np.pi * 185 * t) * env(n, 0.001, 0.05) * 0.4)


def hat():
    n = int(0.06 * SR)
    return hp(RNG.standard_normal(n), 7000) * env(n, 0.001, 0.012) * 0.25


def scene_start(sid):
    return next(s["start"] for s in CUES["scenes"] if s["id"] == sid)


def music():
    n = int((TOTAL + 1) * SR)
    keys, bass, drums = np.zeros(n), np.zeros(n), np.zeros(n)
    t0 = 2.2                                              # after the first bell phrase
    drums_on = [(scene_start("title"), scene_start("sitting")), (scene_start("idea"), scene_start("results") + CUES["lines"][-1]["start"] - scene_start("results") - 0.5)]
    bar = 0
    t = t0
    end = scene_start("end") + 2.0
    while t < end:
        ch, bs = CHORDS[bar % 4], BASS[bar % 4]
        for hit, vel in ((0.0, 1.0), (2.5, 0.55)):
            for k, f in enumerate(ch):
                s = int((t + hit * BEAT + 0.018 * k) * SR)
                tone = epiano(f, 3.0, vel * (0.9 if k else 1.0))
                keys[s:s + len(tone)] += tone[:max(0, n - s)]
        for hit, f in ((0.0, bs), (2.0, bs * 1.5), (3.5, bs)):
            s = int((t + hit * BEAT) * SR)
            tt = t_axis(1.0)
            tone = np.tanh(1.5 * np.sin(2 * np.pi * f * tt)) * env(len(tt), 0.01, 0.35)
            bass[s:s + len(tone)] += tone[:max(0, n - s)]
        if any(a <= t < b for a, b in drums_on):
            for i in range(8):                            # swung eighths
                s = int((t + (i // 2) * BEAT + (i % 2) * BEAT * 0.62) * SR)
                h = hat() * (1.0 if i % 2 == 0 else 0.6)
                drums[s:s + len(h)] += h[:max(0, n - s)]
            for b, w in ((0, kick()), (2, kick()), (2.5, kick() * 0.5), (1, snare()), (3, snare())):
                s = int((t + b * BEAT) * SR)
                drums[s:s + len(w)] += w[:max(0, n - s)]
        t += 4 * BEAT
        bar += 1
    # a final chord under the end card
    s = int(end * SR)
    for k, f in enumerate(CHORDS[0] + [392.0]):
        tone = epiano(f, 5.0, 0.8)
        keys[s + int(0.03 * k * SR):s + int(0.03 * k * SR) + len(tone)] += tone[:max(0, n - s - int(0.03 * k * SR))]
    crackle = np.zeros(n)
    idx = RNG.integers(0, n, int(TOTAL * 6))
    crackle[idx] = RNG.standard_normal(len(idx)) * 0.12
    y = 0.16 * lp(keys, 4500) + 0.22 * lp(bass, 600) + 0.3 * lp(drums, 9000) + lp(crackle, 3000)
    # fade in, fade out, and duck under the narration
    tt = np.arange(n) / SR
    g = np.clip((tt - 1.8) / 1.5, 0, 1) * np.clip((TOTAL - tt) / 3.0, 0, 1)
    # the music stops when 阿哲 finds the rack empty and comes back with the drums on the title
    stop, back = CUES["lines"][2]["start"] - 0.15, scene_start("title")
    g *= 1 - np.clip(np.minimum((tt - stop) / 0.12, (back - tt) / 0.05), 0, 1)
    duck = np.ones(n)
    for l in CUES["lines"]:
        a, b = l["start"] - 0.25, l["end"] + 0.25
        duck = np.minimum(duck, 1 - 0.5 * np.clip(np.minimum((tt - a) / 0.25, (b - tt) / 0.25), 0, 1))
    return y * g * duck


def place(events):
    n = int((TOTAL + 1) * SR)
    y = np.zeros(n)
    for e in events:
        w = SFX[e["name"]]()
        w = w / (np.max(np.abs(w)) + 1e-9) * 0.5 * e["gain"]       # every effect at the same peak before its gain
        s = int(e["t"] * SR)
        y[s:s + len(w)] += w[:max(0, n - s)]
    return y


def stereo(mono, width=0.0):
    """Mono to stereo; width > 0 delays one side by that many seconds, for a little space."""
    d = int(width * SR)
    right = np.concatenate([np.zeros(d), mono[:len(mono) - d]]) if d else mono
    return np.stack([mono, right], 1)


def to_wav(path, st):
    st = st[: int(TOTAL * SR)]
    peak = np.max(np.abs(st))
    if peak > 0.98:
        st = st * 0.98 / peak
    wavfile.write(path, SR, (st * 32767).astype(np.int16))


def get_events():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("http://127.0.0.1:8771/engine/stage.html?scene=hook")
        pg.wait_for_function("window.READY === true", timeout=30000)
        ev = pg.evaluate("sfxEvents()")
        b.close()
    return ev


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    events = get_events()
    (OUT / "sfx.json").write_text(json.dumps(events, ensure_ascii=False, indent=0))
    m, s = music(), place(events)
    ms, ss = stereo(m, 0.012), stereo(s)
    to_wav(OUT / "music.wav", ms)
    to_wav(OUT / "sfx.wav", ss)
    to_wav(OUT / "mix.wav", ms + 0.9 * ss)
    print(f"{len(events)} effects; music peak {np.max(np.abs(m)):.2f}, effects peak {np.max(np.abs(s)):.2f}")
