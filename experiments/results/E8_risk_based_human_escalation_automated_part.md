# E8: Risk-Based Human Escalation (automated part)

Generated: 2026-09-26T23:18:41.191900+00:00

## Config

- **acs**: none - direct SafetyKernel evaluation
- **profiles_compared**: ['approval_required=True', 'approval_required=False']
- **n_tasks**: 6

## Metrics

- **approval_required=True**:
  - **precision**: 0.5
  - **recall**: 1.0
  - **false_escalation_rate**: 1.0
  - **tp**: 3
  - **fp**: 3
  - **fn**: 0
  - **tn**: 0
- **approval_required=False**:
  - **precision**: nan
  - **recall**: 0.0
  - **false_escalation_rate**: 0.0
  - **tp**: 0
  - **fp**: 0
  - **fn**: 3
  - **tn**: 3

## Notes

use_computer carries one fixed RiskLevel.HIGH regardless of task content, so escalation is a single profile-level on/off switch, not risk-sensitive to what the task actually says. Under approval_required=True this shows perfect recall (1.0 - nothing risky ever slips through) but weak precision (0.5) and a high false escalation rate (1.0) - every low-risk read/search/edit gets escalated too. Under approval_required=False, precision/recall invert (nothing escalates, including the genuinely risky tasks). This is an honest limitation, not a bug: closing it would need content-based risk classification for use_computer (e.g. keyword-based tiering like CollectiveOS's own tool_registry.py already does), which does not exist in PAR today.

Full per-trial records: `E8_risk_based_human_escalation_automated_part.json`
