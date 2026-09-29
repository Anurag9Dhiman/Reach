"""E33: Overall Systems Benchmark

RQ: What is the overall effectiveness of Reach when evaluated simultaneously
on task completion, safety, robustness, latency, and delegation quality?

This does not run new trials - per the PDF, it aggregates what the other 32
experiments already produced (run last, once most others exist). Reads
every results/*.json in this directory and reports which of the PDF's
primary metrics are available today vs. still blocked, plus a compact
failure taxonomy (reusing E22's categories) and pointers to representative
successful/unsuccessful episodes rather than duplicating their content.

Honest limitation: the PDF's own primary-metrics line is truncated
("...RecoveryRate, HumanEs...") in the source PDF itself - the exact final
metric list could not be confirmed from the source and should be re-checked
against the original document before treating this section as complete.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_report

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_all_results() -> dict[str, dict]:
    results = {}
    for path in sorted(RESULTS_DIR.glob("E*.json")):
        try:
            data = json.loads(path.read_text())
            results[data["experiment_id"]] = data
        except Exception as exc:  # noqa: BLE001
            print(f"  (skipping unreadable {path.name}: {exc})")
    return results


def main() -> None:
    all_results = load_all_results()
    print(f"Loaded {len(all_results)} experiment result files: {sorted(all_results.keys())}")

    # E33 is the aggregator itself, not one of the 33 numbered experiments -
    # exclude its own prior-run JSON from the roll-up it computes about the
    # other 32, or a re-run double-counts itself as "completed".
    aggregated = {eid: d for eid, d in all_results.items() if eid != "E33"}
    blocked = {eid: d for eid, d in aggregated.items() if d.get("metrics", {}).get("status") == "blocked"}
    completed = {eid: d for eid, d in aggregated.items() if eid not in blocked}

    # -- primary metrics, pulled from whichever experiment actually measured
    #    each one, where available ------------------------------------------
    primary_metrics = {}

    if "E1" in completed:
        m = completed["E1"]["metrics"]
        primary_metrics["task_success_rate"] = {
            "value": m.get("end_to_end_task_success_rate"),
            "source": "E1",
            "caveat": "small pilot (12 trials) - see E1's own report for its failure-cause breakdown "
            "(quota/503/max_iter/screencapture-bug/unexplained) before reading this number at face value.",
        }
    if "E9" in completed:
        m = completed["E9"]["metrics"]
        primary_metrics["delegation_precision_recall"] = {
            "value": {"precision": m.get("delegation_precision"), "recall": m.get("delegation_recall")},
            "source": "E9",
        }
    elif "E19" in completed:
        m = completed["E19"]["metrics"].get("gemini", {})
        primary_metrics["delegation_precision_recall"] = {
            "value": {"correct_delegation_rate": m.get("correct_delegation_rate")},
            "source": "E19 (gemini arm)",
        }
    else:
        primary_metrics["delegation_precision_recall"] = {"value": None, "source": "E9/E19", "caveat": "not yet run"}

    if "E5" in completed:
        m = completed["E5"]["metrics"]
        primary_metrics["unsafe_execution_rate"] = {
            "value": m.get("admission_and_policy", {}).get("unsafe_execution_rate"),
            "source": "E5 (full safety kernel config)",
        }
    if "E11" in completed:
        m = completed["E11"]["metrics"]
        primary_metrics["recovery_rate"] = {
            "value": m.get("retry_recovery_rate"),
            "source": "E11",
            "caveat": "measured as retry-level recovery, not within-single-run_task recovery - see E11's notes",
        }
    if "E8" in completed:
        m = completed["E8"]["metrics"]
        primary_metrics["human_escalation_behavior"] = {
            "value": m,
            "source": "E8 (automated part only)",
            "caveat": "human response time/decision accuracy blocked - needs a real operator (see E23)",
        }

    # -- compact failure taxonomy, reusing E22's categories ------------------
    failure_taxonomy = None
    if "E22" in completed:
        failure_taxonomy = completed["E22"]["metrics"].get("per_category")

    # -- status roll-up -------------------------------------------------------
    status_summary = {
        "total_experiments": 33,
        "completed": len(completed),
        "blocked": len(blocked),
        "not_yet_run": 33 - len(completed) - len(blocked),
        "completed_ids": sorted(completed.keys()),
        "blocked_ids": sorted(blocked.keys()),
    }

    print("\n=== Status roll-up ===")
    for k, v in status_summary.items():
        print(f"  {k}: {v}")
    print("\n=== Primary metrics available today ===")
    for k, v in primary_metrics.items():
        print(f"  {k}: {v}")

    write_report(
        "E33",
        "Overall Systems Benchmark",
        config={
            "aggregates": sorted(all_results.keys()),
            "note": "run last; aggregates other experiments' results rather than running new trials",
        },
        metrics={
            "status_summary": status_summary,
            "primary_metrics": primary_metrics,
            "failure_taxonomy": failure_taxonomy,
        },
        trials=[],
        notes=(
            "The PDF's own primary-metrics line is truncated in the source "
            "document ('...RecoveryRate, HumanEs...') - the exact intended final "
            "metric list could not be confirmed and should be re-checked against "
            "the original PDF. This report aggregates what's measurable today: "
            f"{len(completed)}/33 experiments completed, {len(blocked)}/33 "
            f"explicitly blocked (Webots install, human operator, or exhausted "
            "quota - see README.md's status table for which), "
            f"{status_summary['not_yet_run']}/33 not yet attempted. A real "
            "statistical comparison against baselines with confidence intervals, "
            "and qualitative examples of representative episodes, both need the "
            "quota-blocked experiments (especially E1's clean re-run and E2) to "
            "exist first - this is an honest snapshot of current coverage, not "
            "the final benchmark result the PDF describes."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
