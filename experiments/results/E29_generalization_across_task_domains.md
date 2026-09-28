# E29: Generalization Across Task Domains

Generated: 2026-09-28T15:06:22.819318+00:00

## Config

- **acs**: real (live CollectiveOS + Gemini Navigation Agent)
- **par_planner**: GeminiPlanner (gemini-3.1-flash-lite)
- **domains**: ['industrial_inspection', 'laboratory_measurement', 'inventory_management', 'machine_maintenance', 'office_document_interaction']
- **scope_note**: domains are task-phrasing variations against the same MockRobot stand-in, not genuinely different physical hardware - see module docstring

## Metrics

- **success_rate**: 0.0
- **per_domain**:
  - **industrial_inspection**:
    - **success**: False
    - **delegations**: 0
  - **laboratory_measurement**:
    - **success**: False
    - **delegations**: 1
  - **inventory_management**:
    - **success**: False
    - **delegations**: 0
  - **machine_maintenance**:
    - **success**: False
    - **delegations**: 0
  - **office_document_interaction**:
    - **success**: False
    - **delegations**: 0

## Notes

PAR interface and safety kernel were unchanged across all 5 domains by construction, so this measures whether the real ACS/planner handle varied task vocabulary consistently. 4 of 5 domains failed with ServerError 503 ("model currently experiencing high demand") on PAR own gemini-3.1-flash-lite planner call, persisting across 3 attempts per domain with increasing backoff (up to 90s) - this is a genuine, sustained external Gemini service degradation during this testing window, not a per-minute rate limit (which recovers within a minute, see E9/E10/E19 earlier the same day) and not the daily gemini-3.6-flash cap (a different model). laboratory_measurement got past the planner and reached a real delegation, but the overall task still did not reach completion within max_steps. Given the sustained external outage, this experiment could not get a clean signal in this session - the honest conclusion is inconclusive due to external service degradation, not a finding about cross-domain generalization itself.

Full per-trial records: `E29_generalization_across_task_domains.json`
