"""E3: Comparison with a Robot-Only System

RQ: Does access to Reach improve completion of tasks with digital subtasks
vs. a robot with no computer-use capability?

Fake ACS (deterministic, for repeatability - this experiment is about
whether *having* the capability helps, not about ACS intelligence).
Compares:
  (1) Robot-only: `use_computer` is never registered as a capability at all.
  (2) Reach:      `use_computer` is registered, backed by a fake ACS.
on the full mixed task suite (harness/scenarios.py), split by whether the
task actually needs a computer, plus a physical-only check that Reach adds
no overhead when the capability goes unused.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.report import write_report
from harness.runner import run_trials
from harness.scenarios import by_id
from harness.stats import rate, summarize

from par.core.agent import Agent
from par.core.gemini_planner import GeminiPlanner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.env import load_env
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill
from harness.telemetry import CollectingTelemetryLogger

# Quota-conscious: GeminiPlanner drives both arms (RuleBasedPlanner can't
# reliably decide when a natural-language goal needs use_computer - see
# reach_experiments_delegation_intelligence memory note - so a real planner
# is required here). PAR's Gemini calls share the same free-tier quota pool
# as CollectiveOS's, so this uses a curated 4-task subset covering the two
# comparison points that matter (a physical-only task for the overhead
# check; digital-only, physical-to-digital, digital-to-physical for the
# actual robot-only-vs-Reach comparison) rather than the full 14-task suite.
TASK_IDS = ["phys-2", "dig-1", "p2d-1", "d2p-1"]
N_TRIALS_PER_TASK = 2
MAX_STEPS = 8


def build(with_computer_capability: bool):
    def _build():
        registry = SkillRegistry()
        for skill in builtin_skills():
            registry.register(skill)
        if with_computer_capability:
            registry.register(computer_use_skill())
            bridge = FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS, correct_message="looked it up: all good")
            robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
        else:
            robot = MockRobot()
        planner = GeminiPlanner.from_api_key()
        agent = Agent(registry, planner=planner)
        telemetry = CollectingTelemetryLogger()
        runtime = Runtime(agent, robot, telemetry=telemetry)
        return runtime, agent, telemetry

    return _build


def run_arm(with_computer_capability: bool) -> dict:
    per_task = {}
    for task_id in TASK_IDS:
        task = by_id(task_id)
        trials = run_trials(build(with_computer_capability), task.goal, n=N_TRIALS_PER_TASK, max_steps=MAX_STEPS)
        per_task[task.id] = {"task": task, "trials": trials}
    return per_task


def summarize_arm(per_task: dict, label: str) -> dict:
    all_trials = [t for entry in per_task.values() for t in entry["trials"]]
    digital_trials = [t for tid, entry in per_task.items() for t in entry["trials"] if entry["task"].requires_computer]
    physical_only_trials = [t for tid, entry in per_task.items() for t in entry["trials"] if not entry["task"].requires_computer]

    unresolved_digital = sum(
        1 for entry in per_task.values() if entry["task"].requires_computer
        for t in entry["trials"]
        if not any(e.skill == "use_computer" for e in t.events)
    )
    failed_attempts = sum(1 for t in all_trials if not t.task_success)

    return {
        "label": label,
        "overall_success_rate": rate(sum(1 for t in all_trials if t.task_success), len(all_trials)),
        "digital_task_success_rate": rate(sum(1 for t in digital_trials if t.task_success), len(digital_trials)) if digital_trials else float("nan"),
        "physical_only_success_rate": rate(sum(1 for t in physical_only_trials if t.task_success), len(physical_only_trials)) if physical_only_trials else float("nan"),
        "physical_only_latency": summarize([t.wall_time_seconds for t in physical_only_trials]).as_dict() if physical_only_trials else None,
        "failed_attempts": failed_attempts,
        "unresolved_digital_subtasks": unresolved_digital,
        "n_trials": len(all_trials),
    }


def main() -> None:
    load_env()

    print("=== Robot-only (no use_computer capability) ===")
    robot_only = run_arm(with_computer_capability=False)
    robot_only_summary = summarize_arm(robot_only, "robot_only")
    print(robot_only_summary)

    print("\n=== Reach (use_computer backed by a fake ACS) ===")
    reach = run_arm(with_computer_capability=True)
    reach_summary = summarize_arm(reach, "reach")
    print(reach_summary)

    metrics = {
        "robot_only": robot_only_summary,
        "reach": reach_summary,
        "digital_success_rate_delta": (
            reach_summary["digital_task_success_rate"] - robot_only_summary["digital_task_success_rate"]
        ),
        "physical_only_overhead_check": (
            "no meaningful difference expected between arms on physical-only tasks - "
            "compare physical_only_latency and physical_only_success_rate above"
        ),
    }

    write_report(
        "E3",
        "Comparison with a Robot-Only System",
        config={
            "acs": "fake (FaultyCollectiveOSBridge, mode=SUCCESS)",
            "planner": "GeminiPlanner (gemini-3.1-flash-lite), both arms",
            "n_trials_per_task": N_TRIALS_PER_TASK,
            "task_ids": TASK_IDS,
        },
        metrics=metrics,
        trials=None,
        notes=(
            "Robot-only's 'unresolved_digital_subtasks' counts every digital-task "
            "trial where use_computer was never called - not a planner mistake but "
            "a structural impossibility, since the capability isn't registered at "
            "all in that arm. digital_task_success_rate for robot-only is expected "
            "near 0 for any task whose completion genuinely requires the computer "
            "step; Reach's is the real test of whether the capability helps."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
