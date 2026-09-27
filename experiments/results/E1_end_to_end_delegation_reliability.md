# E1: End-to-End Delegation Reliability

Generated: 2026-09-26T23:15:46.383181+00:00

## Config

- **acs**: real (live CollectiveOS + Gemini Navigation Agent)
- **par_planner**: GeminiPlanner (gemini-3.1-flash-lite)
- **n_trials_per_task**: 3
- **task_ids**: ['p2d-1', 'd2p-1', 'multi-1', 'multidel-1']
- **max_steps**: 8

## Metrics

- **end_to_end_task_success_rate**: 0.0
- **end_to_end_task_success_ci95**: [-2.1025014877572557e-17, 0.24249400665524073]
- **delegation_success_rate**: 0.0
- **delegation_success_ci95**: [-2.1025014877572557e-17, 0.24249400665524073]
- **acs_success_rate**: 0.0
- **completion_time_seconds**:
  - **n**: 12
  - **mean**: 85.35831643058434
  - **stdev**: 52.14014617987582
  - **ci95_low**: 55.857251546697356
  - **ci95_high**: 114.85938131447132
- **total_delegations**: 12
- **total_replans**: 0
- **total_human_interventions**: 0
- **n_trials**: 12
- **n_tasks**: 4
- **delegation_failure_causes**:
  - **quota_exhausted**: 7
  - **transient_upstream_503**: 4
  - **timeout**: 1
  - **other**: 0
- **delegation_failures_attributable_to_gemini_free_tier**: 12
- **delegation_failures_unexplained**: 0
- **notes_on_failure_causes**: see notes

## Notes

IMPORTANT CAVEAT discovered after this run: 0/12 end-to-end task success, but this pilot ran into the shared GEMINI_API_KEY free-tier quota partway through - 7 of 12 delegation attempts failed with a hard 429 RESOURCE_EXHAUSTED (quota exhausted for the day), 4 with a transient 503 "model experiencing high demand", and 1 timed out. Zero failures (0/12) were unexplained or attributable to a defect in the PAR/CollectiveOS pipeline itself - every single failure traces to external Gemini free-tier flakiness/exhaustion, not the architecture being tested. This IS still a real, honest finding: PAR currently treats any delegation failure (transient or not) as a genuine execution failure and stops the task rather than retrying (see e04 and the paper Discussion) - a retry-with-backoff on 503/429 specifically would likely have recovered several of these trials. A clean re-run for a true reliability signal needs to wait for the daily quota to reset (or a paid Gemini key) - this pilot should be treated as evidence of a quota/retry-policy gap, not evidence that end-to-end delegation itself does not work (see the separate, successful live delegation from the earlier session, and e03/e04 in this batch, which succeeded because they use a fake ACS or ran before the quota was exhausted).

Full per-trial records: `E1_end_to_end_delegation_reliability.json`
