#!/usr/bin/env bash
# The logging loop of .github/workflows/logger.yml: one snapshot every 10 minutes, committed and pushed each time.
#
# The loop ends in one of three ways and tells the workflow what to do next through $GITHUB_OUTPUT:
#   time is up            next=yes streak=0    the successor continues the chain
#   the API refuses us    next=yes streak=N    the YouBike API answers some runners with HTTP 503 for as long as
#                                              they live (seven whole runs were lost that way before this check
#                                              existed); a new run gets a new runner, so give up at once
#   an older loop exists  next=no              two loops were started side by side; the younger one stands down
#
# Environment (set by the workflow): GITHUB_RUN_ID, GITHUB_REF_NAME, GITHUB_OUTPUT, LOOP_MINUTES,
#   PARENT  id of the run that dispatched this one (empty for a cron or manual start)
#   STREAK  how many runs before this one were refused by the API without a single successful fetch
# Test hooks: STEP_SECONDS (default 600), FETCH_CMD, STATE_CMD, REPLAY_CMD.
set -u

LOOP_MINUTES=${LOOP_MINUTES:-340}
STEP_SECONDS=${STEP_SECONDS:-600}
PARENT=${PARENT:-}
STREAK=${STREAK:-0}
BRANCH=${GITHUB_REF_NAME:-main}
ME=${GITHUB_RUN_ID:-0}
FETCH_CMD=${FETCH_CMD:-python3 logger/fetch_youbike.py}
STATE_CMD=${STATE_CMD:-python3 analysis/code/demo_state.py data analysis/results docs/state.json --trucks 1}
REPLAY_CMD=${REPLAY_CMD:-python3 analysis/code/demo_replays.py data analysis/results docs --days 7 --max-new 1}
case "$STREAK" in ''|*[!0-9]*) STREAK=0 ;; esac

git config user.name  "youbike-logger"
git config user.email "youbike-logger@users.noreply.github.com"

fetched=0
snapshot() {
  fetched=1
  timeout 300 $FETCH_CMD || fetched=0
  if [ "$fetched" = 1 ]; then
    # demo state for docs/index.html: stockout probabilities, the after-class forecast and the truck plan (about 5 s)
    timeout 300 $STATE_CMD || true
    # replays of the last 7 complete days for the page's replay menu (builds at most one missing day per call)
    timeout 600 $REPLAY_CMD || true
  fi
  git add -A data docs
  if git diff --cached --quiet; then return 1; fi
  local stamp subject
  stamp=$(TZ=Asia/Taipei date +'%Y-%m-%d %H:%M')
  if [ "$fetched" = 1 ]; then subject="log $stamp"; else subject="fetch failed $stamp"; fi
  # the run id in the body lets two loops recognise each other (see rival below)
  git commit -q -m "$subject" -m "run: ${ME}"
}

# Did a loop that started before us (smaller run id, not our parent, which is ending) commit since we last looked?
# Returns 0 = yes, 1 = no, 2 = the remote could not be read.
seen=$(git rev-parse HEAD)
rival() {
  timeout 120 git fetch -q origin "$BRANCH" 2>/dev/null || return 2
  local ids id
  ids=$(git log --format=%b "${seen}..FETCH_HEAD" 2>/dev/null | sed -n 's/^run: \([0-9][0-9]*\)$/\1/p' | sort -u)
  seen=$(git rev-parse FETCH_HEAD)
  for id in $ids; do
    if [ "$id" != "$ME" ] && [ "$id" != "${PARENT:-none}" ] && [ "$id" -lt "$ME" ]; then
      echo "run $id is logging too and started first: standing down"
      return 0
    fi
  done
  return 1
}

end=$(( SECONDS + LOOP_MINUTES * 60 ))
ok=0          # has this runner fetched the API successfully at least once?
fails=0       # failed fetches in a row
next=yes
while [ "$SECONDS" -lt "$end" ]; do
  if rival; then next=no; break; fi
  if snapshot; then
    for attempt in 1 2 3; do
      timeout 120 git push -q origin "HEAD:${BRANCH}" && break
      # Someone pushed meanwhile. A rebase would conflict (docs/state.json is rewritten by every snapshot), so drop
      # our commit, move to the remote tip and take the snapshot again on top of it.
      echo "push failed (attempt $attempt): resetting to the remote and taking the snapshot again"
      rival; rc=$?
      if [ "$rc" = 0 ]; then next=no; break 2; fi
      if [ "$rc" = 1 ]; then git reset -q --hard FETCH_HEAD; fi
      sleep 5
      if [ "$rc" = 1 ]; then snapshot || true; fi
    done
  fi

  if [ "$fetched" = 1 ]; then ok=1; fails=0; else fails=$(( fails + 1 )); fi
  if [ "$ok" = 1 ]; then limit=2                     # this runner worked before: allow one hiccup
  elif [ "$STREAK" -ge 3 ]; then limit=3             # several runners in a row were refused: the API itself is down, slow down
  else limit=1; fi                                   # a fresh runner that is refused: hand over at once
  if [ "$fails" -ge "$limit" ]; then
    echo "the API refused $fails fetch(es) in a row: handing over to a new runner"
    break
  fi

  now=$(date +%s)
  wake=$(( (now / STEP_SECONDS + 1) * STEP_SECONDS ))   # next hh:00, hh:10, hh:20, ...
  sleep $(( wake - now ))
done

if [ "$ok" = 1 ]; then streak=0; else streak=$(( STREAK + 1 )); fi
echo "loop finished: next=$next streak=$streak"
{ echo "next=$next"; echo "streak=$streak"; } >> "${GITHUB_OUTPUT:-/dev/null}"
