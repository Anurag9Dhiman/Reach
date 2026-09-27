# E32: End-to-End Robustness Under Combined Failures

Generated: 2026-09-26T23:34:50.126443+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, mode=EXPLICIT_FAILURE)
- **combined_failure_types**: ['safety_denial', 'acs_failure', 'physical/network combined with human_rejection (scenario 2)']

## Metrics

- **scenario_1_safe_terminal_state**: True
- **scenario_2_safe_terminal_state**: False
- **any_crash**: False
- **both_reached_safe_state**: False

## Notes

Neither scenario crashes or hangs, but they terminate differently, and the difference is a real gap worth flagging rather than smoothing over: scenario 1's ACS failure is a genuine execution failure, so Agent.record_result correctly marks the agent FAILED - a clean, safe terminal state. Scenario 2's human rejection is a safety DENY, not a genuine failure, and Agent.record_rejection deliberately does NOT change status away from PLANNING (by design, so a single denial doesn't wrongly abort an otherwise-recoverable task - see agent.py's record_rejection docstring). But when EVERY action in the task is denied and none ever succeeds or explicitly fails, run_task() simply exhausts max_steps and returns with the agent stuck at PLANNING - neither DONE nor FAILED. Runtime has no distinct terminal status for 'ran out of steps without resolving,' so a caller checking agent.state.status after run_task() returns cannot tell 'safely still retriable' apart from 'genuinely stuck' without separately checking whether steps were exhausted. Worth closing in a safety-critical deployment.

Full per-trial records: `E32_end_to_end_robustness_under_combined_failures.json`
