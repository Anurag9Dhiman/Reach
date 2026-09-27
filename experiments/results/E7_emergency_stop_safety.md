# E7: Emergency-Stop Safety

Generated: 2026-09-26T23:17:37.827853+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge - a call log proves the ACS was never actually contacted while e-stopped)
- **profile**: simulation, approval_required=False (isolating e-stop from escalation)

## Metrics

- **all_actions_prevented_while_engaged**: True
- **acs_never_contacted_while_engaged**: True
- **recovers_after_clear**: True

## Notes

PAR's Runtime is synchronous and single-threaded per step, so 'before planning' vs 'after planning' vs 'immediately before execution' collapse to the same admit()-time emergency-stop check within one _step() call - what's actually tested here is *which step in the sequence* e-stop is engaged at, including confirming the ACS's fake bridge call log stays empty for any step blocked while e-stopped (not just that the ActionResult reports failure).

Full per-trial records: `E7_emergency_stop_safety.json`
