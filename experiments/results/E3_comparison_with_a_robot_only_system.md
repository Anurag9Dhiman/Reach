# E3: Comparison with a Robot-Only System

Generated: 2026-09-26T23:09:17.689641+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, mode=SUCCESS)
- **planner**: GeminiPlanner (gemini-3.1-flash-lite), both arms
- **n_trials_per_task**: 2
- **task_ids**: ['phys-2', 'dig-1', 'p2d-1', 'd2p-1']

## Metrics

- **robot_only**:
  - **label**: robot_only
  - **overall_success_rate**: 0.375
  - **digital_task_success_rate**: 0.16666666666666666
  - **physical_only_success_rate**: 1.0
  - **physical_only_latency**:
    - **n**: 2
    - **mean**: 5.247775374999037
    - **stdev**: 4.086216823074401
    - **ci95_low**: -0.41543220999010355
    - **ci95_high**: 10.910982959988178
  - **failed_attempts**: 5
  - **unresolved_digital_subtasks**: 6
  - **n_trials**: 8
- **reach**:
  - **label**: reach
  - **overall_success_rate**: 0.625
  - **digital_task_success_rate**: 0.5
  - **physical_only_success_rate**: 1.0
  - **physical_only_latency**:
    - **n**: 2
    - **mean**: 7.238257520504703
    - **stdev**: 2.809854936156924
    - **ci95_low**: 3.3439972606708768
    - **ci95_high**: 11.13251778033853
  - **failed_attempts**: 3
  - **unresolved_digital_subtasks**: 3
  - **n_trials**: 8
- **digital_success_rate_delta**: 0.33333333333333337
- **physical_only_overhead_check**: no meaningful difference expected between arms on physical-only tasks - compare physical_only_latency and physical_only_success_rate above

## Notes

Robot-only's 'unresolved_digital_subtasks' counts every digital-task trial where use_computer was never called - not a planner mistake but a structural impossibility, since the capability isn't registered at all in that arm. digital_task_success_rate for robot-only is expected near 0 for any task whose completion genuinely requires the computer step; Reach's is the real test of whether the capability helps.

Full per-trial records: `E3_comparison_with_a_robot_only_system.json`
