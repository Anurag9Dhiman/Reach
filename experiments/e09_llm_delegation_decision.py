"""E9: LLM Delegation Decision

RQ: Can an LLM-based PAR planner correctly determine when a physical task
requires delegation to the computer-use system?

Fake ACS (SUCCESS mode) - this tests the PLANNER's decision to delegate, not
the ACS's execution quality, so a fast/free/deterministic fake is the
correct choice, saving real ACS quota for E1/E2/E26/E28/E29 which actually
need it. Real GeminiPlanner (the only real LLM planner available - see
README.md's note on why this isn't a multi-LLM comparison).

Uses harness/scenarios.py's full 14-task library, each already labeled with
ground truth (requires_computer). One real Gemini-planner attempt per task.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.rate_limit import pace
from harness.report import write_report
from harness.scenarios import TASKS
from harness.telemetry import CollectingTelemetryLogger

from par.core.agent import Agent
from par.core.gemini_planner import GeminiPlanner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.env import load_env
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill

MAX_STEPS = 8


def classify(task_requires_computer: bool, planner_delegated: bool, physical_actions_taken: bool) -> str:
    if task_requires_computer and planner_delegated:
        return "correct_delegation"
    if task_requires_computer and not planner_delegated:
        return "missed_delegation"
    if not task_requires_computer and planner_delegated:
        return "unnecessary_delegation"
    return "correct_physical_execution"


def run_task_trial(goal: str) -> dict:
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    bridge = FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS, correct_message="done")
    robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
    telemetry = CollectingTelemetryLogger()
    agent = Agent(registry, planner=GeminiPlanner.from_api_key())
    runtime = Runtime(agent, robot, telemetry=telemetry)
    runtime.run_task(goal, max_steps=MAX_STEPS)
    runtime.close()

    delegated = any(e.skill == "use_computer" for e in telemetry.events)
    physical = any(e.skill != "use_computer" for e in telemetry.events)
    return {"delegated": delegated, "physical_actions_taken": physical, "n_steps": len(telemetry.events)}


def main() -> None:
    load_env()
    rows = []
    for i, task in enumerate(TASKS):
        print(f"- {task.id} ({task.category}): {task.goal!r}")
        if i > 0:
            pace()
        try:
            result = run_task_trial(task.goal)
            classification = classify(task.requires_computer, result["delegated"], result["physical_actions_taken"])
            rows.append({
                "task_id": task.id, "category": task.category, "goal": task.goal,
                "requires_computer": task.requires_computer, **result, "classification": classification,
            })
            print(f"    -> {classification} (delegated={result['delegated']})")
        except Exception as exc:  # noqa: BLE001 - a transient API failure is data (errored), not a crash
            rows.append({
                "task_id": task.id, "category": task.category, "goal": task.goal,
                "requires_computer": task.requires_computer, "delegated": None, "physical_actions_taken": None,
                "n_steps": 0, "classification": "errored", "error": str(exc)[:300],
            })
            print(f"    -> errored: {exc!s:.150}")

    scored_rows = [r for r in rows if r["classification"] != "errored"]
    all_delegations = sum(1 for r in scored_rows if r["delegated"])
    correct_delegations = sum(1 for r in scored_rows if r["classification"] == "correct_delegation")
    tasks_requiring_computer = sum(1 for r in scored_rows if r["requires_computer"])

    precision = correct_delegations / all_delegations if all_delegations else float("nan")
    recall = correct_delegations / tasks_requiring_computer if tasks_requiring_computer else float("nan")

    from collections import Counter
    classification_counts = dict(Counter(r["classification"] for r in rows))

    metrics = {
        "delegation_precision": precision,
        "delegation_recall": recall,
        "classification_counts": classification_counts,
        "n_tasks": len(rows),
        "n_errored": len(rows) - len(scored_rows),
    }

    print(f"\nDelegationPrecision={precision:.2f}  DelegationRecall={recall:.2f}")
    print(f"Classification counts: {classification_counts}")

    write_report(
        "E9",
        "LLM Delegation Decision",
        config={
            "acs": "fake (FaultyCollectiveOSBridge, mode=SUCCESS - testing planner decision, not ACS execution)",
            "planner": "GeminiPlanner (gemini-3.1-flash-lite) - the only real LLM planner available, see README.md",
            "n_tasks": len(TASKS),
        },
        metrics=metrics,
        trials=rows,
        notes=(
            "Single LLM (GeminiPlanner), not the PDF's intended multi-planner "
            "comparison - no second LLM key is available in this environment. "
            "Repeat across 'different LLM planners and task difficulties' per "
            "the PDF's own ask would need e.g. an Anthropic key to add a genuinely "
            "different model."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
