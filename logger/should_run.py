#!/usr/bin/env python3
"""Decide whether this workflow run should start the logging loop. Prints "run" or "skip".

A run that was dispatched by the run before it (it carries that run's id as its parent) is the chain itself and
always runs. Every other start (the backup cron, a manual "Run workflow") runs only when nobody is logging.

"Nobody is logging" is read from the repository, not from the Actions API: a live loop writes either
data/latest.json (a snapshot) or a line in data/errors.log (a failed fetch) every 10 minutes and pushes it, so the
newest of the two timestamps in a fresh checkout is the loop's heartbeat. The API was dropped as the signal for two
reasons seen in practice: a run whose runner died stays "in_progress" for up to two hours, which kept the backup
away, and a failed or incomplete run list read as "no other run", which started a second loop next to a live one.

Two loops can still start side by side (two backups at once after an outage). The loop itself settles that: every
commit carries its run id, and the younger run stands down when it sees an older run's commits (see logger.yml).

Usage: should_run.py [--data DIR] [--max-age MINUTES] [<parent run id>]
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

args = sys.argv[1:]


def option(name, default):
    if name in args:
        i = args.index(name)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


DATA = Path(option("--data", "data"))
MAX_AGE = float(option("--max-age", "25"))          # minutes without a heartbeat before a backup run takes over
parent = args[0] if args and args[0].isdigit() else ""


def heartbeat():
    """Newest time at which a loop wrote something, or None."""
    stamps = []
    try:
        stamps.append(datetime.fromisoformat(json.loads((DATA / "latest.json").read_text(encoding="utf-8"))["fetched_at"]))
    except Exception:  # noqa: BLE001 - a missing or broken file simply gives no heartbeat
        pass
    try:
        last = (DATA / "errors.log").read_text(encoding="utf-8").strip().splitlines()[-1]
        stamps.append(datetime.fromisoformat(last.split(" ", 1)[0]))
    except Exception:  # noqa: BLE001
        pass
    return max(stamps) if stamps else None


if parent:
    print(f"dispatched by run {parent}: continuing the chain", file=sys.stderr)
    print("run")
    sys.exit(0)

beat = heartbeat()
now = datetime.now(timezone.utc)
if beat is None:
    print("no heartbeat found: starting", file=sys.stderr)
    print("run")
elif now - beat > timedelta(minutes=MAX_AGE):
    print(f"last heartbeat {beat.isoformat()} is {(now - beat).total_seconds() / 60:.0f} min old: taking over", file=sys.stderr)
    print("run")
else:
    print(f"last heartbeat {beat.isoformat()} is {(now - beat).total_seconds() / 60:.0f} min old: a loop is alive", file=sys.stderr)
    print("skip")
