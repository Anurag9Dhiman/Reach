# E5: Safety Kernel Ablation

Generated: 2026-09-26T23:13:33.229830+00:00

## Config

- **configs_compared**: ['no_kernel', 'admission_only', 'admission_and_policy']
- **scenario_battery**: ['safe_detect', 'workspace_violation', 'collision', 'unsupported_profile', 'high_risk_computer', 'emergency_stop_engaged']
- **profile**: simulation, approval_required=True
- **evaluation_method**: direct SafetyKernel.admit()/check() calls, not a full Runtime round-trip (see module docstring)

## Metrics

- **no_kernel**:
  - **unsafe_execution_rate**: 1.0
  - **correct_denial_rate**: 0.0
  - **correct_escalation_rate**: 0.0
  - **false_rejection_rate**: 0.0
  - **task_recovery**: True
- **admission_only**:
  - **unsafe_execution_rate**: 0.6
  - **correct_denial_rate**: 0.5
  - **correct_escalation_rate**: 0.0
  - **false_rejection_rate**: 0.0
  - **task_recovery**: True
- **admission_and_policy**:
  - **unsafe_execution_rate**: 0.0
  - **correct_denial_rate**: 1.0
  - **correct_escalation_rate**: 1.0
  - **false_rejection_rate**: 0.0
  - **task_recovery**: True
- **full_with_human_escalation**:
  - **executes_with_no_human_present**: False
  - **executes_with_human_approval**: True

## Notes

admission_only correctly blocks the unsupported-profile and emergency-stop scenarios (both are admission-stage checks) but not workspace/collision/risk-escalation (policy-stage checks it deliberately bypasses) - this isolates exactly what each stage contributes. no_kernel blocks nothing (unsafe_execution_rate=1.0). Only 3 configs are compared, not 4: Runtime resolves an ESCALATE outcome to ALLOW/DENY based on the human_approval callback *before* anything is executed - escalation resolution is a property of Runtime + the human callback, not of the SafetyKernel itself, so a 'full kernel with human escalation available' config would test the same kernel decision as admission_and_policy with a different human callback bolted on top - see E8 for that. All 3 configs still reach task_complete after a denial mid-task (task_recovery=True).

Full per-trial records: `E5_safety_kernel_ablation.json`
