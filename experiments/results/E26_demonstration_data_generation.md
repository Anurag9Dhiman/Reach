# E26: Demonstration Data Generation

Generated: 2026-09-28T15:06:31.977783+00:00

## Config

- **acs**: real (analyzes CollectiveOS/data/{nav_runs,demonstrations}/ from this session's real runs)
- **source_experiments**: E1, E2 (and E29, if run before this)

## Metrics

- **total_attempts_recorded**: 44
- **attempts_by_status**:
  - **error**: 30
  - **done**: 6
  - **max_iter**: 8
- **demo_eligible_attempts**: 14
- **demonstration_files_saved**: 14
- **demo_capture_rate_of_eligible**: 1.0
- **demo_capture_rate_of_all_attempts**: 0.3181818181818182
- **trajectory_length_distribution**: [0, 20, 1, 18, 20, 4, 20, 20, 5, 20, 1, 20, 0, 20]
- **action_type_diversity**:
  - **spotlight**: 115
  - **key_press**: 21
  - **type_text**: 15
  - **click**: 17
  - **show_desktop**: 1
- **distinct_tasks_covered**: 11
- **successful_vs_unsuccessful_demos**: not distinguishable from saved demo files alone - the demo JSON doesn't store the run's final status, only task/steps/demos (see notes)

## Notes

Of 44 real delegation attempts recorded today, only 14 reached a demo-eligible terminal state (done or max_iter) - the rest failed via an API-level exception (mostly Gemini free-tier 503/429, see E1's own findings) and were discarded by NavAgent._save_demos()'s early-return-on-exception path before any partial progress could be saved, even when steps had already accumulated. This IS the answer to 'can Reach generate useful demonstrations during normal delegation' under today's conditions: 14 demonstration file(s) resulted from 44 attempts. If this number is 0, E27/E28 (which need real demonstration data) are correspondingly blocked - see their own reports for how that was handled, not silently glossed over.

Full per-trial records: `E26_demonstration_data_generation.json`
