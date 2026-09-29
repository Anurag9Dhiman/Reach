# E10: Delegation Decision Ablation

Generated: 2026-09-27T15:40:43.938410+00:00

## Config

- **acs**: none - single-shot decision classification, no task execution
- **conditions**: ['task_description_only', 'task_plus_observation', 'task_plus_observation_plus_capability_descriptions', 'task_plus_observation_plus_capabilities_plus_risk_info']
- **task_ids**: ['phys-2', 'dig-1', 'p2d-1', 'd2p-1', 'multi-1', 'multidel-1']
- **model**: gemini-3.1-flash-lite

## Metrics

- **task_description_only**:
  - **delegation_precision**: 1.0
  - **delegation_recall**: 0.6
  - **overall_correct_rate**: 0.6666666666666666
  - **unnecessary_delegations**: 0
  - **missed_delegations**: 2
  - **n_errored**: 0
- **task_plus_observation**:
  - **delegation_precision**: 1.0
  - **delegation_recall**: 0.6
  - **overall_correct_rate**: 0.6666666666666666
  - **unnecessary_delegations**: 0
  - **missed_delegations**: 2
  - **n_errored**: 0
- **task_plus_observation_plus_capability_descriptions**:
  - **delegation_precision**: 1.0
  - **delegation_recall**: 0.6
  - **overall_correct_rate**: 0.6666666666666666
  - **unnecessary_delegations**: 0
  - **missed_delegations**: 2
  - **n_errored**: 0
- **task_plus_observation_plus_capabilities_plus_risk_info**:
  - **delegation_precision**: 1.0
  - **delegation_recall**: 0.6
  - **overall_correct_rate**: 0.6666666666666666
  - **unnecessary_delegations**: 0
  - **missed_delegations**: 2
  - **n_errored**: 0

## Notes

Built a standalone minimal Gemini caller for this experiment rather than reusing GeminiPlanner directly, since GeminiPlanner always sends the full observation + full capability descriptions (matching condition 3 exactly) and has no built-in way to withhold information for conditions 1, 2, or 4. Two real findings, one expected and one not: (1) conditions 2, 3, and 4 are identical in every single per-task decision - adding capability descriptions and an explicit risk annotation to use_computer changed nothing here, at least for a name as self-descriptive as use_computer; only adding the observation (condition 1 -> 2) changed any decisions, and only for which non-delegation skill got picked, not delegation correctness itself. (2) A real limitation in this experiment own ground truth, not the model: p2d-1 and multi-1 explicitly ask for a physical step before the digital one (inspect ... then use the computer), so the model choosing inspect/detect as its single first action is plausibly correct sequencing, not a missed delegation - but this single-shot design scores delegate-iff-requires_computer with no notion of step order, so both are counted as missed_delegations here. A full multi-step run (like E9 own) is the fairer test for physical-then-digital tasks; this ablation clean signal is really about dig-1/d2p-1/multidel-1 (digital-first tasks), where all 4 conditions correctly delegate immediately.

Full per-trial records: `E10_delegation_decision_ablation.json`
