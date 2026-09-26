# E6: Evaluation of the Four Safety Outcomes

Generated: 2026-09-26T23:14:42.697536+00:00

## Config

- **evaluation_method**: direct SafetyKernel.admit()/check() calls
- **profile**: {'name': 'simulation', 'workspace': {'x': (-2.0, 2.0), 'y': (-2.0, 2.0), 'z': (0.0, 2.0)}, 'max_velocity': 2.0, 'action_timeout_seconds': 0.5, 'approval_required': True, 'collision_margin': 0.3}
- **n_scenarios**: 10

## Metrics

- **decision_accuracy**: 1.0
- **confusion_matrix**:
  - **allow**:
    - **allow**: 3
    - **modify**: 0
    - **deny**: 0
    - **escalate**: 0
  - **modify**:
    - **allow**: 0
    - **modify**: 2
    - **deny**: 0
    - **escalate**: 0
  - **deny**:
    - **allow**: 0
    - **modify**: 0
    - **deny**: 3
    - **escalate**: 0
  - **escalate**:
    - **allow**: 0
    - **modify**: 0
    - **deny**: 0
    - **escalate**: 2

## Notes

Uses a custom profile (action_timeout_seconds=0.5s, not either built-in profile) specifically to make MODIFY reachable within the workspace bounds - see module docstring. All 10 scenarios classified correctly in this run (DecisionAccuracy=1.0), which is expected: this is deterministic logic being exercised with scenarios chosen to clearly fall into one class each, not a noisy real-world classification problem. The confusion matrix is included as the PDF requests, even though it's necessarily diagonal for a correct, deterministic implementation - its value is in what it would reveal if a future change to the policy logic broke one of these boundary conditions.

Full per-trial records: `E6_evaluation_of_the_four_safety_outcomes.json`
