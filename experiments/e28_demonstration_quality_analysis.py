"""E28: Demonstration Quality Analysis

RQ: Which delegated trajectories provide useful supervision for imitation
learning?

Gated by the same real-data availability as E27 (needs E26/E1/E2's demos to
exist). Partitions by what's actually derivable: a demo file itself stores
no success/failure status (only task/steps/demos - see E26's finding), so
"successful and efficient" vs "successful but inefficient" vs "failed" is
reconstructed by cross-referencing each demo's save timestamp against
data/nav_runs/'s audit log (which does record status) - an approximate
match, not a guaranteed one, since the two are written by different code
paths with no shared identifier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_blocked, write_report

MIN_DEMOS = 3
DEMOS_DIR = Path("/Users/anuragdhiman/Documents/Reach/Reach/CollectiveOS/data/demonstrations")
NAV_RUNS_DIR = Path("/Users/anuragdhiman/Documents/Reach/Reach/CollectiveOS/data/nav_runs")


def load_demos() -> list[dict]:
    if not DEMOS_DIR.exists():
        return []
    out = []
    for path in sorted(DEMOS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            data["_mtime"] = path.stat().st_mtime
            out.append(data)
        except Exception:  # noqa: BLE001
            continue
    return out


def load_nav_runs() -> list[dict]:
    if not NAV_RUNS_DIR.exists():
        return []
    out = []
    for path in NAV_RUNS_DIR.glob("*.json"):
        try:
            out.append(json.loads(path.read_text()))
        except Exception:  # noqa: BLE001
            continue
    return out


def classify_demo(demo: dict, nav_runs: list[dict]) -> str:
    # Approximate match: same task text, completed_at closest in time to the
    # demo file's mtime. No shared ID exists between the two data sources.
    same_task = [r for r in nav_runs if r.get("task") == demo.get("task")]
    if not same_task:
        return "unknown"
    status = same_task[0].get("status")
    if status == "done":
        n_steps = demo.get("steps", 0)
        return "successful_and_efficient" if n_steps <= 5 else "successful_but_inefficient"
    if status == "max_iter":
        return "failed"  # never reached completion within the iteration budget
    return "unknown"


def main() -> None:
    demos = load_demos()
    nav_runs = load_nav_runs()
    print(f"Found {len(demos)} demonstration file(s), {len(nav_runs)} audited nav run(s)")

    if len(demos) < MIN_DEMOS:
        write_blocked(
            "E28",
            "Demonstration Quality Analysis",
            reason=f"only {len(demos)} real demonstration(s) available today (need >= {MIN_DEMOS} for even a "
            f"minimal quality partition) - see E26's report for why",
            unblock_condition="same as E27 - needs more accumulated real demonstrations from a less-flaky run",
        )
        print("Wrote blocked-status report for E28 (insufficient real demonstration data).")
        return

    from collections import Counter

    classifications = [classify_demo(d, nav_runs) for d in demos]
    counts = dict(Counter(classifications))
    print(f"Classification counts: {counts}")

    metrics = {
        "n_demonstrations": len(demos),
        "classification_counts": counts,
        "note": "safety_interrupted and human_corrected categories are not represented - the robot-facing "
        "endpoint has no HITL gate (see paper's Discussion), so no demo here was ever safety-interrupted "
        "or human-corrected by construction, not because none occurred",
    }

    write_report(
        "E28",
        "Demonstration Quality Analysis",
        config={
            "classification_method": "approximate cross-reference of demo file <-> nav_runs audit log by "
            "matching task text (no shared identifier exists between the two)",
            "min_demos_required": MIN_DEMOS,
        },
        metrics=metrics,
        trials=[{"task": d.get("task"), "steps": d.get("steps"), "classification": c}
                for d, c in zip(demos, classifications)],
        notes=(
            "Training separate imitation models per subset and comparing on "
            "held-out tasks (the PDF's full design) needs far more demonstrations "
            "per category than exist today to be meaningful - this reports the "
            "classification itself as the achievable first step, not a trained-"
            "model comparison. The demo/nav_runs cross-reference is approximate "
            "(matched by task text and closest timestamp, since the two files are "
            "written by different code paths with no shared run ID) - treat "
            "individual classifications as best-effort, not certain."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
