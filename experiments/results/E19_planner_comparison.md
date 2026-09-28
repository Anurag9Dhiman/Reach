# E19: Planner Comparison

Generated: 2026-09-27T15:34:34.758970+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, mode=SUCCESS)
- **planners_compared**: ['rule_based', 'gemini']
- **note**: GeminiPlanner vs RuleBasedPlanner only - no second LLM key available, see README.md
- **n_tasks**: 13

## Metrics

- **rule_based**:
  - **task_success_rate**: 0.0
  - **correct_delegation_rate**: 0.23076923076923078
  - **crash_rate**: 0.15384615384615385
  - **total_replans**: 0
  - **mean_latency_seconds**: 0.0002211666142102331
- **gemini**:
  - **task_success_rate**: 0.6923076923076923
  - **correct_delegation_rate**: 0.6923076923076923
  - **crash_rate**: 0.3076923076923077
  - **total_replans**: 0
  - **mean_latency_seconds**: 7.1496466667718215

## Notes

The Reach architecture (safety kernel, delegation plumbing, ACS bridge) is planner-agnostic by construction, but its *effectiveness* is not: rule_based's task_success_rate is expected near 0 because RuleBasedPlanner cannot parse natural-language goals for delegation intent or produce real move coordinates (see module docstring), while gemini's is expected much higher. This is the honest answer to the RQ - Reach 'works' independently of which planner is plugged in only in the sense that it doesn't crash or misbehave unsafely; task-level effectiveness genuinely depends on the planner's own reasoning capability. token_usage was not tracked - GeminiPlanner does not currently expose response.usage_metadata to its caller, which would need a small addition to par.core.gemini_planner to measure directly.

Full per-trial records: `E19_planner_comparison.json`
