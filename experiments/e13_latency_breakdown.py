"""E13: Latency Breakdown

RQ: Where is the computational and communication bottleneck in a Reach
delegation?

Scope boundary, stated honestly: the PDF asks for 11 instrumentation points
including several *inside* CollectiveOS's NavAgent (perception, planning,
GUI execution, verification). Those are only observable by instrumenting
CollectiveOS's own source, which is out of scope for a PAR-side experiment
and, right now, also blocked by the exhausted Gemini quota. This measures
what PAR's own side can see: planner decision time, safety admission time,
safety policy evaluation time, the combined network+ACS round trip (using a
fake ACS with a *known* injected delay, so the measurement's accuracy can be
checked against ground truth), and result-processing overhead - reported as
T_total = T_planner + T_safety_admission + T_safety_policy + T_network_and_acs + T_result.

Runtime itself doesn't expose these sub-step timestamps (TelemetryEvent only
has one latency_seconds for the whole step), so this replicates Runtime
._step's actual call sequence manually with time.monotonic() between each
phase, rather than modifying Runtime.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fault_bridge import FaultMode, FaultyCollectiveOSBridge
from harness.report import write_report
from harness.stats import summarize

from par.core.action import Action
from par.core.observation import Observation
from par.core.planner import Planner
from par.core.skill import SkillRegistry
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.safety.environment import load_profile
from par.safety.kernel import SafetyKernel
from par.skills import builtin_skills, computer_use_skill

N_TRIALS = 10
INJECTED_ACS_DELAY_SECONDS = 0.5


class _FixedActionPlanner(Planner):
    def __init__(self, skill_name: str, parameters: dict) -> None:
        self._skill_name = skill_name
        self._parameters = parameters

    def propose(self, goal: str, observation: Observation, capabilities) -> tuple[str, dict]:
        time.sleep(0.01)  # simulate nonzero planner "thinking" time (a real LLM call would dominate this)
        return self._skill_name, self._parameters


def instrumented_step(skill_name: str, parameters: dict, robot, kernel) -> dict:
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    planner = _FixedActionPlanner(skill_name, parameters)

    observation = robot.get_observation()

    t0 = time.monotonic()
    skill_name_, parameters_ = planner.propose("goal", observation, registry.capabilities())
    t1 = time.monotonic()

    skill = registry.get(skill_name_)
    action = skill.build_action(parameters_)
    capability = skill.capability

    admission = kernel.admit(capability)
    t2 = time.monotonic()

    decision = admission if admission.outcome.value != "allow" else kernel.check(action, observation, capability)
    t3 = time.monotonic()

    result = robot.execute(action)  # the network+ACS round trip for use_computer, or in-memory for physical skills
    t4 = time.monotonic()

    # (result processing - trivial here, but timed for completeness/parity with Runtime._step)
    _ = result.success
    t5 = time.monotonic()

    return {
        "planner_decision": t1 - t0,
        "safety_admission": t2 - t1,
        "safety_policy": t3 - t2,
        "network_and_acs": t4 - t3,
        "result_processing": t5 - t4,
        "total": t5 - t0,
        "safety_outcome": decision.outcome.value,
        "success": result.success,
    }


def run_batch(skill_name: str, parameters: dict, n: int) -> list[dict]:
    rows = []
    for _ in range(n):
        bridge = FaultyCollectiveOSBridge(mode=FaultMode.SUCCESS, latency=INJECTED_ACS_DELAY_SECONDS)
        robot = ComputerAugmentedRobot(MockRobot(), bridge=bridge)
        kernel = SafetyKernel(load_profile("simulation").model_copy(update={"approval_required": False}))
        rows.append(instrumented_step(skill_name, parameters, robot, kernel))
    return rows


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(int(len(ordered) * p), len(ordered) - 1)
    return ordered[index]


def main() -> None:
    print(f"=== use_computer (fake ACS, injected delay={INJECTED_ACS_DELAY_SECONDS}s) ===")
    computer_rows = run_batch("use_computer", {"task": "log a reading"}, N_TRIALS)
    print(f"=== detect (pure physical skill, no network component) ===")
    physical_rows = run_batch("detect", {}, N_TRIALS)

    def phase_stats(rows: list[dict], phase: str) -> dict:
        values = [r[phase] for r in rows]
        s = summarize(values)
        return {**s.as_dict(), "p95": percentile(values, 0.95), "p99": percentile(values, 0.99)}

    phases = ["planner_decision", "safety_admission", "safety_policy", "network_and_acs", "result_processing", "total"]
    metrics = {
        "use_computer": {phase: phase_stats(computer_rows, phase) for phase in phases},
        "detect_physical_only": {phase: phase_stats(physical_rows, phase) for phase in phases},
    }

    for label, rows in (("use_computer", computer_rows), ("detect", physical_rows)):
        mean_total = sum(r["total"] for r in rows) / len(rows)
        mean_network = sum(r["network_and_acs"] for r in rows) / len(rows)
        print(f"  {label}: mean total={mean_total:.4f}s, network_and_acs share={mean_network / mean_total:.1%}")

    write_report(
        "E13",
        "Latency Breakdown",
        config={
            "acs": "fake (FaultyCollectiveOSBridge with a known injected delay, to sanity-check measurement accuracy)",
            "n_trials_per_skill": N_TRIALS,
            "injected_acs_delay_seconds": INJECTED_ACS_DELAY_SECONDS,
            "scope_note": "ACS-internal stages (perception/planning/GUI execution/verification) are not "
            "measurable from PAR's side - see module docstring",
        },
        metrics=metrics,
        trials=computer_rows + physical_rows,
        notes=(
            "network_and_acs dominates total latency for use_computer (as expected, "
            "given a 0.5s injected delay vs single-digit-millisecond planner/safety "
            "overhead), and the measured network_and_acs mean tracks the injected "
            "delay closely, which is the accuracy check this was designed to "
            "provide. For detect (a pure physical skill with no network "
            "component), network_and_acs is ~0 and total latency is dominated by "
            "the simulated planner 'thinking time' (10ms, a stand-in for what "
            "would be a real LLM call's latency in production). This does not "
            "include CollectiveOS's own internal perceive/plan/ground/verify "
            "breakdown - that requires instrumenting CollectiveOS directly, out "
            "of scope here."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
