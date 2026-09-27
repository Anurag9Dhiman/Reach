"""Shared mixed physical-digital task definitions, reused by E1, E2, E9,
E10, E14, E29, E33 rather than each experiment inventing its own task list.

Goal strings are written for an LLM planner (GeminiPlanner) that can reason
about what a task needs - RuleBasedPlanner can't extract real coordinates or
judge whether a step needs a computer (see par.core.planner.RuleBasedPlanner
._extract_params, which always returns (0,0,0) for `move`), so it's only
used as the deterministic baseline arm, not for goal-following correctness.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Matches E2's six task categories exactly.
PHYSICAL_ONLY = "physical_only"
DIGITAL_ONLY = "digital_only"
PHYSICAL_TO_DIGITAL = "physical_to_digital"
DIGITAL_TO_PHYSICAL = "digital_to_physical"
MULTI_STAGE = "multi_stage"
MULTI_DELEGATION = "multi_delegation"


@dataclass
class Task:
    id: str
    category: str
    difficulty: int  # 1 (simplest) .. 3
    goal: str
    requires_computer: bool
    expected_skills: list[str] = field(default_factory=list)  # skills a correct plan should touch, in order


TASKS: list[Task] = [
    # -- physical-only: no digital step, should never delegate ------------
    Task("phys-1", PHYSICAL_ONLY, 1, "Detect the objects in the workspace.",
         requires_computer=False, expected_skills=["detect"]),
    Task("phys-2", PHYSICAL_ONLY, 2, "Pick up the red_object and place it at the blue_container.",
         requires_computer=False, expected_skills=["pick", "place"]),
    Task("phys-3", PHYSICAL_ONLY, 3, "Inspect the red_object, then move to the blue_container, then stop.",
         requires_computer=False, expected_skills=["inspect", "move", "stop"]),

    # -- digital-only: no physical step needed ------------------------------
    Task("dig-1", DIGITAL_ONLY, 1, "Look up today's date using the computer.",
         requires_computer=True, expected_skills=["use_computer"]),
    Task("dig-2", DIGITAL_ONLY, 2, "Search the computer for the specification of part number PN-4471.",
         requires_computer=True, expected_skills=["use_computer"]),

    # -- physical-to-digital: read the physical world, then use a computer --
    Task("p2d-1", PHYSICAL_TO_DIGITAL, 1,
         "Inspect the red_object to read its display, then use the computer to log the reading you found.",
         requires_computer=True, expected_skills=["inspect", "use_computer"]),
    Task("p2d-2", PHYSICAL_TO_DIGITAL, 2,
         "Detect the objects present, then use the computer to search for a maintenance record for whichever "
         "object you found closest to the origin.",
         requires_computer=True, expected_skills=["detect", "use_computer"]),

    # -- digital-to-physical: look something up, then act on it physically --
    Task("d2p-1", DIGITAL_TO_PHYSICAL, 1,
         "Use the computer to look up which container the red_object belongs in, then move to the blue_container.",
         requires_computer=True, expected_skills=["use_computer", "move"]),
    Task("d2p-2", DIGITAL_TO_PHYSICAL, 2,
         "Use the computer to check today's task list, then pick up the red_object and place it at the "
         "blue_container as instructed.",
         requires_computer=True, expected_skills=["use_computer", "pick", "place"]),

    # -- multi-stage: several physical+digital steps interleaved ------------
    Task("multi-1", MULTI_STAGE, 2,
         "Inspect the red_object, use the computer to log what you found, then move to the blue_container and "
         "stop.",
         requires_computer=True, expected_skills=["inspect", "use_computer", "move", "stop"]),
    Task("multi-2", MULTI_STAGE, 3,
         "Detect the objects present, pick up the red_object, use the computer to record that you picked it up, "
         "then place it at the blue_container.",
         requires_computer=True, expected_skills=["detect", "pick", "use_computer", "place"]),

    # -- multi-delegation: more than one computer step in the same task -----
    Task("multidel-1", MULTI_DELEGATION, 2,
         "Use the computer to look up today's date, then use the computer again to look up the current weather, "
         "then move to the blue_container.",
         requires_computer=True, expected_skills=["use_computer", "use_computer", "move"]),
    Task("multidel-2", MULTI_DELEGATION, 3,
         "Inspect the red_object, use the computer to look up its specification, use the computer again to log "
         "your inspection result, then move to the blue_container and stop.",
         requires_computer=True, expected_skills=["inspect", "use_computer", "use_computer", "move", "stop"]),
]


def by_category(category: str) -> list[Task]:
    return [t for t in TASKS if t.category == category]


def by_id(task_id: str) -> Task:
    for t in TASKS:
        if t.id == task_id:
            return t
    raise KeyError(task_id)
