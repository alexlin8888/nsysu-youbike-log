"""Render the final video: every scene to its own mp4, then join, add the sound and burn the subtitles.

Usage: python video/render.py [scene ...]     (no argument renders every scene; needs the server of preview.py)

Writes video/out/ (not committed):
  scenes/<id>.mp4          one file per scene, 1920x1080, 30 fps, H.264
  beat_the_bell_clean.mp4  the joined scenes with music and effects, no subtitles (for YouTube with the .srt)
  beat_the_bell.mp4        the same with the subtitles burnt in
A frame is drawn by engine/stage.html from the scene and the time alone, so any scene can be rendered again by itself.
"""
import base64
import json
import os
import subprocess
import sys
import time
from multiprocessing import Process
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SC = OUT / "scenes"
FPS = 30
CUES = json.loads((HERE / "build" / "cues.json").read_text())
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def frames(s):
    """Frame range of a scene on the global timeline, so the scenes add up to the length of the sound exactly."""
    a = round(s["start"] * FPS)
    b = round((s["start"] + s["dur"]) * FPS)
    return a, b


def render(ids):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        for sid in ids:
            s = next(x for x in CUES["scenes"] if x["id"] == sid)
            a, z = frames(s)
            pg.goto(f"http://127.0.0.1:8771/engine/stage.html?scene={sid}")
            pg.wait_for_function("window.READY === true", timeout=60000)
            tmp, dst = SC / f"{sid}.part.mp4", SC / f"{sid}.mp4"
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-", *ENC, str(tmp)], stdin=subprocess.PIPE)
            t0 = time.time()
            for f in range(a, z):
                data = pg.evaluate(f"frameJpeg({f / FPS - s['start']:.5f}, 0.92)")
                ff.stdin.write(base64.b64decode(data.split(",", 1)[1]))
            ff.stdin.close()
            if ff.wait() != 0:
                raise SystemExit(f"ffmpeg failed on {sid}")
            os.replace(tmp, dst)
            print(f"{sid}: {z - a} frames in {time.time() - t0:.0f} s", flush=True)
            if errs:
                print("page errors:", errs[:3], flush=True)
        b.close()


def main():
    SC.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[1:] or [s["id"] for s in CUES["scenes"]]
    # two workers, scenes dealt out longest first so both finish at about the same time
    order = sorted(ids, key=lambda i: -next(s["dur"] for s in CUES["scenes"] if s["id"] == i))
    jobs, load = [[], []], [0.0, 0.0]
    for i in order:
        k = load.index(min(load))
        jobs[k].append(i)
        load[k] += next(s["dur"] for s in CUES["scenes"] if s["id"] == i)
    ps = [Process(target=render, args=(j,)) for j in jobs if j]
    [p.start() for p in ps]
    [p.join() for p in ps]
    if any(p.exitcode for p in ps):
        raise SystemExit("a render worker failed")
    missing = [s["id"] for s in CUES["scenes"] if not (SC / f"{s['id']}.mp4").exists()]
    if missing:
        print("not joined yet, missing:", " ".join(missing))
        return
    # join, add the sound, burn the subtitles
    lst = OUT / "scenes.txt"
    lst.write_text("".join(f"file 'scenes/{s['id']}.mp4'\n" for s in CUES["scenes"]))
    run = lambda *a: subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)
    run("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(OUT / "silent.mp4"))
    run("-i", str(OUT / "silent.mp4"), "-i", str(HERE / "build" / "mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str(OUT / "beat_the_bell_clean.mp4"))
    ass = HERE / "build" / "subtitles.ass"
    run("-i", str(OUT / "beat_the_bell_clean.mp4"), "-vf", f"ass={ass}", *ENC, "-c:a", "copy", str(OUT / "beat_the_bell.mp4"))
    print("done:", OUT / "beat_the_bell.mp4")


if __name__ == "__main__":
    main()
