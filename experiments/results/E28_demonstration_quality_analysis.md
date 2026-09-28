# E28: Demonstration Quality Analysis

Generated: 2026-09-28T15:06:32.000958+00:00

## Config

- **classification_method**: approximate cross-reference of demo file <-> nav_runs audit log by matching task text (no shared identifier exists between the two)
- **min_demos_required**: 3

## Metrics

- **n_demonstrations**: 14
- **classification_counts**:
  - **successful_and_efficient**: 5
  - **failed**: 7
  - **unknown**: 2
- **note**: safety_interrupted and human_corrected categories are not represented - the robot-facing endpoint has no HITL gate (see paper's Discussion), so no demo here was ever safety-interrupted or human-corrected by construction, not because none occurred

## Notes

Training separate imitation models per subset and comparing on held-out tasks (the PDF's full design) needs far more demonstrations per category than exist today to be meaningful - this reports the classification itself as the achievable first step, not a trained-model comparison. The demo/nav_runs cross-reference is approximate (matched by task text and closest timestamp, since the two files are written by different code paths with no shared run ID) - treat individual classifications as best-effort, not certain.

Full per-trial records: `E28_demonstration_quality_analysis.json`
