# E33: Overall Systems Benchmark

Generated: 2026-09-28T15:07:31.814417+00:00

## Config

- **aggregates**: ['E1', 'E10', 'E11', 'E12', 'E13', 'E14', 'E15', 'E16', 'E17', 'E18', 'E19', 'E2', 'E20', 'E21', 'E22', 'E23', 'E24', 'E25', 'E26', 'E27', 'E28', 'E29', 'E3', 'E30', 'E31', 'E32', 'E33', 'E4', 'E5', 'E6', 'E7', 'E8', 'E8b', 'E9']
- **note**: run last; aggregates other experiments' results rather than running new trials

## Metrics

- **status_summary**:
  - **total_experiments**: 33
  - **completed**: 28
  - **blocked**: 5
  - **not_yet_run**: 0
  - **completed_ids**: ['E1', 'E10', 'E11', 'E12', 'E13', 'E14', 'E15', 'E19', 'E2', 'E20', 'E21', 'E22', 'E24', 'E25', 'E26', 'E27', 'E28', 'E29', 'E3', 'E30', 'E31', 'E32', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9']
  - **blocked_ids**: ['E16', 'E17', 'E18', 'E23', 'E8b']
- **primary_metrics**:
  - **task_success_rate**:
    - **value**: 0.08333333333333333
    - **source**: E1
    - **caveat**: small pilot (12 trials) - see E1's own report for its failure-cause breakdown (quota/503/max_iter/screencapture-bug/unexplained) before reading this number at face value.
  - **delegation_precision_recall**:
    - **value**:
      - **precision**: 1.0
      - **recall**: 1.0
    - **source**: E9
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

The PDF's own primary-metrics line is truncated in the source document ('...RecoveryRate, HumanEs...') - the exact intended final metric list could not be confirmed and should be re-checked against the original PDF. This report aggregates what's measurable today: 28/33 experiments completed, 5/33 explicitly blocked (Webots install, human operator, or exhausted quota - see README.md's status table for which), 0/33 not yet attempted. A real statistical comparison against baselines with confidence intervals, and qualitative examples of representative episodes, both need the quota-blocked experiments (especially E1's clean re-run and E2) to exist first - this is an honest snapshot of current coverage, not the final benchmark result the PDF describes.

Full per-trial records: `E33_overall_systems_benchmark.json`
