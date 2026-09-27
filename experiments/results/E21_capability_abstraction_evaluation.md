# E21: Capability Abstraction Evaluation

Generated: 2026-09-26T23:30:10.333449+00:00

## Config

- **example_task**: look up today's date and log it in a note
- **note**: structural comparison only - see module docstring for why a live planner comparison is out of scope today

## Metrics

- **high_level**:
  - **n_capabilities_exposed_to_planner**: 1
  - **total_input_schema_fields**: 1
  - **calls_needed_for_example_task**: 1
- **low_level**:
  - **n_capabilities_exposed_to_planner**: 5
  - **total_input_schema_fields**: 6
  - **calls_needed_for_example_task**: 5
  - **example_decomposition**: ['screenshot', 'click', 'type_text', 'screenshot', 'click']
- **call_count_ratio_low_to_high**: 5.0

## Notes

The high-level interface exposes 1 capability with 1 parameter to the planner and needs 1 call for the example task; the low-level interface exposes 5 capabilities with 6 parameters total and needs 5 calls for the same task (a hand-authored minimum decomposition, not planner-generated). This supports the PDF's premise directionally (fewer capabilities, fewer parameters, fewer calls per task under the high-level interface) but does not measure planning latency or invalid-action rate under a live planner, which needs real LLM calls currently blocked by the exhausted Gemini quota - see README.md.

Full per-trial records: `E21_capability_abstraction_evaluation.json`
