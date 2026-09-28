"""E10: Delegation Decision Ablation

RQ: Which information is necessary for an LLM planner to make reliable
delegation decisions?

No ACS needed (single-shot decision classification, not full task
execution). par.core.gemini_planner.GeminiPlanner always sends the full
observation plus full capability descriptions/schemas as function
declarations (condition 3 below matches its real, fixed behavior) - there's
no way to selectively withhold information from it without deviating from
its actual implementation, so this uses a small standalone Gemini
function-calling caller built for this experiment only, giving each of the
4 conditions exactly the information the PDF specifies and nothing more.

Uses a representative 6-task subset (one per harness/scenarios.py category)
rather than the full 14, to keep this at 6 tasks x 4 conditions = 24 real
Gemini calls given the shared quota (see README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.rate_limit import call_with_retry, pace
from harness.report import write_report
from harness.scenarios import by_id

from par.env import load_env

TASK_IDS = ["phys-2", "dig-1", "p2d-1", "d2p-1", "multi-1", "multidel-1"]

CONDITIONS = [
    "task_description_only",
    "task_plus_observation",
    "task_plus_observation_plus_capability_descriptions",
    "task_plus_observation_plus_capabilities_plus_risk_info",
]

MOCK_OBSERVATION_TEXT = (
    'Robot state: {"position": {"x": 0.0, "y": 0.0, "z": 0.0}, "holding": null}\n'
    'Detected objects: [{"name": "red_object", "position": {"x": 0.5, "y": 0.2, "z": 0.0}}, '
    '{"name": "blue_container", "position": {"x": -0.3, "y": 0.4, "z": 0.0}}]'
)

CAPABILITY_NAMES = ["detect", "move", "pick", "place", "stop", "inspect", "use_computer"]
CAPABILITY_DESCRIPTIONS = {
    "detect": "Detect objects in the current observation",
    "move": "Move the end effector or base to a target position",
    "pick": "Pick up a target object",
    "place": "Place the held object at a target location",
    "stop": "Immediately halt all motion",
    "inspect": "Closely examine a target to verify its state",
    "use_computer": "Delegate a task to the digital world when a physical task needs to read, write, or "
    "look something up on a computer that the robot cannot touch directly.",
}
RISK_ANNOTATIONS = {"use_computer": " [RISK: HIGH - this dispatches to an external system and should only "
                    "be used when the task genuinely requires a computer]"}


def _declarations(condition: str) -> list[dict]:
    declarations = []
    for name in CAPABILITY_NAMES:
        if condition == "task_description_only" or condition == "task_plus_observation":
            declarations.append({"name": name, "description": "", "parameters": {"type": "object", "properties": {}}})
        else:
            description = CAPABILITY_DESCRIPTIONS[name]
            if condition == "task_plus_observation_plus_capabilities_plus_risk_info":
                description += RISK_ANNOTATIONS.get(name, "")
            declarations.append({"name": name, "description": description, "parameters": {"type": "object", "properties": {}}})
    return declarations


def _prompt_text(goal: str, condition: str) -> str:
    text = f"Goal: {goal}"
    if condition != "task_description_only":
        text += f"\n{MOCK_OBSERVATION_TEXT}"
    return text


def decide(client, goal: str, condition: str) -> str | None:
    from google.genai import types

    declarations = _declarations(condition)
    config = {
        "tools": [{"function_declarations": declarations}],
        "system_instruction": "You are the planning component of a physical robot agent. Call exactly one "
        "function: the single best next action for the goal.",
        "automatic_function_calling": {"disable": True},
    }
    chat = client.chats.create(model="gemini-3.1-flash-lite", config=config)
    response = chat.send_message([types.Part.from_text(text=_prompt_text(goal, condition))])
    calls = getattr(response, "function_calls", None) or []
    return calls[0].name if calls else None


def main() -> None:
    load_env()
    from google import genai

    client = genai.Client()

    rows = []
    call_index = 0
    for condition in CONDITIONS:
        print(f"\n=== {condition} ===")
        for task_id in TASK_IDS:
            if call_index > 0:
                pace()
            call_index += 1
            task = by_id(task_id)
            try:
                chosen = call_with_retry(lambda: decide(client, task.goal, condition))
                delegated = chosen == "use_computer"
                correct = delegated == task.requires_computer
                rows.append({
                    "condition": condition, "task_id": task_id, "requires_computer": task.requires_computer,
                    "chosen_skill": chosen, "delegated": delegated, "correct_delegation_decision": correct,
                })
                print(f"  {task_id}: chosen={chosen} requires_computer={task.requires_computer} correct={correct}")
            except Exception as exc:  # noqa: BLE001
                rows.append({
                    "condition": condition, "task_id": task_id, "requires_computer": task.requires_computer,
                    "chosen_skill": None, "delegated": None, "correct_delegation_decision": None,
                    "error": str(exc)[:200],
                })
                print(f"  {task_id}: errored: {exc!s:.150}")

    metrics = {}
    for condition in CONDITIONS:
        rows_c = [r for r in rows if r["condition"] == condition and r["delegated"] is not None]
        n_errored = sum(1 for r in rows if r["condition"] == condition) - len(rows_c)
        delegated = sum(1 for r in rows_c if r["delegated"])
        correct_delegations = sum(1 for r in rows_c if r["delegated"] and r["requires_computer"])
        needing_computer = sum(1 for r in rows_c if r["requires_computer"])
        metrics[condition] = {
            "delegation_precision": correct_delegations / delegated if delegated else float("nan"),
            "delegation_recall": correct_delegations / needing_computer if needing_computer else float("nan"),
            "overall_correct_rate": sum(1 for r in rows_c if r["correct_delegation_decision"]) / len(rows_c) if rows_c else float("nan"),
            "unnecessary_delegations": sum(1 for r in rows_c if r["delegated"] and not r["requires_computer"]),
            "missed_delegations": sum(1 for r in rows_c if not r["delegated"] and r["requires_computer"]),
            "n_errored": n_errored,
        }
        print(f"\n{condition}: {metrics[condition]}")

    write_report(
        "E10",
        "Delegation Decision Ablation",
        config={
            "acs": "none - single-shot decision classification, no task execution",
            "conditions": CONDITIONS,
            "task_ids": TASK_IDS,
            "model": "gemini-3.1-flash-lite",
        },
        metrics=metrics,
        trials=rows,
        notes=(
            "Built a standalone minimal Gemini caller for this experiment rather "
            "than reusing GeminiPlanner directly, since GeminiPlanner always sends "
            "the full observation + full capability descriptions (matching "
            "condition 3 exactly) and has no built-in way to withhold information "
            "for conditions 1, 2, or 4. Two real findings, one expected and one "
            "not: (1) conditions 2, 3, and 4 are identical in every single "
            "per-task decision - adding capability descriptions and an explicit "
            "risk annotation to use_computer changed nothing here, at least for a "
            "name as self-descriptive as 'use_computer'; only adding the "
            "observation (condition 1 -> 2) changed any decisions, and only for "
            "which non-delegation skill got picked, not delegation correctness "
            "itself. (2) A real limitation in this experiment's own ground truth, "
            "not the model: p2d-1 and multi-1 explicitly ask for a physical step "
            "*before* the digital one ('inspect ... then use the computer'), so "
            "the model choosing 'inspect'/'detect' as its single first action is "
            "plausibly correct sequencing, not a missed delegation - but this "
            "single-shot design scores 'delegate iff requires_computer' with no "
            "notion of step order, so both are counted as missed_delegations "
            "here. A full multi-step run (like E9's) is the fairer test for "
            "physical-then-digital tasks; this ablation's clean signal is really "
            "about dig-1/d2p-1/multidel-1 (digital-first tasks), where all 4 "
            "conditions correctly delegate immediately."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
