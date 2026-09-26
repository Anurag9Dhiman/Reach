# E20: ACS Interoperability

Generated: 2026-09-26T23:29:43.459727+00:00

## Config

- **acs_a**: fake, echoes task text, no delay
- **acs_b**: fake, fixed different-style reply, 0.2s delay
- **par_changes_between_backends**: none - only CollectiveOSBridge.ws_url/api_token differ

## Metrics

- **acs_a_success**: True
- **acs_b_success**: True
- **acs_a_latency_seconds**: 0.012112666998291388
- **acs_b_latency_seconds**: 0.21291841700440273
- **same_par_code_used_for_both**: True
- **planner_or_safety_kernel_changes_required**: 0
- **protocol_compatible_with_both**: True

## Notes

Both backends work through the identical PAR code path (ComputerAugmentedRobot -> CollectiveOSBridge -> the same use_computer capability), confirming the interface is a real abstraction rather than a Pulse-CollectiveOS-specific integration - the only thing that changed between runs is which URL the bridge points at. This is a structural interoperability test (protocol compatibility), not a test of two independently-built real computer-use agents, which is out of scope here.

Full per-trial records: `E20_acs_interoperability.json`
