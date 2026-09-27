"""E16: Physical Safety Constraint Evaluation (Webots) - BLOCKED

RQ: Does the safety kernel correctly enforce workspace, collision-margin,
and velocity constraints during physical robot operation (on the Webots
simulated robot specifically, not just MockRobot)?

Blocked: no Webots installation exists in this environment (Homebrew's
`webots` cask is Gatekeeper-disabled; see Reach/webots/README.md). The
in-memory equivalent of this test already exists and passes
(e05/e06 exercise the same workspace/collision/velocity/reachable-distance
logic directly against SafetyKernel) - what's missing is confirming the
*same* test cases behave identically when driven through par.robots
.webots_bridge.WebotsRobot against a real Webots process, per the PDF's
explicit ask to "evaluate the same test cases using the in-memory
implementation and Webots to determine whether the safety behavior remains
consistent across interfaces."
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness.report import write_blocked

if __name__ == "__main__":
    write_blocked(
        "E16",
        "Physical Safety Constraint Evaluation",
        reason="no Webots installation in this environment",
        unblock_condition="Webots installed and Gatekeeper-approved (Reach/webots/README.md); "
        "then re-run e05/e06's scenario battery through WebotsRobot instead of MockRobot",
    )
    print("Wrote blocked-status report for E16.")
