"""Keep replays of the last complete days for the demo page.

Usage: python demo_replays.py DATA_DIR RESULTS_DIR DOCS_DIR [--days 7] [--max-new 1]

For each of the last --days complete days (yesterday and earlier, local time) that has a logger file, makes sure
docs/replay_YYYY-MM-DD.json exists (built with demo_state.py --replay; at most --max-new per call so that one
logger loop iteration stays short), removes older replay files and writes docs/replays.json, the list the page
offers in its replay menu (newest first).
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA, RESULTS, DOCS = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
DAYS, MAX_NEW = ARG("--days", 7, int), ARG("--max-new", 1, int)
TZ = timezone(timedelta(hours=8))
today = datetime.now(TZ).date()
wanted = [(today - timedelta(days=k)).strftime("%Y-%m-%d") for k in range(1, DAYS + 1)]
wanted = [d for d in wanted if (DATA / "kaohsiung" / f"{d}.csv").exists() or (DATA / "kaohsiung" / f"{d}.csv.gz").exists()]
made = 0
for d in wanted:
    out = DOCS / f"replay_{d}.json"
    if out.exists() or made >= MAX_NEW:
        continue
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "demo_state.py"), str(DATA), str(RESULTS), str(out), "--replay", d, "--trucks", "1"],
                       capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-300:])
    made += 1
for f in DOCS.glob("replay_*.json"):
    if f.stem[7:] not in wanted:
        f.unlink()
have = sorted([d for d in wanted if (DOCS / f"replay_{d}.json").exists()], reverse=True)
index = DOCS / "replays.json"
try:
    unchanged = json.loads(index.read_text(encoding="utf-8")).get("days") == have
except Exception:  # noqa: BLE001 - a missing or broken index is simply rewritten
    unchanged = False
if not unchanged:   # rewritten only when the list of days changes, so a snapshot without news leaves it alone
    index.write_text(json.dumps({"days": have, "generated_at": datetime.now(TZ).isoformat(timespec="seconds")}), encoding="utf-8")
print("replays:", have)
