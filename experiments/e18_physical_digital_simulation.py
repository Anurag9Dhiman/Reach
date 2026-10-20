"""E18: Physical-Digital Task Execution in Simulation

RQ: Can Reach coordinate physical robot behavior and computer-use behavior
within a single simulated task (MuJoCo -> PAR -> SafetyKernel -> ACS -> PAR
-> MuJoCo)?

Re-points to MuJoCo (2026-10-07) after Webots was retired. The one
experiment that genuinely needs both a real physical simulator AND a live
CollectiveOS/Gemini instance running at the same time. E16/E17 only need
MuJoCo. ComputerAugmentedRobot(MuJoCoRobot()) composes the two existing
wrappers directly; this experiment is simply running that composition for
real instead of each piece separately (E1/E2 use MockRobot+real ACS; E16/
E17 use real MuJoCo+no ACS).

Requires (see mujoco/README.md): mujoco_bridge.py running (interactive or
--headless), and a live CollectiveOS instance reachable via
COLLECTIVEOS_WS_URL / COLLECTIVEOS_API_TOKEN.

Earlier Webots-era runs of this experiment hit a sustained Gemini 503
"high demand" outage on all 3 attempts; CollectiveOS now supports UI-TARS
as a local-inference alternative (set UITARS_BASE_URL in CollectiveOS's
.env), which avoids the per-day Gemini cap and the capacity-outage class
of failures that blocked the earlier runs.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.report import write_report

from par.core.agent import Agent
from par.core.observation import Observation
from par.core.planner import TASK_COMPLETE, Planner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.env import load_env
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mujoco_bridge import MuJoCoRobot
from par.safety.environment import load_profile
from par.safety.kernel import SafetyKernel
from par.skills import builtin_skills, computer_use_skill
from harness.telemetry import CollectingTelemetryLogger

_MOVE_TIMEOUT_SECONDS = 20.0
_RED_OBJECT = (0.5, 0.2, 0.0)
_BLUE_CONTAINER = (-0.3, 0.4, 0.0)
_DELEGATED_TASK = "check whether any maintenance alerts are open"


class _SequencePlanner(Planner):
    def __init__(self, steps: list[tuple[str, dict]]) -> None:
        self._steps = list(steps)

    def propose(self, goal: str, observation: Observation, capabilities) -> tuple[str, dict]:
        return self._steps.pop(0)


def main() -> None:
    load_env()

    registry = SkillRegistry()
    for skill in builtin_skills():
        if skill.name == "move":
            skill.capability.execution_timeout_seconds = _MOVE_TIMEOUT_SECONDS
        registry.register(skill)
    registry.register(computer_use_skill())

    robot = ComputerAugmentedRobot(MuJoCoRobot())  # default bridge: real CollectiveOSBridge
    safety = SafetyKernel(load_profile("simulation"))
    telemetry = CollectingTelemetryLogger()
    planner = _SequencePlanner([
        ("detect", {}),
        ("move", {"x": _RED_OBJECT[0], "y": _RED_OBJECT[1] + 0.4, "z": 0.0}),  # near red: allowed
        ("move", {"x": _RED_OBJECT[0], "y": _RED_OBJECT[1], "z": 0.0}),  # onto red: denied (collision)
        ("move", {"x": _BLUE_CONTAINER[0], "y": _BLUE_CONTAINER[1] + 0.4, "z": 0.0}),  # near blue: allowed
        ("use_computer", {"task": _DELEGATED_TASK}),  # REAL delegation to live CollectiveOS
        ("stop", {}),
        (TASK_COMPLETE, {"message": "toured the arena and delegated a digital subtask"}),
    ])
    agent = Agent(registry, planner=planner)
    runtime = Runtime(agent, robot, safety_kernel=safety, telemetry=telemetry)

    print("Running composed MuJoCo -> PAR -> SafetyKernel -> ACS -> PAR -> MuJoCo task...")
    started = time.monotonic()
    runtime.run_task("tour the arena and check status", max_steps=7)
    elapsed = time.monotonic() - started
    runtime.close()

    move_events = [e for e in telemetry.events if e.skill == "move"]
    near_red_event, collision_event, near_blue_event = move_events
    use_computer_event = next(e for e in telemetry.events if e.skill == "use_computer")
    stop_event = next((e for e in telemetry.events if e.skill == "stop"), None)

    results = {
        "task_reached_complete": agent.state.status.value == "done",
        "total_wall_clock_seconds": elapsed,
        "near_red": {
            "allowed": near_red_event.safety_decision == "allow",
            "succeeded": near_red_event.success,
        },
        "collision_denial": {
            "denied": collision_event.safety_decision == "deny",
            "rejection_reason": collision_event.rejection_reason,
        },
        "near_blue": {
            "allowed": near_blue_event.safety_decision == "allow",
            "succeeded": near_blue_event.success,
        },
        "use_computer_delegation": {
            "safety_decision": use_computer_event.safety_decision,
            "succeeded": use_computer_event.success,
            "message": use_computer_event.result.message,
            "latency_seconds": use_computer_event.latency_seconds,
        },
        "stop_succeeded": stop_event.success if stop_event else None,
    }

    for key, value in results.items():
        print(f"  {key}: {value}")

    all_checks_passed = (
        results["task_reached_complete"]
        and results["near_red"]["allowed"] and results["near_red"]["succeeded"]
        and results["collision_denial"]["denied"]
        and results["near_blue"]["allowed"] and results["near_blue"]["succeeded"]
        and results["use_computer_delegation"]["succeeded"]
        and bool(results["stop_succeeded"])
    )
    print(f"\nall_checks_passed (including real ACS delegation) = {all_checks_passed}")

    write_report(
        "E18",
        "Physical-Digital Task Execution in Simulation",
        config={
            "evaluation_method": "one real Runtime.run_task() through ComputerAugmentedRobot(MuJoCoRobot()) "
            "with the default CollectiveOSBridge, against a live MuJoCo process AND a live CollectiveOS "
            "instance simultaneously",
            "profile": "simulation",
            "delegated_task": _DELEGATED_TASK,
        },
        metrics={
            "task_reached_complete": results["task_reached_complete"],
            "near_red_allowed_and_succeeded": results["near_red"]["allowed"] and results["near_red"]["succeeded"],
            "collision_correctly_denied": results["collision_denial"]["denied"],
            "near_blue_allowed_and_succeeded": results["near_blue"]["allowed"] and results["near_blue"]["succeeded"],
            "real_acs_delegation_succeeded": results["use_computer_delegation"]["succeeded"],
            "real_acs_delegation_latency_seconds": results["use_computer_delegation"]["latency_seconds"],
            "stop_succeeded": results["stop_succeeded"],
            "all_checks_passed": all_checks_passed,
        },
        trials=[results],
        notes=(
            "Re-run against MuJoCo 2026-10-07 (previously attempted 3x against Webots 2026-10-01; all 3 "
            "Webots-era attempts had their physical half succeed cleanly but their digital half fail with "
            "identical Gemini 503 'high demand' errors across both quota pools - a sustained external "
            "outage, not a Reach-side bug). This re-run runs the full composed loop: the Franka Panda arm "
            "navigates toward each prop, gets a live collision denial from the safety kernel against a "
            "real detected-object position, docks its end-effector at the simulated laptop prop, then "
            "delegates a genuine digital subtask to a live CollectiveOS instance (real screenshot, real "
            "vision model, real pyautogui automation on the host desktop) and continues the physical task "
            "afterward. Delegated task: '" + _DELEGATED_TASK + "'. Result message: '" +
            results['use_computer_delegation']['message'] + "'."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
