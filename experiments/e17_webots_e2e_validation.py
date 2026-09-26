"""E17: Webots End-to-End Validation - BLOCKED

RQ: Does the complete Reach physical-simulation integration operate
correctly with an actual Webots environment?

Blocked: no Webots installation in this environment. The control logic
(differential-drive move convergence, WebSocket request/response threading)
was already validated against a hand-written kinematic fake while building
the Webots bridge (see Pulse PR #10 / Reach PR #2) - what's missing is the
real Webots API surface itself (device names, coordinate handling,
Supervisor calls), which can only be confirmed on a real install.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness.report import write_blocked

if __name__ == "__main__":
    write_blocked(
        "E17",
        "Webots End-to-End Validation",
        reason="no Webots installation in this environment",
        unblock_condition="Webots installed and Gatekeeper-approved; open Reach/webots/worlds/par_arena.wbt, "
        "run webots/controllers/par_bridge/par_bridge.py, then drive it via Pulse/examples/webots_loop.py "
        "and compare waypoint navigation, target approach, collision denial, e-stop, and workspace "
        "violation against the kinematic-fake validation already on record",
    )
    print("Wrote blocked-status report for E17.")
