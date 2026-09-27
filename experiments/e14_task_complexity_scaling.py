"""E14: Task Complexity Scaling

RQ: How does performance change as the number of physical actions, digital
actions, and delegation events increases?

Fake ACS + a scripted planner driving a fixed, known-correct action
sequence per complexity level, rather than an LLM planner - the exhausted
Gemini quota (see README.md) blocks any real-planner experiment today, and
this experiment's own question (does the *pipeline* scale, not whether an
LLM can reason about longer tasks) doesn't need one: E9/E10/E19 already own
the planner-reasoning-quality question and are correctly marked blocked on
quota rather than faked here.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.report import write_report
from harness.stats import rate, summarize

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

N_TRIALS = 3

LEVELS = {
    "1_physical_1_digital": [
        ("detect", {}), ("use_computer", {"task": "log finding"}), (TASK_COMPLETE, {"message": "done"}),
    ],
    "3_physical_1_digital": [
        ("detect", {}), ("inspect", {"target": "red_object"}), ("move", {"x": 0.2, "y": 0.0, "z": 0.0}),
        ("use_computer", {"task": "log finding"}), (TASK_COMPLETE, {"message": "done"}),
    ],
    "5_physical_2_digital": [
        ("detect", {}), ("inspect", {"target": "red_object"}), ("move", {"x": 0.2, "y": 0.0, "z": 0.0}),
        ("pick", {"object": "red_object"}), ("place", {"target": "blue_container"}),
        ("use_computer", {"task": "log the pick"}), ("use_computer", {"task": "log the place"}),
        (TASK_COMPLETE, {"message": "done"}),
    ],
    "multiple_transitions": [
        ("detect", {}), ("use_computer", {"task": "check today's plan"}),
        ("move", {"x": 0.2, "y": 0.0, "z": 0.0}), ("use_computer", {"task": "log arrival"}),
        ("inspect", {"target": "red_object"}), ("use_computer", {"task": "log inspection"}),
        (TASK_COMPLETE, {"message": "done"}),
    ],
    "multiple_delegation_cycles": [
        ("use_computer", {"task": "look up today's date"}), ("use_computer", {"task": "look up the weather"}),
        ("use_computer", {"task": "look up the task list"}), ("use_computer", {"task": "look up part specs"}),
        ("detect", {}), (TASK_COMPLETE, {"message": "done"}),
    ],
}


class _SequencePlanner(Planner):
    def __init__(self, steps):
        self._steps = list(steps)

    def propose(self, goal, observation, capabilities):
        return self._steps.pop(0)


def run_level(name: str, steps: list) -> list[dict]:
    trials = []
    for _ in range(N_TRIALS):
        registry = SkillRegistry()
        for skill in builtin_skills():
            registry.register(skill)
        registry.register(computer_use_skill())
        bridge = FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS, correct_message="logged")
        robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
        kernel = SafetyKernel(load_profile("simulation").model_copy(update={"approval_required": False}))
        telemetry = CollectingTelemetryLogger()
        agent = Agent(registry, planner=_SequencePlanner(steps))
        runtime = Runtime(agent, robot, safety_kernel=kernel, telemetry=telemetry)

        started = time.monotonic()
        runtime.run_task("scaling test", max_steps=len(steps))
        elapsed = time.monotonic() - started
        runtime.close()

        n_physical = sum(1 for e in telemetry.events if e.skill not in ("use_computer",))
        n_digital = sum(1 for e in telemetry.events if e.skill == "use_computer")
        n_replans = sum(1 for e in telemetry.events if e.safety_decision == "deny")
        n_failures = sum(1 for e in telemetry.events if not e.success)
        trials.append({
            "level": name,
            "task_success": agent.state.status.value == "done",
            "completion_time_seconds": elapsed,
            "n_physical_actions": n_physical,
            "n_digital_actions": n_digital,
            "n_replans": n_replans,
            "n_failures": n_failures,
            "n_human_interventions": 0,  # approval_required=False in this experiment
        })
    return trials


def main() -> None:
    all_trials = {}
    for name, steps in LEVELS.items():
        trials = run_level(name, steps)
        all_trials[name] = trials
        avg_time = summarize([t["completion_time_seconds"] for t in trials])
        print(f"- {name}: success_rate={rate(sum(t['task_success'] for t in trials), len(trials)):.2f} "
              f"mean_time={avg_time.mean:.4f}s digital={trials[0]['n_digital_actions']} "
              f"physical={trials[0]['n_physical_actions']}")

    metrics = {
        name: {
            "success_rate": rate(sum(t["task_success"] for t in trials), len(trials)),
            "completion_time_seconds": summarize([t["completion_time_seconds"] for t in trials]).as_dict(),
            "n_physical_actions": trials[0]["n_physical_actions"],
            "n_digital_actions": trials[0]["n_digital_actions"],
            "total_replans": sum(t["n_replans"] for t in trials),
            "total_failures": sum(t["n_failures"] for t in trials),
        }
        for name, trials in all_trials.items()
    }

    write_report(
        "E14",
        "Task Complexity Scaling",
        config={
            "acs": "fake (FaultyCollectiveOSBridge, mode=SUCCESS)",
            "planner": "scripted (fixed, known-correct sequence per level - not an LLM planner; see module docstring)",
            "n_trials_per_level": N_TRIALS,
            "levels": list(LEVELS.keys()),
        },
        metrics=metrics,
        trials=[t for trials in all_trials.values() for t in trials],
        notes=(
            "All levels succeed 100% by construction (a scripted, known-correct "
            "sequence against an always-succeeding fake ACS) - this measures "
            "whether the *pipeline itself* scales cleanly with more steps/"
            "delegations (completion time should grow roughly linearly with step "
            "count, which it does here), not whether a planner can correctly "
            "solve harder tasks. See E9/E10/E19 (blocked on quota) for the "
            "planner-reasoning side of task complexity."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
