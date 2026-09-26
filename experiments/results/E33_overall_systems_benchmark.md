# E33: Overall Systems Benchmark

Generated: 2026-09-26T23:35:42.978696+00:00

## Config

- **aggregates**: ['E1', 'E11', 'E12', 'E13', 'E14', 'E15', 'E16', 'E17', 'E18', 'E20', 'E21', 'E22', 'E23', 'E24', 'E25', 'E3', 'E30', 'E31', 'E32', 'E4', 'E5', 'E6', 'E7', 'E8', 'E8b']
- **note**: run last; aggregates other experiments' results rather than running new trials

## Metrics

- **status_summary**:
  - **total_experiments**: 33
  - **completed**: 20
  - **blocked**: 5
  - **not_yet_run**: 8
  - **completed_ids**: ['E1', 'E11', 'E12', 'E13', 'E14', 'E15', 'E20', 'E21', 'E22', 'E24', 'E25', 'E3', 'E30', 'E31', 'E32', 'E4', 'E5', 'E6', 'E7', 'E8']
  - **blocked_ids**: ['E16', 'E17', 'E18', 'E23', 'E8b']
- **primary_metrics**:
  - **task_success_rate**:
    - **value**: 0.0
    - **source**: E1
    - **caveat**: 0/12 in the pilot run, but 100% of failures trace to exhausted free-tier quota/transient overload, not the architecture - see E1's own report. Needs a clean re-run once quota resets for a trustworthy number here.
  - **delegation_precision_recall**:
    - **value**: None
    - **source**: E9/E19
    - **caveat**: not yet run (blocked on quota)
  - **unsafe_execution_rate**:
    - **value**: 0.0
    - **source**: E5 (full safety kernel config)
  - **recovery_rate**:
    - **value**: 1.0
    - **source**: E11
    - **caveat**: measured as retry-level recovery, not within-single-run_task recovery - see E11's notes
  - **human_escalation_behavior**:
    - **value**:
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
    - **source**: E8 (automated part only)
    - **caveat**: human response time/decision accuracy blocked - needs a real operator (see E23)
- **failure_taxonomy**:
  - **planner_failure**: True
  - **safety_kernel_denial**: True
  - **acs_side_failure**: True
  - **communication_failure**: True
  - **physical_control_failure**: True
  - **incorrect_result_accepted**: True

## Notes

The PDF's own primary-metrics line is truncated in the source document ('...RecoveryRate, HumanEs...') - the exact intended final metric list could not be confirmed and should be re-checked against the original PDF. This report aggregates what's measurable today: 20/33 experiments completed, 5/33 explicitly blocked (Webots install, human operator, or exhausted quota - see README.md's status table for which), 8/33 not yet attempted. A real statistical comparison against baselines with confidence intervals, and qualitative examples of representative episodes, both need the quota-blocked experiments (especially E1's clean re-run and E2) to exist first - this is an honest snapshot of current coverage, not the final benchmark result the PDF describes.

Full per-trial records: `E33_overall_systems_benchmark.json`
