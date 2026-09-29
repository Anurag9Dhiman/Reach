"""E19: Planner Comparison

RQ: How does the choice of PAR planner affect delegation quality and overall
task performance?

Fake ACS (isolates planner behavior from ACS variability). Compares
RuleBasedPlanner vs. GeminiPlanner (the only two real planners available -
no second LLM key exists here, so this is not a multi-LLM comparison; see
README.md) on the identical task set, safety kernel, and ACS configuration.

RuleBasedPlanner's known limitation (par.core.planner.RuleBasedPlanner:
keyword-matches the goal text, never emits task_complete on its own, and
_extract_params always returns (0,0,0) for `move`) means it is expected to
fail almost every natural-language task in harness/scenarios.py outright -
this IS the finding, not a bug in the experiment: it shows the Reach
architecture's effectiveness depends on a capable planner, not just on the
delegation/safety plumbing around it.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.rate_limit import pace
from harness.report import write_report
from harness.scenarios import TASKS
from harness.stats import rate
from harness.telemetry import CollectingTelemetryLogger

from par.core.agent import Agent
from par.core.gemini_planner import GeminiPlanner
from par.core.planner import RuleBasedPlanner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.env import load_env
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill

MAX_STEPS = 8


def run_with_planner(planner_name: str, planner_factory, task) -> dict:
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    bridge = FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS, correct_message="done")
    robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
    telemetry = CollectingTelemetryLogger()
    agent = Agent(registry, planner=planner_factory())
    runtime = Runtime(agent, robot, telemetry=telemetry)

    started = time.monotonic()
    crash_reason = None
    try:
        runtime.run_task(task.goal, max_steps=MAX_STEPS)
    except Exception as exc:  # noqa: BLE001 - RuleBasedPlanner raises PlannerError when nothing matches
        crash_reason = str(exc)[:200]
    elapsed = time.monotonic() - started
    runtime.close()

    crashed = crash_reason is not None
    delegated = any(e.skill == "use_computer" for e in telemetry.events)
    return {
        "planner": planner_name,
        "task_id": task.id,
        "task_success": (not crashed) and agent.state.status.value == "done",
        "crashed": crashed,
        "crash_reason": crash_reason,
        "correct_delegation": (not crashed) and delegated == task.requires_computer,
        "n_replans": sum(1 for e in telemetry.events if e.safety_decision == "deny"),
        "latency_seconds": elapsed,
    }


def main() -> None:
    load_env()
    planners = {
        "rule_based": lambda: RuleBasedPlanner(),
        "gemini": lambda: GeminiPlanner.from_api_key(),
    }

    all_rows = []
    for name, factory in planners.items():
        print(f"\n=== {name} ===")
        for i, task in enumerate(TASKS):
            if name == "gemini" and i > 0:
                pace()  # rule_based is instant/local, no rate limit to worry about
            row = run_with_planner(name, factory, task)
            all_rows.append(row)
            print(f"  {task.id}: success={row['task_success']} crashed={row['crashed']} "
                  f"correct_delegation={row['correct_delegation']}")

    metrics = {}
    for name in planners:
        rows = [r for r in all_rows if r["planner"] == name]
        metrics[name] = {
            "task_success_rate": rate(sum(1 for r in rows if r["task_success"]), len(rows)),
            "correct_delegation_rate": rate(sum(1 for r in rows if r["correct_delegation"]), len(rows)),
            "crash_rate": rate(sum(1 for r in rows if r["crashed"]), len(rows)),
            "total_replans": sum(r["n_replans"] for r in rows),
            "mean_latency_seconds": sum(r["latency_seconds"] for r in rows) / len(rows),
        }
        print(f"\n{name}: {metrics[name]}")

    write_report(
        "E19",
        "Planner Comparison",
        config={
            "acs": "fake (FaultyCollectiveOSBridge, mode=SUCCESS)",
            "planners_compared": list(planners.keys()),
            "note": "GeminiPlanner vs RuleBasedPlanner only - no second LLM key available, see README.md",
            "n_tasks": len(TASKS),
        },
        metrics=metrics,
        trials=all_rows,
        notes=(
            "The Reach architecture (safety kernel, delegation plumbing, ACS "
            "bridge) is planner-agnostic by construction, but its *effectiveness* "
            "is not: rule_based's task_success_rate is expected near 0 because "
            "RuleBasedPlanner cannot parse natural-language goals for delegation "
            "intent or produce real move coordinates (see module docstring), "
            "while gemini's is expected much higher. This is the honest answer "
            "to the RQ - Reach 'works' independently of which planner is plugged "
            "in only in the sense that it doesn't crash or misbehave unsafely; "
            "task-level effectiveness genuinely depends on the planner's own "
            "reasoning capability. token_usage was not tracked - GeminiPlanner "
            "does not currently expose response.usage_metadata to its caller, "
            "which would need a small addition to par.core.gemini_planner "
            "to measure directly."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
