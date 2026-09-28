"""E27: Imitation Learning from Delegated Demonstrations (small proof-of-concept)

RQ: Can demonstrations generated through Reach delegation be used to train a
computer-use policy?

Scope, per the user's own decision when this was planned: a small
proof-of-concept only, not a rigorous benchmark - collecting enough
demonstrations, choosing a real model architecture, training, and evaluating
generalization is a real ML project on its own. This is also gated by E26's
actual finding: if today's real runs produced too few demonstrations to
learn anything from (a real, separate possibility - see E26's report on
NavAgent's early-return-on-exception behavior discarding most attempts),
this reports that honestly as data-insufficiency rather than fabricating
synthetic demonstrations and presenting a "trained policy" result based on
data that was never actually collected through real delegation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_blocked, write_report

MIN_DEMOS_FOR_POC = 3
DEMOS_DIR = Path("/Users/anuragdhiman/Documents/Reach/Reach/CollectiveOS/data/demonstrations")


def load_demos() -> list[dict]:
    if not DEMOS_DIR.exists():
        return []
    demos = []
    for path in sorted(DEMOS_DIR.glob("*.json")):
        try:
            demos.append(json.loads(path.read_text()))
        except Exception:  # noqa: BLE001
            continue
    return demos


def nearest_neighbor_policy(demos: list[dict], task: str) -> dict | None:
    """The smallest possible thing that could be called a 'policy': given a
    new task string, replay the first action of whichever training demo has
    the most word overlap with it. Not a trained model in any real sense -
    a proof that *some* signal in a handful of demonstrations is usable,
    nothing more. A real E27 needs real training data volume and a real
    architecture, which is out of scope here by design (see docstring)."""
    if not demos:
        return None
    task_words = set(task.lower().split())
    best, best_overlap = None, -1
    for demo in demos:
        overlap = len(task_words & set(demo.get("task", "").lower().split()))
        if overlap > best_overlap and demo.get("demos"):
            best, best_overlap = demo, overlap
    if best is None:
        return None
    return {"predicted_first_action": best["demos"][0].get("action"), "matched_training_task": best.get("task"),
            "word_overlap": best_overlap}


def main() -> None:
    demos = load_demos()
    print(f"Found {len(demos)} real demonstration file(s) in {DEMOS_DIR}")

    if len(demos) < MIN_DEMOS_FOR_POC:
        write_blocked(
            "E27",
            "Imitation Learning from Delegated Demonstrations",
            reason=f"only {len(demos)} real demonstration(s) available today (need >= {MIN_DEMOS_FOR_POC} even "
            f"for a proof-of-concept) - see E26's report: most real delegation attempts today failed via an "
            f"API-level exception before NavAgent ever saved a demonstration",
            unblock_condition="run E1/E2/E29 again on a day with less Gemini free-tier flakiness, or "
            "accumulate more real trials over time, until data/demonstrations/ has several files",
        )
        print("Wrote blocked-status report for E27 (insufficient real demonstration data).")
        return

    # Held-out split: last demo is held out, the rest are "training data" for
    # the toy nearest-neighbor lookup - illustrative only, not a real
    # train/val/test methodology at this data volume.
    train, held_out = demos[:-1], demos[-1]
    prediction = nearest_neighbor_policy(train, held_out.get("task", ""))

    metrics = {
        "n_demonstrations_available": len(demos),
        "n_training": len(train),
        "held_out_task": held_out.get("task"),
        "held_out_actual_first_action": held_out["demos"][0].get("action") if held_out.get("demos") else None,
        "toy_policy_prediction": prediction,
        "note": "illustrative proof-of-concept only - see module docstring",
    }

    write_report(
        "E27",
        "Imitation Learning from Delegated Demonstrations",
        config={"policy": "nearest-neighbor task-text lookup (toy POC, not a trained model)",
                "min_demos_required": MIN_DEMOS_FOR_POC},
        metrics=metrics,
        trials=demos,
        notes=(
            "This is a proof-of-concept illustrating the pipeline shape (collect "
            "demonstrations -> hold one out -> predict its first action from the "
            "rest), not a real imitation-learning result - a real E27 needs "
            "orders of magnitude more demonstrations and an actual model "
            "architecture (e.g. a small vision-language-action model fine-tuned "
            "on screenshot+action pairs), which is a dedicated ML project beyond "
            "this experiment's scope, per the original scope decision."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
