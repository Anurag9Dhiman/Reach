#!/usr/bin/env bash
# Brings up the whole Reach simulation with one command: the MuJoCo bridge
# (Franka Panda arm in a scripted arena) and CollectiveOS (the real
# computer-use agent). Replaces the earlier Webots+par_bridge+computer_arm
# three-process launcher - MuJoCo is a library (not an application), so the
# bridge is one Python process that owns the physics model, the viewer,
# and the WebSocket server all in one.
#
# What it does NOT do: grant macOS permissions. Screen Recording (for
# CollectiveOS to see your screen) and Accessibility (for its UI-inspection
# calls) must be approved once by you in System Settings > Privacy &
# Security, the first time each is needed - no script can click that dialog
# for you.
#
# Usage:
#   ./scripts/run_simulation.sh              # start everything, leave running
#   ./scripts/run_simulation.sh --demo       # also run examples/mujoco_loop.py
#   ./scripts/run_simulation.sh --headless   # bridge without the viewer window
#                                            # (CI / unit tests; no `mjpython` needed)
#   ./scripts/run_simulation.sh --stop       # stop everything this script started
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$REACH_ROOT/.sim_state"
mkdir -p "$STATE_DIR"

COS_PORT="${COS_PORT:-8000}"
MUJOCO_PORT="${MUJOCO_PORT:-6003}"

log() { printf '[run_simulation] %s\n' "$1"; }
die() { printf '[run_simulation] ERROR: %s\n' "$1" >&2; exit 1; }

# Parse flags
HEADLESS=0
DEMO=0
STOP=0
for arg in "$@"; do
    case "$arg" in
        --headless) HEADLESS=1 ;;
        --demo) DEMO=1 ;;
        --stop) STOP=1 ;;
    esac
done

# -- stop mode --------------------------------------------------------------
if [[ "$STOP" == 1 ]]; then
    for name in mujoco_bridge collectiveos; do
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
    # Belt-and-braces by pattern, scoped tightly enough not to catch unrelated work.
    pkill -9 -f "mujoco/bridge/mujoco_bridge.py" 2>/dev/null || true
    pkill -9 -f "uvicorn src.api:app --port $COS_PORT" 2>/dev/null || true
    exit 0
fi

# -- preflight ---------------------------------------------------------------
[[ -f "$REACH_ROOT/CollectiveOS/.env" ]] || die "CollectiveOS/.env not found - needed for GEMINI_API_KEY/API_TOKEN."

API_TOKEN="$(grep '^API_TOKEN=' "$REACH_ROOT/CollectiveOS/.env" | cut -d= -f2)"
[[ -n "$API_TOKEN" ]] || die "API_TOKEN is empty in CollectiveOS/.env."

if command -v pg_isready >/dev/null && ! pg_isready >/dev/null 2>&1; then
    log "WARNING: Postgres doesn't look reachable - CollectiveOS will still start (routines/checkpointing degrade gracefully), but see CollectiveOS/README for full setup."
fi

# -- venvs (created once, reused after) --------------------------------------
PULSE_VENV="$REACH_ROOT/Pulse/.venv"
if [[ ! -d "$PULSE_VENV" ]]; then
    log "creating Pulse venv (first run only, installs mujoco + Menagerie, takes ~2 min first time only)..."
    python3 -m venv "$PULSE_VENV"
    "$PULSE_VENV/bin/pip" install -q -e "$REACH_ROOT/Pulse[dev,mujoco]"
fi

COS_VENV="$REACH_ROOT/CollectiveOS/.venv"
if [[ ! -d "$COS_VENV" ]]; then
    log "creating CollectiveOS venv (first run only)..."
    python3 -m venv "$COS_VENV"
    "$COS_VENV/bin/pip" install -q -r "$REACH_ROOT/CollectiveOS/requirements.txt"
fi

# -- 1. MuJoCo bridge --------------------------------------------------------
# Single process (physics loop + WS server + viewer). On macOS the
# interactive viewer requires `mjpython`, not plain `python`; headless mode
# works with either. We default to interactive; pass --headless to skip the
# window.
if [[ -f "$STATE_DIR/mujoco_bridge.pid" ]] && kill -0 "$(cat "$STATE_DIR/mujoco_bridge.pid")" 2>/dev/null; then
    log "mujoco_bridge already running (pid $(cat "$STATE_DIR/mujoco_bridge.pid"))"
else
    if [[ "$HEADLESS" == 1 ]]; then
        log "starting mujoco_bridge.py (headless, no viewer window)..."
        nohup "$PULSE_VENV/bin/python3" \
            "$REACH_ROOT/mujoco/bridge/mujoco_bridge.py" --headless \
            > "$STATE_DIR/mujoco_bridge.log" 2>&1 &
    else
        log "starting mujoco_bridge.py (interactive viewer via mjpython)..."
        nohup "$PULSE_VENV/bin/mjpython" \
            "$REACH_ROOT/mujoco/bridge/mujoco_bridge.py" \
            > "$STATE_DIR/mujoco_bridge.log" 2>&1 &
    fi
    echo $! > "$STATE_DIR/mujoco_bridge.pid"
fi

# -- 2. CollectiveOS ---------------------------------------------------------
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

log "waiting for mujoco_bridge (ws://localhost:$MUJOCO_PORT) and CollectiveOS (http://localhost:$COS_PORT)..."
bridge_up=0; cos_up=0
for i in $(seq 1 30); do
    bridge_up=0; cos_up=0
    grep -q "listening on ws" "$STATE_DIR/mujoco_bridge.log" 2>/dev/null && bridge_up=1
    curl -s -o /dev/null "http://localhost:$COS_PORT/" 2>/dev/null && cos_up=1
    [[ "$bridge_up" == 1 && "$cos_up" == 1 ]] && break
    sleep 2
done

[[ "$bridge_up" != 1 ]] && log "mujoco_bridge isn't listening yet. Check $STATE_DIR/mujoco_bridge.log."
[[ "$cos_up" != 1 ]] && log "CollectiveOS isn't responding yet. Check $STATE_DIR/collectiveos.log."
[[ "$bridge_up" == 1 && "$cos_up" == 1 ]] && log "all up. The Franka Panda arm can move, exercise the Safety Kernel's collision check against real detected-object positions, and delegate to CollectiveOS."

echo
if [[ "$HEADLESS" == 0 ]]; then
    log "MuJoCo viewer window is open on your screen - the Panda arm and the arena (red_object, blue_container, laptop) are there to look at directly."
fi
log "Logs: $STATE_DIR/{mujoco_bridge,collectiveos}.log"
log "Stop everything with: ./scripts/run_simulation.sh --stop"

# -- optional demo run -------------------------------------------------------
if [[ "$DEMO" == 1 ]]; then
    log "running examples/mujoco_loop.py (drives the arena, then delegates a real use_computer task)..."
    export MUJOCO_BRIDGE_URL="ws://localhost:$MUJOCO_PORT"
    export COLLECTIVEOS_WS_URL="ws://localhost:$COS_PORT/robot/ws"
    export COLLECTIVEOS_API_TOKEN="$API_TOKEN"
    (cd "$REACH_ROOT/Pulse" && "$PULSE_VENV/bin/python3" examples/mujoco_loop.py)
fi
