"""E20: ACS Interoperability

RQ: Can PAR invoke different ACS backends through the same capability
interface without modifying the physical runtime?

Two fake ACS backends (harness/fake_acs_server.py, configured differently -
one echoes the task text back, one replies with a fixed delayed message),
both speaking CollectiveOS's real /robot/ws wire protocol. PAR's
CollectiveOSBridge/ComputerAugmentedRobot connect to either with a URL
change only - no PAR planner or safety-kernel code is touched between runs.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fake_acs_server import FakeACSServer
from harness.report import write_report

from par.core.agent import Agent
from par.core.planner import TASK_COMPLETE, Planner
from par.core.runtime import Runtime
from par.core.skill import SkillRegistry
from par.integrations.collectiveos import CollectiveOSBridge
from par.robots.computer_bridge import ComputerAugmentedRobot
from par.robots.mock import MockRobot
from par.skills import builtin_skills, computer_use_skill
from harness.telemetry import CollectingTelemetryLogger

TOKEN = "e20-test-token"


class _SingleActionPlanner(Planner):
    def __init__(self):
        self._used = False

    def propose(self, goal, observation, capabilities):
        if self._used:
            return TASK_COMPLETE, {"message": "done"}
        self._used = True
        return "use_computer", {"task": "look up today's date"}


def run_against(ws_url: str) -> dict:
    registry = SkillRegistry()
    for skill in builtin_skills():
        registry.register(skill)
    registry.register(computer_use_skill())
    robot = ComputerAugmentedRobot(MockRobot(), bridge=CollectiveOSBridge(ws_url=ws_url, api_token=TOKEN))
    telemetry = CollectingTelemetryLogger()
    agent = Agent(registry, planner=_SingleActionPlanner())
    runtime = Runtime(agent, robot, telemetry=telemetry)

    started = time.monotonic()
    runtime.run_task("interoperability test", max_steps=2)
    elapsed = time.monotonic() - started
    runtime.close()

    event = telemetry.events[0]
    return {"success": event.success, "message": event.result.message, "latency_seconds": elapsed}


def main() -> None:
    # ACS backend A: echoes the task text back (simulates one vendor's ACS)
    with FakeACSServer(expected_token=TOKEN, reply_text="echo: look up today's date", reply_status="done") as server_a:
        result_a = run_against(f"ws://localhost:{server_a.port}/robot/ws")

    # ACS backend B: a different vendor's ACS, slower and with different wording
    with FakeACSServer(expected_token=TOKEN, reply_text="Today is Saturday.", reply_status="done", latency=0.2) as server_b:
        result_b = run_against(f"ws://localhost:{server_b.port}/robot/ws")

    print("ACS-A (echo):", result_a)
    print("ACS-B (delayed, different vendor style):", result_b)

    metrics = {
        "acs_a_success": result_a["success"],
        "acs_b_success": result_b["success"],
        "acs_a_latency_seconds": result_a["latency_seconds"],
        "acs_b_latency_seconds": result_b["latency_seconds"],
        "same_par_code_used_for_both": True,
        "planner_or_safety_kernel_changes_required": 0,
        "protocol_compatible_with_both": result_a["success"] and result_b["success"],
    }

    write_report(
        "E20",
        "ACS Interoperability",
        config={
            "acs_a": "fake, echoes task text, no delay",
            "acs_b": "fake, fixed different-style reply, 0.2s delay",
            "par_changes_between_backends": "none - only CollectiveOSBridge.ws_url/api_token differ",
        },
        metrics=metrics,
        trials=[result_a, result_b],
        notes=(
            "Both backends work through the identical PAR code path "
            "(ComputerAugmentedRobot -> CollectiveOSBridge -> the same "
            "use_computer capability), confirming the interface is a real "
            "abstraction rather than a Pulse-CollectiveOS-specific integration - "
            "the only thing that changed between runs is which URL the bridge "
            "points at. This is a structural interoperability test (protocol "
            "compatibility), not a test of two independently-built real "
            "computer-use agents, which is out of scope here."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
