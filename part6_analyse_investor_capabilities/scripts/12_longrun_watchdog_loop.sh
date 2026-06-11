#!/usr/bin/env bash
set -u

REPO_ROOT="/home/benl66/PitchBook_project"
INTERVAL_SECONDS="${PART6_WATCHDOG_INTERVAL_SECONDS:-1800}"
LOG_FILE="$REPO_ROOT/part6_analyse_investor_capabilities/agent_runs/crypto_investor_watchdog_loop.log"
WATCHDOG="$REPO_ROOT/part6_analyse_investor_capabilities/scripts/11_longrun_watchdog.py"

cd "$REPO_ROOT" || exit 1
mkdir -p "$(dirname "$LOG_FILE")"

while true; do
  printf '%s watchdog_loop_tick interval_seconds=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$INTERVAL_SECONDS" >> "$LOG_FILE"
  /usr/bin/python3 "$WATCHDOG" --restart-mode foreground --complete-exit-code 10 >> "$LOG_FILE" 2>&1
  exit_code="$?"
  if [ "$exit_code" = "10" ]; then
    printf '%s watchdog_loop_complete exiting=true\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG_FILE"
    exit 0
  fi
  sleep "$INTERVAL_SECONDS"
done
