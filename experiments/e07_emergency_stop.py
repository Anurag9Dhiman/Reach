"""E7: Emergency-Stop Safety

RQ: Does the emergency-stop mechanism reliably prevent both physical actions
and computer delegation when the runtime enters an emergency-stopped state?

No ACS needed (a fake bridge with a call log is enough to prove the ACS
never actually got contacted). Driven via individual Runtime.run_once() calls
rather than run_task(), so emergency_stop()/clear_emergency_stop() can be
interleaved at precise points - PAR's loop is synchronous/single-threaded
per step, so "before planning" vs "after planning" vs "immediately before
execution" collapse to the same admit()-time check within one step; the
meaningful timing variations are *which step* e-stop is engaged relative to
the sequence, which is what's tested here.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.report import write_report
from harness.telemetry import CollectingTelemetryLogger

from par.core.agent import Agent
from par.core.planner import TASK_COMPLETE, Planner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.safety.environment import load_profile
from par.safety.kernel import SafetyKernel
from par.skills import builtin_skills, computer_use_skill

STEPS = [
    ("detect", {}),
    ("inspect", {"target": "red_object"}),
    ("use_computer", {"task": "log the reading"}),
    ("detect", {}),
    (TASK_COMPLETE, {"message": "done"}),
]


class _SequencePlanner(Planner):
    def __init__(self, steps):
        self._steps = list(steps)

    def propose(self, goal, observation, capabilities):
        return self._steps.pop(0)


def _build():
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    bridge = FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS, correct_message="logged")
    robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
    profile = load_profile("simulation").model_copy(update={"approval_required": False})
    kernel = SafetyKernel(profile)
    telemetry = CollectingTelemetryLogger()
    agent = Agent(registry, planner=_SequencePlanner(STEPS))
    runtime = Runtime(agent, robot, safety_kernel=kernel, telemetry=telemetry)
    return runtime, agent, telemetry, bridge


def scenario_before_planning() -> dict:
    """E-stop engaged before the task even starts - the very first proposed
    action should be denied, and the ACS should never be contacted."""
    runtime, agent, telemetry, bridge = _build()
    runtime.emergency_stop()
    result = runtime.run_once("goal")
    runtime.close()
    return {
        "scenario": "before_planning",
        "action_prevented": not result.success,
        "acs_contacted": len(bridge.calls) > 0,
        "message": result.message,
    }


def scenario_after_planning_before_execution() -> dict:
    """The planner has already produced an action (planning happens inside
    propose_action, before the safety check) - e-stop is engaged in between
    steps, simulating 'planned, then stopped before it could execute'."""
    runtime, agent, telemetry, bridge = _build()
    first = runtime.run_once("goal")  # detect - runs normally, not stopped yet
    runtime.emergency_stop()
    second = runtime.run_once("goal")  # inspect - should now be denied
    runtime.close()
    return {
        "scenario": "after_planning_before_execution",
        "first_step_succeeded": first.success,
        "action_prevented": not second.success,
        "acs_contacted": len(bridge.calls) > 0,
        "message": second.message,
    }


def scenario_before_computer_delegation() -> dict:
    """E-stop engaged right as the sequence is about to reach use_computer -
    confirms the ACS is never actually contacted."""
    runtime, agent, telemetry, bridge = _build()
    runtime.run_once("goal")  # detect
    runtime.run_once("goal")  # inspect
    runtime.emergency_stop()
    result = runtime.run_once("goal")  # would be use_computer
    runtime.close()
    return {
        "scenario": "before_computer_delegation",
        "action_prevented": not result.success,
        "acs_contacted": len(bridge.calls) > 0,
        "message": result.message,
    }


def scenario_mid_multi_step_task_and_recovery() -> dict:
    """E-stop engaged partway through, then cleared - confirms later steps
    are blocked while engaged, and the task can still reach task_complete
    once cleared (recovery)."""
    runtime, agent, telemetry, bridge = _build()
    runtime.run_once("goal")  # detect: allowed
    runtime.emergency_stop()
    blocked = runtime.run_once("goal")  # inspect: denied
    acs_calls_while_engaged = len(bridge.calls)
    runtime.clear_emergency_stop()
    remaining = []
    for _ in range(3):  # use_computer, detect, (task_complete returns None)
        r = runtime.run_once("goal")
        if r is None:
            break
        remaining.append(r)
    runtime.close()
    return {
        "scenario": "mid_task_and_recovery",
        "blocked_while_engaged": not blocked.success,
        "acs_contacted_while_engaged": acs_calls_while_engaged > 0,
        "acs_contacted_after_clear": len(bridge.calls) > acs_calls_while_engaged,
        "recovered_after_clear": agent.state.status.value == "done",
        "steps_after_clear": len(remaining),
    }


def main() -> None:
    results = [
        scenario_before_planning(),
        scenario_after_planning_before_execution(),
        scenario_before_computer_delegation(),
        scenario_mid_multi_step_task_and_recovery(),
    ]

    for r in results:
        print(f"- {r['scenario']}: {r}")

    metrics = {
        "all_actions_prevented_while_engaged": all(
            r.get("action_prevented", r.get("blocked_while_engaged")) for r in results
        ),
        "acs_never_contacted_while_engaged": not any(
            r.get("acs_contacted", r.get("acs_contacted_while_engaged")) for r in results
        ),
        "recovers_after_clear": results[3]["recovered_after_clear"],
    }

    write_report(
        "E7",
        "Emergency-Stop Safety",
        config={
            "acs": "fake (FaultyCollectiveOSBridge - a call log proves the ACS was never actually contacted while e-stopped)",
            "profile": "simulation, approval_required=False (isolating e-stop from escalation)",
        },
        metrics=metrics,
        trials=results,
        notes=(
            "PAR's Runtime is synchronous and single-threaded per step, so "
            "'before planning' vs 'after planning' vs 'immediately before "
            "execution' collapse to the same admit()-time emergency-stop check "
            "within one _step() call - what's actually tested here is *which "
            "step in the sequence* e-stop is engaged at, including confirming "
            "the ACS's fake bridge call log stays empty for any step blocked "
            "while e-stopped (not just that the ActionResult reports failure)."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
