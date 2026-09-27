"""E21: Capability Abstraction Evaluation

RQ: Does representing computer use as one high-level capability simplify
planning/integration compared to exposing low-level GUI operations to the
physical planner?

Scope, stated honestly: comparing a real planner's *live* behavior under
both interfaces needs an LLM actually choosing actions, which is blocked by
the exhausted Gemini quota today. What's measured here instead is the
*structural* difference between the two interfaces - capability surface
size, input schema complexity, and the minimum number of calls a
hand-authored low-level decomposition needs vs. the high-level call for the
same task - not planner-generated invalid-action rates, which need a live
LLM and are left as quota-blocked future work.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_report

from par.core.capability import Capability, RiskLevel
from par.core.skill import ParameterizedSkill, SkillRegistry
from par.skills.computer_use import computer_use_skill

LOW_LEVEL_SPECS = [
    ("screenshot", "Capture the current screen", {}),
    ("click", "Click at a screen coordinate", {"x": "int", "y": "int"}),
    ("type_text", "Type text at the current focus", {"text": "str"}),
    ("scroll", "Scroll the current window", {"direction": "str", "amount": "int"}),
    ("browser_navigate", "Navigate the browser to a URL", {"url": "str"}),
]


def build_low_level_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for name, description, input_schema in LOW_LEVEL_SPECS:
        registry.register(
            ParameterizedSkill(
                Capability(name=name, description=description, input_schema=input_schema, risk=RiskLevel.MEDIUM),
                required_params=set(input_schema.keys()),
            )
        )
    return registry


def build_high_level_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(computer_use_skill())
    return registry


# A hand-authored minimum decomposition of "look up today's date and log it
# in a note" under the low-level interface, for the call-count comparison.
LOW_LEVEL_TASK_DECOMPOSITION = [
    "screenshot", "click", "type_text",  # open a search/notes surface, focus it
    "screenshot", "click",               # read the result, click to confirm/save
]


def main() -> None:
    high = build_high_level_registry()
    low = build_low_level_registry()

    high_level_calls_needed = 1  # use_computer(task="look up today's date and log it")
    low_level_calls_needed = len(LOW_LEVEL_TASK_DECOMPOSITION)

    high_level_params = sum(len(c.input_schema) for c in high.capabilities())
    low_level_params = sum(len(c.input_schema) for c in low.capabilities())

    metrics = {
        "high_level": {
            "n_capabilities_exposed_to_planner": len(high.capabilities()),
            "total_input_schema_fields": high_level_params,
            "calls_needed_for_example_task": high_level_calls_needed,
        },
        "low_level": {
            "n_capabilities_exposed_to_planner": len(low.capabilities()),
            "total_input_schema_fields": low_level_params,
            "calls_needed_for_example_task": low_level_calls_needed,
            "example_decomposition": LOW_LEVEL_TASK_DECOMPOSITION,
        },
        "call_count_ratio_low_to_high": low_level_calls_needed / high_level_calls_needed,
    }

    print(f"high-level: {metrics['high_level']}")
    print(f"low-level:  {metrics['low_level']}")
    print(f"low-level needs {metrics['call_count_ratio_low_to_high']:.0f}x as many calls for this example task")

    write_report(
        "E21",
        "Capability Abstraction Evaluation",
        config={
            "example_task": "look up today's date and log it in a note",
            "note": "structural comparison only - see module docstring for why a live planner comparison is out of scope today",
        },
        metrics=metrics,
        trials=[],
        notes=(
            "The high-level interface exposes 1 capability with 1 parameter to "
            "the planner and needs 1 call for the example task; the low-level "
            "interface exposes 5 capabilities with 6 parameters total and needs "
            f"{low_level_calls_needed} calls for the same task (a hand-authored "
            "minimum decomposition, not planner-generated). This supports the "
            "PDF's premise directionally (fewer capabilities, fewer parameters, "
            "fewer calls per task under the high-level interface) but does not "
            "measure planning latency or invalid-action rate under a live "
            "planner, which needs real LLM calls currently blocked by the "
            "exhausted Gemini quota - see README.md."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
