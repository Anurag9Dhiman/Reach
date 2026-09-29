"""E29: Generalization Across Task Domains

RQ: Does Reach generalize across different physical and digital task
domains?

Real ACS. Scope, stated honestly: there is no real diverse physical
hardware available (industrial inspection rigs, lab instruments, etc.) - all
5 domains run against the same MockRobot/red_object/blue_container stand-ins
used everywhere else in this suite, with domain-flavored task phrasing
standing in for genuinely different physical environments. This tests
whether PAR's interface and safety kernel (held unchanged across all 5, per
the PDF's own design) generalize across different *task framing/vocabulary*
sent to the real ACS - not across genuinely different physical hardware,
which this environment cannot provide.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.rate_limit import pace
from harness.report import write_report
from harness.runner import run_trials

from par.core.agent import Agent
from par.core.gemini_planner import GeminiPlanner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.env import load_env
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill
from harness.telemetry import CollectingTelemetryLogger

MAX_STEPS = 6

DOMAINS = {
    "industrial_inspection": "Inspect the red_object for damage, then use the computer to log the inspection result.",
    "laboratory_measurement": "Inspect the red_object to read its measurement, then use the computer to record the reading in the lab log.",
    "inventory_management": "Detect the objects present, then use the computer to update the inventory count.",
    "machine_maintenance": "Inspect the red_object, then use the computer to check whether maintenance is due.",
    "office_document_interaction": "Use the computer to check the document status, then move the blue_container to file it.",
}


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
    rows = []
    for i, (domain, goal) in enumerate(DOMAINS.items()):
        print(f"\n=== {domain}: {goal!r} ===")
        if i > 0:
            pace()
        try:
            # run_trial() catches exceptions internally (stores them in
            # TrialResult.error rather than raising - see harness/runner.py),
            # so call_with_retry's raise-based retry wouldn't actually retry
            # anything here. Retry manually on t.error instead.
            t = None
            for attempt in range(3):
                trials = run_trials(build_runtime, goal, n=1, max_steps=MAX_STEPS)
                t = trials[0]
                if not t.error:
                    break
                if attempt < 2:
                    wait = 45.0 * (attempt + 1)
                    print(f"    (attempt {attempt + 1}/3 errored: {t.error!s:.120}; retrying in {wait:.0f}s)")
                    time.sleep(wait)
            delegated = sum(1 for e in t.events if e.skill == "use_computer")
            rows.append({
                "domain": domain, "goal": goal, "task_success": t.task_success,
                "delegations": delegated, "latency_seconds": t.wall_time_seconds, "error": t.error,
            })
            print(f"  success={t.task_success} delegations={delegated} time={t.wall_time_seconds:.1f}s")
        except Exception as exc:  # noqa: BLE001
            rows.append({"domain": domain, "goal": goal, "task_success": False, "delegations": 0,
                         "latency_seconds": None, "error": str(exc)[:200]})
            print(f"  errored: {exc!s:.150}")

    from harness.stats import rate
    metrics = {
        "success_rate": rate(sum(1 for r in rows if r["task_success"]), len(rows)),
        "per_domain": {r["domain"]: {"success": r["task_success"], "delegations": r["delegations"]} for r in rows},
    }

    write_report(
        "E29",
        "Generalization Across Task Domains",
        config={
            "acs": "real (live CollectiveOS + Gemini Navigation Agent)",
            "par_planner": "GeminiPlanner (gemini-3.1-flash-lite)",
            "domains": list(DOMAINS.keys()),
            "scope_note": "domains are task-phrasing variations against the same MockRobot stand-in, "
            "not genuinely different physical hardware - see module docstring",
        },
        metrics=metrics,
        trials=rows,
        notes=(
            "PAR's interface and safety kernel were unchanged across all 5 "
            "domains by construction (same registry, same SafetyKernel config), "
            "so this measures whether the real ACS handles varied task "
            "vocabulary consistently, not whether PAR's own code needs "
            "domain-specific changes (it doesn't, by design). Any failures here "
            "should be cross-checked against E1's failure-cause breakdown before "
            "concluding a domain-specific problem, since today's real-ACS calls "
            "are subject to the same transient Gemini flakiness documented there."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
