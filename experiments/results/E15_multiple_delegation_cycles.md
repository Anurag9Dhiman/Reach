# E15: Multiple Delegation Cycles

Generated: 2026-09-26T23:28:20.347157+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, each delegation independently fails with probability 0.15)
- **planner**: scripted (fixed pattern per condition)
- **n_trials_per_pattern**: 30
- **random_seed**: 42
- **patterns**: {'P-D-P': 'PDP', 'P-D-P-D-P': 'PDPDP', 'P-D-P-D-P-D': 'PDPDPD'}

## Metrics

- **P-D-P**:
  - **n_delegations**: 1
  - **success_rate**: 0.7666666666666667
  - **observed_failure_rate**: 0.23333333333333334
  - **theoretical_failure_rate**: 0.15000000000000002
  - **accumulated_latency_seconds**:
    - **n**: 30
    - **mean**: 0.00011767236719606444
    - **stdev**: 4.4705801745409543e-05
    - **ci95_low**: 0.00010167460149875222
    - **ci95_high**: 0.00013367013289337665
  - **total_incorrect_transitions**: 0
  - **total_replans**: 0
- **P-D-P-D-P**:
  - **n_delegations**: 2
  - **success_rate**: 0.7
  - **observed_failure_rate**: 0.3
  - **theoretical_failure_rate**: 0.2775000000000001
  - **accumulated_latency_seconds**:
    - **n**: 30
    - **mean**: 0.00013739580026594922
    - **stdev**: 2.997787457950639e-05
    - **ci95_low**: 0.0001266683556188884
    - **ci95_high**: 0.00014812324491301004
  - **total_incorrect_transitions**: 0
  - **total_replans**: 0
- **P-D-P-D-P-D**:
  - **n_delegations**: 3
  - **success_rate**: 0.6
  - **observed_failure_rate**: 0.4
  - **theoretical_failure_rate**: 0.3858750000000001
  - **accumulated_latency_seconds**:
    - **n**: 30
    - **mean**: 0.00014397096674656495
    - **stdev**: 3.0325312309968565e-05
    - **ci95_low**: 0.00013311919310439983
    - **ci95_high**: 0.00015482274038873008
  - **total_incorrect_transitions**: 0
  - **total_replans**: 0

## Notes

observed_failure_rate tracks theoretical_failure_rate (1-(1-p)^n_delegations) reasonably closely across all three patterns, confirming task failure probability compounds with delegation count purely from exposure to independent per-call failures - not from any change in PAR's own logic as the pattern grows. incorrect_transitions is 0 throughout (the scripted sequence is followed exactly every time), which is expected and confirms the harness itself is not introducing noise into this measurement.

Full per-trial records: `E15_multiple_delegation_cycles.json`
