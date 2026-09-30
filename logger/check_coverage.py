#!/usr/bin/env python3
"""Summarise what the logger has collected so far.

Usage:  python3 logger/check_coverage.py [DATA_DIR]

Prints one line per day: number of snapshots, stations per snapshot, first and last
fetch time, the largest gap between consecutive snapshots, and how many rows were
stockouts (bikes == 0 while status == 1). Standard library only.
"""
import csv
import gzip
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

data_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
daily_dir = data_dir / "kaohsiung"
files = sorted(list(daily_dir.glob("*.csv")) + list(daily_dir.glob("*.csv.gz")))
if not files:
    print(f"no daily files under {daily_dir}")
    sys.exit(0)

print(f"{'day':<10} {'runs':>5} {'stations':>8} {'first':>8} {'last':>8} {'max gap':>8} {'stockout rows':>14}")
total_rows = 0
for path in files:
    opener = gzip.open if path.suffix == ".gz" else open
    day = path.name.split(".")[0]
    times = defaultdict(int)
    stockouts = rows = 0
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rows += 1
            times[r["time"]] += 1
            if r["bikes"] == "0" and r["status"] == "1":
                stockouts += 1
    stamps = sorted(datetime.strptime(t, "%H:%M:%S") for t in times)
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(stamps, stamps[1:])]
    per_run = sorted(times.values())
    stations = f"{per_run[0]}" if per_run[0] == per_run[-1] else f"{per_run[0]}-{per_run[-1]}"
    print(f"{day:<10} {len(stamps):>5} {stations:>8} {stamps[0]:%H:%M:%S} {stamps[-1]:%H:%M:%S} "
          f"{(max(gaps) if gaps else 0):>6.0f}m {stockouts:>8} / {rows}")
    total_rows += rows

errors = data_dir / "errors.log"
n_err = len(errors.read_text(encoding="utf-8").splitlines()) if errors.exists() else 0
print(f"\n{len(files)} days, {total_rows} rows, {n_err} failed fetches logged")
