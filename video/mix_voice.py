"""Put the recorded narration into the finished video.

Usage:
  python video/mix_voice.py VOICE_DIR    one file per line, named by the line number in build/NARRATION.md
                                         (01.wav ... 41.wav; .m4a and .mp3 also work)
  python video/mix_voice.py VOICE_FILE   one recording of the whole narration, already in time with the video

Each line is trimmed of the silence around it and placed at the start of its subtitle. A line that is longer than its
slot (up to the next line) is sped up by at most 12% so it ends in time; lines that would need more are listed, so they
can be read again a little faster. Under the voice the music goes down 8 dB more and the effects 4 dB, and the whole
mix is normalized to -14 LUFS, the level YouTube plays at. Needs render.py and audio.py to have run.

Writes video/out/beat_the_bell_voice.mp4 (subtitles burnt in) and beat_the_bell_voice_clean.mp4 (for the .srt).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SR = 48000
CUES = json.loads((HERE / "build" / "cues.json").read_text())
MAX_SPEEDUP = 1.12


def decode(path, tempo=1.0):
    af = ["-af", f"atempo={tempo:.4f}"] if abs(tempo - 1) > 1e-3 else []
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def trim(x, thr_db=-42):
    """Cut the silence before and after the speech (20 ms frames quieter than thr_db below the peak)."""
    f = int(0.02 * SR)
    n = len(x) // f
    if n == 0:
        return x
    rms = np.sqrt(np.mean(x[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    on = np.where(20 * np.log10(rms / (rms.max() + 1e-12)) > thr_db)[0]
    if len(on) == 0:
        return x
    a, b = max(0, on[0] - 2) * f, min(len(x), (on[-1] + 3) * f)
    return x[a:b]


def read_stereo(path):
    sr, x = wavfile.read(path)
    return x.astype(np.float64) / 32767


def main():
    src = Path(sys.argv[1])
    n = int(CUES["total"] * SR)
    voice = np.zeros(n)
    lines = CUES["lines"]
    if src.is_dir():
        files = {int(p.stem): p for p in src.iterdir() if p.suffix.lower() in (".wav", ".m4a", ".mp3", ".aac", ".flac") and p.stem.isdigit()}
        missing = [l["i"] + 1 for l in lines if l["i"] + 1 not in files]
        if missing:
            print("missing lines:", " ".join(f"{m:02d}" for m in missing))
        slow = []
        for k, l in enumerate(lines):
            p = files.get(l["i"] + 1)
            if not p:
                continue
            x = trim(decode(p))
            nxt = lines[k + 1]["start"] if k + 1 < len(lines) else CUES["total"]
            room = nxt - l["start"] - 0.12
            dur = len(x) / SR
            if dur > room:
                tempo = min(MAX_SPEEDUP, dur / room)
                x = trim(decode(p, tempo))
                if dur / room > MAX_SPEEDUP:
                    slow.append(f"{l['i'] + 1:02d} ({dur:.1f} s for {room:.1f} s)")
            x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.1        # every line at the same loudness before the final level
            s = int(l["start"] * SR)
            voice[s:s + len(x)] += x[: max(0, n - s)]
        if slow:
            print("read these lines again a little faster:", "; ".join(slow))
    else:
        x = decode(src)
        voice[: min(n, len(x))] = x[:n]
    music, sfx = read_stereo(HERE / "build" / "music.wav")[:n], read_stereo(HERE / "build" / "sfx.wav")[:n]
    mix = np.stack([voice, voice], 1)[: len(music)] + 0.4 * music + 0.6 * sfx
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
