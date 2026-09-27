"""E24: Multi-Robot Scalability

RQ: How does Reach behave when multiple physical agents share one ACS?

Fake ACS at the real WebSocket level (harness/fake_acs_server.py) - a real
CollectiveOS instance was deliberately avoided for this one even beyond the
exhausted quota: 8 concurrent real desktop-automation loops fighting over
one physical screen would not measure PAR's own concurrency handling, it
would measure undefined behavior from contending GUI automation, which
isn't this experiment's question. 1, 2, 4, 8 concurrent robot clients
against one fake ACS server.
"""
from __future__ import annotations

import concurrent.futures
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

TOKEN = "e24-test-token"
CLIENT_COUNTS = [1, 2, 4, 8]


def _action(robot_id: int) -> Action:
    return Action(
        action_id=f"robot-{robot_id}", skill_name="use_computer", parameters={},
        created_at=datetime.now(timezone.utc),
    )


def one_client_call(ws_url: str, robot_id: int) -> dict:
    bridge = CollectiveOSBridge(ws_url=ws_url, api_token=TOKEN)
    started = time.monotonic()
    result = bridge.run_task(_action(robot_id), f"task from robot {robot_id}", timeout=10)
    elapsed = time.monotonic() - started
    return {"robot_id": robot_id, "success": result.success, "latency_seconds": elapsed}


def run_for_n_clients(n: int) -> dict:
    with FakeACSServer(expected_token=TOKEN, reply_text="ok") as server:
        ws_url = f"ws://localhost:{server.port}/robot/ws"
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(lambda i: one_client_call(ws_url, i), range(n)))
        wall_time = time.monotonic() - started

        return {
            "n_clients": n,
            "connections_seen": server.connections_seen,
            "concurrent_peak": server.concurrent_peak,
            "throughput_requests_per_second": n / wall_time,
            "success_rate": rate(sum(1 for r in results if r["success"]), n),
            "latency_seconds": summarize([r["latency_seconds"] for r in results]).as_dict(),
            "all_requests_correctly_isolated": server.connections_seen == n,  # see notes
        }


def main() -> None:
    all_results = {}
    for n in CLIENT_COUNTS:
        result = run_for_n_clients(n)
        all_results[n] = result
        print(f"- n_clients={n}: success_rate={result['success_rate']:.2f} "
              f"throughput={result['throughput_requests_per_second']:.1f} req/s "
              f"concurrent_peak={result['concurrent_peak']}")

    write_report(
        "E24",
        "Multi-Robot Scalability",
        config={
            "acs": "fake, real WebSocket server (harness/fake_acs_server.py)",
            "client_counts": CLIENT_COUNTS,
        },
        metrics={str(n): r for n, r in all_results.items()},
        trials=[{"n_clients": n, **r} for n, r in all_results.items()],
        notes=(
            "Requests stay correctly associated with their originating robot by "
            "construction, not by any request-ID matching logic: each robot opens "
            "its own dedicated WebSocket connection (CollectiveOSBridge.run_task "
            "connects fresh per call), so there is no shared channel where "
            "cross-talk between robots could even occur at the transport level. "
            "The real production concern this doesn't cover is CollectiveOS's "
            "single shared NavAgent instance under concurrent load (a resource-"
            "contention question - e.g. 8 real desktop-automation loops on one "
            "screen - not a correctness/isolation one), which needs a real "
            "CollectiveOS instance and is out of scope for a fake-ACS experiment."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
