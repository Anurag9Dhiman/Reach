# E22: Failure Taxonomy Analysis

Generated: 2026-09-26T23:30:55.473334+00:00

## Config

- **categories**: ['planner_failure', 'safety_kernel_denial', 'acs_side_failure', 'communication_failure', 'physical_control_failure', 'incorrect_result_accepted']

## Metrics

- **categories_tested**: 6
- **correctly_reproduced**: 6
- **per_category**:
  - **planner_failure**: True
  - **safety_kernel_denial**: True
  - **acs_side_failure**: True
  - **communication_failure**: True
  - **physical_control_failure**: True
  - **incorrect_result_accepted**: True

## Notes

The PDF's 10 categories collapse to 6 distinguishable ones from PAR's side of the PAR/ACS boundary: 'ACS perception failure', 'ACS planning failure', and 'GUI grounding/execution failure' are all invisible to PAR - it only sees 'the ACS call failed or returned something,' grouped here as acs_side_failure. 'incorrect_result_accepted' is not one of the PDF's original 10 but is the single most important finding this taxonomy surfaces: PAR has no semantic verification of ACS results, so a confidently-wrong answer is indistinguishable from a correct one (see e31 for the dedicated experiment on this). Frequency-in-production analysis (how often each category actually occurs, and how the distribution shifts with task complexity, per the PDF's ask) needs real usage data - this only confirms each category is individually reproducible and correctly surfaced by PAR's telemetry.

Full per-trial records: `E22_failure_taxonomy_analysis.json`
