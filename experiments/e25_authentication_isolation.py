"""E25: Authentication and Request Isolation

RQ: Can the PAR-ACS communication layer prevent unauthorized or cross-robot
task execution?

Fake ACS at the real WebSocket level. Honest scope note up front: the
current CollectiveOS/PAR auth scheme is a *single shared secret* with no
concept of per-robot identity at all (confirmed in the paper's Discussion
and README.md) - so "expired credentials," "unknown robot identity," and
"mismatched robot/request identifiers" are not representable as distinct
test cases against the real system, because there is no identity or
expiry mechanism to test. What's tested here is what actually exists: valid
vs. invalid vs. empty token, and whether a valid token can be replayed
(reused) - which it can, because there's no nonce or single-use mechanism
either. Report this as the security-boundary evaluation the PDF itself asks
for, not a claim of complete system security.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness.fake_acs_server import FakeACSServer
from harness.report import write_report

from par.core.action import Action
from par.integrations.collectiveos import CollectiveOSBridge

REAL_TOKEN = "e25-real-token"


def _action() -> Action:
    return Action(action_id="a", skill_name="use_computer", parameters={}, created_at=datetime.now(timezone.utc))


def try_token(ws_url: str, token: str) -> bool:
    bridge = CollectiveOSBridge(ws_url=ws_url, api_token=token)
    return bridge.run_task(_action(), "task", timeout=5).success


def main() -> None:
    with FakeACSServer(expected_token=REAL_TOKEN, reply_text="ok") as server:
        ws_url = f"ws://localhost:{server.port}/robot/ws"

        rows = [
            {"case": "valid_credentials", "accepted": try_token(ws_url, REAL_TOKEN), "expected_accepted": True},
            {"case": "invalid_credentials", "accepted": try_token(ws_url, "wrong-token"), "expected_accepted": False},
            {"case": "empty_credentials", "accepted": try_token(ws_url, ""), "expected_accepted": False},
            {"case": "expired_credentials", "accepted": None, "expected_accepted": None,
             "note": "not representable - no expiry mechanism exists in the current single-shared-secret scheme"},
            {"case": "unknown_robot_identity", "accepted": None, "expected_accepted": None,
             "note": "not representable - there is no per-robot identity concept at all, only one shared secret"},
            {"case": "mismatched_robot_request_identifiers", "accepted": None, "expected_accepted": None,
             "note": "not representable - requests carry no robot/request identifiers to mismatch"},
        ]

        # Replay: reuse the SAME valid token for a second, independent request.
        first_replay = try_token(ws_url, REAL_TOKEN)
        second_replay = try_token(ws_url, REAL_TOKEN)
        rows.append({
            "case": "request_replay",
            "accepted": second_replay,
            "expected_accepted": None,
            "note": f"first_use_accepted={first_replay}, replay_accepted={second_replay} - "
            "a valid token can be reused indefinitely; nothing invalidates it after one use",
        })

    for row in rows:
        print(f"- {row['case']:34} accepted={row['accepted']}  {row.get('note', '')}")

    testable = [r for r in rows if r["expected_accepted"] is not None]
    correct = sum(1 for r in testable if r["accepted"] == r["expected_accepted"])

    write_report(
        "E25",
        "Authentication and Request Isolation",
        config={"acs": "fake, real WebSocket server", "real_token_scheme": "single shared secret, no per-robot identity"},
        metrics={
            "testable_cases": len(testable),
            "correctly_handled": correct,
            "not_representable_cases": len(rows) - len(testable),
            "valid_token_is_replayable": second_replay,
        },
        trials=rows,
        notes=(
            "3 of 6 PDF-requested scenarios are not representable against the "
            "real auth scheme: it is a single shared secret with no per-robot "
            "identity, expiry, or request nonce at all. Of what IS testable: "
            "valid/invalid/empty tokens are all handled correctly (accept/reject/"
            "reject), but a valid token can be replayed indefinitely - there is "
            "no mechanism preventing reuse. This is exactly the limitation the "
            "paper's Discussion already names as 'adequate for one robot and one "
            "ACS instance in development but not for a multi-robot or "
            "multi-tenant deployment' - this experiment is the empirical "
            "confirmation of that claim, not a new finding."
        ),
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
