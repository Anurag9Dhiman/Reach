"""E1: End-to-End Delegation Reliability

RQ: Can Reach reliably execute complete tasks needing a robot to delegate a
digital subtask to the ACS and then continue its physical task?

Real ACS (see README.md's real-vs-fake table): this experiment's whole point
is whether the real pipeline works end to end, so it must use a live
CollectiveOS instance, not a fake. N is small (quota-conscious): 3 trials on
each of 4 representative mixed physical+digital tasks (one from each of the
p2d/d2p/multi-stage/multi-delegation categories that actually contain both a
physical and a digital step, per the PDF's task definition for this
experiment) = 12 full pipeline runs, each making at least 2 real Gemini calls
(PAR's own planner + CollectiveOS's nav agent). Report this sample size
honestly - it's a reliability pilot, not a large statistically powered study.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_report
from harness.runner import run_trials
from harness.scenarios import by_id
from harness.stats import summarize, wilson_ci95
from harness.telemetry import CollectingTelemetryLogger

from par.core.agent import Agent
from par.core.gemini_planner import GeminiPlanner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.env import load_env
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill

N_TRIALS_PER_TASK = 3
TASK_IDS = ["p2d-1", "d2p-1", "multi-1", "multidel-1"]
MAX_STEPS = 8


def build_runtime():
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    robot = ComputerAugmentedRobot(MockRobot())
    planner = GeminiPlanner.from_api_key()
    agent = Agent(registry, planner=planner)
    telemetry = CollectingTelemetryLogger()
    runtime = Runtime(agent, robot, telemetry=telemetry)
    return runtime, agent, telemetry


def main() -> None:
    load_env()

    per_task = {}
    all_trials = []
    all_delegation_successes = 0
    all_delegation_attempts = 0
    all_acs_successes = 0

    for task_id in TASK_IDS:
        task = by_id(task_id)
        print(f"\n=== {task.id} ({task.category}): {task.goal!r} ===")
        trials = run_trials(build_runtime, task.goal, n=N_TRIALS_PER_TASK, max_steps=MAX_STEPS)
        for t in trials:
            t.trial_task_id = task.id  # tag for the aggregate JSON
            delegation_events = [e for e in t.events if e.skill == "use_computer"]
            delegations = len(delegation_events)
            successful_delegations = sum(1 for e in delegation_events if e.success)
            all_delegation_attempts += delegations
            all_delegation_successes += successful_delegations
            all_acs_successes += successful_delegations  # ACS success == delegation success here (same signal)
            print(
                f"  trial {t.index}: task_success={t.task_success} delegations={delegations} "
                f"replans={t.replans} escalations={t.escalations} time={t.wall_time_seconds:.1f}s"
            )
        all_trials.extend(trials)
        per_task[task_id] = trials

    n = len(all_trials)
    task_successes = sum(1 for t in all_trials if t.task_success)
    completion_times = [t.wall_time_seconds for t in all_trials]
    total_delegations = sum(len([e for e in t.events if e.skill == "use_computer"]) for t in all_trials)
    total_replans = sum(t.replans for t in all_trials)
    total_human_interventions = sum(t.escalations for t in all_trials)

    # Free-tier Gemini quota is shared across every real-ACS/real-planner
    # experiment and can run out mid-pilot (observed in practice - see
    # results/E1_*.md's notes) - classify delegation failures by cause so a
    # quota exhaustion doesn't get silently conflated with a genuine
    # architecture reliability problem.
    failure_causes = {"quota_exhausted": 0, "transient_upstream_503": 0, "timeout": 0, "other": 0}
    for t in all_trials:
        for e in t.events:
            if e.skill == "use_computer" and not e.success:
                msg = e.result.message
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    failure_causes["quota_exhausted"] += 1
                elif "503" in msg or "UNAVAILABLE" in msg:
                    failure_causes["transient_upstream_503"] += 1
                elif "timed out" in msg:
                    failure_causes["timeout"] += 1
                else:
                    failure_causes["other"] += 1

    success_ci = wilson_ci95(task_successes, n)
    delegation_ci = wilson_ci95(all_delegation_successes, all_delegation_attempts) if all_delegation_attempts else (float("nan"),) * 2

    metrics = {
        "end_to_end_task_success_rate": task_successes / n,
        "end_to_end_task_success_ci95": list(success_ci),
        "delegation_success_rate": (all_delegation_successes / all_delegation_attempts) if all_delegation_attempts else float("nan"),
        "delegation_success_ci95": list(delegation_ci),
        "acs_success_rate": (all_acs_successes / all_delegation_attempts) if all_delegation_attempts else float("nan"),
        "completion_time_seconds": summarize(completion_times).as_dict(),
        "total_delegations": total_delegations,
        "total_replans": total_replans,
        "total_human_interventions": total_human_interventions,
        "n_trials": n,
        "n_tasks": len(TASK_IDS),
        "delegation_failure_causes": failure_causes,
        "delegation_failures_unexplained": failure_causes["other"],
    }

    print("\n=== E1 summary ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    write_report(
        "E1",
        "End-to-End Delegation Reliability",
        config={
            "acs": "real (live CollectiveOS + Gemini Navigation Agent)",
            "par_planner": "GeminiPlanner (gemini-3.1-flash-lite)",
            "n_trials_per_task": N_TRIALS_PER_TASK,
            "task_ids": TASK_IDS,
            "max_steps": MAX_STEPS,
        },
        metrics=metrics,
        trials=[
            {**t.as_dict(), "task_id": getattr(t, "trial_task_id", None)}
            for t in all_trials
        ],
        notes=(
            "Small, quota-conscious pilot (12 real end-to-end runs against Gemini's "
            "free tier), not a large statistically powered study - confidence "
            "intervals here are wide and should be read as such. 'ACS success rate' "
            "is measured as delegation success here (the ACS's own internal status "
            "== 'done'), since that is the only ACS-side signal PAR's bridge "
            "receives. Check 'delegation_failure_causes' before reading "
            "end_to_end_task_success_rate at face value: the shared free-tier "
            "GEMINI_API_KEY quota is used by every real-ACS/real-planner experiment "
            "and can exhaust mid-pilot (429 RESOURCE_EXHAUSTED) or hit transient "
            "upstream overload (503) - only 'delegation_failures_unexplained' "
            "(failures NOT attributable to quota/503/timeout) reflects an actual "
            "defect in the pipeline being tested."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
