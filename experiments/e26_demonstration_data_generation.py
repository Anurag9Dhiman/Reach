"""E26: Demonstration Data Generation

RQ: Can Reach generate useful computer-use demonstrations during normal
robot delegation?

Real ACS - analyzes whatever CollectiveOS/data/demonstrations/ and
CollectiveOS/data/nav_runs/ already contain from this session's real runs
(E1, E2, and later E29), rather than triggering fresh calls itself, since
those experiments already exercise real delegation and any successful run
among them is recorded as a demonstration automatically (record=True is
always on for the robot-facing endpoint - see robot_stream.py).

A real finding surfaced while investigating why data/demonstrations/ didn't
exist yet after E1's 12 real trials: NavAgent._save_demos() (nav_agent.py)
is only called when a run reaches status="done" or exhausts the iteration
limit (status="max_iter") - a run that fails via an API-level exception
(nav_agent.py's vision-model-call except block, ~line 605-610) returns
immediately WITHOUT saving anything, even if steps were already recorded in
that run's demos list. data/nav_runs/ (the audit log) records every attempt
regardless of outcome via _save_audit_run, giving an honest denominator this
script cross-references against data/demonstrations/'s numerator.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_report

NAV_RUNS_DIR = Path("/Users/anuragdhiman/Documents/Reach/Reach/CollectiveOS/data/nav_runs")
DEMOS_DIR = Path("/Users/anuragdhiman/Documents/Reach/Reach/CollectiveOS/data/demonstrations")


def load_nav_runs() -> list[dict]:
    if not NAV_RUNS_DIR.exists():
        return []
    runs = []
    for path in NAV_RUNS_DIR.glob("*.json"):
        try:
            runs.append(json.loads(path.read_text()))
        except Exception:  # noqa: BLE001
            continue
    return runs


def load_demos() -> list[dict]:
    if not DEMOS_DIR.exists():
        return []
    demos = []
    for path in DEMOS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            data["_file"] = path.name
            demos.append(data)
        except Exception:  # noqa: BLE001
            continue
    return demos


def main() -> None:
    runs = load_nav_runs()
    demos = load_demos()

    by_status = {}
    for run in runs:
        by_status.setdefault(run.get("status", "unknown"), 0)
        by_status[run.get("status", "unknown")] += 1

    trajectory_lengths = [d.get("steps", 0) for d in demos]
    action_types = []
    tasks_seen = set()
    for d in demos:
        tasks_seen.add(d.get("task", ""))
        for step in d.get("demos", []):
            action = step.get("action", {})
            if isinstance(action, dict):
                action_types.append(action.get("action", "unknown"))

    from collections import Counter

    print(f"Total real nav-agent attempts recorded in nav_runs/: {len(runs)}")
    print(f"By status: {by_status}")
    print(f"Demonstration files saved: {len(demos)}")
    if demos:
        print(f"Trajectory lengths: {trajectory_lengths}")
        print(f"Action type diversity: {dict(Counter(action_types))}")
        print(f"Distinct tasks covered: {len(tasks_seen)}")

    eligible = by_status.get("done", 0) + by_status.get("max_iter", 0)
    metrics = {
        "total_attempts_recorded": len(runs),
        "attempts_by_status": by_status,
        "demo_eligible_attempts": eligible,
        "demonstration_files_saved": len(demos),
        "demo_capture_rate_of_eligible": (len(demos) / eligible) if eligible else float("nan"),
        "demo_capture_rate_of_all_attempts": (len(demos) / len(runs)) if runs else float("nan"),
        "trajectory_length_distribution": trajectory_lengths,
        "action_type_diversity": dict(Counter(action_types)),
        "distinct_tasks_covered": len(tasks_seen),
        "successful_vs_unsuccessful_demos": "not distinguishable from saved demo files alone - "
        "the demo JSON doesn't store the run's final status, only task/steps/demos (see notes)",
    }

    write_report(
        "E26",
        "Demonstration Data Generation",
        config={
            "acs": "real (analyzes CollectiveOS/data/{nav_runs,demonstrations}/ from this session's real runs)",
            "source_experiments": "E1, E2 (and E29, if run before this)",
        },
        metrics=metrics,
        trials=[{"run_id": r.get("run_id"), "task": r.get("task", "")[:80], "status": r.get("status"),
                 "step_count": r.get("step_count")} for r in runs],
        notes=(
            f"Of {len(runs)} real delegation attempts recorded today, only "
            f"{eligible} reached a demo-eligible terminal state (done or "
            f"max_iter) - the rest failed via an API-level exception (mostly "
            f"Gemini free-tier 503/429, see E1's own findings) and were "
            f"discarded by NavAgent._save_demos()'s early-return-on-exception "
            f"path before any partial progress could be saved, even when steps "
            f"had already accumulated. This IS the answer to 'can Reach generate "
            f"useful demonstrations during normal delegation' under today's "
            f"conditions: {len(demos)} demonstration file(s) resulted from "
            f"{len(runs)} attempts. If this number is 0, E27/E28 (which need "
            f"real demonstration data) are correspondingly blocked - see their "
            f"own reports for how that was handled, not silently glossed over."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
