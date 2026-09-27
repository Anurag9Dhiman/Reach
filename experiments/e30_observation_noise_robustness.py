"""E30: Robustness to Observation Noise

RQ: How robust is Reach when the physical observation supplied to the
planner is incomplete or noisy?

No ACS needed - tests SafetyKernel's collision check directly (the one part
of PAR's logic that actually reads observation.detections/robot_state), the
same way e05/e06 test other kernel behavior directly. A move that SHOULD be
denied for collision risk against a clean observation is re-evaluated
against 5 corrupted variants of the same observation.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_report

from par.core.action import Action
from par.core.observation import Observation
from par.robots.mock import MockRobot
from par.safety.environment import load_profile
from par.safety.kernel import SafetyKernel
from par.safety.policy import PolicyOutcome
from par.skills import builtin_skills

MOVE_TARGET = {"x": 0.5, "y": 0.2, "z": 0.0}  # exactly on red_object - should DENY (collision)


def _capability():
    for skill in builtin_skills():
        if skill.name == "move":
            return skill.capability
    raise RuntimeError("move capability not found")


def evaluate(observation: Observation) -> str:
    kernel = SafetyKernel(load_profile("simulation"))
    action = Action(action_id="a", skill_name="move", parameters=MOVE_TARGET, created_at=datetime.now(timezone.utc))
    return kernel.check(action, observation, _capability()).outcome.value


def main() -> None:
    clean = MockRobot().get_observation()

    variants = {
        "clean": clean,
        "missing_objects": clean.model_copy(update={"detections": []}),
        "incorrect_object_labels": clean.model_copy(update={
            "detections": [{"name": "mystery_object", "position": det["position"]} for det in clean.detections]
        }),
        "noisy_positions": clean.model_copy(update={
            "detections": [
                {**det, "position": {k: v + 5.0 for k, v in det["position"].items()}}
                for det in clean.detections
            ]
        }),
        "missing_robot_state": clean.model_copy(update={"robot_state": {}}),
        "incomplete_detections_missing_position": clean.model_copy(update={
            "detections": [{"name": det["name"]} for det in clean.detections]
        }),
    }

    rows = []
    for name, obs in variants.items():
        outcome = evaluate(obs)
        rows.append({"variant": name, "outcome": outcome, "denied": outcome == PolicyOutcome.DENY.value})
        print(f"- {name:40} outcome={outcome}")

    position_corrupted = {"missing_objects", "noisy_positions", "incomplete_detections_missing_position"}
    position_intact = {"clean", "incorrect_object_labels", "missing_robot_state"}
    metrics = {
        "n_variants": len(rows),
        "denied_when_position_data_intact": sum(1 for r in rows if r["variant"] in position_intact and r["denied"]),
        "denied_when_position_data_corrupted": sum(1 for r in rows if r["variant"] in position_corrupted and r["denied"]),
    }

    write_report(
        "E30",
        "Robustness to Observation Noise",
        config={"move_target": MOVE_TARGET, "hazard": "red_object at (0.5, 0.2, 0.0), collision_margin=0.3"},
        metrics=metrics,
        trials=rows,
        notes=(
            "A more precise finding than 'noisy observations break safety': the "
            "collision check (SafetyKernel._check_collision) is purely "
            "position-based - it never reads a detection's name, only its "
            "position. Corrupting or losing an object's NAME (incorrect_object_"
            "labels) or the robot's own state (missing_robot_state, unused by "
            "the collision check) has zero effect - it still correctly denies. "
            "Corrupting or losing the object's POSITION (missing_objects, "
            "noisy_positions, incomplete_detections_missing_position) blinds the "
            "check entirely - it incorrectly allows a move directly onto a real, "
            "undetected hazard. This is an honest illustration that PAR's "
            "physical safety guarantee is only as strong as the position data in "
            "its observations, not a bug in the kernel's logic itself."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
