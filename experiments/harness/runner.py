"""Generic multi-trial runner used by most experiment scripts: builds a
fresh Runtime (+ Agent + telemetry collector) per trial via a factory
function, runs one goal through it, and records what happened.

Fresh construction per trial matters - GeminiPlanner keeps chat state
(`self._chat`) across calls, MockRobot keeps mutable object/position state,
so reusing one Runtime across "independent trials" would leak state between
them and invalidate exactly the independence E1's "multiple independent
trials" language requires.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from par.core.action import ActionResult
from par.core.agent import Agent
from par.core.agent_state import AgentStatus
from par.core.runtime import Runtime
from par.telemetry.events import TelemetryEvent

from harness.telemetry import CollectingTelemetryLogger

BuildFn = Callable[[], tuple[Runtime, Agent, CollectingTelemetryLogger]]
SuccessFn = Callable[[list[ActionResult], Agent], bool]


def _default_success(step_results: list[ActionResult], agent: Agent) -> bool:
    """Reached task_complete. Only meaningful for planners that actually
    emit task_complete (GeminiPlanner, LLMPlanner, a scripted planner with
    it in the step list) - RuleBasedPlanner never does (see
    par.core.planner.RuleBasedPlanner: it keeps re-matching the same
    capability on the same goal text until something fails, since it has no
    completion signal at all). Pass a custom success_fn for RuleBasedPlanner
    trials, e.g. `lambda results, agent: bool(results) and results[-1].success`."""
    return agent.state.status == AgentStatus.DONE


@dataclass
class TrialResult:
    index: int
    goal: str
    task_success: bool
    step_results: list[ActionResult] = field(default_factory=list)
    events: list[TelemetryEvent] = field(default_factory=list)
    wall_time_seconds: float = 0.0
    replans: int = 0        # number of DENY safety outcomes during the trial
    escalations: int = 0    # number of ESCALATE safety outcomes during the trial
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "goal": self.goal,
            "task_success": self.task_success,
            "wall_time_seconds": self.wall_time_seconds,
            "replans": self.replans,
            "escalations": self.escalations,
            "error": self.error,
            "steps": [
                {
                    "skill": e.skill,
                    "safety_decision": e.safety_decision,
                    "success": e.success,
                    "latency_seconds": e.latency_seconds,
                    "message": e.result.message,
                }
                for e in self.events
            ],
        }


def run_trial(
    build_fn: BuildFn,
    goal: str,
    index: int = 0,
    max_steps: int = 10,
    success_fn: SuccessFn = _default_success,
) -> TrialResult:
    runtime, agent, telemetry = build_fn()
    error: str | None = None
    step_results: list[ActionResult] = []
    started = time.monotonic()
    try:
        step_results = runtime.run_task(goal, max_steps=max_steps)
    except Exception as exc:  # noqa: BLE001 - a trial failing outright is data, not a crash
        error = f"{type(exc).__name__}: {exc}"
    finally:
        elapsed = time.monotonic() - started
        runtime.close()

    task_success = error is None and success_fn(step_results, agent)
    replans = sum(1 for e in telemetry.events if e.safety_decision == "deny")
    escalations = sum(1 for e in telemetry.events if e.safety_decision == "escalate")
    return TrialResult(
        index=index,
        goal=goal,
        task_success=task_success,
        step_results=step_results,
        events=list(telemetry.events),
        wall_time_seconds=elapsed,
        replans=replans,
        escalations=escalations,
        error=error,
    )


def run_trials(
    build_fn: BuildFn,
    goal: str,
    n: int,
    max_steps: int = 10,
    success_fn: SuccessFn = _default_success,
) -> list[TrialResult]:
    return [run_trial(build_fn, goal, index=i, max_steps=max_steps, success_fn=success_fn) for i in range(n)]
