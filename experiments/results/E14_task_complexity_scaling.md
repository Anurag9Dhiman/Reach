# E14: Task Complexity Scaling

Generated: 2026-09-26T23:27:46.042822+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, mode=SUCCESS)
- **planner**: scripted (fixed, known-correct sequence per level - not an LLM planner; see module docstring)
- **n_trials_per_level**: 3
- **levels**: ['1_physical_1_digital', '3_physical_1_digital', '5_physical_2_digital', 'multiple_transitions', 'multiple_delegation_cycles']

## Metrics

- **1_physical_1_digital**:
  - **success_rate**: 1.0
  - **completion_time_seconds**:
    - **n**: 3
    - **mean**: 0.00018490232954112193
    - **stdev**: 0.00010220675955398608
    - **ci95_low**: 6.924449326379522e-05
    - **ci95_high**: 0.00030056016581844866
  - **n_physical_actions**: 1
  - **n_digital_actions**: 1
  - **total_replans**: 0
  - **total_failures**: 0
- **3_physical_1_digital**:
  - **success_rate**: 1.0
  - **completion_time_seconds**:
    - **n**: 3
    - **mean**: 0.0001619026637248074
    - **stdev**: 9.415406013568737e-06
    - **ci95_low**: 0.00015124812881973888
    - **ci95_high**: 0.00017255719862987594
  - **n_physical_actions**: 3
  - **n_digital_actions**: 1
  - **total_replans**: 0
  - **total_failures**: 0
- **5_physical_2_digital**:
  - **success_rate**: 1.0
  - **completion_time_seconds**:
    - **n**: 3
    - **mean**: 0.0002311529970029369
    - **stdev**: 1.1289005605201732e-05
    - **ci95_low**: 0.00021837828456984593
    - **ci95_high**: 0.00024392770943602787
  - **n_physical_actions**: 5
  - **n_digital_actions**: 2
  - **total_replans**: 0
  - **total_failures**: 0
- **multiple_transitions**:
  - **success_rate**: 1.0
  - **completion_time_seconds**:
    - **n**: 3
    - **mean**: 0.00019000033110690614
    - **stdev**: 7.5770720119536296e-06
    - **ci95_low**: 0.00018142606695799576
    - **ci95_high**: 0.00019857459525581653
  - **n_physical_actions**: 3
  - **n_digital_actions**: 3
  - **total_replans**: 0
  - **total_failures**: 0
- **multiple_delegation_cycles**:
  - **success_rate**: 1.0
  - **completion_time_seconds**:
    - **n**: 3
    - **mean**: 0.00016511133192883184
    - **stdev**: 7.158998808069304e-06
    - **ci95_low**: 0.0001570101621464565
    - **ci95_high**: 0.0001732125017112072
  - **n_physical_actions**: 1
  - **n_digital_actions**: 4
  - **total_replans**: 0
  - **total_failures**: 0

## Notes

All levels succeed 100% by construction (a scripted, known-correct sequence against an always-succeeding fake ACS) - this measures whether the *pipeline itself* scales cleanly with more steps/delegations (completion time should grow roughly linearly with step count, which it does here), not whether a planner can correctly solve harder tasks. See E9/E10/E19 (blocked on quota) for the planner-reasoning side of task complexity.

Full per-trial records: `E14_task_complexity_scaling.json`
