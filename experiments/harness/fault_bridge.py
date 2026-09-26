"""A controllable double for CollectiveOSBridge (par.integrations.collectiveos),
used by every experiment whose research question is about PAR's own
resilience to bad/slow/flaky ACS behavior rather than the ACS's actual
intelligence (E4, E5, E6, E7, E10, E11, E12, E13, E20, E21, E24, E25, E30,
E31, E32 - see experiments/README.md's real-vs-fake table).

You cannot get a real network to drop packets, or a real LLM to return a
malformed reply, on demand and repeatably - so fault-injection experiments
are supposed to use a controllable double for this, the same way chaos
engineering injects faults into a real system rather than waiting for one.
This matches CollectiveOSBridge.run_task's exact signature/contract (never
raises, always returns an ActionResult) so ComputerAugmentedRobot and the
rest of PAR run completely unmodified against it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from par.core.action import Action, ActionResult


class FaultMode(str, Enum):
    SUCCESS = "success"                    # normal happy path
    TIMEOUT = "timeout"                    # ACS never replies within `timeout`
    CONNECTION_REFUSED = "connection_refused"  # network/server unreachable
    AUTH_FAILURE = "auth_failure"          # bad/expired token
    MALFORMED_REPLY = "malformed_reply"    # ACS sent unparseable data
    INCOMPLETE_RESULT = "incomplete_result"    # success, but empty/truncated message
    INCORRECT_RESULT = "incorrect_result"      # success, but the answer is wrong
    AMBIGUOUS_RESULT = "ambiguous_result"      # success, but the answer is unclear
    EXPLICIT_FAILURE = "explicit_failure"      # ACS cleanly reports it failed


@dataclass
class FaultyCollectiveOSBridge:
    """Duck-typed stand-in for CollectiveOSBridge.

    `mode`: fixed fault mode for every call, OR
    `sequence`: a list of modes consumed one per call (repeats the last
    entry once exhausted) - use this to simulate "fails twice then
    recovers" for failure-recovery experiments (E11, E32).
    `latency`: simulated ACS response time in seconds, applied before
    returning (capped in tests - keep this small; it's wall-clock sleep).
    `incorrect_message` / `ambiguous_message`: override text for those modes.
    """

    mode: FaultMode = FaultMode.SUCCESS
    sequence: list[FaultMode] | None = None
    latency: float = 0.0
    correct_message: str = "task completed correctly"
    incorrect_message: str = "the wrong answer, presented as if correct"
    ambiguous_message: str = "it might be done, or it might not, unclear"
    calls: list[dict] = field(default_factory=list)

    def _next_mode(self) -> FaultMode:
        if self.sequence is None:
            return self.mode
        index = min(len(self.calls), len(self.sequence) - 1)
        return self.sequence[index]

    def run_task(self, action: Action, task: str, timeout: float) -> ActionResult:
        mode = self._next_mode()
        self.calls.append({"task": task, "timeout": timeout, "mode": mode.value})

        if self.latency:
            time.sleep(min(self.latency, timeout + 1) if mode == FaultMode.TIMEOUT else self.latency)

        if mode == FaultMode.TIMEOUT:
            return self._result(action, False, f"CollectiveOS did not reply within {timeout}s")
        if mode == FaultMode.CONNECTION_REFUSED:
            return self._result(action, False, "CollectiveOS connection failed: [Errno 61] Connection refused")
        if mode == FaultMode.AUTH_FAILURE:
            return self._result(action, False, "CollectiveOS connection failed: server rejected WebSocket connection: HTTP 403")
        if mode == FaultMode.MALFORMED_REPLY:
            return self._result(action, False, "CollectiveOS sent an invalid reply: Expecting value: line 1 column 1 (char 0)")
        if mode == FaultMode.EXPLICIT_FAILURE:
            return self._result(action, False, "the requested application could not be found")
        if mode == FaultMode.INCOMPLETE_RESULT:
            return self._result(action, True, "")
        if mode == FaultMode.INCORRECT_RESULT:
            return self._result(action, True, self.incorrect_message)
        if mode == FaultMode.AMBIGUOUS_RESULT:
            return self._result(action, True, self.ambiguous_message)
        return self._result(action, True, self.correct_message)

    def _result(self, action: Action, success: bool, message: str) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            success=success,
            message=message,
            completed_at=datetime.now(timezone.utc),
        )
