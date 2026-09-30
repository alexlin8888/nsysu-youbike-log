#!/usr/bin/env python3
"""Snapshot YouBike 2.0 station inventory around NSYSU into daily CSV files.

Intended to run every 10 minutes from GitHub Actions (.github/workflows/logger.yml).
Standard library only; no third-party packages.

Outputs (all paths relative to DATA_DIR, default ./data):
  kaohsiung/YYYY-MM-DD.csv   one row per logged station per run, local (UTC+8) date
  kaohsiung/YYYY-MM-DD.csv.gz  finished days are gzipped on the first run of the next day
  stations.csv               metadata for every station in AREA_CODES (rewritten only when changed)
  latest.json                the most recent snapshot of the logged stations (for the demo page)
  errors.log                 one line per failed fetch

Row format of the daily CSV:
  time    HH:MM:SS local time at which the API was fetched
  sno     station number (e.g. 501208097)
  bikes   available bikes (available_spaces, all types)
  ebikes  electric bikes among them (available_spaces_detail.eyb)
  empty   empty docks (empty_spaces)
  status  API status field (1 = in service, 2 = out of service; 0/0 is then not a stockout)
  age     minutes between the station's own updated_at and the fetch time (staleness)

Environment variables:
  AREA_CODES  comma-separated YouBike area codes to keep, default "12" (Kaohsiung)
  CENTER      "lat,lng" of the reference point, default NSYSU (22.6273,120.2658)
  RADIUS_KM   log only stations within this distance of CENTER; 0 = all stations in AREA_CODES
  DATA_DIR    output directory, default "data"
"""
import csv
import gzip
import json
import math
import os
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://apis.youbike.com.tw/json/station-yb2.json"
TZ = timezone(timedelta(hours=8))  # Asia/Taipei has no DST
AREA_CODES = {c.strip() for c in os.environ.get("AREA_CODES", "12").split(",") if c.strip()}
CENTER = tuple(float(x) for x in os.environ.get("CENTER", "22.6273,120.2658").split(","))
RADIUS_KM = float(os.environ.get("RADIUS_KM", "5"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
DAILY_DIR = DATA_DIR / "kaohsiung"
ROW_FIELDS = ["time", "sno", "bikes", "ebikes", "empty", "status", "age"]
STATION_FIELDS = ["sno", "name_tw", "name_en", "district", "lat", "lng", "capacity", "dist_m", "logged"]


def fetch_json(retries=3, backoff=10):
    """Download the station list; retry a few times before giving up."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, headers={"User-Agent": "nsysu-youbike-logger/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.load(resp)
            if isinstance(payload, dict):  # defensive: some endpoints wrap the list
                payload = payload.get("retVal") or next(iter(payload.values()))
            if not isinstance(payload, list) or not payload:
                raise ValueError("unexpected payload shape")
            return payload
        except Exception as exc:  # noqa: BLE001 - we want to log anything and retry
            last_err = exc
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} attempts: {last_err}")


def dist_m(lat, lng):
    """Equirectangular distance from CENTER in metres (fine for a few km)."""
    p = math.pi / 180
    x = (lat - CENTER[0]) * p
    y = (lng - CENTER[1]) * p * math.cos((lat + CENTER[0]) / 2 * p)
    return 6371000 * math.hypot(x, y)


def parse_age(updated_at, now):
    """Minutes between the station's updated_at (local time string) and now."""
    try:
        upd = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
        return max(0, int((now - upd).total_seconds() // 60))
    except Exception:  # noqa: BLE001
        return ""


def record_error(msg, now):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = DATA_DIR / "errors.log"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{now.isoformat()} {msg}\n")
    # Fail the job (which triggers a GitHub e-mail) only when three fetches in a row failed.
    recent = 0
    for line in log.read_text(encoding="utf-8").splitlines()[-3:]:
        try:
            ts = datetime.fromisoformat(line.split(" ", 1)[0])
            if (now - ts) <= timedelta(minutes=35):
                recent += 1
        except Exception:  # noqa: BLE001
            pass
    return recent >= 3


def compact_old_days(today_name):
    """gzip every finished day's CSV so the repository checkout stays small."""
    if not DAILY_DIR.exists():
        return
    for csv_path in sorted(DAILY_DIR.glob("*.csv")):
        if csv_path.stem >= today_name:
            continue
        gz_path = csv_path.with_suffix(".csv.gz")
        with csv_path.open("rb") as src, gzip.open(gz_path, "wb", compresslevel=9) as dst:
            shutil.copyfileobj(src, dst)
        csv_path.unlink()
        print(f"compacted {csv_path.name} -> {gz_path.name}")


def write_if_changed(path, text):
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main():
    now = datetime.now(TZ).replace(microsecond=0)
    try:
        stations = fetch_json()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1 if record_error(str(exc), now) else 0)

    area = [s for s in stations if str(s.get("area_code")) in AREA_CODES]
    if not area:
        print("ERROR no stations matched AREA_CODES", file=sys.stderr)
        sys.exit(1 if record_error("no stations matched AREA_CODES", now) else 0)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    today_name = now.strftime("%Y-%m-%d")
    compact_old_days(today_name)

    # ---- station metadata (all stations of the area, flag the logged ones) ----
    meta_rows, logged = [], []
    for s in area:
        try:
            lat, lng = float(s["lat"]), float(s["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        d = dist_m(lat, lng)
        keep = RADIUS_KM <= 0 or d <= RADIUS_KM * 1000
        meta_rows.append({
            "sno": s.get("station_no", ""),
            "name_tw": s.get("name_tw", ""),
            "name_en": s.get("name_en", ""),
            "district": s.get("district_tw", ""),
            "lat": f"{lat:.6f}",
            "lng": f"{lng:.6f}",
            "capacity": s.get("parking_spaces", ""),
            "dist_m": int(round(d)),
            "logged": int(keep),
        })
        if keep:
            logged.append(s)
    meta_rows.sort(key=lambda r: r["sno"])
    buf = []
    w = csv.DictWriter(_ListWriter(buf), fieldnames=STATION_FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(meta_rows)
    if write_if_changed(DATA_DIR / "stations.csv", "".join(buf)):
        print("stations.csv updated")

    # ---- append today's rows ----
    daily = DAILY_DIR / f"{today_name}.csv"
    new_file = not daily.exists()
    t = now.strftime("%H:%M:%S")
    with daily.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new_file:
            w.writerow(ROW_FIELDS)
        for s in sorted(logged, key=lambda s: s.get("station_no", "")):
            detail = s.get("available_spaces_detail") or {}
            w.writerow([
                t,
                s.get("station_no", ""),
                s.get("available_spaces", ""),
                detail.get("eyb", ""),
                s.get("empty_spaces", ""),
                s.get("status", ""),
                parse_age(s.get("updated_at", ""), now),
            ])

    # ---- latest snapshot for the demo page ----
    latest = {
        "fetched_at": now.isoformat(),
        "center": CENTER,
        "radius_km": RADIUS_KM,
        "stations": [
            {
                "sno": s.get("station_no"),
                "bikes": s.get("available_spaces"),
                "ebikes": (s.get("available_spaces_detail") or {}).get("eyb"),
                "empty": s.get("empty_spaces"),
                "status": s.get("status"),
                "updated_at": s.get("updated_at"),
            }
            for s in sorted(logged, key=lambda s: s.get("station_no", ""))
        ],
    }
    (DATA_DIR / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    empties = sum(1 for s in logged if s.get("available_spaces") == 0 and s.get("status") == 1)
    print(f"{now.isoformat()} logged {len(logged)}/{len(area)} stations to {daily.name}; {empties} empty")


class _ListWriter:
    """Minimal file-like object that collects csv output into a list of strings."""

    def __init__(self, buf):
        self.buf = buf

    def write(self, s):
        self.buf.append(s)


if __name__ == "__main__":
    main()
