"""E2: Mixed Physical-Digital Task Benchmark

RQ: How does Reach perform across different categories and levels of mixed
physical-digital tasks?

Real ACS (this experiment's own point is generality across real tasks, so a
fake ACS would defeat the purpose). Uses harness/scenarios.py's full 14-task
library, which was authored to cover all 6 of the PDF's categories
(physical-only, digital-only, physical-to-digital, digital-to-physical,
multi-stage, multi-delegation) across difficulty levels 1-3. 1 trial per
task (14 real end-to-end runs) to stay quota-conscious given E1 already
shares the same daily budget - this is a coverage benchmark across task
variety, not a repeated-trials reliability study (that's E1's job).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.rate_limit import pace
from harness.report import write_report
from harness.runner import run_trials
from harness.scenarios import TASKS
from harness.stats import rate
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


def build_runtime():
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    robot = ComputerAugmentedRobot(MockRobot())
    agent = Agent(registry, planner=GeminiPlanner.from_api_key())
    telemetry = CollectingTelemetryLogger()
    runtime = Runtime(agent, robot, telemetry=telemetry)
    return runtime, agent, telemetry


def main() -> None:
    load_env()

    by_category: dict[str, list] = {}
    by_difficulty: dict[int, list] = {}
    all_trials = []

    for i, task in enumerate(TASKS):
        print(f"\n=== {task.id} ({task.category}, difficulty={task.difficulty}): {task.goal!r} ===")
        if i > 0:
            pace()
        try:
            trials = run_trials(build_runtime, task.goal, n=1, max_steps=MAX_STEPS)
            for t in trials:
                t.task_id = task.id
                t.category = task.category
                t.difficulty = task.difficulty
                print(f"  success={t.task_success} delegations={sum(1 for e in t.events if e.skill == 'use_computer')} "
                      f"replans={t.replans} time={t.wall_time_seconds:.1f}s")
        except Exception as exc:  # noqa: BLE001 - a transient API failure is data, not a crash
            print(f"  errored: {exc!s:.150}")
            trials = []
        by_category.setdefault(task.category, []).extend(trials)
        by_difficulty.setdefault(task.difficulty, []).extend(trials)
        all_trials.extend(trials)

    metrics = {
        "overall_success_rate": rate(sum(1 for t in all_trials if t.task_success), len(all_trials)),
        "n_tasks": len(TASKS),
        "by_category": {
            cat: {
                "n": len(trials),
                "success_rate": rate(sum(1 for t in trials if t.task_success), len(trials)),
                "mean_delegations": sum(sum(1 for e in t.events if e.skill == "use_computer") for t in trials) / len(trials),
            }
            for cat, trials in by_category.items()
        },
        "by_difficulty": {
            str(level): {
                "n": len(trials),
                "success_rate": rate(sum(1 for t in trials if t.task_success), len(trials)),
            }
            for level, trials in by_difficulty.items()
        },
    }

    print("\n=== E2 summary ===")
    print(f"overall_success_rate={metrics['overall_success_rate']:.2f}")
    for cat, m in metrics["by_category"].items():
        print(f"  {cat}: success_rate={m['success_rate']:.2f} (n={m['n']})")
    for level, m in metrics["by_difficulty"].items():
        print(f"  difficulty {level}: success_rate={m['success_rate']:.2f} (n={m['n']})")

    write_report(
        "E2",
        "Mixed Physical-Digital Task Benchmark",
        config={
            "acs": "real (live CollectiveOS + Gemini Navigation Agent)",
            "par_planner": "GeminiPlanner (gemini-3.1-flash-lite)",
            "n_trials_per_task": 1,
            "n_tasks": len(TASKS),
            "max_steps": MAX_STEPS,
        },
        metrics=metrics,
        trials=[
            {**t.as_dict(), "task_id": t.task_id, "category": t.category, "difficulty": t.difficulty}
            for t in all_trials
        ],
        notes=(
            "1 trial per task (14 real end-to-end runs), not repeated trials per "
            "task - this is a coverage benchmark across the 6 categories x 3 "
            "difficulty levels the task library was authored to span, not a "
            "reliability study (see E1 for repeated-trials reliability on a "
            "smaller task subset). A single real Gemini/CollectiveOS call chain "
            "is inherently noisy (see E1's transient-503 findings), so any one "
            "task's pass/fail here is a single data point, not a stable rate."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
