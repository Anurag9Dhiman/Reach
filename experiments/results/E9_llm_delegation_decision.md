# E9: LLM Delegation Decision

Generated: 2026-09-27T15:31:23.957931+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, mode=SUCCESS - testing planner decision, not ACS execution)
- **planner**: GeminiPlanner (gemini-3.1-flash-lite) - the only real LLM planner available, see README.md
- **n_tasks**: 13

## Metrics

- **delegation_precision**: 1.0
- **delegation_recall**: 1.0
- **classification_counts**:
  - **correct_physical_execution**: 3
  - **correct_delegation**: 7
  - **errored**: 3
- **n_tasks**: 13
- **n_errored**: 3

## Notes

Single LLM (GeminiPlanner), not the PDF's intended multi-planner comparison - no second LLM key is available in this environment. Repeat across 'different LLM planners and task difficulties' per the PDF's own ask would need e.g. an Anthropic key to add a genuinely different model.

Full per-trial records: `E9_llm_delegation_decision.json`
