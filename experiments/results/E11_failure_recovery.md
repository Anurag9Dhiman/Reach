# E11: Failure Recovery

Generated: 2026-09-26T23:24:20.464798+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, one fault mode per trial)
- **failure_modes**: ['acs_timeout', 'connection_refused', 'auth_failure', 'malformed_reply', 'acs_explicit_failure']

## Metrics

- **failure_detection_rate**: 1.0
- **within_run_task_recovery_rate**: 0.0
- **retry_recovery_rate**: 1.0

## Notes

within_run_task_recovery_rate is 0/5 by design, not a bug: Runtime treats any genuine execution failure as terminal for the current run_task() call (Agent.record_result marks FAILED; only safety DENY/ESCALATE outcomes get fed back for re-planning within the same call - see Agent.record_result vs record_rejection). retry_recovery_rate measures the more realistic notion of recovery: a fresh run_task() call, informed the previous one failed, succeeds once the transient fault clears. This is itself a limitation worth carrying into future work: PAR has no built-in retry-with-backoff for transient ACS failures (503/timeout) within a single task attempt, which the E1 pilot's quota-exhaustion failures also illustrate in a real run.

Full per-trial records: `E11_failure_recovery.json`
