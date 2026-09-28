# E2: Mixed Physical-Digital Task Benchmark

Generated: 2026-09-27T16:32:08.776044+00:00

## Config

- **acs**: real (live CollectiveOS + Gemini Navigation Agent)
- **par_planner**: GeminiPlanner (gemini-3.1-flash-lite)
- **n_trials_per_task**: 1
- **n_tasks**: 13
- **max_steps**: 8

## Metrics

- **overall_success_rate**: 0.3076923076923077
- **n_tasks**: 13
- **by_category**:
  - **physical_only**:
    - **n**: 3
    - **success_rate**: 1.0
    - **mean_delegations**: 0.0
  - **digital_only**:
    - **n**: 2
    - **success_rate**: 0.5
    - **mean_delegations**: 1.0
  - **physical_to_digital**:
    - **n**: 2
    - **success_rate**: 0.0
    - **mean_delegations**: 1.0
  - **digital_to_physical**:
    - **n**: 2
    - **success_rate**: 0.0
    - **mean_delegations**: 0.0
  - **multi_stage**:
    - **n**: 2
    - **success_rate**: 0.0
    - **mean_delegations**: 0.0
  - **multi_delegation**:
    - **n**: 2
    - **success_rate**: 0.0
    - **mean_delegations**: 0.0
- **by_difficulty**:
  - **1**:
    - **n**: 4
    - **success_rate**: 0.5
  - **2**:
    - **n**: 6
    - **success_rate**: 0.16666666666666666
  - **3**:
    - **n**: 3
    - **success_rate**: 0.3333333333333333

## Notes

1 trial per task (14 real end-to-end runs), not repeated trials per task - this is a coverage benchmark across the 6 categories x 3 difficulty levels the task library was authored to span, not a reliability study (see E1 for repeated-trials reliability on a smaller task subset). A single real Gemini/CollectiveOS call chain is inherently noisy (see E1's transient-503 findings), so any one task's pass/fail here is a single data point, not a stable rate.

Full per-trial records: `E2_mixed_physical_digital_task_benchmark.json`
