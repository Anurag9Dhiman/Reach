"""E12: Communication Robustness

RQ: How robust is the PAR-ACS WebSocket bridge to communication degradation?

Fake ACS at the real WebSocket level (harness/fake_acs_server.py) - this
exercises PAR's actual CollectiveOSBridge network client, not an in-process
double, so latency/drops are real network-level behavior, just against a
controllable server instead of the real CollectiveOS.

Conditions, and an honest note on two of them: "packet loss" is approximated
as a per-connection drop probability (a real TCP packet loss simulation
would need raw socket manipulation this harness doesn't do); "ACS response
delay" is mechanistically identical to "increased latency" from the
client's point of view (CollectiveOSBridge cannot distinguish network
latency from ACS processing time) - kept as two conditions at different
magnitudes to match the PDF's naming, with this note recorded rather than
pretending they measure different things.

A real finding surfaces here too: CollectiveOSBridge.run_task() makes
exactly one connection attempt and never retries - "reconnection after
failure" is therefore not something the client does on its own; it is only
possible if whatever calls the bridge (the PAR planner, in a later step)
decides to try again, matching E11's retry-based recovery model.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fake_acs_server import FakeACSServer
from harness.report import write_report
from harness.stats import rate, summarize

from par.core.action import Action
from par.integrations.collectiveos import CollectiveOSBridge

N_TRIALS = 6
TOKEN = "e12-test-token"


def _action() -> Action:
    return Action(action_id="a", skill_name="use_computer", parameters={}, created_at=datetime.now(timezone.utc))


def run_condition(name: str, **server_kwargs) -> dict:
    calls = []
    with FakeACSServer(expected_token=TOKEN, reply_text="ok", **server_kwargs) as server:
        bridge = CollectiveOSBridge(ws_url=f"ws://localhost:{server.port}/robot/ws", api_token=TOKEN)
        for _ in range(N_TRIALS):
            started = time.monotonic()
            result = bridge.run_task(_action(), "task", timeout=5)
            elapsed = time.monotonic() - started
            calls.append({
                "success": result.success,
                "message": result.message,
                "latency_seconds": elapsed,
                "is_timeout": "did not reply within" in result.message,
            })

    n = len(calls)
    return {
        "condition": name,
        "message_delivery_rate": rate(sum(1 for c in calls if c["success"]), n),
        "task_completion_rate": rate(sum(1 for c in calls if c["success"]), n),
        "timeout_rate": rate(sum(1 for c in calls if c["is_timeout"]), n),
        "latency_seconds": summarize([c["latency_seconds"] for c in calls]).as_dict(),
        "calls": calls,
    }


def run_reconnection_after_failure() -> dict:
    """First attempt against a server that drops every connection mid-task;
    a second, fresh attempt against a healthy server succeeds - modeling
    recovery as a caller-level retry, since the bridge itself never retries."""
    with FakeACSServer(expected_token=TOKEN, drop_connection=True) as bad_server:
        bridge = CollectiveOSBridge(ws_url=f"ws://localhost:{bad_server.port}/robot/ws", api_token=TOKEN)
        first = bridge.run_task(_action(), "task", timeout=5)

    with FakeACSServer(expected_token=TOKEN, reply_text="recovered") as good_server:
        bridge = CollectiveOSBridge(ws_url=f"ws://localhost:{good_server.port}/robot/ws", api_token=TOKEN)
        second = bridge.run_task(_action(), "task", timeout=5)

    return {
        "condition": "reconnection_after_failure",
        "first_attempt_success": first.success,
        "retry_success": second.success,
        "recovered": (not first.success) and second.success,
    }


def main() -> None:
    results = {
        "normal": run_condition("normal"),
        "increased_latency": run_condition("increased_latency", latency=1.0),
        "acs_response_delay": run_condition("acs_response_delay", latency=3.0),
    }
    # Approximate packet loss as ~50% of connections dropped, by alternating
    # a dropping and a healthy server across trials (a single FakeACSServer
    # instance is one fixed behavior for its lifetime, so this is done as
    # two half-batches rather than a per-request coin flip).
    half = N_TRIALS // 2
    lossy_calls = []
    for drop in (True, False):
        with FakeACSServer(expected_token=TOKEN, reply_text="ok", drop_connection=drop) as server:
            bridge = CollectiveOSBridge(ws_url=f"ws://localhost:{server.port}/robot/ws", api_token=TOKEN)
            for _ in range(half):
                r = bridge.run_task(_action(), "task", timeout=5)
                lossy_calls.append({"success": r.success, "message": r.message})
    results["packet_loss_approx"] = {
        "condition": "packet_loss_approx (~50% connections dropped)",
        "message_delivery_rate": rate(sum(1 for c in lossy_calls if c["success"]), len(lossy_calls)),
        "task_completion_rate": rate(sum(1 for c in lossy_calls if c["success"]), len(lossy_calls)),
        "calls": lossy_calls,
    }
    results["temporary_disconnection"] = run_condition("temporary_disconnection", drop_connection=True)
    results["reconnection_after_failure"] = run_reconnection_after_failure()

    for name, r in results.items():
        print(f"- {name}: { {k: v for k, v in r.items() if k != 'calls'} }")

    write_report(
        "E12",
        "Communication Robustness",
        config={
            "acs": "fake, real WebSocket server (harness/fake_acs_server.py)",
            "n_trials_per_condition": N_TRIALS,
            "conditions": list(results.keys()),
        },
        metrics={name: {k: v for k, v in r.items() if k != "calls"} for name, r in results.items()},
        trials=[{"condition": name, **r} for name, r in results.items()],
        notes=(
            "'packet_loss_approx' is a per-connection drop probability, not real "
            "TCP-level packet loss. 'increased_latency' and 'acs_response_delay' "
            "are mechanistically identical from CollectiveOSBridge's point of view "
            "(it cannot distinguish network latency from ACS processing time) - "
            "kept as two conditions at different magnitudes (1s vs 3s) to match "
            "the PDF's naming. reconnection_after_failure confirms recovery is "
            "possible, but only because a fresh connection attempt was made "
            "against a healthy server - CollectiveOSBridge.run_task() itself "
            "makes exactly one attempt and never retries on its own."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
