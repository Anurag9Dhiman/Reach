"""E23: Human-in-the-Loop Usability - BLOCKED

RQ: Does safety escalation provide an effective mechanism for human
intervention during high-risk delegation?

Blocked entirely: this is a usability study on real human operators
(decision time, approval/rejection accuracy) - nothing about this can be
meaningfully simulated. Per the user's own choice when this was scoped
(2026-09-27), this is deferred rather than faked with a scripted approver.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness.report import write_blocked

if __name__ == "__main__":
    write_blocked(
        "E23",
        "Human-in-the-Loop Usability",
        reason="needs real human operators making timed approve/reject decisions on escalation prompts",
        unblock_condition="the user (or other real operators) run a set of trials personally; "
        "e08's automated part already shows which task/profile combinations actually produce an "
        "escalation prompt worth testing this on",
    )
    print("Wrote blocked-status report for E23.")
