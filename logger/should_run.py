#!/usr/bin/env python3
"""Decide whether this workflow run should start the logging loop.

Reads the JSON of `gh api .../actions/workflows/logger.yml/runs?status=in_progress`
from stdin and prints "run" or "skip".

Rule: skip when another run of this workflow is already looping. A run that is not
us and not our parent (the run that dispatched us, which is about to finish) counts
as looping when it has a smaller run id (it was created first) or has been running
for more than 90 seconds (it already passed this check). Both runs apply the same
rule, so exactly one of two simultaneous starts proceeds.

Usage: should_run.py <own run id> [<parent run id>]
"""
import json
import sys
from datetime import datetime, timezone

me = int(sys.argv[1])
parent = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
runs = json.load(sys.stdin).get("workflow_runs", [])
now = datetime.now(timezone.utc)

for r in runs:
    rid = r.get("id")
    if rid in (me, parent) or r.get("status") != "in_progress":
        continue
    started = r.get("run_started_at") or r.get("created_at") or ""
    try:
        age = (now - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds()
    except ValueError:
        age = 0
    if rid < me or age > 90:
        print(f"skip: run {rid} is already logging", file=sys.stderr)
        print("skip")
        sys.exit(0)
print("run")
