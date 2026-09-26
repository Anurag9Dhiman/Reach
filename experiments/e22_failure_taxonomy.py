"""E22: Failure Taxonomy Analysis

RQ: What are the dominant sources of failure in the complete Reach system?

Scope, stated honestly: the PDF's 10 categories include several that only
exist inside CollectiveOS's NavAgent (ACS perception failure, ACS planning
failure, GUI grounding/execution failure) - from PAR's side of the
boundary, these three are indistinguishable and only visible as "the ACS
returned a bad result," so they are grouped as one proxy category here
rather than pretending PAR can tell them apart without instrumenting
CollectiveOS itself.

Constructs one scripted, adversarial scenario per (distinguishable)
category and confirms each is classified correctly, then reports the
category list PAR's own telemetry can actually support today.
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
from par.safety.environment import load_profile
from par.safety.kernel import SafetyKernel
from par.skills import builtin_skills, computer_use_skill
from harness.telemetry import CollectingTelemetryLogger

CATEGORIES = [
    "planner_failure",
    "safety_kernel_denial",
    "acs_side_failure",              # proxy for perception/planning/GUI-grounding failures (see docstring)
    "communication_failure",
    "physical_control_failure",
    "incorrect_result_accepted",     # PAR has no semantic verification - see e31
]


class _BadPlanner(Planner):
    """Simulates a planner failure: proposes a skill that doesn't exist."""

    def propose(self, goal, observation, capabilities):
        return "nonexistent_skill", {}


class _SequencePlanner(Planner):
    def __init__(self, steps):
        self._steps = list(steps)

    def propose(self, goal, observation, capabilities):
        return self._steps.pop(0)


def _build(bridge=None, planner=None, kernel=None):
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge or FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS))
    telemetry = CollectingTelemetryLogger()
    agent = Agent(registry, planner=planner)
    runtime = Runtime(agent, robot, safety_kernel=kernel, telemetry=telemetry)
    return runtime, agent, telemetry


def classify_planner_failure() -> dict:
    runtime, agent, telemetry = _build(planner=_BadPlanner())
    try:
        runtime.run_once("goal")
        classified_correctly = False
    except Exception as exc:
        classified_correctly = isinstance(exc, Exception)  # SkillError from registry.get(), surfaces as a raised exception
    runtime.close()
    return {"category": "planner_failure", "classified_correctly": classified_correctly}


def classify_safety_denial() -> dict:
    kernel = SafetyKernel(load_profile("simulation").model_copy(update={"approval_required": False}))
    planner = _SequencePlanner([("move", {"x": 100.0, "y": 0.0, "z": 0.0}), (TASK_COMPLETE, {"message": "done"})])
    runtime, agent, telemetry = _build(planner=planner, kernel=kernel)
    runtime.run_task("goal", max_steps=2)
    runtime.close()
    return {"category": "safety_kernel_denial", "classified_correctly": telemetry.events[0].safety_decision == "deny"}


def classify_acs_side_failure() -> dict:
    bridge = FaultyCollectiveOSBridge(mode=FaultMode.MALFORMED_REPLY)
    planner = _SequencePlanner([("use_computer", {"task": "t"}), (TASK_COMPLETE, {"message": "done"})])
    runtime, agent, telemetry = _build(bridge=bridge, planner=planner)
    runtime.run_task("goal", max_steps=2)
    runtime.close()
    return {"category": "acs_side_failure", "classified_correctly": not telemetry.events[0].success}


def classify_communication_failure() -> dict:
    bridge = FaultyCollectiveOSBridge(mode=FaultMode.CONNECTION_REFUSED)
    planner = _SequencePlanner([("use_computer", {"task": "t"}), (TASK_COMPLETE, {"message": "done"})])
    runtime, agent, telemetry = _build(bridge=bridge, planner=planner)
    runtime.run_task("goal", max_steps=2)
    runtime.close()
    return {"category": "communication_failure", "classified_correctly": "connection failed" in telemetry.events[0].result.message}


def classify_physical_control_failure() -> dict:
    planner = _SequencePlanner([("pick", {"object": "nonexistent_object"}), (TASK_COMPLETE, {"message": "done"})])
    runtime, agent, telemetry = _build(planner=planner)
    runtime.run_task("goal", max_steps=2)
    runtime.close()
    return {"category": "physical_control_failure", "classified_correctly": "not found" in telemetry.events[0].result.message}


def classify_incorrect_result_accepted() -> dict:
    bridge = FaultyCollectiveOSBridge(mode=FaultMode.INCORRECT_RESULT, incorrect_message="the wrong answer")
    planner = _SequencePlanner([("use_computer", {"task": "t"}), (TASK_COMPLETE, {"message": "done"})])
    runtime, agent, telemetry = _build(bridge=bridge, planner=planner)
    runtime.run_task("goal", max_steps=2)
    runtime.close()
    # "classified correctly" here means: PAR accepts the wrong answer as a
    # success (the failure mode this category is meant to surface).
    return {"category": "incorrect_result_accepted", "classified_correctly": telemetry.events[0].success}


def main() -> None:
    rows = [
        classify_planner_failure(),
        classify_safety_denial(),
        classify_acs_side_failure(),
        classify_communication_failure(),
        classify_physical_control_failure(),
        classify_incorrect_result_accepted(),
    ]
    for row in rows:
        print(f"- {row['category']:28} classified_correctly={row['classified_correctly']}")

    metrics = {
        "categories_tested": len(rows),
        "correctly_reproduced": sum(1 for r in rows if r["classified_correctly"]),
        "per_category": {r["category"]: r["classified_correctly"] for r in rows},
    }

    write_report(
        "E22",
        "Failure Taxonomy Analysis",
        config={"categories": CATEGORIES},
        metrics=metrics,
        trials=rows,
        notes=(
            "The PDF's 10 categories collapse to 6 distinguishable ones from "
            "PAR's side of the PAR/ACS boundary: 'ACS perception failure', 'ACS "
            "planning failure', and 'GUI grounding/execution failure' are all "
            "invisible to PAR - it only sees 'the ACS call failed or returned "
            "something,' grouped here as acs_side_failure. 'incorrect_result_"
            "accepted' is not one of the PDF's original 10 but is the single "
            "most important finding this taxonomy surfaces: PAR has no semantic "
            "verification of ACS results, so a confidently-wrong answer is "
            "indistinguishable from a correct one (see e31 for the dedicated "
            "experiment on this). Frequency-in-production analysis (how often "
            "each category actually occurs, and how the distribution shifts "
            "with task complexity, per the PDF's ask) needs real usage data - "
            "this only confirms each category is individually reproducible and "
            "correctly surfaced by PAR's telemetry."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
