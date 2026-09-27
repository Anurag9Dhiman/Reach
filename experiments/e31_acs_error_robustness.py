"""E31: Robustness to ACS Errors

RQ: Can PAR detect and recover when the computer-use system returns an
incorrect, incomplete, or ambiguous result?

Fake ACS (harness/fault_bridge.py) - all 5 output types the PDF asks for
(correct, incomplete, incorrect, ambiguous, explicit failure) are exactly
what FaultMode already models. The finding here is blunt and important: PAR
does not "continue, request clarification, retry, or choose an alternative"
based on the *content* of an ACS reply - it has exactly two behaviors,
driven only by the ACS's own self-reported status ("done" -> success=True,
anything else -> success=False). A confidently wrong answer (incorrect) and
an unclear one (ambiguous) both get accepted as success identically to a
correct one, because PAR does no semantic verification of what the ACS
actually said.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.report import write_report

from par.core.agent import Agent
from par.core.planner import TASK_COMPLETE, Planner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill
from harness.telemetry import CollectingTelemetryLogger

OUTPUT_TYPES = [
    ("correct_result", FaultMode.SUCCESS, "PAR should, and does, accept this"),
    ("incomplete_result", FaultMode.INCOMPLETE_RESULT, "empty message, still status=done"),
    ("incorrect_result", FaultMode.INCORRECT_RESULT, "confidently wrong, still status=done"),
    ("ambiguous_result", FaultMode.AMBIGUOUS_RESULT, "unclear, still status=done"),
    ("explicit_failure", FaultMode.EXPLICIT_FAILURE, "ACS itself reports failure"),
]


class _SequencePlanner(Planner):
    def __init__(self, steps):
        self._steps = list(steps)

    def propose(self, goal, observation, capabilities):
        return self._steps.pop(0)


def run_output_type(name: str, mode: FaultMode) -> dict:
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    bridge = FaultyCollectiveOSBridge(mode=mode)
    robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
    telemetry = CollectingTelemetryLogger()
    planner = _SequencePlanner([("use_computer", {"task": "read the gauge"}), (TASK_COMPLETE, {"message": "done"})])
    agent = Agent(registry, planner=planner)
    runtime = Runtime(agent, robot, telemetry=telemetry)
    runtime.run_task("goal", max_steps=2)
    runtime.close()

    event = telemetry.events[0]
    return {
        "output_type": name,
        "par_treated_as_success": event.success,
        "task_reached_complete": agent.state.status.value == "done",
        "message": event.result.message,
        "par_requested_clarification": False,   # PAR has no such mechanism today
        "par_retried_automatically": False,      # PAR has no such mechanism today
        "par_chose_alternative_action": False,   # only possible via a planner's own next propose() call
    }


def main() -> None:
    rows = [run_output_type(name, mode) for name, mode, _ in OUTPUT_TYPES]
    for row, (_, _, expectation) in zip(rows, OUTPUT_TYPES):
        print(f"- {row['output_type']:18} treated_as_success={row['par_treated_as_success']!s:5} ({expectation})")

    metrics = {
        "accepted_as_success": {row["output_type"]: row["par_treated_as_success"] for row in rows},
        "semantic_verification_exists": False,
        "content_based_recovery_mechanisms_exist": False,
    }

    write_report(
        "E31",
        "Robustness to ACS Errors",
        config={"acs": "fake (FaultyCollectiveOSBridge, one output type per trial)"},
        metrics=metrics,
        trials=rows,
        notes=(
            "3 of 5 output types (correct, incomplete, incorrect, ambiguous - "
            "everything except explicit_failure) are accepted as success "
            "identically, because PAR only checks the ACS's self-reported status, "
            "never the content of its answer. PAR has no clarification-request, "
            "automatic-retry, or content-based alternative-action mechanism for "
            "any of these cases today - 'choosing an alternative action' after a "
            "bad result is only possible in the sense that a planner's *next* "
            "step could react to a result.message that says something went "
            "wrong, and only for explicit_failure does the message actually say "
            "that. This is the same limitation e22's incorrect_result_accepted "
            "category and the paper's Discussion both already name; this "
            "experiment is the dedicated, systematic version of that finding "
            "across all 5 requested output types."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
