#!/usr/bin/env bash
# Brings up the whole Reach simulation with one command: Webots (physical
# robot), par_bridge.py (the extern controller bridging it to Pulse), and
# CollectiveOS (the real computer-use agent). Previously this was three-plus
# manually-run terminals with hand-set env vars - this script is that,
# scripted and made idempotent, not a new capability.
#
# What it does NOT do: grant macOS permissions. Screen Recording (for
# CollectiveOS to see your screen) and Accessibility (for its UI-inspection
# calls) must be approved once by you in System Settings > Privacy &
# Security, the first time each is needed - no script can click that dialog
# for you.
#
# Usage:
#   ./scripts/run_simulation.sh              # start everything, leave running
#   ./scripts/run_simulation.sh --demo       # also run examples/webots_loop.py
#   ./scripts/run_simulation.sh --stop       # stop everything this script started
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$REACH_ROOT/.sim_state"
mkdir -p "$STATE_DIR"

WEBOTS_APP="${WEBOTS_APP:-/Applications/Webots.app}"
COS_PORT="${COS_PORT:-8000}"
BRIDGE_PORT="${BRIDGE_PORT:-6001}"

log() { printf '[run_simulation] %s\n' "$1"; }
die() { printf '[run_simulation] ERROR: %s\n' "$1" >&2; exit 1; }

# -- stop mode --------------------------------------------------------------
if [[ "${1:-}" == "--stop" ]]; then
    # SIGKILL, not SIGTERM: Webots does not exit promptly on SIGTERM in this
    # environment, and - more importantly - a graceful exit makes it re-save
    # par_arena.wbt with whatever transient runtime state it's in (the
    # robot's live position, camera pan from manual navigation, internal
    # joint state), clobbering the authored default arena. SIGKILL can't be
    # caught, so no such save ever happens.
    for name in webots par_bridge collectiveos; do
        pidfile="$STATE_DIR/$name.pid"
        if [[ -f "$pidfile" ]]; then
            pid="$(cat "$pidfile")"
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
                log "stopped $name (pid $pid)"
            fi
            rm -f "$pidfile"
        fi
    done
    # par_bridge and CollectiveOS's own child processes (uvicorn's reload
    # workers, if any) don't always share the captured pid - belt-and-braces
    # cleanup by pattern, scoped tightly enough not to catch unrelated work.
    pkill -9 -f "MacOS/webots.*par_arena.wbt" 2>/dev/null || true
    pkill -9 -f "par_bridge/par_bridge.py" 2>/dev/null || true
    pkill -9 -f "uvicorn src.api:app --port $COS_PORT" 2>/dev/null || true
    exit 0
fi

# -- preflight ---------------------------------------------------------------
[[ -d "$WEBOTS_APP" ]] || die "Webots not found at $WEBOTS_APP (install it, or set WEBOTS_APP). See webots/README.md."
[[ -f "$REACH_ROOT/CollectiveOS/.env" ]] || die "CollectiveOS/.env not found - needed for GEMINI_API_KEY/API_TOKEN."

API_TOKEN="$(grep '^API_TOKEN=' "$REACH_ROOT/CollectiveOS/.env" | cut -d= -f2)"
[[ -n "$API_TOKEN" ]] || die "API_TOKEN is empty in CollectiveOS/.env."

if command -v pg_isready >/dev/null && ! pg_isready >/dev/null 2>&1; then
    log "WARNING: Postgres doesn't look reachable - CollectiveOS will still start (routines/checkpointing degrade gracefully), but see CollectiveOS/README for full setup."
fi

# -- venvs (created once, reused after) --------------------------------------
PULSE_VENV="$REACH_ROOT/Pulse/.venv"
if [[ ! -d "$PULSE_VENV" ]]; then
    log "creating Pulse venv (first run only)..."
    python3 -m venv "$PULSE_VENV"
    "$PULSE_VENV/bin/pip" install -q -e "$REACH_ROOT/Pulse[dev,webots]"
fi

COS_VENV="$REACH_ROOT/CollectiveOS/.venv"
if [[ ! -d "$COS_VENV" ]]; then
    log "creating CollectiveOS venv (first run only)..."
    python3 -m venv "$COS_VENV"
    "$COS_VENV/bin/pip" install -q -r "$REACH_ROOT/CollectiveOS/requirements.txt"
fi

export WEBOTS_HOME="$WEBOTS_APP"
export PYTHONPATH="$WEBOTS_HOME/Contents/lib/controller/python:${PYTHONPATH:-}"

# -- 1. Webots ----------------------------------------------------------------
if [[ -f "$STATE_DIR/webots.pid" ]] && kill -0 "$(cat "$STATE_DIR/webots.pid")" 2>/dev/null; then
    log "Webots already running (pid $(cat "$STATE_DIR/webots.pid"))"
else
    log "starting Webots..."
    nohup "$WEBOTS_APP/Contents/MacOS/webots" --mode=realtime --stdout --stderr \
        "$REACH_ROOT/webots/worlds/par_arena.wbt" > "$STATE_DIR/webots.log" 2>&1 &
    echo $! > "$STATE_DIR/webots.pid"
    sleep 6
    if grep -q "^ERROR" "$STATE_DIR/webots.log" 2>/dev/null; then
        log "Webots reported errors - check $STATE_DIR/webots.log"
    fi
fi

# -- 2. par_bridge.py -----------------------------------------------------------
if [[ -f "$STATE_DIR/par_bridge.pid" ]] && kill -0 "$(cat "$STATE_DIR/par_bridge.pid")" 2>/dev/null; then
    log "par_bridge already running (pid $(cat "$STATE_DIR/par_bridge.pid"))"
else
    log "starting par_bridge.py (waits for Webots' simulation to be running)..."
    nohup "$PULSE_VENV/bin/python3" "$REACH_ROOT/webots/controllers/par_bridge/par_bridge.py" \
        > "$STATE_DIR/par_bridge.log" 2>&1 &
    echo $! > "$STATE_DIR/par_bridge.pid"
fi

# -- 3. CollectiveOS ------------------------------------------------------------
if [[ -f "$STATE_DIR/collectiveos.pid" ]] && kill -0 "$(cat "$STATE_DIR/collectiveos.pid")" 2>/dev/null; then
    log "CollectiveOS already running (pid $(cat "$STATE_DIR/collectiveos.pid"))"
else
    log "starting CollectiveOS on port $COS_PORT..."
    # Not wrapped in `(cd ... && cmd &)` - $! there captures the subshell's
    # pid, not the actual python process, which broke --stop. cd in the
    # current shell and back, so $! is the real pid.
    pushd "$REACH_ROOT/CollectiveOS" >/dev/null
    PYTHONUNBUFFERED=1 nohup "$COS_VENV/bin/python3" \
        -m uvicorn src.api:app --port "$COS_PORT" > "$STATE_DIR/collectiveos.log" 2>&1 &
    echo $! > "$STATE_DIR/collectiveos.pid"
    popd >/dev/null
fi

log "waiting for the bridge (ws://localhost:$BRIDGE_PORT) and CollectiveOS (http://localhost:$COS_PORT)..."
for i in $(seq 1 30); do
    bridge_up=0; cos_up=0
    grep -q "listening on ws" "$STATE_DIR/par_bridge.log" 2>/dev/null && bridge_up=1
    curl -s -o /dev/null "http://localhost:$COS_PORT/" 2>/dev/null && cos_up=1
    [[ "$bridge_up" == 1 && "$cos_up" == 1 ]] && break
    sleep 2
done

if [[ "$bridge_up" != 1 ]]; then
    log "par_bridge isn't listening yet - it waits for Webots' simulation to actually be running, not just loaded. Check $STATE_DIR/par_bridge.log and $STATE_DIR/webots.log."
fi
if [[ "$cos_up" != 1 ]]; then
    log "CollectiveOS isn't responding yet. Check $STATE_DIR/collectiveos.log."
fi
[[ "$bridge_up" == 1 && "$cos_up" == 1 ]] && log "both up. Robot can now move (via par_bridge) and delegate (via CollectiveOS)."

echo
log "Webots window is open on your screen - the e-puck robot and the arena (including the 'laptop' prop) are there to look at directly."
log "Logs: $STATE_DIR/{webots,par_bridge,collectiveos}.log"
log "Stop everything with: ./scripts/run_simulation.sh --stop"

# -- optional demo run --------------------------------------------------------
if [[ "${1:-}" == "--demo" ]]; then
    log "running examples/webots_loop.py (drives the arena, then delegates a real use_computer task)..."
    export COLLECTIVEOS_WS_URL="ws://localhost:$COS_PORT/robot/ws"
    export COLLECTIVEOS_API_TOKEN="$API_TOKEN"
    (cd "$REACH_ROOT/Pulse" && "$PULSE_VENV/bin/python3" examples/webots_loop.py)
fi
