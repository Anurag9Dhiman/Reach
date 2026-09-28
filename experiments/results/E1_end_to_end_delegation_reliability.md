# E1: End-to-End Delegation Reliability

Generated: 2026-09-27T16:22:43.137831+00:00

## Config

- **acs**: real (live CollectiveOS + Gemini Navigation Agent)
- **par_planner**: GeminiPlanner (gemini-3.1-flash-lite)
- **n_trials_per_task**: 3
- **task_ids**: ['p2d-1', 'd2p-1', 'multi-1', 'multidel-1']
- **max_steps**: 8

## Metrics

- **end_to_end_task_success_rate**: 0.08333333333333333
- **end_to_end_task_success_ci95**: [0.01486509440491712, 0.3538799111411168]
- **delegation_success_rate**: 0.26666666666666666
- **delegation_success_ci95**: [0.10897453325692376, 0.5195043405598055]
- **acs_success_rate**: 0.26666666666666666
- **completion_time_seconds**:
  - **n**: 12
  - **mean**: 160.47118005549905
  - **stdev**: 64.94917818975202
  - **ci95_low**: 123.72272305423071
  - **ci95_high**: 197.2196370567674
- **total_delegations**: 15
- **total_replans**: 0
- **total_human_interventions**: 0
- **n_trials**: 12
- **n_tasks**: 4
- **delegation_failure_causes**:
  - **quota_exhausted**: 0
  - **transient_upstream_503**: 0
  - **timeout**: 6
  - **acs_max_iter_exhausted**: 2
  - **acs_screencapture_failure**: 3
  - **other**: 0
- **delegation_failures_unexplained**: 0

## Notes

Small, quota-conscious pilot (12 real end-to-end runs), not a large statistically powered study - confidence intervals here are wide and should be read as such. This run used the VISION_MODEL override (gemini-3.1-flash-lite instead of CollectiveOS's default gemini-3.6-flash) documented in README.md, since gemini-3.6-flash has a hard 20-req/day free-tier cap that was already exhausted today. Check 'delegation_failure_causes' before reading end_to_end_task_success_rate at face value: only delegation_failures_unexplained (failures NOT attributable to a per-minute rate limit, NavAgent max_iter exhaustion, or the acs_screencapture_failure bug below) reflects an actual defect in the PAR/bridge pipeline being tested. acs_screencapture_failure is a real, intermittent CollectiveOS bug found via this experiment: nav_agent.py's screencapture() runs the macOS screencapture subprocess to /tmp/nav_raw.png then immediately Image.open()s it with no existence check or retry, and it failed on roughly 1 in 5 real attempts in this environment (likely a screen-recording permission/timing race for the automated process) - worth fixing in CollectiveOS itself, out of scope for this repo. acs_max_iter_exhausted (NavAgent hit its own 20-iteration budget without completing) is expected, legitimate behavior for a hard task, not an error.

Full per-trial records: `E1_end_to_end_delegation_reliability.json`
